"""Pydantic-Schemas fuer Megastrukturen."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class MegaCostOut(BaseModel):
    metal: float = 0
    crystal: float = 0
    deuterium: float = 0
    dark_matter: float = 0


class MegastructureOptionOut(BaseModel):
    type: str
    name: str
    level: int
    max_level: int
    next_level: int
    cost: MegaCostOut
    build_seconds: int
    effect: str | None = None
    effect_per_level: float = 0
    blurb: str = ""
    building_until: dt.datetime | None = None
    busy: bool
    maxed: bool
    can_afford: bool


class MegastructureListOut(BaseModel):
    dark_matter: float
    antimatter: float
    structures: list[MegastructureOptionOut]


class BuildMegastructureResponse(BaseModel):
    type: str
    level: int
    building_until: dt.datetime | None
