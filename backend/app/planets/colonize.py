"""Kolonisierung: die ``colonize``-Mission gründet auf einer freien Zelle eine Kolonie.

Kernmechanik (Doku 03b §9: universell — ALLE Spieler können kolonisieren). Bei Ankunft
prüft ``resolve_colonize`` das Ziel (leer / nur Trümmer), das Kolonie-Limit und ob ein
Kolonieschiff dabei ist. Erfolg: neuer Planet (Typ/Temp/Felder aus der Position abgeleitet),
Zelle belegt, Start-Ressourcen (Config + mitgeführte Fracht), ein Kolonieschiff verbraucht.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import RESOURCE_KEYS, refresh_resources
from app.planets.derive import derive_planet, fields_max_for
from app.platform.balance import get_balance
from app.platform.models import Building, Fleet, Planet, Resource, Ship
from app.universe.service import occupy_cell

log = logging.getLogger("universe.colonize")


def colonize_check(
    occupant_type: str | None, planet_count: int, max_planets: int, colony_ships: int
) -> tuple[bool, str]:
    """Reine Entscheidung, ob eine Kolonisierung zulässig ist. Liefert (ok, grund)."""
    if colony_ships < 1:
        return False, "kein_kolonieschiff"
    if occupant_type in ("player", "npc"):
        return False, "besetzt"
    if planet_count >= max_planets:
        return False, "limit_erreicht"
    return True, "ok"


async def resolve_colonize(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Gründet bei Ankunft eine Kolonie am Zielort. Liefert eine kurze Zusammenfassung."""
    bal = get_balance()
    cfg = bal.data.get("colonization", {})
    g, s, p = fleet.target_galaxy, fleet.target_system, fleet.target_position
    ship_type = cfg.get("ship_type", "colony_ship")

    # Bestehender Planet an der Koordinate? (occupy/derive sind sonst sauber.)
    planet_here = (await session.execute(
        select(Planet).where(Planet.galaxy == g, Planet.system == s, Planet.position == p)
    )).scalar_one_or_none()

    from app.platform.models import UniverseCell
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == g, UniverseCell.system == s, UniverseCell.position == p
        )
    )).scalar_one_or_none()
    occupant = "player" if planet_here is not None else (cell.occupant_type if cell else None)

    planet_count = (await session.execute(
        select(func.count()).select_from(Planet).where(Planet.player_id == fleet.player_id)
    )).scalar_one()

    colony_ship_row = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet.id, Ship.type == ship_type, Ship.count > 0)
    )).scalars().first()
    colony_ships = colony_ship_row.count if colony_ship_row else 0

    # Kolonie-Limit (OHNE Heimatplanet): base_colonies + Astrophysik (+N/Stufe), hart bei max_colonies.
    # max_planets = 1 (Heimat) + Kolonien.
    from app.economy.service import get_research_levels
    research = await get_research_levels(session, fleet.player_id)
    reff = bal.data["research"].get("effects", {})
    base_colonies = int(cfg.get("base_colonies", 3))
    max_colonies = int(cfg.get("max_colonies", 20))
    per_level = int(reff.get("astrophysics_colonies_per_level", 1))
    colonies = min(max_colonies, base_colonies + per_level * int(research.get("astrophysics", 0)))
    max_planets = 1 + colonies
    ok, reason = colonize_check(occupant, int(planet_count), max_planets, colony_ships)
    if not ok:
        log.info("Kolonisierung @ %d:%d:%d abgelehnt: %s", g, s, p, reason)
        return {"ok": False, "reason": reason, "location": f"{g}:{s}:{p}"}

    # Planet gründen.
    derived = derive_planet(g, s, p)
    planet = Planet(
        player_id=fleet.player_id,
        galaxy=g, system=s, position=p,
        name=f"Kolonie {g}:{s}:{p}",
        planet_type=derived["planet_type"],
        temp_max=derived["temp_max"],
        fields_max=fields_max_for(g, s, p, is_homeworld=False),
        is_homeworld=False,
    )
    session.add(planet)
    await session.flush()
    await occupy_cell(session, g, s, p, "player", planet.id)

    # Start-Ressourcen = Config + mitgefuehrte Fracht.
    now = dt.datetime.now(dt.timezone.utc)
    base_res = cfg.get("colony_resources", {})
    cargo = fleet.cargo or {}
    for key in RESOURCE_KEYS:
        amount = float(base_res.get(key, 0)) + float(cargo.get(key, 0))
        session.add(Resource(planet_id=planet.id, type=key, amount=amount, rate=0.0, last_updated=now))
    for btype, level in (cfg.get("colony_buildings", {}) or {}).items():
        session.add(Building(planet_id=planet.id, type=btype, level=level))
    await session.flush()
    await refresh_resources(session, planet)

    # Kolonieschiff verbrauchen, Fracht abgeladen.
    colony_ship_row.count -= 1
    if colony_ship_row.count <= 0:
        await session.delete(colony_ship_row)
    fleet.cargo = {}

    log.info("Kolonie gegruendet @ %d:%d:%d (player=%s)", g, s, p, fleet.player_id)
    return {"ok": True, "location": f"{g}:{s}:{p}", "planet_id": str(planet.id)}
