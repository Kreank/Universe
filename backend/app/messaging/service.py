"""Messaging-Pipeline (events.md, GDD §10.5).

Sofort-Reaktion nach Kampf OHNE LLM:
1. Eine ungenutzte Zeile aus ``reaction_banks`` des Commanders zur Situation holen
   (used=false -> als used markieren).
2. Slot-Filling ({enemy}, {planet}, {loot}).
3. In ``transmissions`` schreiben und via Redis ``ws:player:{id}`` pushen.
4. Sind keine Bank-Eintraege da -> Template-Fallback-Zeile (Ebene 1).
5. Bei entscheidender Schlacht zusaetzlich ``big_moment``-Job in ``ai:jobs`` enqueuen.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.eventbus import event_bus
from app.platform.models import Commander, ReactionBank, Transmission

log = logging.getLogger("universe.messaging")

# Ebene-1-Fallback je Situation (wenn Banken leer sind).
_FALLBACK = {
    "victory": "Ziel {enemy} bei {planet} ausgeschaltet. Beute gesichert: {loot}.",
    "crushing_victory": "Vernichtender Sieg ueber {enemy} ({planet}). Kaum Verluste, Beute: {loot}.",
    "close_win": "Knapper Sieg bei {enemy} ({planet}). Es war eng, aber wir halten {loot}.",
    "defeat": "Niederlage bei {enemy} ({planet}). Wir mussten uns zurueckziehen.",
    "mutiny": "Unruhe in der Crew bei {enemy} ({planet}).",
}

_SUBJECT = {
    "victory": "Sieg gemeldet",
    "crushing_victory": "Ueberlegener Sieg",
    "close_win": "Knapper Sieg",
    "defeat": "Niederlage",
    "mutiny": "Meuterei-Warnung",
}


def _format_loot(loot: dict | None) -> str:
    if not loot:
        return "keine Beute"
    parts = []
    labels = {"metal": "Metall", "crystal": "Kristall", "deuterium": "Deuterium"}
    for key in ("metal", "crystal", "deuterium"):
        val = loot.get(key, 0)
        if val:
            parts.append(f"{int(val):,} {labels[key]}".replace(",", "."))
    return ", ".join(parts) if parts else "keine Beute"


def _slot_fill(template: str, context: dict) -> str:
    loot_str = _format_loot(context.get("loot"))
    return (
        template
        .replace("{enemy}", str(context.get("enemy", "der Gegner")))
        .replace("{planet}", str(context.get("planet", "unbekannt")))
        .replace("{loot}", loot_str)
    )


def transmission_to_dict(t: Transmission) -> dict:
    """Serialisiert eine Transmission gemaess api-contract §8."""
    return {
        "id": str(t.id),
        "type": t.type,
        "subject": t.subject,
        "body": t.body,
        "commander_id": str(t.commander_id) if t.commander_id else None,
        "requires_decision": t.requires_decision,
        "decision_payload": t.decision_payload,
        "read": t.read,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


async def after_combat_reaction(
    session: AsyncSession,
    *,
    player_id: uuid.UUID,
    commander: Commander | None,
    situation: str,
    context: dict,
    decisive: bool,
) -> Transmission:
    """Erzeugt die Sofort-Reaktion und published sie. Enqueued ggf. big_moment."""
    body_template: str | None = None
    used_bank = False

    if commander is not None:
        bank = (await session.execute(
            select(ReactionBank)
            .where(
                ReactionBank.commander_id == commander.id,
                ReactionBank.situation == situation,
                ReactionBank.used.is_(False),
            )
            .limit(1)
        )).scalar_one_or_none()
        if bank is not None:
            bank.used = True
            body_template = bank.template_text
            used_bank = True

    if body_template is None:
        # Ebene-1-Fallback (Banken leer oder kein Commander).
        body_template = _FALLBACK.get(situation, _FALLBACK["victory"])

    body = _slot_fill(body_template, context)
    subject = _SUBJECT.get(situation, "Funkspruch")

    transmission = Transmission(
        player_id=player_id,
        commander_id=commander.id if commander else None,
        type="reaction",
        subject=subject,
        body=body,
        requires_decision=False,
        decision_payload=None,
        read=False,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(transmission)
    await session.flush()

    await event_bus.publish_ws(player_id, {
        "type": "transmission",
        "transmission": transmission_to_dict(transmission),
    })

    if decisive and commander is not None:
        # big_moment-Job fuer den ai-worker (Format aus events.md).
        await event_bus.enqueue_job({
            "job_type": "big_moment",
            "commander_id": str(commander.id),
            "player_id": str(player_id),
            "context": {
                "situation": situation,
                "enemy": context.get("enemy"),
                "planet": context.get("planet"),
                "loot": context.get("loot"),
                "outcome": context.get("outcome"),
            },
        })

    log.info(
        "Reaktion (%s) fuer player=%s commander=%s bank=%s decisive=%s",
        situation, player_id, commander.id if commander else None, used_bank, decisive,
    )
    return transmission


async def create_system_transmission(
    session: AsyncSession,
    *,
    player_id: uuid.UUID,
    subject: str,
    body: str,
    ttype: str = "system",
    commander_id: uuid.UUID | None = None,
    requires_decision: bool = False,
    decision_payload: dict | None = None,
    publish: bool = True,
) -> Transmission:
    """Generischer Helfer fuer system-/routine-/demand-Transmissionen."""
    transmission = Transmission(
        player_id=player_id,
        commander_id=commander_id,
        type=ttype,
        subject=subject,
        body=body,
        requires_decision=requires_decision,
        decision_payload=decision_payload,
        read=False,
        created_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(transmission)
    await session.flush()
    if publish:
        await event_bus.publish_ws(player_id, {
            "type": "transmission",
            "transmission": transmission_to_dict(transmission),
        })
    return transmission
