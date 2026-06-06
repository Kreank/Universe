"""Job: persona_init.

Fuer einen neuen Commander das Persona-Profil bestaetigen/anreichern und eine
erste (kleine) Reaktions-Bank je Situation fuellen.
"""
from __future__ import annotations

import logging

from config import settings
from db import Database
from generation import fill_reaction_bank
from models import Job
from ollama_client import OllamaClient
from personas import (
    SITUATIONS,
    build_persona_enrichment_prompt,
    needs_persona_enrichment,
    parse_persona_json,
)

log = logging.getLogger("job.persona_init")


async def run(job: Job, db: Database, ollama: OllamaClient) -> None:
    if not job.commander_id:
        log.warning("persona_init ohne commander_id — verworfen")
        return

    commander = await db.get_commander(job.commander_id)
    if commander is None:
        log.warning("persona_init: Commander %s nicht gefunden — verworfen", job.commander_id)
        return

    # Als veraenderbares dict weiterreichen (asyncpg.Record ist read-only).
    data = dict(commander)
    persona = dict(data.get("persona") or {})

    # 1) Persona bestaetigen / anreichern.
    if needs_persona_enrichment(data):
        system, user = build_persona_enrichment_prompt(data)
        raw = await ollama.generate(system, user)  # OllamaUnavailable -> requeue
        enriched = parse_persona_json(raw)
        if enriched:
            persona = {**persona, **enriched}
            await db.update_persona(str(data["id"]), persona)
            data["persona"] = persona
            log.info("Persona fuer %s angereichert (background/voice)", data.get("name"))
        else:
            # Ollama war erreichbar, lieferte aber kein brauchbares JSON.
            # Job NICHT verlieren: mit bestehender/minimaler Persona weitermachen.
            log.warning(
                "Persona-Anreicherung fuer %s lieferte kein gueltiges JSON — "
                "fahre mit vorhandener Persona fort",
                data.get("name"),
            )
    else:
        log.info("Persona fuer %s bereits vollstaendig — keine Anreicherung", data.get("name"))

    # 2) Erste Reaktions-Bank je Situation fuellen.
    total = 0
    for situation in SITUATIONS:
        total += await fill_reaction_bank(
            db, ollama, data, situation, settings.persona_init_bank_count
        )
    log.info("persona_init fuer %s abgeschlossen: %d Varianten gesamt", data.get("name"), total)
