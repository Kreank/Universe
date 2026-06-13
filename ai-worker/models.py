"""Pydantic-Modelle fuer die Job-Payloads aus der Redis-Queue `ai:jobs`.

Format laut shared/events.md. `extra="allow"`, weil der game-server jederzeit
zusaetzliche Kontextfelder mitschicken darf, ohne den Worker zu brechen.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

JobType = Literal["big_moment", "nightly_batch", "persona_init", "flavor"]


class JobContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    situation: Optional[str] = None
    enemy: Optional[str] = None
    planet: Optional[str] = None
    loot: Optional[dict[str, Any]] = None
    outcome: Optional[str] = None
    # Flavor-Jobs (Phase 2): erzaehlerischer Text ohne Entitaet/Bank (Spionage, Expedition, …).
    narrator: Optional[str] = None
    subject: Optional[str] = None
    detail: Optional[dict[str, Any]] = None
    # Ziel-Transmission-Typ der Flavor-Nachricht (spy_report/system/routine/…). Default routine —
    # NIE big_moment, ausser explizit gewollt (sonst landet z.B. ein Spio-Text als "Großmoment").
    ttype: Optional[str] = None
    # Broadcast (Phase 4, Galaxie-News): einmal generieren, an ALLE aktiven Spieler verteilen.
    broadcast: Optional[bool] = None


class Job(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_type: JobType
    commander_id: Optional[str] = None
    npc_id: Optional[str] = None
    player_id: Optional[str] = None
    context: JobContext = Field(default_factory=JobContext)
    enqueued_at: Optional[str] = None
