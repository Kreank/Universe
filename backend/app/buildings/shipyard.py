"""Werft-Logik (api-contract §5): Schiffe & Verteidigung bauen.

Die Bau-Warteschlange ist persistent (Tabelle ``shipyard_queue``): jeder Auftrag
wird als ``ShipyardQueueItem`` gespeichert und beim Abschluss per Scheduler-Job in
``ships``/``defenses`` ueberfuehrt. Offene Auftraege ueberleben Neustarts —
``recover_pending_jobs`` plant sie nach (Tech-Debt #2 geschlossen)."""
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
from app.platform.models import Defense, Planet, Ship, ShipyardQueueItem
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.shipyard")


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


def _requirement_list(requires: dict, rlevels: dict[str, int], blevels: dict[str, int]) -> list[dict]:
    """Uebersetzt das ``requires``-Dict in eine Liste mit Erfuellungs-Status je Eintrag."""
    return [
        {
            "type": key,
            "level": needed,
            "met": rlevels.get(key, blevels.get(key, 0)) >= needed,
        }
        for key, needed in requires.items()
    ]


async def shipyard_view(session: AsyncSession, planet: Planet) -> dict:
    """Liefert Schiff-/Verteidigungs-Optionen + aktuelle Queue."""
    bal = get_balance()
    blevels = await get_building_levels(session, planet.id)
    rlevels = await get_research_levels(session, planet.player_id)
    shipyard_lvl = blevels.get("shipyard", 0)

    roster = bal.combat_roster

    def build_options(catalog: dict) -> list[dict]:
        out = []
        for typ, cfg in catalog.items():
            # ``_``-praefixierte Keys sind Meta-/Kommentar-Eintraege (z. B. "_note").
            if typ.startswith("_") or not isinstance(cfg, dict):
                continue
            # Virtuelle Einheiten (z. B. Mond-Orbitalbatterie) sind nicht direkt baubar.
            if cfg.get("virtual"):
                continue
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
                "requirements": _requirement_list(req, rlevels, blevels),
                "weapon_type": (roster.get(typ) or {}).get("weapon_type"),
                "drive": (roster.get(typ) or {}).get("drive"),
                "range": (roster.get(typ) or {}).get("range"),
            })
        return out

    return {
        "ships": build_options(bal.ships),
        "defenses": build_options(bal.defenses),
        "queue": await _queue_items(session, planet.id),
    }


async def _queue_items(session: AsyncSession, planet_id: uuid.UUID) -> list[dict]:
    """Aktuelle Werft-Queue eines Planeten (nach Fertigstellung sortiert)."""
    rows = (await session.execute(
        select(ShipyardQueueItem)
        .where(ShipyardQueueItem.planet_id == planet_id)
        .order_by(ShipyardQueueItem.finishes_at)
    )).scalars().all()
    return [
        {
            "type": q.type,
            "count": q.count,
            "category": q.category,
            "finishes_at": q.finishes_at.isoformat(),
        }
        for q in rows
    ]


async def queue_build(session: AsyncSession, planet: Planet, typ: str, count: int, category: str) -> list[dict]:
    """Reiht einen Bauauftrag ein, zieht Ressourcen ab und plant den Abschluss."""
    if category not in ("ship", "defense"):
        raise ValueError("category muss 'ship' oder 'defense' sein")
    if count <= 0:
        raise ValueError("count muss > 0 sein")
    catalog = _catalog(category)
    if typ not in catalog or catalog[typ].get("virtual"):
        raise ValueError("Unbekannter Typ")

    blevels = await get_building_levels(session, planet.id)
    if blevels.get("shipyard", 0) < 1:
        raise RuntimeError("Raumschiffwerft erforderlich")

    rlevels = await get_research_levels(session, planet.player_id)
    req = catalog[typ].get("requires", {})
    if not _requirements_met(req, rlevels, blevels):
        raise RuntimeError("Vorbedingungen nicht erfuellt")

    # Doktrin-Rabatt fuer Signatur-Schiffe (Kosten + Bauzeit).
    cost_mult, time_mult = 1.0, 1.0
    if category == "ship":
        from app.platform.doctrine import signature_mult
        from app.platform.models import Player
        player = await session.get(Player, planet.player_id)
        cost_mult, time_mult = signature_mult(player.doctrine if player else None, typ)

    unit_cost = catalog[typ]["cost"]
    total_cost = {
        "metal": round(unit_cost.get("metal", 0) * count * cost_mult),
        "crystal": round(unit_cost.get("crystal", 0) * count * cost_mult),
        "deuterium": round(unit_cost.get("deuterium", 0) * count * cost_mult),
    }
    if not await spend_resources(session, planet, total_cost):
        raise RuntimeError("Nicht genug Ressourcen")

    secs_each = max(1, int(round(build_seconds_each(unit_cost, blevels.get("shipyard", 0)) * time_mult)))
    finish = _now() + dt.timedelta(seconds=secs_each * count)
    item = ShipyardQueueItem(
        planet_id=planet.id,
        type=typ,
        count=count,
        category=category,
        finishes_at=finish,
    )
    session.add(item)
    await session.flush()  # item.id verfuegbar machen

    schedule_at(
        finish,
        complete_shipyard_build,
        str(item.id),
        job_id=f"shipyard:{item.id}",
    )
    return await _queue_items(session, planet.id)


async def complete_shipyard_build(queue_item_id: str) -> None:
    """Scheduler-Callback: ueberfuehrt einen abgeschlossenen Auftrag in ships/defenses."""
    async with session_scope() as session:
        item = (await session.execute(
            select(ShipyardQueueItem).where(ShipyardQueueItem.id == uuid.UUID(queue_item_id))
        )).scalar_one_or_none()
        if item is None:
            return  # bereits abgeschlossen (z. B. doppelter Misfire)

        pid, typ, count, category = item.planet_id, item.type, item.count, item.category
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

        await session.delete(item)

    log.info("Werft fertig: %sx %s (%s) auf %s", count, typ, category, pid)
