"""Mining-Mission: Bergbauschiffe foerdern an einem Asteroidenfeld (Doku 03c).

Eine Flotte mit Mission ``mine`` fliegt zu einem Sektor; liegt dort ein Asteroidenfeld
(occupant 'asteroid_field'), foerdern die Bergbauschiffe Metall/Kristall als Fracht fuer die
Heimreise. Ertrag = Bergbauschiffe x Ertrag/Schiff x Feld-Reichtum, gedeckelt durch den
endlichen Restvorrat des Feldes UND die Frachtkapazitaet der Flotte. Das Feld erschoepft
(zehrt den Vorrat) und regeneriert lazy ueber die Zeit. Kein Feld am Ziel -> kein Ertrag.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import AsteroidField, Fleet, Ship
from app.universe.asteroids import mine_from_field, regen_field

log = logging.getLogger("universe.mining")


def mine_yield(miners: int, yield_per_miner: dict, capacity: float) -> dict[str, float]:
    """Reines Frachtdeckel-Primitiv: Ertrag = miners x yield_per_miner, gedeckelt durch die
    Frachtkapazitaet (Metall zuerst, dann Kristall). Reichtum/Restvorrat ignoriert
    -> ``mine_from_field`` (asteroids.py) ist die vollstaendige Foerder-Logik."""
    remaining = max(0.0, float(capacity))
    out: dict[str, float] = {"metal": 0.0, "crystal": 0.0}
    for key in ("metal", "crystal"):
        want = miners * float(yield_per_miner.get(key, 0))
        take = min(want, remaining)
        out[key] = round(take, 1)
        remaining -= take
    return out


def _cargo_capacity(ships: dict[str, int]) -> float:
    bal = get_balance()
    cap = 0.0
    for typ, count in ships.items():
        cfg = bal.ships.get(typ)
        if cfg:
            cap += cfg.get("cargo", 0) * count
    return cap


async def resolve_mine(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Foerdert Erz aus dem Asteroidenfeld am Zielort in die Flotten-Fracht.
    Liefert eine kurze Zusammenfassung (oder None ohne Bergbauschiffe)."""
    bal = get_balance()
    cfg = bal.data.get("mining", {})
    ship_type = cfg.get("ship_type", "miner")
    location = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"

    ships = {
        r.type: r.count
        for r in (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        if r.count > 0
    }
    miners = ships.get(ship_type, 0)
    if miners <= 0:
        return None

    field = (await session.execute(
        select(AsteroidField).where(
            AsteroidField.galaxy == fleet.target_galaxy,
            AsteroidField.system == fleet.target_system,
            AsteroidField.position == fleet.target_position,
        )
    )).scalar_one_or_none()

    if field is None:
        log.info("Mining @ %s -> kein Asteroidenfeld (%d Bergbauschiffe leer zurueck)", location, miners)
        return {"location": location, "mined": {"metal": 0.0, "crystal": 0.0}, "note": "kein_asteroidenfeld"}

    # Lazy-Regeneration vor der Foerderung anwenden.
    regen_field(field)

    gained, new_metal, new_crystal = mine_from_field(
        miners, cfg.get("yield_per_miner", {}), field.mult,
        field.metal_remaining, field.crystal_remaining, _cargo_capacity(ships),
    )
    field.metal_remaining = new_metal
    field.crystal_remaining = new_crystal

    cargo = dict(fleet.cargo or {})
    cargo["metal"] = round(cargo.get("metal", 0) + gained["metal"], 1)
    cargo["crystal"] = round(cargo.get("crystal", 0) + gained["crystal"], 1)
    fleet.cargo = cargo

    log.info("Mining @ %s [%s] -> %s (%d Bergbauschiffe, Rest m=%.0f k=%.0f)",
             location, field.richness, gained, miners, new_metal, new_crystal)
    return {
        "location": location,
        "richness": field.richness,
        "mined": gained,
        "remaining": {"metal": round(new_metal, 1), "crystal": round(new_crystal, 1)},
    }
