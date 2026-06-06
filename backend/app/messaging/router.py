"""Router fuer Postfach/Funksprueche (api-contract §8)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.schemas import (
    DecideRequest,
    DecideResponse,
    OkResponse,
    TransmissionOut,
)
from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import Commander, Player, Transmission
from app.platform.security import get_current_player

router = APIRouter(tags=["messaging"])


@router.get("/transmissions", response_model=list[TransmissionOut])
async def list_transmissions(
    unread: bool = False,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[Transmission]:
    stmt = select(Transmission).where(Transmission.player_id == player.id)
    if unread:
        stmt = stmt.where(Transmission.read.is_(False))
    stmt = stmt.order_by(Transmission.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


@router.post("/transmissions/{transmission_id}/read", response_model=OkResponse)
async def mark_read(
    transmission_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> OkResponse:
    t = await session.get(Transmission, transmission_id)
    if t is None or t.player_id != player.id:
        raise HTTPException(status_code=404, detail="Transmission nicht gefunden")
    t.read = True
    return OkResponse(ok=True)


@router.post("/transmissions/{transmission_id}/decide", response_model=DecideResponse)
async def decide(
    transmission_id: uuid.UUID,
    body: DecideRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> DecideResponse:
    """Forderungs-Mechanik (Doku 05 §7). Kein LLM noetig."""
    t = await session.get(Transmission, transmission_id)
    if t is None or t.player_id != player.id:
        raise HTTPException(status_code=404, detail="Transmission nicht gefunden")
    if not t.requires_decision:
        raise HTTPException(status_code=409, detail="Diese Transmission erfordert keine Entscheidung")
    if body.choice not in ("accept", "reject", "negotiate"):
        raise HTTPException(status_code=400, detail="Ungueltige Wahl")

    bal = get_balance()
    deltas = bal.commander["morale"]["deltas"]
    if body.choice == "accept":
        morale_delta = deltas["demand_fulfilled"]
        message = "Forderung erfuellt. Die Crew ist zufrieden."
    elif body.choice == "reject":
        morale_delta = deltas["demand_ignored"]
        message = "Forderung abgelehnt. Die Moral leidet."
    else:  # negotiate -> halber positiver Effekt
        morale_delta = deltas["demand_fulfilled"] // 2
        message = "Kompromiss gefunden. Teilweise zufrieden."

    if t.commander_id:
        commander = await session.get(Commander, t.commander_id)
        if commander is not None:
            commander.morale = max(0, min(100, commander.morale + morale_delta))
            commander.loyalty = max(0, min(100, commander.loyalty + (morale_delta // 2)))

    t.requires_decision = False
    t.read = True
    return DecideResponse(ok=True, morale_delta=morale_delta, message=message)
