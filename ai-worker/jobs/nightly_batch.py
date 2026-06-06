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
from personas import SITUATIONS

log = logging.getLogger("job.nightly_batch")


async def run(job: Job, db: Database, ollama: OllamaClient) -> None:
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
