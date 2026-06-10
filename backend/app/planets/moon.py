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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import Planet, Resource

log = logging.getLogger("universe.moon")

RESOURCES = ("metal", "crystal", "deuterium")


async def moon_of(session: AsyncSession, planet_id) -> Planet | None:
    return (await session.execute(
        select(Planet).where(Planet.parent_planet_id == planet_id, Planet.planet_type == "moon")
    )).scalars().first()


async def moon_defense_support(session: AsyncSession, planet: Planet, bal) -> tuple[dict, int]:
    """Mond-Unterstuetzung beim Angriff auf den Planeten: (extra_defenses, shield_tech_bonus).

    Orbitalbatterie -> orbital_gun-Einheiten in die Verteidigung; Schildkuppel -> Schild-Tech-Bonus."""
    from app.economy.service import get_building_levels

    if planet is None or planet.planet_type == "moon":
        return {}, 0
    moon = await moon_of(session, planet.id)
    if moon is None:
        return {}, 0
    levels = await get_building_levels(session, moon.id)
    mcfg = bal.data["moon"]
    extra: dict[str, int] = {}
    ob = levels.get("orbital_battery", 0)
    if ob > 0:
        extra["orbital_gun"] = ob * int(mcfg["orbital_battery_units_per_level"])
    shield_bonus = levels.get("shield_dome_moon", 0) * int(mcfg["shield_dome_tech_per_level"])
    return extra, shield_bonus


def moon_chance(debris_metal: float, debris_crystal: float, cfg: dict) -> float:
    total = max(0.0, float(debris_metal)) + max(0.0, float(debris_crystal))
    return min(float(cfg["max_chance"]), total / float(cfg["value_per_chance"]))


async def maybe_form_moon(session: AsyncSession, planet: Planet, debris_metal: float, debris_crystal: float) -> bool:
    """Versucht (ein Wurf) einen Mond am Planeten zu bilden. True = Mond entstanden.

    Kein zweiter Mond, wenn schon einer existiert. Erzeugt eine Mond-Planet-Zeile + 0-Ressourcen."""
    if planet is None or planet.planet_type == "moon":
        return False
    mcfg = get_balance().data["moon"]
    if await moon_of(session, planet.id) is not None:
        return False
    chance = moon_chance(debris_metal, debris_crystal, mcfg)
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
