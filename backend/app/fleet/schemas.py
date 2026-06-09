"""Pydantic-Schemas fuer Flotten (api-contract §6)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


class TargetCoords(BaseModel):
    galaxy: int
    system: int
    position: int


class FleetOut(BaseModel):
    id: uuid.UUID
    mission: str
    status: str
    origin: str | None = None
    target: TargetCoords
    commander_id: uuid.UUID | None = None
    ships: dict[str, int]
    cargo: dict
    depart_at: dt.datetime
    arrive_at: dt.datetime
    return_at: dt.datetime | None = None


class IncomingAttackOut(BaseModel):
    id: uuid.UUID
    attacker: str
    origin: str | None = None
    target: TargetCoords
    ships_total: int
    arrive_at: dt.datetime


class SendFleetRequest(BaseModel):
    origin_planet_id: str
    target: TargetCoords
    mission: str
    ships: dict[str, int]
    cargo: dict = Field(default_factory=dict)
    commander_id: str | None = None
    speed_pct: int = 100
    # Handel (mission == 'trade'): die Angebots-Ressource faehrt als Fracht mit,
    # getauscht wird gegen want_res zu dynamischen Preisen (Slippage).
    offer_res: str | None = None
    offer_amount: float | None = None
    want_res: str | None = None
