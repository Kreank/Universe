"""Pydantic-Schemas fuer Gebaeude (api-contract §3)."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class CostOut(BaseModel):
    metal: float
    crystal: float
    deuterium: float
    # Exotische Endgame-Kosten (Capstone-Schiffe), kontoweit. 0 = nicht relevant.
    antimatter: float = 0
    dark_matter: float = 0


class RequirementOut(BaseModel):
    """Eine einzelne Voraussetzung (Forschung ODER Gebaeude) mit Erfuellungs-Status."""
    type: str
    level: int
    met: bool


class BuildingStateOut(BaseModel):
    type: str
    level: int
    upgrade_finishes_at: dt.datetime | None = None


class BuildingOptionOut(BaseModel):
    type: str
    next_level: int
    cost: CostOut
    build_seconds: int
    can_afford: bool
    requirements_met: bool
    requirements: list[RequirementOut] = []
    # Energiebilanz dieses Gebaeudes (Vorzeichen: + erzeugt, - verbraucht, 0 = neutral).
    energy_now: float = 0.0      # bei aktueller Stufe
    energy_next: float = 0.0     # bei naechster Stufe
    energy_delta: float = 0.0    # Veraenderung durch den Ausbau
    # Positions-Gate (Exo-Minen): auf diesem Planeten-Slot baubar? + erlaubte Positionen.
    position_ok: bool = True
    allowed_positions: list[int] = []


class BuildingsResponse(BaseModel):
    buildings: list[BuildingStateOut]
    available: list[BuildingOptionOut]


class UpgradeResponse(BaseModel):
    type: str
    level: int
    # None nach einem Abbruch (kein laufender Ausbau mehr) — sonst scheitert die Antwort-
    # Serialisierung des cancel-Endpunkts (Befund: ValidationError -> verwaister Build-Job).
    upgrade_finishes_at: dt.datetime | None = None


class DemolishResponse(BaseModel):
    type: str
    level: int  # neue Stufe nach dem Abriss


# -- Werft (api-contract §5) ---------------------------------------------------
class CapstoneInfoOut(BaseModel):
    """Besitz-Status eines Capstone-Schiffs (Endgame): wie viele besessen / erlaubt."""
    owned: int
    cap: int


class ShipOptionOut(BaseModel):
    type: str
    cost: CostOut
    build_seconds_each: int
    can_build: bool
    requirements_met: bool
    requirements: list[RequirementOut] = []
    weapon_type: str | None = None
    drive: int | None = None
    range: str | None = None
    capstone: CapstoneInfoOut | None = None
    # Pro-Planet-Limit (z. B. Schildkuppeln 1; null = unbegrenzt) + aktueller Bestand inkl. Queue.
    max_per_planet: int | None = None
    planet_owned: int | None = None


class BuildQueueItemOut(BaseModel):
    id: str
    type: str
    count: int
    category: str
    finishes_at: dt.datetime


class ShipyardResponse(BaseModel):
    ships: list[ShipOptionOut]
    defenses: list[ShipOptionOut]
    queue: list[BuildQueueItemOut]


class ShipyardBuildRequest(BaseModel):
    type: str
    count: int
    category: str  # "ship" | "defense"


class ShipyardBuildResponse(BaseModel):
    queue: list[BuildQueueItemOut]
