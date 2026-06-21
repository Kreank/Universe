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
import random
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
    # Friedliche Einsaetze (Kommandeur meldet sich auch ohne Kampf).
    "expedition_success": "Expedition bei {planet} abgeschlossen, Kommandant. Wir bringen unsere Funde heim.",
    "mining_haul": "Frachtraeume voll, Kommandant — der Abbau bei {planet} hat sich gelohnt.",
    "trade_profit": "Handel bei {planet} abgewickelt, Kommandant. Ein gutes Geschaeft.",
}

_SUBJECT = {
    "victory": "Sieg gemeldet",
    "crushing_victory": "Ueberlegener Sieg",
    "close_win": "Knapper Sieg",
    "defeat": "Niederlage",
    "expedition_success": "Funkspruch von der Expedition",
    "mining_haul": "Funkspruch vom Bergbau",
    "trade_profit": "Funkspruch vom Handel",
}

# NPC-Funksprueche (Phase 1): Fallback je Situation, wenn die NPC-Bank leer ist. {enemy}=Spieler, {planet}=Ort.
_NPC_FALLBACK = {
    "attack": "Wir kommen fuer dich, {enemy}. {planet} wird brennen.",
    "defend_win": "Du bist gescheitert, {enemy}. Wage es nicht erneut, uns bei {planet} anzugreifen.",
    "defend_loss": "Das wirst du bereuen, {enemy}. {planet} ist nicht das Ende — wir kehren zurueck.",
    "spied": "Wir haben deine Sonden bei {planet} entdeckt, {enemy}. Spioniere uns nicht aus.",
    "taunt": "Beuge dich, {enemy}, oder erfahre unseren Zorn.",
}
_NPC_SUBJECT = {
    "attack": "Feindliche Funkuebertragung",
    "defend_win": "Trotzige Funkuebertragung",
    "defend_loss": "Funkuebertragung des Geschlagenen",
    "spied": "Warnung eines fremden Imperiums",
    "taunt": "Unerbetene Funkuebertragung",
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
            # Deterministische Reihenfolge + Zeilensperre (Befund M-3): sonst koennen zwei
            # parallele Kaempfe dieselbe Zeile lesen und denselben Funkspruch senden.
            .order_by(ReactionBank.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
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
                # Welle 2: Gegner-Identitaet -> der ai-worker laedt die FRISCHE Meinung des
                # Kommandeurs ueber diesen Gegner (verhasst/gefuerchtet/geachtet) + sein
                # Erinnerungs-Narrativ und faerbt den Funkspruch spuerbar.
                "about_player_id": context.get("about_player_id"),
                "about_npc_id": context.get("about_npc_id"),
            },
        })

    log.info(
        "Reaktion (%s) fuer player=%s commander=%s bank=%s decisive=%s",
        situation, player_id, commander.id if commander else None, used_bank, decisive,
    )
    return transmission


async def commander_flavor_reaction(
    session: AsyncSession,
    *,
    player_id: uuid.UUID,
    commander: Commander | None,
    situation: str,
    context: dict,
    chance: float = 0.5,
) -> Transmission | None:
    """Friedlicher Kommandeur-Funkspruch (kein Kampf): zieht persona-gefaerbt aus der ReactionBank
    (sonst Fallback-Text) und stellt ihn zu. Anders als ``after_combat_reaction`` ohne big_moment.

    ``chance`` drosselt die Haeufigkeit (nicht jede Mission soll funken). Gibt die Transmission
    zurueck oder None (kein Kommandeur / per chance uebersprungen / unbekannte Situation)."""
    if commander is None or random.random() > chance:
        return None

    body_template: str | None = None
    bank = (await session.execute(
        select(ReactionBank)
        .where(
            ReactionBank.commander_id == commander.id,
            ReactionBank.situation == situation,
            ReactionBank.used.is_(False),
        )
        .order_by(ReactionBank.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )).scalar_one_or_none()
    if bank is not None:
        bank.used = True
        body_template = bank.template_text
    if body_template is None:
        body_template = _FALLBACK.get(situation)
    if body_template is None:
        return None

    transmission = Transmission(
        player_id=player_id,
        commander_id=commander.id,
        type="reaction",
        subject=_SUBJECT.get(situation, "Funkspruch"),
        body=_slot_fill(body_template, context),
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
    return transmission


async def npc_reaction(
    session: AsyncSession,
    *,
    player_id: uuid.UUID,
    npc,
    situation: str,
    context: dict,
    big_moment: bool = False,
) -> Transmission | None:
    """Ein NPC-Imperium funkt den Spieler an (Phase 1). Zieht eine ungenutzte NPC-Bank-Zeile zur
    Situation, Slot-Fill ({enemy}=Spieler, {planet}=Ort), schreibt eine Transmission + WS-Push.
    Fallback-Template, wenn die Bank leer ist. ``big_moment=True`` enqueued zusaetzlich einen
    frischen, kontextbezogenen LLM-Funkspruch (ai-worker)."""
    npc_persona = bool(getattr(npc, "persona", None))
    body_template: str | None = None
    used_bank = False
    bank = (await session.execute(
        select(ReactionBank)
        .where(
            ReactionBank.npc_id == npc.id,
            ReactionBank.situation == situation,
            ReactionBank.used.is_(False),
        )
        # Deterministisch + Zeilensperre (Befund M-3): kein Doppel-Funkspruch bei Parallelkampf.
        .order_by(ReactionBank.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )).scalar_one_or_none()
    if bank is not None:
        bank.used = True
        body_template = bank.template_text
        used_bank = True
    if body_template is None:
        body_template = _NPC_FALLBACK.get(situation, _NPC_FALLBACK["taunt"])

    body = _slot_fill(body_template, context)
    subject = f"{getattr(npc, 'name', 'Fremdes Imperium')}: {_NPC_SUBJECT.get(situation, 'Funkuebertragung')}"
    transmission = Transmission(
        player_id=player_id,
        commander_id=None,
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

    # Frischen LLM-Funkspruch nur, wenn die Persona schon angereichert ist (sonst wenig Mehrwert).
    if big_moment and npc_persona:
        await event_bus.enqueue_job({
            "job_type": "big_moment",
            "npc_id": str(npc.id),
            "player_id": str(player_id),
            "context": {
                "situation": situation,
                "enemy": context.get("enemy"),
                "planet": context.get("planet"),
                "outcome": context.get("outcome"),
            },
        })

    log.info("NPC-Reaktion (%s) npc=%s player=%s bank=%s", situation, npc.id, player_id, used_bank)
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
