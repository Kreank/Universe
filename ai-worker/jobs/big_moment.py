"""Job: big_moment.

EINEN kontextbezogenen Funkspruch generieren (RAG: Persona + Lore + Situation),
deduplizieren, in `transmissions` schreiben (type='big_moment') und via
Redis-PubSub `ws:player:{player_id}` als WS-Event publishen
(Format gemaess shared/api-contract.md §8 / events.md).
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from config import settings
from db import Database
from models import Job
from ollama_client import OllamaClient, OllamaUnavailable
from personas import (
    NPC_SITUATIONS,
    SITUATIONS,
    build_big_moment_prompt,
    build_npc_big_moment_prompt,
    build_npc_system_prompt,
    build_system_prompt,
)

log = logging.getLogger("job.big_moment")

_DEFAULT_SITUATION = "victory"


def _query_text(situation_label: str, job: Job) -> str:
    """Kurztext fuer die RAG-Embedding-Suche im flavor_pool."""
    ctx = job.context
    parts = [situation_label]
    for value in (ctx.enemy, ctx.planet, ctx.outcome):
        if value:
            parts.append(str(value))
    return " | ".join(parts)


def _transmission_to_dict(row: Any) -> dict[str, Any]:
    """asyncpg.Record -> JSON-serialisierbares Transmission-Objekt (api-contract §8)."""
    created = row["created_at"]
    return {
        "id": str(row["id"]),
        "type": row["type"],
        "subject": row["subject"],
        "body": row["body"],
        "commander_id": str(row["commander_id"]) if row["commander_id"] else None,
        "requires_decision": bool(row["requires_decision"]),
        "decision_payload": row["decision_payload"],
        "read": bool(row["read"]),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else created,
    }


async def _run_npc(job: Job, db: Database, ollama: OllamaClient, redis: aioredis.Redis) -> None:
    """NPC-Funkspruch an den Spieler (gleiche RAG-/Dedup-Mechanik, NPC-Persona/Situationen)."""
    npc = await db.get_npc(job.npc_id)
    if npc is None:
        log.warning("big_moment: NPC %s nicht gefunden — verworfen", job.npc_id)
        return
    data = dict(npc)
    player_id = job.player_id
    if not player_id:
        log.warning("big_moment(npc): kein player_id — verworfen")
        return
    situation = job.context.situation or "taunt"
    sit = NPC_SITUATIONS.get(situation, {"label": situation, "subject": "Funkuebertragung"})

    system = build_npc_system_prompt(data)
    user = build_npc_big_moment_prompt(data, situation, job.context)
    body: str | None = None
    candidate = ""
    for attempt in range(1, settings.max_generation_attempts + 1):
        candidate = await ollama.generate(system, user)
        embedding = await ollama.embed(candidate)
        dist = await db.nearest_reaction_distance(str(data["id"]), situation, embedding, "npc")
        if dist is None or dist >= settings.dedup_cosine_threshold:
            body = candidate
            break
        log.info("big_moment(npc) zu aehnlich (dist=%.4f) — Versuch %d", dist, attempt)
    if body is None:
        body = candidate

    row = await db.insert_transmission(
        player_id=player_id, commander_id=None, ttype="big_moment",
        subject=sit.get("subject", "Funkuebertragung"), body=body,
    )
    transmission = _transmission_to_dict(row)
    channel = f"ws:player:{player_id}"
    message = json.dumps({"type": "transmission", "transmission": transmission}, ensure_ascii=False)
    receivers = await redis.publish(channel, message)
    log.info("big_moment(npc) fuer %s gesendet (transmission=%s, %d WS-Empfaenger)",
             data.get("name"), transmission["id"], receivers)


async def run(job: Job, db: Database, ollama: OllamaClient, redis: aioredis.Redis) -> None:
    if job.npc_id:
        await _run_npc(job, db, ollama, redis)
        return
    if not job.commander_id:
        log.warning("big_moment ohne commander_id — verworfen")
        return

    commander = await db.get_commander(job.commander_id)
    if commander is None:
        log.warning("big_moment: Commander %s nicht gefunden — verworfen", job.commander_id)
        return

    data = dict(commander)
    player_id = job.player_id or (str(data["player_id"]) if data.get("player_id") else None)
    if not player_id:
        log.warning("big_moment: kein player_id — verworfen")
        return

    situation = job.context.situation or _DEFAULT_SITUATION
    sit = SITUATIONS.get(situation, {"label": situation, "subject": "Funkspruch"})

    # 1) RAG: passende Lore-Schnipsel holen (best effort).
    lore: list[str] = []
    try:
        query_emb = await ollama.embed(_query_text(sit["label"], job))
        lore = await db.retrieve_lore(query_emb, limit=3)
    except OllamaUnavailable:
        raise  # transient -> Job zurueckstellen

    # 2) EINEN Funkspruch erzeugen, gegen die Bank deduplizieren (Retry).
    # Welle 2: Erinnerungs-Narrativ (persona.memory_summary) + Meinung ueber DIESEN Gegner
    # (frisch aus der DB, der Kampf-Hook hat sie bereits committet) faerben den Funkspruch.
    persona = data.get("persona")
    if isinstance(persona, str):
        try:
            persona = json.loads(persona)
        except (json.JSONDecodeError, TypeError):
            persona = {}
    memory_summary = (persona or {}).get("memory_summary") if isinstance(persona, dict) else None
    opinion = None
    about_player_id = getattr(job.context, "about_player_id", None)
    about_npc_id = getattr(job.context, "about_npc_id", None)
    if about_player_id or about_npc_id:
        rec = await db.get_commander_opinion_about(str(data["id"]), about_player_id, about_npc_id)
        if rec is not None:
            opinion = {"opinion_type": rec["opinion_type"], "strength": rec["strength"]}

    system = build_system_prompt(data)
    user = build_big_moment_prompt(
        data, situation, job.context, lore, memory_summary=memory_summary, opinion=opinion
    )

    body: str | None = None
    candidate = ""
    for attempt in range(1, settings.max_generation_attempts + 1):
        candidate = await ollama.generate(system, user)
        embedding = await ollama.embed(candidate)
        dist = await db.nearest_reaction_distance(str(data["id"]), situation, embedding)
        if dist is None or dist >= settings.dedup_cosine_threshold:
            body = candidate
            break
        log.info("big_moment zu aehnlich (dist=%.4f) — Versuch %d/%d",
                 dist, attempt, settings.max_generation_attempts)

    if body is None:
        # Alle Versuche aehnlich — letzten Kandidaten nehmen (besser als nichts;
        # Latenz ist Feature, leere Transmission waere schlechter).
        body = candidate
        log.info("big_moment: kein klar einzigartiger Treffer — nehme letzten Kandidaten")

    # 3) In transmissions schreiben.
    row = await db.insert_transmission(
        player_id=player_id,
        commander_id=str(data["id"]),
        ttype="big_moment",
        subject=sit.get("subject", "Funkspruch"),
        body=body,
    )
    transmission = _transmission_to_dict(row)

    # 4) Via PubSub an den WS-Fan-out des game-server pushen.
    channel = f"ws:player:{player_id}"
    message = json.dumps({"type": "transmission", "transmission": transmission}, ensure_ascii=False)
    receivers = await redis.publish(channel, message)
    log.info(
        "big_moment fuer %s gesendet (transmission=%s, %d WS-Empfaenger)",
        data.get("name"), transmission["id"], receivers,
    )
