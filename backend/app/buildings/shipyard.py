"""Werft-Logik (api-contract §5): Schiffe & Verteidigung bauen.

Die Bau-Warteschlange ist persistent (Tabelle ``shipyard_queue``): jeder Auftrag
wird als ``ShipyardQueueItem`` gespeichert und beim Abschluss per Scheduler-Job in
``ships``/``defenses`` ueberfuehrt. Offene Auftraege ueberleben Neustarts —
``recover_pending_jobs`` plant sie nach (Tech-Debt #2 geschlossen)."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import (
    add_resources,
    get_building_levels,
    get_research_levels,
    spend_resources,
)
from app.platform.balance import catalog_items, get_balance
from app.platform.db import session_scope
from app.platform.models import Defense, Fleet, Planet, Player, Ship, ShipyardQueueItem

# Exotische, kontoweite Ressourcen (Player-Spalten) — moegliche Capstone-Schiff-Kosten.
EXOTIC_KEYS = ("antimatter", "dark_matter")
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


# Pro Planet einmalige Verteidigung (OGame: Schildkuppeln gibt es nur je 1x pro Planet).
UNIQUE_PER_PLANET: dict[str, int] = {"small_shield_dome": 1, "large_shield_dome": 1}


async def _unique_owned_on_planet(session: AsyncSession, planet_id: uuid.UUID, typ: str) -> int:
    """Bestand einer pro-Planet-einmaligen Einheit auf DIESEM Planeten: gebaut + in der Queue."""
    built = int((await session.execute(
        select(func.coalesce(func.sum(Defense.count), 0))
        .where(Defense.planet_id == planet_id, Defense.type == typ)
    )).scalar() or 0)
    queued = int((await session.execute(
        select(func.coalesce(func.sum(ShipyardQueueItem.count), 0))
        .where(ShipyardQueueItem.planet_id == planet_id, ShipyardQueueItem.type == typ)
    )).scalar() or 0)
    return built + queued


def build_seconds_each(cost: dict[str, float], building_lvl: int, nanite_lvl: int = 0) -> int:
    """Bauzeit je Einheit (Sekunden): (M+K)/(2500*(1+gebaeude)*speed) Std * nanite_ship_factor^nanite_lvl.
    ``building_lvl`` ist das Tempo-Gebaeude der jeweiligen Kategorie — Werft fuer Schiffe,
    Verteidigungsfabrik fuer Verteidigung. Nanitenfabrik senkt die Bauzeit je Stufe multiplikativ
    (Default 0.95 = -5%/Stufe)."""
    bal = get_balance()
    bt = bal.data["build_time"]
    divisor = bt["divisor"]
    speed = bal.speed
    nanite_factor = float(bt.get("nanite_ship_factor", 0.95)) ** max(0, int(nanite_lvl))
    hours = (cost.get("metal", 0) + cost.get("crystal", 0)) / (
        divisor * (1 + building_lvl) * speed
    ) * nanite_factor
    return max(bt["min_seconds"], int(round(hours * 3600)))


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


def capstone_cap(cfg: dict, rlevels: dict[str, int]) -> int:
    """Erlaubte Besitzmenge eines Capstone-Schiffs: default_cap + Stufe der Kommando-Forschung."""
    bal = get_balance()
    default_cap = int(bal.data.get("capstone", {}).get("default_cap", 1))
    return default_cap + int(rlevels.get(cfg.get("capstone"), 0))


async def capstone_owned(session: AsyncSession, player_id: uuid.UUID, typ: str) -> int:
    """Besessene Capstone-Schiffe eines Typs: auf Planeten + in Flotten + in der Bau-Queue."""
    on_planets = int((await session.execute(
        select(func.coalesce(func.sum(Ship.count), 0))
        .join(Planet, Ship.planet_id == Planet.id)
        .where(Planet.player_id == player_id, Ship.type == typ)
    )).scalar() or 0)
    in_fleets = int((await session.execute(
        select(func.coalesce(func.sum(Ship.count), 0))
        .join(Fleet, Ship.fleet_id == Fleet.id)
        .where(Fleet.player_id == player_id, Ship.type == typ)
    )).scalar() or 0)
    in_queue = int((await session.execute(
        select(func.coalesce(func.sum(ShipyardQueueItem.count), 0))
        .join(Planet, ShipyardQueueItem.planet_id == Planet.id)
        .where(Planet.player_id == player_id, ShipyardQueueItem.type == typ)
    )).scalar() or 0)
    return on_planets + in_fleets + in_queue


async def shipyard_view(session: AsyncSession, planet: Planet) -> dict:
    """Liefert Schiff-/Verteidigungs-Optionen + aktuelle Queue."""
    bal = get_balance()
    blevels = await get_building_levels(session, planet.id)
    rlevels = await get_research_levels(session, planet.player_id)
    shipyard_lvl = blevels.get("shipyard", 0)
    defense_lvl = blevels.get("defense_factory", 0)
    nanite_lvl = blevels.get("nanite_factory", 0)

    roster = bal.combat_roster

    # Capstone-Schiffe: Besitz-Status (owned/cap) vorab (async) — fuers Frontend + can_build.
    capstone_status: dict[str, dict] = {}
    for typ, cfg in catalog_items(bal.ships):
        if cfg.get("capstone"):
            capstone_status[typ] = {
                "owned": await capstone_owned(session, planet.player_id, typ),
                "cap": capstone_cap(cfg, rlevels),
            }

    # Pro-Planet-einmalige Einheiten (Schildkuppeln): aktueller Bestand auf diesem Planeten
    # (gebaut + Queue), damit das Frontend "1/1" zeigen + den Bau-Button sperren kann.
    unique_owned: dict[str, int] = {}
    for typ in UNIQUE_PER_PLANET:
        unique_owned[typ] = await _unique_owned_on_planet(session, planet.id, typ)

    def build_options(catalog: dict, building_lvl: int) -> list[dict]:
        """``building_lvl`` ist das Tempo-/Freischalt-Gebaeude der Kategorie (Werft fuer Schiffe,
        Verteidigungsfabrik fuer Verteidigung): bestimmt Bauzeit und ``can_build`` (>=1 noetig)."""
        out = []
        # ``catalog_items`` filtert ``_``-Meta-Keys + Nicht-Dicts zentral (Befund #7).
        for typ, cfg in catalog_items(catalog):
            # Virtuelle Einheiten (z. B. Mond-Orbitalbatterie) sind nicht direkt baubar.
            if cfg.get("virtual"):
                continue
            cost = cfg["cost"]
            req = cfg.get("requires", {})
            req_met = _requirements_met(req, rlevels, blevels)
            cap_info = capstone_status.get(typ)
            cap_ok = cap_info is None or cap_info["owned"] < cap_info["cap"]
            # Pro-Planet-Limit (Schildkuppeln): bei erreichtem Bestand nicht mehr baubar.
            unique_cap = UNIQUE_PER_PLANET.get(typ)
            unique_ok = unique_cap is None or unique_owned.get(typ, 0) < unique_cap
            cap_ok = cap_ok and unique_ok
            out.append({
                "type": typ,
                "cost": {
                    "metal": cost.get("metal", 0),
                    "crystal": cost.get("crystal", 0),
                    "deuterium": cost.get("deuterium", 0),
                    "antimatter": cost.get("antimatter", 0),
                    "dark_matter": cost.get("dark_matter", 0),
                },
                "build_seconds_each": build_seconds_each(cost, building_lvl, nanite_lvl),
                "can_build": building_lvl >= 1 and req_met and cap_ok,
                "requirements_met": req_met,
                "requirements": _requirement_list(req, rlevels, blevels),
                "weapon_type": (roster.get(typ) or {}).get("weapon_type"),
                "drive": (roster.get(typ) or {}).get("drive"),
                "range": (roster.get(typ) or {}).get("range"),
                "capstone": cap_info,
                # Pro-Planet-Limit (null = unbegrenzt) + aktueller Bestand inkl. Queue.
                "max_per_planet": unique_cap,
                "planet_owned": unique_owned.get(typ) if unique_cap is not None else None,
            })
        return out

    return {
        "ships": build_options(bal.ships, shipyard_lvl),
        "defenses": build_options(bal.defenses, defense_lvl),
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
    # Tempo-/Freischalt-Gebaeude je Kategorie: Schiffe brauchen die Werft, Verteidigung die
    # Verteidigungsfabrik (2026-06-17: Verteidigung aus der Werft herausgeloest).
    gate_building = "shipyard" if category == "ship" else "defense_factory"
    if blevels.get(gate_building, 0) < 1:
        raise RuntimeError(
            "Raumschiffwerft erforderlich" if category == "ship" else "Verteidigungsfabrik erforderlich"
        )

    rlevels = await get_research_levels(session, planet.player_id)
    req = catalog[typ].get("requires", {})
    if not _requirements_met(req, rlevels, blevels):
        raise RuntimeError("Vorbedingungen nicht erfuellt")

    cfg = catalog[typ]
    player = await session.get(Player, planet.player_id) if category == "ship" else None

    # Capstone-Schiffe: Besitz-Limit (default_cap + Kommando-Forschung), keine Stapelung ueber das Limit.
    if cfg.get("capstone"):
        cap = capstone_cap(cfg, rlevels)
        owned = await capstone_owned(session, planet.player_id, typ)
        if owned + count > cap:
            raise RuntimeError(
                f"Besitz-Limit erreicht ({owned}/{cap}). Forsche {cfg['capstone']} fuer +1."
            )

    # Pro-Planet-einmalige Verteidigung (Schildkuppeln): nur je 1x pro Planet (gebaut + Queue).
    unique_cap = UNIQUE_PER_PLANET.get(typ)
    if unique_cap is not None:
        owned_here = await _unique_owned_on_planet(session, planet.id, typ)
        if owned_here + count > unique_cap:
            raise RuntimeError(
                f"Pro Planet nur {unique_cap}x moeglich — bereits vorhanden/in Bau ({owned_here})."
            )

    # Doktrin-Rabatt fuer Signatur-Schiffe (Kosten + Bauzeit).
    cost_mult, time_mult = 1.0, 1.0
    if category == "ship":
        from app.platform.doctrine import signature_mult
        cost_mult, time_mult = signature_mult(player.doctrine if player else None, typ)

    unit_cost = cfg["cost"]
    total_cost = {
        "metal": round(unit_cost.get("metal", 0) * count * cost_mult),
        "crystal": round(unit_cost.get("crystal", 0) * count * cost_mult),
        "deuterium": round(unit_cost.get("deuterium", 0) * count * cost_mult),
    }
    # Exoten (pro Planet, 2026-06-15): Capstone-Schiffe zahlen ihre Exoten-Kosten VOM BAU-PLANETEN,
    # gemeinsam mit metal/crystal (atomar via spend_resources) — nicht mehr kontoweit.
    for k in EXOTIC_KEYS:
        amt = float(unit_cost.get(k, 0)) * count
        if amt:
            total_cost[k] = amt

    if not await spend_resources(session, planet, total_cost):
        raise RuntimeError("Nicht genug Ressourcen (inkl. Exoten am Bau-Planeten)")

    # Verwaltungs-Garnitur (Equipment des Gouverneurs auf dem Bau-Planeten): +Schiffbau-Tempo.
    gov_build = 1.0
    if getattr(planet, "governor_commander_id", None):
        from app.commander.equipment import commander_stat_bonus
        from app.platform.models import Commander as _Cmd
        _gov = await session.get(_Cmd, planet.governor_commander_id)
        gov_build = 1.0 + await commander_stat_bonus(
            session, planet.governor_commander_id, "shipbuild_speed", _gov.morale if _gov else 100)
    secs_each = max(1, int(round(build_seconds_each(unit_cost, blevels.get(gate_building, 0), blevels.get("nanite_factory", 0)) * time_mult / gov_build)))
    # Serielle Schlange JE GEBAEUDE (OGame-nah): Werft und Verteidigungsfabrik bauen unabhaengig
    # voneinander parallel, jede aber fuer sich seriell. Der neue Auftrag startet erst, wenn der
    # letzte Auftrag DERSELBEN Kategorie VOLLSTAENDIG fertig ist (= sein GESAMT-Ende). Innerhalb
    # eines Auftrags entsteht je ``secs_each`` EINE Einheit (stueckweise) -> ``finishes_at`` markiert
    # die naechste Einheit dieses Auftrags. Andere Kategorie blockiert NICHT.
    existing = (await session.execute(
        select(ShipyardQueueItem).where(
            ShipyardQueueItem.planet_id == planet.id,
            ShipyardQueueItem.category == category,
        )
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

    # Nur die serielle Schlange DERSELBEN Kategorie aufruecken (Werft- und Verteidigungs-Queue
    # laufen parallel und unabhaengig).
    items = list((await session.execute(
        select(ShipyardQueueItem)
        .where(
            ShipyardQueueItem.planet_id == planet.id,
            ShipyardQueueItem.category == target.category,
        )
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
