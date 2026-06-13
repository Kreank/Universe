"""Router fuer Forschung (api-contract §4)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import Planet, Player, Research
from app.platform.security import get_current_player
from app.research.schemas import (
    CostOut,
    RequirementOut,
    ResearchOptionOut,
    ResearchResponse,
    ResearchStateOut,
    StartResearchRequest,
    StartResearchResponse,
)
from app.research.service import cancel_research, research_options, start_research

router = APIRouter(tags=["research"])


async def _homeworld(session: AsyncSession, player: Player) -> Planet | None:
    return (await session.execute(
        select(Planet)
        .where(Planet.player_id == player.id)
        .order_by(Planet.is_homeworld.desc(), Planet.created_at)
    )).scalars().first()


@router.get("/research", response_model=ResearchResponse)
async def get_research(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> ResearchResponse:
    rows = (await session.execute(
        select(Research).where(Research.player_id == player.id)
    )).scalars().all()
    # Verfuegbarkeit wird gegen die Heimatwelt (Labor-Standardstandort) gerechnet.
    home = await _homeworld(session, player)
    options = await research_options(session, player.id, home)
    return ResearchResponse(
        research=[
            ResearchStateOut(type=r.type, level=r.level, finishes_at=r.finishes_at) for r in rows
        ],
        available=[
            ResearchOptionOut(
                type=o["type"],
                next_level=o["next_level"],
                cost=CostOut(**o["cost"]),
                research_seconds=o["research_seconds"],
                can_afford=o["can_afford"],
                requirements_met=o["requirements_met"],
                requirements=[RequirementOut(**r) for r in o.get("requirements", [])],
            )
            for o in options
        ],
    )


@router.post("/research/{type}/start", status_code=202, response_model=StartResearchResponse)
async def start_research_endpoint(
    type: str,
    body: StartResearchRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> StartResearchResponse:
    planet = await session.get(Planet, uuid.UUID(body.planet_id))
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    try:
        row = await start_research(session, planet, type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return StartResearchResponse(
        type=row.type,
        level=row.level + 1,
        finishes_at=row.finishes_at,
    )


@router.post("/research/cancel", response_model=StartResearchResponse)
async def cancel_research_endpoint(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> StartResearchResponse:
    # Refund auf die Heimatwelt (Labor-Standardstandort).
    home = await _homeworld(session, player)
    if home is None:
        raise HTTPException(status_code=404, detail="Keine Heimatwelt gefunden")
    try:
        row = await cancel_research(session, home)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return StartResearchResponse(type=row.type, level=row.level, finishes_at=None)
