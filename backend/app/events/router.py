"""API für Game-Events: aktive Welt-Events anzeigen + Event-Entscheidungen treffen."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.decisions import VALID_CHOICES, decide_event
from app.events.service import active_map_events
from app.platform.db import get_session
from app.platform.models import Player, Transmission
from app.platform.security import get_current_player

router = APIRouter(tags=["events"])


class EventOut(BaseModel):
    id: str
    event_type: str
    scope: str
    galaxy: int | None = None
    system: int | None = None
    position: int | None = None
    coords: str | None = None
    data: dict = {}
    expires_at: str


class DecideEventRequest(BaseModel):
    transmission_id: uuid.UUID
    choice: str


@router.get("/events", response_model=list[EventOut])
async def list_events(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[EventOut]:
    """Aktuell laufende Welt-/Karten-Events (für die Galaxie-Karte + ein Event-Panel)."""
    rows = await active_map_events(session)
    out: list[EventOut] = []
    for ev in rows:
        coords = (
            f"{ev.galaxy}:{ev.system}:{ev.position}" if ev.position is not None
            else (f"{ev.galaxy}:{ev.system}" if ev.system is not None else None)
        )
        # Interne Felder (NPC-IDs etc.) nicht ausliefern.
        public = {k: v for k, v in (ev.data or {}).items() if k not in ("npc_id",)}
        out.append(EventOut(
            id=str(ev.id), event_type=ev.event_type, scope=ev.scope,
            galaxy=ev.galaxy, system=ev.system, position=ev.position, coords=coords,
            data=public, expires_at=ev.expires_at.isoformat(),
        ))
    return out


@router.post("/events/decide")
async def decide(
    body: DecideEventRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trifft eine offline-sichere Event-Entscheidung (z. B. Minen-Streik: bestechen/niederschlagen)."""
    t = await session.get(Transmission, body.transmission_id)
    if t is None or t.player_id != player.id:
        raise HTTPException(status_code=404, detail="Funkspruch nicht gefunden")
    if not t.requires_decision or (t.decision_payload or {}).get("kind") != "event":
        raise HTTPException(status_code=409, detail="Keine offene Event-Entscheidung")
    choices = (t.decision_payload or {}).get("choices", [])
    if body.choice not in choices or body.choice not in VALID_CHOICES:
        raise HTTPException(status_code=422, detail="Ungültige Wahl")
    msg = await decide_event(session, t, body.choice)
    await session.commit()
    return {"ok": True, "message": msg}
