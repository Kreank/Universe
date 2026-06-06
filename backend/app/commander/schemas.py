"""Pydantic-Schemas fuer Commander (api-contract §7)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel


class MoraleBandOut(BaseModel):
    label: str
    combat_mod: float


class CommanderOut(BaseModel):
    id: uuid.UUID
    name: str
    persona: dict
    traits: list[str]
    specialization: str
    rank: str
    xp: int
    morale: int
    loyalty: int
    span_capacity: int
    status: str
    morale_band: MoraleBandOut
    assigned_fleet_id: uuid.UUID | None = None
    training_finishes_at: dt.datetime | None = None


class CommanderDetailOut(CommanderOut):
    history: list[dict] = []


class TrainRequest(BaseModel):
    planet_id: str


class TrainResponse(BaseModel):
    commander: CommanderOut


class SpanOut(BaseModel):
    base: int
    from_command_center: int
    from_doctrine: int
    total: int
    in_use: int
