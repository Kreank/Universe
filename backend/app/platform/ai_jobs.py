"""Einreihen von KI-Jobs (ai-worker) — entkoppelt vom Spiel-Tick (GDD §10.5 "Munition").

Phase 0 (2026-06-12): nightly_batch fuer alle Commander AUTOMATISCH schedulen, damit sich die
Reaktions-Banken von selbst auffuellen (vorher nur per Dev-Tool ``dev_enqueue.py`` ausloesbar).
Der ai-worker BRPOPt die Jobs einzeln und arbeitet sie sequenziell ab -> GPU-schonend, offline.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Commander, NpcEmpire

log = logging.getLogger("universe.ai_jobs")


async def enqueue_npc_persona_init(npc_id) -> None:
    """persona_init fuer einen (neu gespawnten) NPC einreihen — erzeugt Persona + Erst-Banken."""
    await event_bus.enqueue_job({"job_type": "persona_init", "npc_id": str(npc_id)})


async def enqueue_nightly_batches() -> None:
    """Periodischer Tick: fuellt die Reaktions-Banken automatisch auf.
    - Commander: nightly_batch.
    - NPC OHNE Persona: persona_init (Persona + Erst-Banken; deckt Alt-NPCs ohne KI ab).
    - NPC MIT Persona: nightly_batch.
    Idempotent genug (pgvector-Dedup in fill_reaction_bank). trade_center bleibt aussen vor."""
    async with session_scope() as session:
        cmd_ids = (await session.execute(select(Commander.id))).scalars().all()
        npcs = (await session.execute(
            select(NpcEmpire.id, NpcEmpire.persona, NpcEmpire.behavior_profile)
        )).all()
    for cid in cmd_ids:
        await event_bus.enqueue_job({"job_type": "nightly_batch", "commander_id": str(cid)})
    npc_n = 0
    for nid, persona, profile in npcs:
        if profile == "trade_center":
            continue  # neutrale Infrastruktur funkt (noch) nicht
        if persona:
            await event_bus.enqueue_job({"job_type": "nightly_batch", "npc_id": str(nid)})
        else:
            await event_bus.enqueue_job({"job_type": "persona_init", "npc_id": str(nid)})
        npc_n += 1
    if cmd_ids or npc_n:
        log.info("AI-Banken-Tick: %d Commander + %d NPC eingereiht", len(cmd_ids), npc_n)
