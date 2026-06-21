"""Pydantic-Schemas fuer den Ziele/Bedrohungen-Screen (Welle 1)."""
from __future__ import annotations

from pydantic import BaseModel


class CoordsOut(BaseModel):
    galaxy: int
    system: int
    position: int


class NpcTargetOut(BaseModel):
    """Ein entdecktes, angreifbares NPC-Imperium (KEINE Handelszentren)."""
    npc_id: str
    name: str
    behavior_profile: str
    galaxy: int
    system: int
    position: int
    coords: str
    intel_level: int = 1
    ships_total: int = 0
    defenses_total: int = 0
    # Diplomatie-Status aus NpcRelation (None = nie kontaktiert -> faktisch neutral).
    relation_status: str | None = None
    # Galaxien-Distanz zur Heimat des Spielers (None, wenn keine Heimat ermittelbar).
    distance_galaxies: int | None = None
    # Zeitpunkt der letzten Aufklaerung (Discovery-Snapshot).
    last_intel_at: str | None = None


class PlayerTargetOut(BaseModel):
    """Ein entdecktes fremdes Spieler-Imperium."""
    player_id: str | None = None
    name: str
    galaxy: int
    system: int
    position: int
    coords: str
    intel_level: int = 1
    ships_total: int = 0
    # Wirbt der Spieler offen ein P2P-Handelsangebot? (-> Verweis Handel-Reiter)
    has_trade_offer: bool = False
    distance_galaxies: int | None = None
    last_intel_at: str | None = None


class ThreatOut(BaseModel):
    """Eine Bedrohung: eingehender Angriff ODER feindliches NPC in der Naehe."""
    kind: str  # 'incoming' | 'hostile_npc'
    name: str
    # Bei 'incoming': Angreifer-Art ('npc' | 'player'); bei 'hostile_npc': None.
    attacker_kind: str | None = None
    npc_id: str | None = None  # nur bei 'hostile_npc' gesetzt (Deep-Link Diplomatie/Angriff)
    origin: str | None = None  # Quell-Koordinate ("g:s:p") soweit bekannt
    target: CoordsOut | None = None  # angegriffener eigener Planet (nur 'incoming')
    arrive_at: str | None = None  # Ankunftszeit (nur 'incoming') -> Fleetsave-Countdown
    ships_total: int = 0
    intel_level: int = 1
    distance_galaxies: int | None = None  # nur 'hostile_npc'
    mission: str | None = None  # 'attack' o. ae. (nur 'incoming')
    priority: int = 0  # 0 = akut (eingehend), 1 = latent (feindlich nah)
