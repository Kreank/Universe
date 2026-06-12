"""Pydantic-Modelle fuer die Job-Payloads aus der Redis-Queue `ai:jobs`.

Format laut shared/events.md. `extra="allow"`, weil der game-server jederzeit
zusaetzliche Kontextfelder mitschicken darf, ohne den Worker zu brechen.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

JobType = Literal["big_moment", "nightly_batch", "persona_init"]


class JobContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    situation: Optional[str] = None
    enemy: Optional[str] = None
    planet: Optional[str] = None
    loot: Optional[dict[str, Any]] = None
    outcome: Optional[str] = None


class Job(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_type: JobType
    commander_id: Optional[str] = None
    npc_id: Optional[str] = None
    player_id: Optional[str] = None
    context: JobContext = Field(default_factory=JobContext)
    enqueued_at: Optional[str] = None
