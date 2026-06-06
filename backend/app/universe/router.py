"""Router fuer das Universum/Galaxie-Ansicht (api-contract §6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import NpcEmpire, Planet, Player, UniverseCell
from app.platform.security import get_current_player

router = APIRouter(tags=["universe"])


class CellOut(BaseModel):
    position: int
    occupant_type: str
    name: str | None = None
    player_id: str | None = None
    npc_id: str | None = None


class GalaxyViewOut(BaseModel):
    cells: list[CellOut]


@router.get("/galaxy/{galaxy}/{system}", response_model=GalaxyViewOut)
async def galaxy_view(
    galaxy: int,
    system: int,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> GalaxyViewOut:
    bal = get_balance()
    rows = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == galaxy, UniverseCell.system == system
        )
    )).scalars().all()
    by_pos = {c.position: c for c in rows}

    cells: list[CellOut] = []
    for pos in range(1, bal.positions_per_system + 1):
        cell = by_pos.get(pos)
        if cell is None or cell.occupant_type == "empty":
            cells.append(CellOut(position=pos, occupant_type="empty"))
            continue
        name = None
        player_id = None
        npc_id = None
        if cell.occupant_type == "player" and cell.ref_id:
            planet = await session.get(Planet, cell.ref_id)
            if planet:
                name = planet.name
                player_id = str(planet.player_id)
        elif cell.occupant_type == "npc" and cell.ref_id:
            npc = await session.get(NpcEmpire, cell.ref_id)
            if npc:
                name = npc.name
                npc_id = str(npc.id)
        cells.append(CellOut(
            position=pos,
            occupant_type=cell.occupant_type,
            name=name,
            player_id=player_id,
            npc_id=npc_id,
        ))
    return GalaxyViewOut(cells=cells)
