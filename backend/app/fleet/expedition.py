"""Expeditions-Mission: Langstrecken-Erkundung mit Zufalls-Fund (Doku 05 / 03c).

Eine Flotte mit Mission ``expedition`` fliegt in einen Sektor; bei Ankunft wird ein gewichteter
Zufalls-Ausgang gezogen: Ressourcen-Fund, gefundene Schiffe, nichts, oder eine Gefahr
(Schiffsverluste). Die reine Auswahl (``pick_outcome``) ist testbar; die Anwendung läuft im
Handler mit Session.
"""
from __future__ import annotations

import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import Fleet, Ship

log = logging.getLogger("universe.expedition")


def pick_outcome(outcomes: list[dict], roll: float) -> dict:
    """Reine Auswahl: ``roll`` in [0, summe_gewichte) -> der getroffene Ausgang."""
    acc = 0.0
    for o in outcomes:
        acc += float(o.get("weight", 0))
        if roll < acc:
            return o
    return outcomes[-1] if outcomes else {"type": "nothing"}


def _rand_range(rng: random.Random, span) -> int:
    if isinstance(span, (list, tuple)) and len(span) == 2:
        lo, hi = int(span[0]), int(span[1])
        return rng.randint(min(lo, hi), max(lo, hi))
    return int(span or 0)


async def resolve_expedition(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Zieht den Expeditions-Ausgang und wendet ihn an. Liefert eine kurze Zusammenfassung."""
    bal = get_balance()
    cfg = bal.data.get("expedition", {})
    outcomes = cfg.get("outcomes", [])
    if not outcomes:
        return None

    rng = random.Random(random.randrange(1, 2 ** 62))
    total_w = sum(float(o.get("weight", 0)) for o in outcomes)
    outcome = pick_outcome(outcomes, rng.random() * total_w)
    otype = outcome.get("type", "nothing")
    result: dict = {
        "location": f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}",
        "outcome": otype,
    }

    if otype == "resources":
        gain = {k: _rand_range(rng, outcome.get(k, 0)) for k in ("metal", "crystal", "deuterium")}
        cargo = dict(fleet.cargo or {})
        for k in ("metal", "crystal", "deuterium"):
            cargo[k] = round(cargo.get(k, 0) + gain[k], 1)
        fleet.cargo = cargo
        result["found"] = gain

    elif otype == "ships":
        ship_type = outcome.get("ship", "light_fighter")
        n = _rand_range(rng, outcome.get("count", 0))
        if n > 0 and ship_type in bal.ships:
            session.add(Ship(planet_id=None, fleet_id=fleet.id, type=ship_type, count=n))
            result["found_ships"] = {ship_type: n}

    elif otype == "hazard":
        loss_pct = _rand_range(rng, outcome.get("loss_pct", 0)) / 100.0
        lost: dict[str, int] = {}
        rows = (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        for row in rows:
            destroyed = int(row.count * loss_pct)
            if destroyed > 0:
                row.count -= destroyed
                lost[row.type] = destroyed
                if row.count <= 0:
                    await session.delete(row)
        result["lost"] = lost

    log.info("Expedition @ %s -> %s", result["location"], otype)
    return result
