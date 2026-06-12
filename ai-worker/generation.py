"""Gemeinsame Generierungs-Logik fuer die Reaktions-Banken.

Wird von persona_init und nightly_batch geteilt: pro Situation Varianten vom LLM
erzeugen, parsen, per pgvector deduplizieren und einfuegen.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Mapping

from config import settings
from db import Database
from ollama_client import OllamaClient
from personas import (
    build_npc_situation_prompt,
    build_npc_system_prompt,
    build_situation_prompt,
    build_system_prompt,
)

log = logging.getLogger("generation")

# Fuehrende Nummerierung / Aufzaehlungszeichen entfernen ("1. ", "- ", "* ", "• ").
_LIST_PREFIX = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def parse_variants(raw: str) -> list[str]:
    """Roh-Antwort in saubere, intern entduplizierte Zeilen zerlegen."""
    out: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        cleaned = _LIST_PREFIX.sub("", line.strip()).strip().strip('"').strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


async def fill_reaction_bank(
    db: Database,
    ollama: OllamaClient,
    entity: Mapping[str, Any],
    situation: str,
    target_count: int,
    kind: str = "commander",
) -> int:
    """Die Bank fuer (entity, situation) bis target_count auffuellen.

    ``kind`` ∈ {"commander","npc"} waehlt Prompt-Stil UND FK-Spalte. Gibt die Anzahl neu
    eingefuegter Varianten zurueck. Idempotent: zaehlt vorhandene Eintraege und fuellt nur das
    Defizit — so kann ein nach einem Ollama-Ausfall erneut eingereihter Job nahtlos fortsetzen.
    """
    entity_id = str(entity["id"])
    name = entity.get("name", entity_id)

    existing = await db.count_bank(entity_id, situation, kind)
    needed = target_count - existing
    if needed <= 0:
        log.info("%s / %s: Bank voll (%d) — uebersprungen", name, situation, existing)
        return 0

    if kind == "npc":
        system = build_npc_system_prompt(entity)
        user = build_npc_situation_prompt(entity, situation, count=needed + settings.generation_overshoot)
    else:
        system = build_system_prompt(entity)
        # Etwas mehr anfragen als noetig, damit Dedup-Verluste abgefedert sind.
        user = build_situation_prompt(entity, situation, count=needed + settings.generation_overshoot)

    raw = await ollama.generate(system, user)  # OllamaUnavailable -> Aufrufer requeued
    candidates = parse_variants(raw)

    inserted = 0
    for text in candidates:
        if inserted >= needed:
            break
        embedding = await ollama.embed(text)  # OllamaUnavailable -> Aufrufer requeued
        dist = await db.nearest_reaction_distance(entity_id, situation, embedding, kind)
        if dist is not None and dist < settings.dedup_cosine_threshold:
            log.debug("%s / %s: dedupe verworfen (dist=%.4f): %s", name, situation, dist, text)
            continue
        await db.insert_reaction(entity_id, situation, text, embedding, kind)
        inserted += 1

    log.info(
        "%s / %s: +%d neue Varianten (vorher %d, Ziel %d)",
        name, situation, inserted, existing, target_count,
    )
    return inserted
