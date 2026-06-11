"""Pydantic-Schemas fuer Planet & Wirtschaft (api-contract §2)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict


class PlanetOut(BaseModel):
    # from_attributes: erlaubt FastAPI, ORM-Objekte (Planet) direkt zu serialisieren.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    galaxy: int
    system: int
    position: int
    planet_type: str
    temp_max: int
    fields_used: int
    fields_max: int
    is_homeworld: bool
    governor_commander_id: uuid.UUID | None = None


class BuildingStateOut(BaseModel):
    type: str
    level: int
    upgrade_finishes_at: dt.datetime | None = None


class CountOut(BaseModel):
    type: str
    count: int


class PlanetDetailOut(PlanetOut):
    resources: dict
    buildings: list[BuildingStateOut]
    ships: list[CountOut]
    defenses: list[CountOut]
    # Monde: Mutterplanet-Verknuepfung + letzter Sprung (fuer Sprungtor-Cooldown-Vorschau im FE).
    parent_planet_id: uuid.UUID | None = None
    last_jump_at: dt.datetime | None = None
