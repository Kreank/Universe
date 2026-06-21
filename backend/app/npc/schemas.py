"""Pydantic-Schemas fuer die NPC-Diplomatie (Welle 1)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict


class NegotiateRequest(BaseModel):
    """Kontaktaufnahme/Verhandlung mit einem NPC-Imperium.

    ``offer_type``: 'alliance' | 'ceasefire' | 'tribute'.
    ``tribute_metal``: bei 'tribute' angebotenes Metall je Zyklus (wird auf Caps + Bestand geklemmt).
    ``ceasefire_hours``: bei 'ceasefire' gewuenschte Dauer (auf Cap geklemmt; 0 = volle Cap).
    ``message``: optionaler Freitext des Spielers — wird im Prompt als DATEN behandelt, nie als
    Instruktion (Anti-Prompt-Injection)."""
    offer_type: str
    tribute_metal: int = 0
    ceasefire_hours: int = 0
    message: str | None = None


class NegotiateResponse(BaseModel):
    ok: bool = True
    status: str          # aktueller Beziehungsstatus (vor der KI-Antwort)
    message: str         # UI-Hinweis ("Funkspruch unterwegs ...")


class RelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    npc_id: uuid.UUID
    status: str
    alliance_since: dt.datetime | None = None
    ceasefire_until: dt.datetime | None = None
    tribute_metal_per_cycle: float = 0.0
    betrayed_by_player: bool = False
    betrayed_by_npc: bool = False
    message_count: int = 0
    positive_actions: int = 0
    negative_actions: int = 0
    last_decision_at: dt.datetime | None = None


class RelationListItem(BaseModel):
    """Ein Eintrag der Diplomatie-Uebersicht: NpcRelation-Felder + Name/Koordinaten des
    Imperiums (Join NpcEmpire). Fuer GET /api/npc/relations — der Diplomatie-Reiter."""
    npc_id: uuid.UUID
    npc_name: str
    galaxy: int
    system: int
    position: int
    coords: str
    status: str
    alliance_since: dt.datetime | None = None
    ceasefire_until: dt.datetime | None = None
    tribute_metal_per_cycle: float = 0.0
    betrayed_by_player: bool = False
    betrayed_by_npc: bool = False
    broken_at: dt.datetime | None = None
    message_count: int = 0
    positive_actions: int = 0
    negative_actions: int = 0
    last_decision_at: dt.datetime | None = None
