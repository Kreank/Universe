"""Mining-Mission: Bergbauschiffe bauen im Zielsektor Erz ab (Doku 03c).

Eine Flotte mit Mission ``mine`` fliegt in einen Sektor; bei Ankunft fördern die Bergbauschiffe
Metall/Kristall (Ertrag je Schiff, gedeckelt durch die Frachtkapazität der Flotte) als Fracht
für die Heimreise. Kostet Sprit + Zeit + Flottenslot — eine aktive Wirtschafts-Tätigkeit.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import Fleet, Ship

log = logging.getLogger("universe.mining")


def mine_yield(miners: int, yield_per_miner: dict, capacity: float) -> dict[str, float]:
    """Reine Logik: Erz-Ertrag = miners * yield_per_miner, gedeckelt durch die Frachtkapazität
    (Metall zuerst, dann Kristall)."""
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
    """Fördert Erz in die Flotten-Fracht. Liefert eine kurze Zusammenfassung."""
    bal = get_balance()
    cfg = bal.data.get("mining", {})
    ship_type = cfg.get("ship_type", "miner")

    ships = {
        r.type: r.count
        for r in (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        if r.count > 0
    }
    miners = ships.get(ship_type, 0)
    if miners <= 0:
        return None

    gained = mine_yield(miners, cfg.get("yield_per_miner", {}), _cargo_capacity(ships))
    cargo = dict(fleet.cargo or {})
    cargo["metal"] = round(cargo.get("metal", 0) + gained["metal"], 1)
    cargo["crystal"] = round(cargo.get("crystal", 0) + gained["crystal"], 1)
    fleet.cargo = cargo

    log.info("Mining @ %d:%d:%d -> %s (%d Bergbauschiffe)",
             fleet.target_galaxy, fleet.target_system, fleet.target_position, gained, miners)
    return {
        "location": f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}",
        "mined": gained,
    }
