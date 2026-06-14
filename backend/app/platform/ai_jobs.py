"""Einreihen von KI-Jobs (ai-worker) — entkoppelt vom Spiel-Tick (GDD §10.5 "Munition").

Phase 0 (2026-06-12): nightly_batch fuer alle Commander AUTOMATISCH schedulen, damit sich die
Reaktions-Banken von selbst auffuellen (vorher nur per Dev-Tool ``dev_enqueue.py`` ausloesbar).
Der ai-worker BRPOPt die Jobs einzeln und arbeitet sie sequenziell ab -> GPU-schonend, offline.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Commander, NpcEmpire, ReactionBank

log = logging.getLogger("universe.ai_jobs")


async def enqueue_npc_persona_init(npc_id) -> None:
    """persona_init fuer einen (neu gespawnten) NPC einreihen — erzeugt Persona + Erst-Banken."""
    await event_bus.enqueue_job({"job_type": "persona_init", "npc_id": str(npc_id)})


async def enqueue_flavor(
    player_id=None, *, narrator: str, situation=None, planet=None, outcome=None,
    detail: dict | None = None, subject=None, broadcast: bool = False, ttype: str = "routine",
) -> None:
    """Erzaehlerischen Flavor-Text einreihen — Live-Generierung ohne Entitaet/Bank.
    Phase 2: an EINEN Spieler (Spionage/Expedition). Phase 4: ``broadcast=True`` -> einmal generieren,
    an ALLE Spieler verteilen (Galaxie-News). Additiv: ein Basis-Bericht existiert ohnehin.
    ``ttype`` = Ziel-Transmission-Typ (z.B. ``spy_report`` fuer Spionage). Default ``routine`` —
    NIE ``big_moment``, ausser der Aufrufer will es ausdruecklich (sonst falsches "Großmoment")."""
    job: dict = {
        "job_type": "flavor",
        "context": {
            "narrator": narrator,
            "situation": situation,
            "planet": planet,
            "outcome": outcome,
            "detail": detail or {},
            "subject": subject,
            "broadcast": broadcast,
            "ttype": ttype,
        },
    }
    if player_id is not None:
        job["player_id"] = str(player_id)
    await event_bus.enqueue_job(job)


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
        # persona_init, solange noch nicht 'named' (deckt leere Persona UND Alt-NPCs ohne
        # evokativen Namen ab -> einmalige Umbenennung); danach nur noch nightly_batch.
        if (persona or {}).get("named"):
            await event_bus.enqueue_job({"job_type": "nightly_batch", "npc_id": str(nid)})
        else:
            await event_bus.enqueue_job({"job_type": "persona_init", "npc_id": str(nid)})
        npc_n += 1
    if cmd_ids or npc_n:
        log.info("AI-Banken-Tick: %d Commander + %d NPC eingereiht", len(cmd_ids), npc_n)


async def bootstrap_nightly_batches() -> None:
    """Startup-Bootstrap (Befund #10): reiht die Nacht-Batches NUR ein, wenn die Reaktions-Banken
    noch komplett leer sind (frischer Deploy). Sind bereits Banken vorhanden, uebernimmt der
    24h-Scheduler die Pflege -> kein erneutes Fluten der Job-Queue bei jedem (Dev-)Neustart."""
    async with session_scope() as session:
        bank_count = int((await session.execute(
            select(func.count()).select_from(ReactionBank)
        )).scalar_one() or 0)
    if bank_count > 0:
        log.info("AI-Bootstrap uebersprungen: %d Banken vorhanden (24h-Scheduler pflegt nach)", bank_count)
        return
    await enqueue_nightly_batches()
