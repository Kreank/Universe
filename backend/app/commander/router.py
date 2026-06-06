"""Router fuer Commander & Span (api-contract §7)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commander.schemas import (
    CommanderDetailOut,
    CommanderOut,
    SpanOut,
    TrainRequest,
    TrainResponse,
)
from app.commander.service import commander_to_dict, compute_span, start_training
from app.messaging.service import transmission_to_dict
from app.platform.db import get_session
from app.platform.models import Commander, Planet, Player, Transmission
from app.platform.security import get_current_player

router = APIRouter(tags=["commander"])


@router.get("/commanders", response_model=list[CommanderOut])
async def list_commanders(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (await session.execute(
        select(Commander).where(Commander.player_id == player.id).order_by(Commander.created_at)
    )).scalars().all()
    return [await commander_to_dict(session, c) for c in rows]


@router.get("/player/span", response_model=SpanOut)
async def get_span(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> SpanOut:
    span = await compute_span(session, player.id)
    return SpanOut(**span)


@router.get("/commanders/{commander_id}", response_model=CommanderDetailOut)
async def get_commander(
    commander_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    c = await session.get(Commander, commander_id)
    if c is None or c.player_id != player.id:
        raise HTTPException(status_code=404, detail="Commander nicht gefunden")
    data = await commander_to_dict(session, c)
    history = (await session.execute(
        select(Transmission)
        .where(Transmission.commander_id == c.id)
        .order_by(Transmission.created_at.desc())
    )).scalars().all()
    data["history"] = [transmission_to_dict(t) for t in history]
    return data


@router.post("/commanders/train", status_code=202, response_model=TrainResponse)
async def train_commander(
    body: TrainRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> TrainResponse:
    planet = await session.get(Planet, uuid.UUID(body.planet_id))
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    try:
        commander = await start_training(session, planet)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    data = await commander_to_dict(session, commander)
    return TrainResponse(commander=CommanderOut(**data))