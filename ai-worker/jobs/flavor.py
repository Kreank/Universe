"""Job: flavor (Phase 2).

Erzeugt EINEN erzaehlerischen Flavor-Text via Erzaehler-Persona (intel_officer / expedition_log / …)
+ Kontext — OHNE Entitaet, OHNE Bank, OHNE Dedup (reiner Live-Verschuss fuer seltene Ereignisse wie
Spionage-Berichte und Expeditions-Funde). Schreibt eine Transmission (type='big_moment') und pusht
sie via Redis-PubSub ``ws:player:{id}`` an den Spieler. Faellt Ollama aus -> Job wird requeued
(der nuechterne Basis-Bericht existiert ohnehin schon; Flavor ist additiv).
"""
from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from db import Database
from jobs.big_moment import _transmission_to_dict
from models import Job
from ollama_client import OllamaClient
from personas import build_flavor_prompt, narrator_subject

log = logging.getLogger("job.flavor")


async def run(job: Job, db: Database, ollama: OllamaClient, redis: aioredis.Redis) -> None:
    player_id = job.player_id
    if not player_id:
        log.warning("flavor ohne player_id — verworfen")
        return

    narrator = job.context.narrator or "expedition_log"
    system, user = build_flavor_prompt(narrator, job.context)
    body = await ollama.generate(system, user)  # OllamaUnavailable -> Aufrufer requeued
    subject = job.context.subject or narrator_subject(narrator)

    row = await db.insert_transmission(
        player_id=player_id,
        commander_id=None,
        ttype="big_moment",
        subject=subject,
        body=body,
    )
    transmission = _transmission_to_dict(row)

    channel = f"ws:player:{player_id}"
    message = json.dumps({"type": "transmission", "transmission": transmission}, ensure_ascii=False)
    receivers = await redis.publish(channel, message)
    log.info("flavor (%s) an player=%s gesendet (transmission=%s, %d WS-Empfaenger)",
             narrator, player_id, transmission["id"], receivers)
