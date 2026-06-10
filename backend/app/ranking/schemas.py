"""Pydantic-Schemas fuer die Rangliste."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class RankingEntryOut(BaseModel):
    rank: int
    player_id: uuid.UUID
    display_name: str
    is_self: bool
    points: int
    # Aufschluesselung (jeweils in Punkten = investierte Ress / 1000).
    buildings: int
    research: int
    fleet: int
    defense: int


class RankingResponse(BaseModel):
    entries: list[RankingEntryOut]
    me: RankingEntryOut | None
    total_players: int
