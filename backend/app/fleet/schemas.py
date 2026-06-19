"""Pydantic-Schemas fuer Flotten (api-contract §6)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field


class TargetCoords(BaseModel):
    galaxy: int
    system: int
    position: int


class MiningProgressOut(BaseModel):
    """Live-Schuerf-Fortschritt (Frachtbalken) waehrend einer zeitbasierten Mining-Session."""
    metal: float
    crystal: float
    filled: float       # bisher gefuellte Frachtmenge
    capacity: float     # voller Frachtraum
    progress: float     # 0..1


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
    # Nur bei laufender Mining-Session gesetzt: Live-Frachtbalken.
    mining: MiningProgressOut | None = None


class IncomingAttackOut(BaseModel):
    id: uuid.UUID
    attacker: str
    kind: str = "npc"  # 'npc' | 'player'
    origin: str | None = None
    target: TargetCoords
    ships_total: int
    arrive_at: dt.datetime
    mission: str = "attack"
    # Aufklaerungsstufe des Betrachters (1..3, analog Planeten-Spionage):
    # L1 = nur Gesamtstaerke, L2 (spy_tech>=2) = + Flotten-Zusammensetzung, L3 (spy_tech>=4) = + Fracht.
    intel_level: int = 1
    # Schiffs-Zusammensetzung (nur ab Aufklaerungsstufe 2 befuellt, sonst None).
    ships: dict[str, int] | None = None
    # Mitgefuehrte Fracht (nur ab Aufklaerungsstufe 3 befuellt, sonst None).
    cargo: dict | None = None


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
    # Gewaehlte Eskort-Patrouillen (StationedFleet-IDs), die die Route decken sollen.
    escort_ids: list[str] = Field(default_factory=list)
    # Scharfzuschaltende erlernte Kommandeur-Faehigkeiten (Keys; bis arm_slots).
    ability_keys: list[str] = Field(default_factory=list)
    # Expedition (mission == 'expedition'): gewuenschte Verweildauer in Stunden (1..max, max aus Astrophysik).
    expedition_hours: int | None = None
    # Expeditions-Doktrin (offline-sichere Vorab-Wahl): 'cautious' | 'bold' (sonst neutral).
    expedition_doctrine: str | None = None
    # Ziel-Typ an der Koordinate: 'moon' greift/spioniert den Mond statt des Planeten (sonst Planet).
    target_type: str | None = None
    # Kapern (mission == 'attack'): bevorzugtes Kaperziel — Schiffstyp-Key oder 'value' (teuerste zuerst, Default).
    capture_priority: str | None = None
    # Abfangen (mission == 'intercept'): Patrouillen-Radius in Systemen (Default 0 = nur Zielsystem).
    radius: int | None = None
    # Eskorte (mission == 'escort'): Deckungs-Radius in Systemen + Gebuehr (Anteil 0..max_fee_pct).
    escort_radius: int | None = None
    escort_fee_pct: float | None = None
