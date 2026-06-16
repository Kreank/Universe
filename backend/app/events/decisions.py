"""Offline-sichere Event-Entscheidungen übers Postfach.

Eine Entscheidung ist ein Funkspruch mit ``requires_decision=True`` und einem
``decision_payload`` (kind='event'). Bei Nichtreaktion wendet ein Timeout-Job die Default-Wahl
an. Der Spieler kann jederzeit (online) entscheiden — der Timeout-Job wird dann gecancelt.
"""
from __future__ import annotations

import datetime as dt
import logging
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
