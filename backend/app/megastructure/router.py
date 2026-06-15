"""Router fuer Endgame-Megastrukturen."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.megastructure.schemas import (
    BuildMegastructureResponse,
    MegaCostOut,
    MegastructureListOut,
    MegastructureOptionOut,
)
from app.megastructure.service import homeworld_exotics, options, start_build
from app.platform.db import get_session
from app.platform.models import Player
from app.platform.security import get_current_player

router = APIRouter(tags=["megastructure"])


@router.get("/megastructures", response_model=MegastructureListOut)
async def get_megastructures(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> MegastructureListOut:
    opts = await options(session, player)
    exo = await homeworld_exotics(session, player.id)
    return MegastructureListOut(
        dark_matter=exo["dark_matter"],
        antimatter=exo["antimatter"],
        structures=[
            MegastructureOptionOut(**{**o, "cost": MegaCostOut(**o["cost"])}) for o in opts
        ],
    )


@router.post("/megastructures/{mtype}/build", response_model=BuildMegastructureResponse)
async def build_megastructure(
    mtype: str,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> BuildMegastructureResponse:
    try:
        row = await start_build(session, player, mtype)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await session.commit()
    return BuildMegastructureResponse(
        type=row.type, level=row.level, building_until=row.building_until
    )
