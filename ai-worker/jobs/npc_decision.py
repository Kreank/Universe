"""Job: npc_decision (Welle 1 — Verhandelbare KI-NPC-Imperien).

Das NPC-Imperium ENTSCHEIDET emergent per LLM ueber ein Spieler-Angebot (Buendnis /
Waffenstillstand / Tribut): annehmen, ablehnen oder Gegenangebot. Der Worker

1. laedt den NPC + den vom Backend gelieferten Kontext (Angebot, Caps, Spielzustand),
2. befragt das Entscheidungs-Modell (Override ``qwen3.5:9b``, think=false, format=json) —
   robustes JSON-Parsen + bis zu 2 Retries,
3. schreibt die Audit-Zeile (``npc_decisions``),
4. funkt die in-character Antwort an den Spieler (Transmission ``npc_diplomacy``;
   requires_decision NUR beim Gegenangebot) und pusht sie via WS,
5. WENDET die Beziehungsaenderung in ``npc_relations`` an — STRIKT innerhalb der Caps.

Die Klemm-/Status-Logik spiegelt ``backend/app/npc/diplomacy.py`` (resolve_terms/apply_decision).
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from config import settings
from db import Database
from models import Job
from ollama_client import OllamaClient
from personas import (
    build_npc_diplomacy_system_prompt,
    build_npc_diplomacy_user_prompt,
    parse_decision_json,
)

log = logging.getLogger("job.npc_decision")

_MAX_ATTEMPTS = 3  # 1 Versuch + bis zu 2 Retries bei Parse-Fehler

_RES_DE = {"metal": "Metall", "crystal": "Kristall", "deuterium": "Deuterium"}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _fmt_metal(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


# -- Mirror von backend/app/npc/diplomacy.py (Caps gelten als harte Leitplanke) --------

def _clamp(value: Any, cap: Any) -> int:
    try:
        v = max(0, int(float(value)))
    except (TypeError, ValueError):
        v = 0
    try:
        c = int(float(cap))
    except (TypeError, ValueError):
        c = 0
    return min(v, c)


def _resolve_terms(offer_type: str, choice: str, offered: dict, decision: dict, caps: dict) -> dict:
    """accept -> (geklemmte) Spieler-Konditionen; counter -> (geklemmte) NPC-Forderung; reject -> {}."""
    if choice == "accept":
        return {
            "tribute_metal": _clamp(offered.get("tribute_metal"), caps.get("tribute_max", 0)),
            "ceasefire_hours": _clamp(offered.get("ceasefire_hours"), caps.get("ceasefire_max_hours", 0)),
        }
    if choice == "counter":
        return {
            "tribute_metal": _clamp(decision.get("tribut_gefordert"), caps.get("tribute_max", 0)),
            "ceasefire_hours": _clamp(decision.get("ceasefire_stunden"), caps.get("ceasefire_max_hours", 0)),
        }
    return {"tribute_metal": 0, "ceasefire_hours": 0}


def _apply_fields(offer_type: str, result: dict, caps: dict, prev_positive: int, now: dt.datetime) -> dict:
    """Beziehungsfelder fuer einen ANGENOMMENEN Deal (Spiegel von apply_decision)."""
    fields: dict[str, Any] = {"last_decision_at": now, "positive_actions": prev_positive + 1}
    if offer_type == "alliance":
        fields.update(status="allied", alliance_since=now, ceasefire_until=None,
                      tribute_metal_per_cycle=0.0)
    elif offer_type == "ceasefire":
        hrs = int(result.get("ceasefire_hours") or 0) or int(caps.get("ceasefire_max_hours", 0))
        fields.update(status="ceasefire", ceasefire_until=now + dt.timedelta(hours=max(1, hrs)),
                      tribute_metal_per_cycle=0.0)
    elif offer_type == "tribute":
        cycle = int(caps.get("tribute_cycle_hours", 24))
        fields.update(status="ceasefire", tribute_metal_per_cycle=float(result.get("tribute_metal") or 0),
                      tribute_last_paid=now, ceasefire_until=now + dt.timedelta(hours=max(1, cycle)))
    return fields


# ---------------------------------------------------------------------------------------

def _summary_line(offer_type: str, choice: str, result: dict) -> str:
    """Kurze, klare Status-Zeile unter dem Funkspruch (fuers Postfach)."""
    if choice == "reject":
        return "[Angebot abgelehnt]"
    if choice == "counter":
        bits = []
        if result.get("tribute_metal"):
            bits.append(f"{_fmt_metal(result['tribute_metal'])} Metall Tribut/Zyklus")
        if result.get("ceasefire_hours"):
            bits.append(f"{result['ceasefire_hours']} Std. Waffenstillstand")
        return "[Gegenangebot: " + (", ".join(bits) if bits else "neue Bedingungen") + "]"
    # accept
    if offer_type == "alliance":
        return "[Buendnis geschlossen]"
    if offer_type == "ceasefire":
        return f"[Waffenstillstand fuer {result.get('ceasefire_hours', 0)} Stunden]"
    if offer_type == "tribute":
        return f"[Tribut-Abkommen: {_fmt_metal(result.get('tribute_metal', 0))} Metall/Zyklus]"
    return "[Vereinbarung]"


def _transmission_to_dict(row: Any) -> dict[str, Any]:
    created = row["created_at"]
    return {
        "id": str(row["id"]),
        "type": row["type"],
        "subject": row["subject"],
        "body": row["body"],
        "commander_id": None,
        "requires_decision": bool(row["requires_decision"]),
        "decision_payload": row["decision_payload"],
        "read": bool(row["read"]),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
    }


async def run(job: Job, db: Database, ollama: OllamaClient, redis: aioredis.Redis) -> None:
    player_id = job.player_id
    if not job.npc_id or not player_id:
        log.warning("npc_decision ohne npc_id/player_id — verworfen")
        return
    offer_type = job.offer_type or "ceasefire"
    offered = job.terms or {}
    caps = job.caps or {}

    npc = await db.get_npc(job.npc_id)
    if npc is None:
        log.warning("npc_decision: NPC %s nicht gefunden — verworfen", job.npc_id)
        return
    data = dict(npc)

    system = build_npc_diplomacy_system_prompt(data)
    user = build_npc_diplomacy_user_prompt(job)
    model = str(caps.get("decision_model") or settings.ollama_model)

    decision: dict[str, Any] | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        raw = await ollama.generate(system, user, model=model, format="json", think=False)
        decision = parse_decision_json(raw)
        if decision is not None:
            break
        log.info("npc_decision: ungueltiges JSON (Versuch %d/%d)", attempt, _MAX_ATTEMPTS)

    if decision is None:
        # Robustheit: kein verwertbares JSON -> charaktertreue Ablehnung, keine Beziehungsaenderung.
        decision = {
            "decision": "reject", "tribut_gefordert": 0, "ceasefire_stunden": 0,
            "funkspruch": "Wir haben deinen Funkspruch empfangen — und schweigen.",
            "begruendung": "(kein verwertbares Modell-Ergebnis)",
        }
        log.warning("npc_decision: nach %d Versuchen kein JSON — Fallback reject", _MAX_ATTEMPTS)

    choice = decision["decision"]
    result = _resolve_terms(offer_type, choice, offered, decision, caps)
    now = _now()

    # 1) Audit.
    await db.insert_npc_decision(
        npc_id=str(data["id"]), player_id=player_id, offer_type=offer_type,
        offered_terms=offered, npc_choice=choice, npc_reasoning=decision.get("begruendung", ""),
        terms_result=result,
    )

    # 2) Beziehung anwenden (nur bei accept aendert sich der Status; sonst nur last_decision_at).
    if choice == "accept":
        prev = await db.get_npc_relation(player_id, str(data["id"]))
        prev_positive = int(prev["positive_actions"]) if prev else 0
        fields = _apply_fields(offer_type, result, caps, prev_positive, now)
    else:
        fields = {"last_decision_at": now}
    await db.upsert_npc_relation(player_id, str(data["id"]), fields)

    # 3) Antwort-Funkspruch ins Postfach (Gegenangebot erfordert eine Spieler-Entscheidung).
    body = f"{decision['funkspruch']}\n\n{_summary_line(offer_type, choice, result)}"
    requires_decision = choice == "counter"
    payload = None
    if requires_decision:
        payload = {
            "kind": "diplomacy_counter",
            "npc_id": str(data["id"]),
            "offer_type": offer_type,
            "proposed_terms": result,
        }
    row = await db.insert_diplomacy_transmission(
        player_id=player_id,
        subject=f"{data.get('name', 'Fremdes Imperium')}: Antwort auf deinen Funkspruch",
        body=body, requires_decision=requires_decision, decision_payload=payload,
    )

    # 4) WS-Push.
    channel = f"ws:player:{player_id}"
    message = json.dumps(
        {"type": "transmission", "transmission": _transmission_to_dict(row)}, ensure_ascii=False
    )
    receivers = await redis.publish(channel, message)
    log.info("npc_decision: %s entscheidet '%s' (offer=%s) -> player=%s (%d WS)",
             data.get("name"), choice, offer_type, player_id, receivers)
