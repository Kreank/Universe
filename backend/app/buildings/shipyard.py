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
    add_resources,
    get_building_levels,
    get_research_levels,
    spend_resources,
)
from app.platform.balance import catalog_items, get_balance
from app.platform.db import session_scope
from app.platform.models import Defense, Planet, Ship, ShipyardQueueItem
from app.platform.scheduler import cancel_job, schedule_at

log = logging.getLogger("universe.shipyard")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _aware(d: dt.datetime) -> dt.datetime:
    return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d


def _item_total_end(item: ShipyardQueueItem) -> dt.datetime:
    """Zeitpunkt, zu dem die LETZTE noch offene Einheit dieses Auftrags fertig ist
    (stueckweise: naechste Einheit + (count-1) weitere je seconds_each)."""
    per = item.seconds_each or 0
    return _aware(item.finishes_at) + dt.timedelta(seconds=per * max(0, item.count - 1))


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
        # ``catalog_items`` filtert ``_``-Meta-Keys + Nicht-Dicts zentral (Befund #7).
        for typ, cfg in catalog_items(catalog):
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
            "id": str(q.id),
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
    # Serielle Werft-Schlange (OGame): EINE Werft pro Planet baut nacheinander. Der neue Auftrag
    # startet erst, wenn der letzte VOLLSTAENDIG fertig ist (= sein GESAMT-Ende, nicht nur die
    # naechste Einheit). Innerhalb eines Auftrags entsteht je ``secs_each`` EINE Einheit
    # (stueckweise) -> ``finishes_at`` markiert die naechste Einheit dieses Auftrags.
    existing = (await session.execute(
        select(ShipyardQueueItem).where(ShipyardQueueItem.planet_id == planet.id)
    )).scalars().all()
    start = _now()
    for it in existing:
        start = max(start, _item_total_end(it))
    finish = start + dt.timedelta(seconds=secs_each)  # Fertigstellung der ERSTEN Einheit
    item = ShipyardQueueItem(
        planet_id=planet.id,
        type=typ,
        count=count,
        category=category,
        finishes_at=finish,
        seconds_each=secs_each,
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


async def cancel_queue_item(session: AsyncSession, planet: Planet, item_id: uuid.UUID) -> list[dict]:
    """Bricht einen Werft-Auftrag ab: voller Ressourcen-Refund, Scheduler-Job entfernt, und die
    NACHFOLGENDEN Auftraege der seriellen Schlange ruecken um die freigewordene Zeit auf."""
    target = (await session.execute(
        select(ShipyardQueueItem).where(
            ShipyardQueueItem.id == item_id,
            ShipyardQueueItem.planet_id == planet.id,
        )
    )).scalar_one_or_none()
    if target is None:
        raise RuntimeError("Auftrag nicht gefunden")

    items = list((await session.execute(
        select(ShipyardQueueItem)
        .where(ShipyardQueueItem.planet_id == planet.id)
        .order_by(ShipyardQueueItem.finishes_at)
    )).scalars().all())

    now = _now()
    k = next(i for i, it in enumerate(items) if it.id == target.id)
    # Zeit-Span, den der Auftrag ab JETZT in der Schlange belegt (bis seine letzte Einheit faellt).
    prev_end = _item_total_end(items[k - 1]) if k > 0 else now
    start_k = max(now, prev_end)
    delta = _item_total_end(target) - start_k
    if delta.total_seconds() < 0:
        delta = dt.timedelta(0)

    # Refund: Stueckkosten * Anzahl * (Doktrin-)Kostenmultiplikator wie beim Einreihen.
    catalog = _catalog(target.category)
    unit_cost = catalog.get(target.type, {}).get("cost", {})
    cost_mult = 1.0
    if target.category == "ship":
        from app.platform.doctrine import signature_mult
        from app.platform.models import Player
        player = await session.get(Player, planet.player_id)
        cost_mult, _ = signature_mult(player.doctrine if player else None, target.type)
    refund = {
        "metal": round(unit_cost.get("metal", 0) * target.count * cost_mult),
        "crystal": round(unit_cost.get("crystal", 0) * target.count * cost_mult),
        "deuterium": round(unit_cost.get("deuterium", 0) * target.count * cost_mult),
    }
    await add_resources(session, planet, refund)

    cancel_job(f"shipyard:{target.id}")
    await session.delete(target)

    # Nachfolger der seriellen Schlange aufruecken (Luecke schliessen) + neu planen.
    if delta.total_seconds() > 0:
        for it in items[k + 1:]:
            it.finishes_at = _aware(it.finishes_at) - delta
            schedule_at(it.finishes_at, complete_shipyard_build, str(it.id), job_id=f"shipyard:{it.id}")
    await session.flush()
    return await _queue_items(session, planet.id)


async def complete_shipyard_build(queue_item_id: str) -> None:
    """Scheduler-Callback: schliesst EINE Einheit des Auftrags ab (stueckweise, OGame). Sind
    noch Einheiten offen, wird der naechste Einzel-Tick eingeplant; sonst Auftrag entfernen.
    Legacy-Auftraege (seconds_each=0) werden in einem Schritt vollstaendig abgeschlossen."""
    next_finish: dt.datetime | None = None
    produced = 0
    typ = category = ""
    pid = None
    async with session_scope() as session:
        item = (await session.execute(
            select(ShipyardQueueItem).where(ShipyardQueueItem.id == uuid.UUID(queue_item_id))
        )).scalar_one_or_none()
        if item is None:
            return  # bereits abgeschlossen (z. B. doppelter Misfire)

        pid, typ, category = item.planet_id, item.type, item.category
        per = item.seconds_each or 0
        # Stueckweise: genau 1 Einheit pro Tick. Legacy/atomar (per<=0): ganzen Rest.
        produced = item.count if per <= 0 else 1

        if category == "ship":
            row = (await session.execute(
                select(Ship).where(
                    Ship.planet_id == pid, Ship.fleet_id.is_(None), Ship.type == typ
                )
            )).scalar_one_or_none()
            if row is None:
                row = Ship(planet_id=pid, fleet_id=None, type=typ, count=0)
                session.add(row)
            row.count += produced
        else:
            row = (await session.execute(
                select(Defense).where(Defense.planet_id == pid, Defense.type == typ)
            )).scalar_one_or_none()
            if row is None:
                row = Defense(planet_id=pid, type=typ, count=0)
                session.add(row)
            row.count += produced

        item.count -= produced
        if item.count <= 0:
            await session.delete(item)
        else:
            # Naechste Einheit dieses Auftrags einplanen (Kette innerhalb des Auftrags).
            item.finishes_at = _aware(item.finishes_at) + dt.timedelta(seconds=per)
            next_finish = item.finishes_at

        # WS: Werft-Fertigstellung -> Frontend laedt Werft + Planet automatisch neu.
        from app.platform.eventbus import event_bus
        owner = await session.get(Planet, pid)
        if owner is not None:
            await event_bus.publish_ws(owner.player_id, {
                "type": "shipyard_complete",
                "planet_id": str(pid),
                "ship_type": typ,
                "count": produced,
                "category": category,
            })

    # Naechsten Einzel-Tick NACH dem Commit einplanen (persistiertes finishes_at).
    if next_finish is not None:
        schedule_at(next_finish, complete_shipyard_build, queue_item_id, job_id=f"shipyard:{queue_item_id}")

    log.info("Werft: %sx %s (%s) fertig auf %s", produced, typ, category, pid)
