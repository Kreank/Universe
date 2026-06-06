"""Pydantic-Schemas fuer Forschung (api-contract §4)."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class CostOut(BaseModel):
    metal: float
    crystal: float
    deuterium: float


class ResearchStateOut(BaseModel):
    type: str
    level: int
    finishes_at: dt.datetime | None = None


class ResearchOptionOut(BaseModel):
    type: str
    next_level: int
    cost: CostOut
    research_seconds: int
    can_afford: bool
    requirements_met: bool


class ResearchResponse(BaseModel):
    research: list[ResearchStateOut]
    available: list[ResearchOptionOut]


class StartResearchRequest(BaseModel):
    planet_id: str


class StartResearchResponse(BaseModel):
    type: str
    level: int
    finishes_at: dt.datetime
