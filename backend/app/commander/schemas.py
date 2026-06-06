"""Pydantic-Schemas fuer Commander (api-contract §7)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel


class MoraleBandOut(BaseModel):
    label: str
    combat_mod: float


class BonusOut(BaseModel):
    stat: str       # "attack" | "shield" | "speed"
    target: str     # "all" | Schiffsklasse (fighter/cruiser/capital/civil)
    pct: float      # Basiswert (im Kampf zusaetzlich moral-skaliert)


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
    focus: str | None = None
    bonuses: list[BonusOut] = []
    assigned_fleet_id: uuid.UUID | None = None
    training_finishes_at: dt.datetime | None = None


class CommanderDetailOut(CommanderOut):
    history: list[dict] = []


class TrainRequest(BaseModel):
    planet_id: str
    # Optional: Spezialisierung + Fokus-Schiffsklasse waehlen (sonst Default/auto).
    specialization: str | None = None
    focus: str | None = None


class TrainResponse(BaseModel):
    commander: CommanderOut


class SpanOut(BaseModel):
    base: int
    from_command_center: int
    from_doctrine: int
    total: int
    in_use: int
