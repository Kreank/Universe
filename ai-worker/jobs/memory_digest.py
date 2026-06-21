"""Job: memory_digest (Welle 2 — Kommandeure mit Gedaechtnis & Eigenleben).

Verdichtet die juengsten Erinnerungen + Meinungen ueber Gegner + Beziehungen EINES
Kommandeurs per LLM zu einem kurzen Erinnerungs-Narrativ (Ich-Perspektive) und legt es in
``persona.memory_summary`` ab (``last_digest_at`` wird gesetzt). Dieses Narrativ speist
kuenftige big_moment-Funksprueche, die dadurch SPUERBAR von der Geschichte des Kommandeurs
gefaerbt werden ("Endlich den verhassten Admiral X besiegt!").

Entscheidungs-/Qualitaetsstufe wie npc_decision: Modell-Override ``qwen3.5:9b``, think=false.
Best-effort: bei leerem Ergebnis bleibt die alte Persona unangetastet (Job geht nicht verloren).
"""
from __future__ import annotations

import logging

from db import Database
from models import Job
from ollama_client import OllamaClient
from personas import build_memory_digest_prompt

log = logging.getLogger("job.memory_digest")

# Qualitaetsmodell (wie Welle-1-Entscheidungen). Bewusst NICHT das schnelle Default-Modell.
_DIGEST_MODEL = "qwen3.5:9b"


async def run(job: Job, db: Database, ollama: OllamaClient) -> None:
    if not job.commander_id:
        log.warning("memory_digest ohne commander_id — verworfen")
        return

    commander = await db.get_commander(job.commander_id)
    if commander is None:
        log.warning("memory_digest: Commander %s nicht gefunden — verworfen", job.commander_id)
        return
    data = dict(commander)

    memories = [dict(r) for r in await db.get_commander_memories(job.commander_id)]
    if not memories:
        log.info("memory_digest: %s hat keine Erinnerungen — uebersprungen", data.get("name"))
        return
    opinions = [dict(r) for r in await db.get_commander_opinions(job.commander_id)]
    relationships = [dict(r) for r in await db.get_commander_relationships(job.commander_id)]

    system, user = build_memory_digest_prompt(data, memories, opinions, relationships)
    narrative = (await ollama.generate(system, user, model=_DIGEST_MODEL, think=False)).strip()
    if not narrative:
        log.info("memory_digest: leeres Narrativ fuer %s — Persona unveraendert", data.get("name"))
        return

    await db.save_memory_summary(job.commander_id, narrative[:1200])
    log.info("memory_digest fuer %s: Narrativ (%d Zeichen) aus %d Erinnerungen, %d Meinungen",
             data.get("name"), len(narrative), len(memories), len(opinions))
