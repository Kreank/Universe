"""API der Lebenden Galaxie-Chronik (Welle 3): veroeffentlichte Saga-Eintraege auflisten."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import GameChronicle, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["chronicle"])


class ChronicleOut(BaseModel):
    id: str
    title: str
    body: str
    narrator: str
    span_start: str | None = None
    span_end: str | None = None
    key_events: list = []   # nur die Fakten-Liste (Snapshot wird nicht ausgeliefert)
    published_at: str | None = None


def _events(key_events) -> list:
    """Liefert die reine Fakten-Liste aus dem gespeicherten ``{"events":[...],"snapshot":{...}}``
    (oder eine Alt-Form, die bereits eine Liste ist)."""
    if isinstance(key_events, dict):
        return list(key_events.get("events") or [])
    if isinstance(key_events, list):
        return key_events
    return []


@router.get("/chronicle", response_model=list[ChronicleOut])
async def list_chronicle(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[ChronicleOut]:
    """Veroeffentlichte Chronik-Eintraege, neueste zuerst (paginierbar)."""
    rows = (await session.execute(
        select(GameChronicle)
        .where(GameChronicle.status == "published")
        .order_by(GameChronicle.published_at.desc())
        .limit(limit).offset(offset)
    )).scalars().all()
    return [
        ChronicleOut(
            id=str(c.id), title=c.title, body=c.body, narrator=c.narrator,
            span_start=c.span_start.isoformat() if c.span_start else None,
            span_end=c.span_end.isoformat() if c.span_end else None,
            key_events=_events(c.key_events),
            published_at=c.published_at.isoformat() if c.published_at else None,
        )
        for c in rows
    ]
