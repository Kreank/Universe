"""Job: nightly_batch.

Pro Commander die Reaktions-Banken je Situation nachfuellen (Ziel ~10 Varianten
je Situation, GDD §10.5 "Munition"). Embeddings + pgvector-Dedup laufen in
fill_reaction_bank.
"""
from __future__ import annotations

import logging

from config import settings
from db import Database
from generation import fill_reaction_bank
from models import Job
from ollama_client import OllamaClient
from personas import NPC_SITUATIONS, SITUATIONS

log = logging.getLogger("job.nightly_batch")


async def run(job: Job, db: Database, ollama: OllamaClient) -> None:
    if job.npc_id:
        npc = await db.get_npc(job.npc_id)
        if npc is None:
            log.warning("nightly_batch: NPC %s nicht gefunden — verworfen", job.npc_id)
            return
        data = dict(npc)
        total = 0
        for situation in NPC_SITUATIONS:
            total += await fill_reaction_bank(
                db, ollama, data, situation, settings.bank_target_per_situation, kind="npc"
            )
        log.info("nightly_batch(npc) fuer %s: %d neue Varianten", data.get("name"), total)
        return
    if not job.commander_id:
        log.warning("nightly_batch ohne commander_id — verworfen")
        return

    commander = await db.get_commander(job.commander_id)
    if commander is None:
        log.warning("nightly_batch: Commander %s nicht gefunden — verworfen", job.commander_id)
        return

    data = dict(commander)
    total = 0
    for situation in SITUATIONS:
        total += await fill_reaction_bank(
            db, ollama, data, situation, settings.bank_target_per_situation
        )
    log.info("nightly_batch fuer %s abgeschlossen: %d neue Varianten", data.get("name"), total)
