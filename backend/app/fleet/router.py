"""Router fuer Flotten (api-contract §6)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fleet.schemas import FleetOut, IncomingAttackOut, SendFleetRequest
from app.fleet.service import fleet_to_dict, list_incoming_attacks, recall_fleet, send_fleet
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


@router.get("/incoming-attacks", response_model=list[IncomingAttackOut])
async def incoming_attacks(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_incoming_attacks(session, player.id)


@router.post("/fleets/send", status_code=202, response_model=FleetOut)
async def send(
    body: SendFleetRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cargo = body.cargo
    mission_data: dict = {}
    # Handel: Angebots-Ressource faehrt als Fracht mit; Auftrag in mission_data.
    if body.mission == "trade":
        if body.offer_res is None or body.want_res is None or body.offer_amount is None:
            raise HTTPException(status_code=422, detail="Handel benoetigt offer_res, offer_amount und want_res")
        mission_data = {
            "offer_res": body.offer_res,
            "offer_amount": body.offer_amount,
            "want_res": body.want_res,
        }
        cargo = {body.offer_res: body.offer_amount}
    try:
        fleet = await send_fleet(
            session,
            player,
            origin_planet_id=uuid.UUID(body.origin_planet_id),
            target=(body.target.galaxy, body.target.system, body.target.position),
            mission=body.mission,
            ships=body.ships,
            cargo=cargo,
            commander_id=uuid.UUID(body.commander_id) if body.commander_id else None,
            speed_pct=body.speed_pct,
            mission_data=mission_data,
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


@router.get("/trade/index")
async def trade_index(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Oeffentlicher, immer sichtbarer globaler Handelskurs der Handelszentren.

    Kurs je Ressource (Wert/Einheit) aus dem EMA-geglaetteten Weltvorrat. Damit
    braucht das Handels-UI keine Aufklaerung mehr — der Kurs ist immer abrufbar."""
    from app.fleet.trade_index import get_world_market, index_prices
    from app.platform.balance import get_balance

    wm = await get_world_market(session)
    bal = get_balance()
    prices = index_prices(wm.supply or {}, wm.players or 1, bal.trade)
    return {
        "prices": prices,
        "base_value": bal.trade["base_value"],
        "players": wm.players or 1,
        "updated_at": wm.updated_at.isoformat() if wm.updated_at else None,
    }
