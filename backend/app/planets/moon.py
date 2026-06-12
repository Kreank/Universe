"""Mond-Entstehung aus Truemmerfeldern (OGame-Modell).

Nach einem Kampf AN einem Spieler-Planeten kann sich aus dem Truemmerfeld ein Mond bilden:
``chance = min(max_chance, truemmer_gesamt / value_per_chance)`` (Cap 20 %). Ein Mond ist
eine ``planets``-Zeile mit ``planet_type='moon'`` + ``parent_planet_id`` (gleiche Koordinate,
Besitzer = Planet-Besitzer), ohne Minen, mit wenigen Feldern (Mondbasis hebt sie). Er traegt
die Kriegsfuehrungs-Gebaeude (Phalanx, Sprungtor, Orbitalbatterie, Schildkuppel, Gravitationslabor).
"""
from __future__ import annotations

import logging
import random

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import Building, Defense, Planet, Resource, Ship

log = logging.getLogger("universe.moon")

RESOURCES = ("metal", "crystal", "deuterium")


async def moon_of(session: AsyncSession, planet_id) -> Planet | None:
    return (await session.execute(
        select(Planet).where(Planet.parent_planet_id == planet_id, Planet.planet_type == "moon")
    )).scalars().first()


async def moon_building_defense(session: AsyncSession, moon: Planet, owner_id, bal) -> tuple[dict, int]:
    """Verteidigungs-Beitrag der Mond-GEBAEUDE: (extra_defenses, shield_tech_bonus).

    Orbitalbatterie -> orbital_gun-Einheiten; Schildkuppel -> Schild-Tech-Bonus. Genutzt sowohl fuer
    die Unterstuetzung des Planeten (moon_defense_support) als auch fuer den DIREKTEN Mond-Angriff
    (resolve_attack mit target_type='moon')."""
    from app.economy.service import get_building_levels, get_research_levels

    if moon is None:
        return {}, 0
    levels = await get_building_levels(session, moon.id)
    mcfg = bal.data["moon"]
    eff = bal.data["research"]["effects"]
    research = await get_research_levels(session, owner_id)
    extra: dict[str, int] = {}
    ob = levels.get("orbital_battery", 0)
    if ob > 0:
        per = int(mcfg["orbital_battery_units_per_level"]) + int(research.get("gravitics", 0)) * int(eff.get("orbital_units_per_level", 0))
        extra["orbital_gun"] = ob * per
    shield_bonus = levels.get("shield_dome_moon", 0) * int(mcfg["shield_dome_tech_per_level"])
    return extra, shield_bonus


async def moon_defense_support(session: AsyncSession, planet: Planet, bal) -> tuple[dict, int]:
    """Mond-Unterstuetzung beim Angriff auf den PLANETEN: (extra_defenses, shield_tech_bonus)."""
    if planet is None or planet.planet_type == "moon":
        return {}, 0
    moon = await moon_of(session, planet.id)
    if moon is None:
        return {}, 0
    return await moon_building_defense(session, moon, planet.player_id, bal)


def moon_chance(debris_metal: float, debris_crystal: float, cfg: dict) -> float:
    total = max(0.0, float(debris_metal)) + max(0.0, float(debris_crystal))
    return min(float(cfg["max_chance"]), total / float(cfg["value_per_chance"]))


def moon_destroy_chance(n_deathstars: int, moon_fields: int, cfg: dict) -> float:
    """Mondzerstoerungs-Chance (03d): waechst mit der Zahl der Todessterne, sinkt mit der
    Mondgroesse (fields). Pure Funktion fuer Tuning/Tests."""
    if n_deathstars <= 0:
        return 0.0
    size_ref = float(cfg.get("size_ref_fields", 10))
    return min(
        float(cfg.get("chance_cap", 0.9)),
        n_deathstars * float(cfg.get("chance_per_deathstar", 0.15)) * (size_ref / max(1, int(moon_fields))),
    )


async def maybe_form_moon(session: AsyncSession, planet: Planet, debris_metal: float, debris_crystal: float) -> bool:
    """Versucht (ein Wurf) einen Mond am Planeten zu bilden. True = Mond entstanden.

    Kein zweiter Mond, wenn schon einer existiert. Erzeugt eine Mond-Planet-Zeile + 0-Ressourcen."""
    if planet is None or planet.planet_type == "moon":
        return False
    bal = get_balance()
    mcfg = bal.data["moon"]
    if await moon_of(session, planet.id) is not None:
        return False
    # Gravitationsforschung hebt die Entstehungs-Obergrenze.
    from app.economy.service import get_research_levels
    eff = bal.data["research"]["effects"]
    research = await get_research_levels(session, planet.player_id)
    cap = float(mcfg["max_chance"]) + int(research.get("gravitics", 0)) * float(eff.get("moon_chance_cap_per_level", 0.0))
    total = max(0.0, float(debris_metal)) + max(0.0, float(debris_crystal))
    chance = min(cap, total / float(mcfg["value_per_chance"]))
    if chance <= 0 or random.random() >= chance:
        return False

    moon = Planet(
        player_id=planet.player_id,
        galaxy=planet.galaxy, system=planet.system, position=planet.position,
        name=f"Mond {planet.galaxy}:{planet.system}:{planet.position}",
        planet_type="moon",
        parent_planet_id=planet.id,
        temp_max=planet.temp_max,
        fields_used=0,
        fields_max=int(mcfg["base_fields"]),
        is_homeworld=False,
    )
    session.add(moon)
    await session.flush()
    for k in RESOURCES:
        session.add(Resource(planet_id=moon.id, type=k, amount=0.0, rate=0.0))
    await create_system_transmission(
        session,
        player_id=planet.player_id,
        subject=f"🌑 Ein Mond ist entstanden ({planet.galaxy}:{planet.system}:{planet.position})",
        body=(f"Aus den Trümmern der Schlacht hat sich ein Mond bei {planet.name} gebildet — etwas Seltenes. "
              f"Bau eine Mondbasis, um darauf Sensorphalanx, Sprungtor und weitere Kriegsführungs-Anlagen zu errichten."),
        ttype="system",
    )
    log.info("Mond entstanden: player=%s @ %d:%d:%d chance=%.3f",
             planet.player_id, planet.galaxy, planet.system, planet.position, chance)
    return True


async def maybe_destroy_moon(session: AsyncSession, target_planet, n_deathstars: int, rng=random) -> dict | None:
    """03d — Todesstern-Mondzerstoerung (Belagerung). Ueberlebende Todessterne versuchen, den
    Mond des Ziel-Planeten zu zerstoeren. Chance ~ Anzahl Todessterne, SCHWERER bei groesserem
    Mond (fields_max); Rueckschlag-Risiko: Todessterne koennen beim Versuch selbst draufgehen.

    Liefert ``{destroyed, backfire, moon_name, owner_id}`` oder ``None`` (kein Mond/keine RIPs).
    Bei destroyed=True ist der Mond inkl. Gebaeude/Schiffe/Verteidigung/Ressourcen geloescht.
    Der Aufrufer zieht ``backfire`` von den ueberlebenden Todessternen ab.
    """
    if n_deathstars <= 0 or target_planet is None or getattr(target_planet, "planet_type", None) == "moon":
        return None
    moon = await moon_of(session, target_planet.id)
    if moon is None:
        return None
    cfg = get_balance().data["moon"].get("destruction", {})
    if not cfg.get("enabled", True):
        return None
    chance = moon_destroy_chance(n_deathstars, int(moon.fields_max), cfg)
    bf_chance = float(cfg.get("backfire_chance_per_deathstar", 0.04))
    backfire = sum(1 for _ in range(n_deathstars) if rng.random() < bf_chance)
    backfire = min(backfire, int(cfg.get("backfire_cap_per_attempt", n_deathstars)), n_deathstars)
    destroyed = rng.random() < chance
    result = {"destroyed": destroyed, "backfire": backfire, "moon_name": moon.name, "owner_id": moon.player_id}
    if destroyed:
        for M in (Building, Ship, Defense, Resource):
            await session.execute(delete(M).where(M.planet_id == moon.id))
        await session.delete(moon)
        log.info("Mond zerstoert: %s @ %d:%d:%d (RIPs=%d, Rueckschlag=%d)",
                 moon.name, moon.galaxy, moon.system, moon.position, n_deathstars, backfire)
    return result
