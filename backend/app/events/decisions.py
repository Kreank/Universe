"""Offline-sichere Event-Entscheidungen übers Postfach.

Eine Entscheidung ist ein Funkspruch mit ``requires_decision=True`` und einem
``decision_payload`` (kind='event'). Bei Nichtreaktion wendet ein Timeout-Job die Default-Wahl
an. Der Spieler kann jederzeit (online) entscheiden — der Timeout-Job wird dann gecancelt.
"""
from __future__ import annotations

import datetime as dt
import logging
import random
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import create_system_transmission
from app.platform.db import session_scope
from app.platform.models import CosmicEvent, EventBuff, Transmission
from app.platform.scheduler import cancel_job, schedule_at

log = logging.getLogger("universe.events.decisions")

VALID_CHOICES = {"bribe", "force", "wait", "board", "ignore", "help"}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def create_event_decision(
    session: AsyncSession,
    *,
    player_id: uuid.UUID,
    event: CosmicEvent,
    subject: str,
    body: str,
    choices: list[str],
    default_choice: str,
    timeout_hours: float,
) -> Transmission:
    timeout_at = _now() + dt.timedelta(hours=float(timeout_hours))
    t = await create_system_transmission(
        session,
        player_id=player_id,
        subject=subject,
        body=body,
        ttype="demand",
        requires_decision=True,
        decision_payload={
            "kind": "event",
            "event_type": event.event_type,
            "event_id": str(event.id),
            "choices": choices,
            "default_choice": default_choice,
            "timeout_at": timeout_at.isoformat(),
        },
    )
    await session.flush()
    schedule_at(timeout_at, apply_event_default, str(t.id), job_id=f"event-decide:{t.id}")
    return t


async def _clear_event_buffs(session: AsyncSession, event_id: uuid.UUID) -> None:
    await session.execute(delete(EventBuff).where(EventBuff.source_event_id == event_id))


async def _resolve_choice(session: AsyncSession, t: Transmission, choice: str, by: str) -> str:
    """Wendet die gewählte Option an. Liefert eine kurze Ergebnis-Meldung."""
    payload = t.decision_payload or {}
    etype = payload.get("event_type")
    event_id = payload.get("event_id")
    ev = await session.get(CosmicEvent, uuid.UUID(event_id)) if event_id else None

    if etype == "mine_strike":
        data = (ev.data if ev else {}) or {}
        planet_id = data.get("planet_id")
        from app.platform.models import Commander, Planet
        if choice == "bribe":
            from app.economy.service import spend_resources
            planet = await session.get(Planet, uuid.UUID(planet_id)) if planet_id else None
            cost = int(data.get("bribe_deuterium", 30000))
            if planet is None or not await spend_resources(session, planet, {"deuterium": cost}):
                return "Nicht genug Deuterium für die Bestechung — der Streik geht weiter."
            await _clear_event_buffs(session, ev.id)
            if ev:
                ev.status = "resolved"
            return f"Du hast die Gemüter mit {cost} Deuterium beruhigt — die Produktion läuft wieder normal."
        if choice == "force":
            await _clear_event_buffs(session, ev.id)
            penalty = int(data.get("morale_penalty", 10))
            cmds = (await session.execute(
                select(Commander).where(Commander.player_id == t.player_id)
            )).scalars().all()
            for c in cmds:
                c.morale = max(0, int(c.morale) - penalty)
            if ev:
                ev.status = "resolved"
            return f"Der Streik wurde gewaltsam niedergeschlagen. Produktion normal, aber die Crew-Moral sank um {penalty}."
        # wait / default: nichts tun, Debuff läuft aus.
        return "Du lässt den Streik aussitzen — der Produktions-Einbruch läuft mit der Zeit aus."

    if etype == "refugee_flotilla":
        data = (ev.data if ev else {}) or {}
        if choice != "help":
            return "Du lässt die Flüchtlinge weiterziehen."
        from app.economy.service import spend_resources
        from app.platform.models import Commander, Planet, Ship
        planet = (await session.execute(
            select(Planet).where(
                Planet.player_id == t.player_id, Planet.galaxy == (ev.galaxy if ev else None),
                Planet.system == (ev.system if ev else None), Planet.planet_type != "moon",
            )
        )).scalars().first()
        cost = int(data.get("deuterium_cost", 50000))
        if planet is None or not await spend_resources(session, planet, {"deuterium": cost}):
            return "Nicht genug Deuterium am Planeten im System — du konntest nicht helfen."
        from app.events.buffs import apply_buff
        await apply_buff(
            session, buff_type="build_speed", magnitude=float(data.get("build_speed_buff", 1.5)),
            duration_hours=float(data.get("buff_hours", 24)), scope="player",
            player_id=t.player_id, source_event_id=ev.id if ev else None,
        )
        bonus = int(data.get("morale_bonus", 12))
        for c in (await session.execute(
            select(Commander).where(Commander.player_id == t.player_id)
        )).scalars().all():
            c.morale = min(100, int(c.morale) + bonus)
        for stype, n in (data.get("keep_ships", {}) or {}).items():
            existing = (await session.execute(
                select(Ship).where(Ship.planet_id == planet.id, Ship.fleet_id.is_(None), Ship.type == stype)
            )).scalars().first()
            if existing:
                existing.count += int(n)
            else:
                session.add(Ship(planet_id=planet.id, fleet_id=None, type=stype, count=int(n)))
        if ev is not None:
            helpers = list((ev.data or {}).get("helpers", []))
            if str(t.player_id) not in helpers:
                helpers.append(str(t.player_id))
            ev.data = {**(ev.data or {}), "helpers": helpers}
        # Globale-Event-Belohnung: Chance auf ein Kommandeurs-Ausruestungsstueck.
        from app.commander.equipment import maybe_grant_item
        dropped = await maybe_grant_item(session, t.player_id, "global_event")
        keep_txt = ", ".join(f"{int(n)}× {s}" for s, n in (data.get("keep_ships", {}) or {}).items())
        gear_txt = " Unter ihrer Fracht fand sich Kommandeurs-Ausrüstung!" if dropped else ""
        return (f"Du hast geholfen ({cost} Deuterium): +{bonus} Crew-Moral, schnelleres Bauen "
                f"und {keep_txt or 'einige Zivilschiffe'} sind dir beigetreten.{gear_txt} "
                f"Halte dich für ihre Verfolger bereit!")

    if etype == "pirate_raid":
        from app.economy.service import spend_resources
        from app.platform.models import NpcAttack, Planet
        data = (ev.data if ev else {}) or {}
        if choice != "bribe":
            return "Du lässt die Razzia kommen — deine Verteidigung stellt sich ihnen."
        atk_id = data.get("attack_id")
        atk = await session.get(NpcAttack, uuid.UUID(atk_id)) if atk_id else None
        if atk is None or atk.status != "incoming":
            return "Die Piraten sind bereits da — für eine Bestechung ist es zu spät."
        planet = await session.get(Planet, uuid.UUID(data["planet_id"])) if data.get("planet_id") else None
        cost = dict(data.get("bribe_cost", {}))
        if planet is None or not await spend_resources(session, planet, cost):
            return "Nicht genug Ressourcen für die Bestechung — die Razzia kommt wie geplant."
        if ev is not None:
            ev.status = "resolved"
        # Restrisiko: Piraten kassieren UND greifen trotzdem (reduziert) an.
        if random.random() < float(data.get("partial_chance", 0.2)):
            mult = float(data.get("partial_fleet_mult", 0.5))
            reduced = {t: int(n * mult) for t, n in (atk.fleet or {}).items() if int(n * mult) >= 1}
            atk.fleet = reduced or ({next(iter(atk.fleet)): 1} if atk.fleet else {"light_fighter": 1})
            atk.data = {
                **(atk.data or {}),
                "debris_mult": float(data.get("partial_debris_mult", 1.6)),
                "item_chance": float(data.get("partial_item_chance", 0.35)),
            }
            return ("Die Piraten kassieren dein Gold — und greifen TROTZDEM an, wenn auch mit weniger "
                    "Schiffen. Immerhin: Schlägst du sie zurück, lassen sie ein besonders ergiebiges "
                    "Trümmerfeld zurück (vielleicht sogar mit Ausrüstung).")
        # Abgewendet: geplanten Angriff stoppen.
        cancel_job(f"npc-attack:{atk.id}")
        atk.status = "resolved"
        await session.delete(atk)
        return "Die Piraten nehmen das Gold und ziehen ab — die Razzia ist abgewendet."

    # Unbekannter Event-Typ: einfach abschließen.
    return "Entscheidung verbucht."


async def decide_event(session: AsyncSession, t: Transmission, choice: str) -> str:
    """Spieler-Entscheidung (online). Cancelt den Timeout-Job."""
    cancel_job(f"event-decide:{t.id}")
    msg = await _resolve_choice(session, t, choice, by="player")
    t.requires_decision = False
    t.read = True
    payload = dict(t.decision_payload or {})
    payload["chosen"] = choice
    payload["applied_by"] = "player"
    t.decision_payload = payload
    return msg


async def apply_event_default(transmission_id: str) -> None:
    """Timeout-Job: wendet die Default-Wahl an, falls noch unbeantwortet (offline-sicher)."""
    async with session_scope() as session:
        t = await session.get(Transmission, uuid.UUID(transmission_id))
        if t is None or not t.requires_decision:
            return
        payload = t.decision_payload or {}
        default = payload.get("default_choice", "wait")
        await _resolve_choice(session, t, default, by="timeout")
        t.requires_decision = False
        payload = dict(payload)
        payload["chosen"] = default
        payload["applied_by"] = "timeout"
        t.decision_payload = payload
        await session.commit()
    log.info("Event-Entscheidung per Timeout-Default angewandt: %s -> %s", transmission_id, default)
