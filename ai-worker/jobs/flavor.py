"""Job: flavor (Phase 2).

Erzeugt EINEN erzaehlerischen Flavor-Text via Erzaehler-Persona (intel_officer / expedition_log / …)
+ Kontext — OHNE Entitaet, OHNE Bank, OHNE Dedup (reiner Live-Verschuss fuer seltene Ereignisse wie
Spionage-Berichte und Expeditions-Funde). Schreibt eine Transmission mit dem vom Backend gewuenschten
Typ (``context.ttype``, Default ``routine`` — z.B. ``spy_report`` fuer Spionage; NIE ``big_moment``,
ausser explizit gewollt) und pusht sie via Redis-PubSub ``ws:player:{id}`` an den Spieler. Faellt
Ollama aus -> Job wird requeued (der nuechterne Basis-Bericht existiert ohnehin schon; Flavor ist additiv).
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
    narrator = job.context.narrator or "expedition_log"
    subject = job.context.subject or narrator_subject(narrator)

    # Zielspieler: Broadcast (Galaxie-News -> alle) ODER ein einzelner Spieler.
    if job.context.broadcast:
        targets = await db.active_player_ids()
    elif job.player_id:
        targets = [job.player_id]
    else:
        log.warning("flavor ohne player_id/broadcast — verworfen")
        return
    if not targets:
        log.info("flavor (%s): keine Zielspieler", narrator)
        return

    system, user = build_flavor_prompt(narrator, job.context)
    # Welle 4: optionaler Modell-/Thinking-Override (z.B. qwen3.5:9b think=false fuer die
    # Waechter-Stimme). None -> Worker-Default (llama3.1:8b). EINMAL generieren (-> requeue bei Ausfall).
    body = await ollama.generate(
        system, user, model=job.context.model, think=job.context.think,
    )

    # Ziel-Typ kommt vom Backend (z.B. spy_report fuer Spionage). Default routine — Flavor ist KEIN
    # Großmoment; big_moment nur, wenn das Backend es ausdruecklich setzt (z.B. Galaxie-News).
    ttype = job.context.ttype or "routine"
    for pid in targets:
        row = await db.insert_transmission(
            player_id=pid, commander_id=None, ttype=ttype, subject=subject, body=body,
        )
        transmission = _transmission_to_dict(row)
        message = json.dumps({"type": "transmission", "transmission": transmission}, ensure_ascii=False)
        await redis.publish(f"ws:player:{pid}", message)
    log.info("flavor (%s) an %d Spieler gesendet%s",
             narrator, len(targets), " [broadcast]" if job.context.broadcast else "")
