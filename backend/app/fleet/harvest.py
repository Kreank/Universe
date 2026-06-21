"""Recycler-Harvest: sammelt das Truemmerfeld am Zielort ein (Doku 04 / Trümmer-Loop).

Nach einem Kampf persistiert ``combat/service.py`` die Trümmer in ``universe_cells.debris_field``.
Eine Recycler-Flotte mit Mission ``recycle`` fliegt hin und liest sie ab; die eingesammelte
Menge ist durch die Frachtkapazität der Flotte begrenzt und landet als Fracht für die Heimreise.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import Fleet, Ship, UniverseCell

log = logging.getLogger("universe.harvest")


def harvest_split(debris: dict, capacity: float) -> tuple[dict[str, float], dict[str, float]]:
    """Reine Logik: füllt die Fracht (capacity) mit Trümmern, Metall zuerst, dann Kristall.

    Liefert (eingesammelt, rest) — beide als {metal, crystal}."""
    remaining = max(0.0, float(capacity))
    collected: dict[str, float] = {"metal": 0.0, "crystal": 0.0}
    for key in ("metal", "crystal"):
        avail = max(0.0, float(debris.get(key, 0)))
        take = min(avail, remaining)
        collected[key] = round(take, 1)
        remaining -= take
    rest = {
        "metal": round(max(0.0, float(debris.get("metal", 0)) - collected["metal"]), 1),
        "crystal": round(max(0.0, float(debris.get("crystal", 0)) - collected["crystal"]), 1),
    }
    return collected, rest


def _cargo_capacity(ships: dict[str, int]) -> float:
    bal = get_balance()
    cap = 0.0
    for typ, count in ships.items():
        cfg = bal.ships.get(typ)
        if cfg:
            cap += cfg.get("cargo", 0) * count
    return cap


async def resolve_harvest(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Sammelt das Trümmerfeld am Zielort in die Flotten-Fracht. Liefert eine kurze
    Zusammenfassung (oder None, wenn kein Trümmerfeld vorhanden)."""
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == fleet.target_galaxy,
            UniverseCell.system == fleet.target_system,
            UniverseCell.position == fleet.target_position,
        )
    )).scalar_one_or_none()
    if cell is None or not cell.debris_field:
        return None
    field = dict(cell.debris_field)
    if field.get("metal", 0) <= 0 and field.get("crystal", 0) <= 0:
        return None

    ships = {
        r.type: r.count
        for r in (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        if r.count > 0
    }
    capacity = _cargo_capacity(ships)
    collected, rest = harvest_split(field, capacity)

    cargo = dict(fleet.cargo or {})
    cargo["metal"] = round(cargo.get("metal", 0) + collected["metal"], 1)
    cargo["crystal"] = round(cargo.get("crystal", 0) + collected["crystal"], 1)
    fleet.cargo = cargo

    # Rest-Trümmer bleiben liegen (für weitere Recycler), sonst Feld leeren.
    cell.debris_field = rest if (rest["metal"] > 0 or rest["crystal"] > 0) else {}

    log.info(
        "Harvest @ %d:%d:%d -> eingesammelt %s, Rest %s",
        fleet.target_galaxy, fleet.target_system, fleet.target_position, collected, rest,
    )

    # Feedback an den Spieler: was wurde recycelt? (Tester-Feedback — vorher kam keine Meldung.)
    _m, _c = int(collected["metal"]), int(collected["crystal"])
    if _m or _c:
        try:
            from app.messaging.service import create_system_transmission
            loc = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
            rest_note = ""
            if rest["metal"] > 0 or rest["crystal"] > 0:
                rest_note = (
                    f" Frachtraum voll — {int(rest['metal']):,} Metall / {int(rest['crystal']):,} "
                    f"Kristall bleiben im Trümmerfeld.".replace(",", ".")
                )
            await create_system_transmission(
                session,
                player_id=fleet.player_id,
                subject=f"♻️ Recycling abgeschlossen ({loc})",
                body=(
                    f"Deine Recycler haben {_m:,} Metall und {_c:,} Kristall aus dem Trümmerfeld "
                    f"geborgen (bei Rückkehr gutgeschrieben).{rest_note}".replace(",", ".")
                ),
                ttype="system",
            )
        except Exception:  # noqa: BLE001 — Meldung darf den Harvest nie stören
            pass

    return {
        "location": f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}",
        "collected": collected,
        "remaining": rest,
    }
