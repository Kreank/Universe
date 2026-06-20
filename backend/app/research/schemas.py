"""Pydantic-Schemas fuer Forschung (api-contract §4)."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class CostOut(BaseModel):
    metal: float
    crystal: float
    deuterium: float


class RequirementOut(BaseModel):
    """Eine einzelne Voraussetzung (Forschung ODER Gebaeude) mit Erfuellungs-Status."""
    type: str
    level: int
    met: bool


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
    requirements: list[RequirementOut] = []


class ResearchResponse(BaseModel):
    research: list[ResearchStateOut]
    available: list[ResearchOptionOut]


class StartResearchRequest(BaseModel):
    planet_id: str


class StartResearchResponse(BaseModel):
    type: str
    level: int
    # None nach einem Abbruch (keine laufende Forschung mehr) — sonst scheitert die Antwort-
    # Serialisierung des cancel-Endpunkts (ValidationError -> HTTP 500). Analog UpgradeResponse.
    finishes_at: dt.datetime | None = None
