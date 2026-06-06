"""Router fuer Flotten (api-contract §6)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fleet.schemas import FleetOut, SendFleetRequest
from app.fleet.service import fleet_to_dict, recall_fleet, send_fleet
from app.platform.db import get_session
from app.platform.models import Fleet, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["fleet"])


@router.get("/fleets", response_model=list[FleetOut])
async def list_fleets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (await session.execute(
        select(Fleet)
        .where(Fleet.player_id == player.id, Fleet.status != "done")
        .order_by(Fleet.created_at.desc())
    )).scalars().all()
    return [await fleet_to_dict(session, f) for f in rows]


@router.post("/fleets/send", status_code=202, response_model=FleetOut)
async def send(
    body: SendFleetRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        fleet = await send_fleet(
            session,
            player,
            origin_planet_id=uuid.UUID(body.origin_planet_id),
            target=(body.target.galaxy, body.target.system, body.target.position),
            mission=body.mission,
            ships=body.ships,
            cargo=body.cargo,
            commander_id=uuid.UUID(body.commander_id) if body.commander_id else None,
            speed_pct=body.speed_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await fleet_to_dict(session, fleet)


@router.post("/fleets/{fleet_id}/recall", response_model=FleetOut)
async def recall(
    fleet_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        fleet = await recall_fleet(session, player, fleet_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await fleet_to_dict(session, fleet)
