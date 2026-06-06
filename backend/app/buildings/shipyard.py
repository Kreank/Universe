"""Werft-Logik (api-contract §5): Schiffe & Verteidigung bauen.

Hinweis (Slice-Einschraenkung): Das Schema hat keine eigene Bau-Warteschlangen-
Tabelle. Die Queue wird daher prozess-lokal im Speicher gehalten; abgeschlossene
Bauten landen ueber einen Scheduler-Job persistent in ``ships``/``defenses``.
Ueber Neustarts hinweg ueberlebt die Queue-Anzeige nicht (im README vermerkt)."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import (
    get_building_levels,
    get_research_levels,
    refresh_resources,
    spend_resources,
)
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import Defense, Planet, Ship
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.shipyard")

# Prozess-lokale Bau-Warteschlange: planet_id(str) -> Liste von Queue-Items.
_QUEUE: dict[str, list[dict]] = {}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _catalog(category: str) -> dict:
    bal = get_balance()
    return bal.ships if category == "ship" else bal.defenses


def build_seconds_each(cost: dict[str, float], shipyard_lvl: int) -> int:
    """Bauzeit je Einheit (Sekunden): (M+K)/(2500*(1+werft)*speed) Stunden."""
    bal = get_balance()
    divisor = bal.data["build_time"]["divisor"]
    speed = bal.speed
    hours = (cost.get("metal", 0) + cost.get("crystal", 0)) / (
        divisor * (1 + shipyard_lvl) * speed
    )
    return max(bal.data["build_time"]["min_seconds"], int(round(hours * 3600)))


def _requirements_met(requires: dict, rlevels: dict[str, int], blevels: dict[str, int]) -> bool:
    for key, needed in requires.items():
        have = rlevels.get(key, blevels.get(key, 0))
        if have < needed:
            return False
    return True


async def shipyard_view(session: AsyncSession, planet: Planet) -> dict:
    """Liefert Schiff-/Verteidigungs-Optionen + aktuelle Queue."""
    bal = get_balance()
    blevels = await get_building_levels(session, planet.id)
    rlevels = await get_research_levels(session, planet.player_id)
    shipyard_lvl = blevels.get("shipyard", 0)

    def build_options(catalog: dict) -> list[dict]:
        out = []
        for typ, cfg in catalog.items():
            cost = cfg["cost"]
            req = cfg.get("requires", {})
            req_met = _requirements_met(req, rlevels, blevels)
            out.append({
                "type": typ,
                "cost": {
                    "metal": cost.get("metal", 0),
                    "crystal": cost.get("crystal", 0),
                    "deuterium": cost.get("deuterium", 0),
                },
                "build_seconds_each": build_seconds_each(cost, shipyard_lvl),
                "can_build": shipyard_lvl >= 1 and req_met,
                "requirements_met": req_met,
            })
        return out

    return {
        "ships": build_options(bal.ships),
        "defenses": build_options(bal.defenses),
        "queue": list(_QUEUE.get(str(planet.id), [])),
    }


async def queue_build(session: AsyncSession, planet: Planet, typ: str, count: int, category: str) -> list[dict]:
    """Reiht einen Bauauftrag ein, zieht Ressourcen ab und plant den Abschluss."""
    if category not in ("ship", "defense"):
        raise ValueError("category muss 'ship' oder 'defense' sein")
    if count <= 0:
        raise ValueError("count muss > 0 sein")
    catalog = _catalog(category)
    if typ not in catalog:
        raise ValueError("Unbekannter Typ")

    blevels = await get_building_levels(session, planet.id)
    if blevels.get("shipyard", 0) < 1:
        raise RuntimeError("Raumschiffwerft erforderlich")

    rlevels = await get_research_levels(session, planet.player_id)
    req = catalog[typ].get("requires", {})
    if not _requirements_met(req, rlevels, blevels):
        raise RuntimeError("Vorbedingungen nicht erfuellt")

    unit_cost = catalog[typ]["cost"]
    total_cost = {
        "metal": unit_cost.get("metal", 0) * count,
        "crystal": unit_cost.get("crystal", 0) * count,
        "deuterium": unit_cost.get("deuterium", 0) * count,
    }
    if not await spend_resources(session, planet, total_cost):
        raise RuntimeError("Nicht genug Ressourcen")

    secs_each = build_seconds_each(unit_cost, blevels.get("shipyard", 0))
    finish = _now() + dt.timedelta(seconds=secs_each * count)
    item = {
        "type": typ,
        "count": count,
        "category": category,
        "finishes_at": finish.isoformat(),
    }
    _QUEUE.setdefault(str(planet.id), []).append(item)

    schedule_at(
        finish,
        complete_shipyard_build,
        str(planet.id),
        typ,
        count,
        category,
        finish.isoformat(),
        job_id=f"shipyard:{planet.id}:{typ}:{finish.timestamp()}",
    )
    return list(_QUEUE[str(planet.id)])


async def complete_shipyard_build(
    planet_id: str, typ: str, count: int, category: str, finish_iso: str
) -> None:
    """Scheduler-Callback: fuegt die gebauten Einheiten dem Planeten hinzu."""
    async with session_scope() as session:
        pid = uuid.UUID(planet_id)
        if category == "ship":
            row = (await session.execute(
                select(Ship).where(
                    Ship.planet_id == pid, Ship.fleet_id.is_(None), Ship.type == typ
                )
            )).scalar_one_or_none()
            if row is None:
                row = Ship(planet_id=pid, fleet_id=None, type=typ, count=0)
                session.add(row)
            row.count += count
        else:
            row = (await session.execute(
                select(Defense).where(Defense.planet_id == pid, Defense.type == typ)
            )).scalar_one_or_none()
            if row is None:
                row = Defense(planet_id=pid, type=typ, count=0)
                session.add(row)
            row.count += count
        await session.commit()

    # Aus der In-Memory-Queue entfernen.
    queue = _QUEUE.get(planet_id, [])
    _QUEUE[planet_id] = [
        q for q in queue
        if not (q["type"] == typ and q["count"] == count and q["finishes_at"] == finish_iso)
    ]
    log.info("Werft fertig: %sx %s (%s) auf %s", count, typ, category, planet_id)
