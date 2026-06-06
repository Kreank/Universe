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


class TargetOut(BaseModel):
    """Ein bekanntes (PvE-)Ziel — damit der Spieler weiss, wen er angreifen kann."""
    npc_id: str
    name: str
    galaxy: int
    system: int
    position: int
    coords: str
    ships_total: int
    defenses_total: int


@router.get("/galaxy/targets", response_model=list[TargetOut])
async def galaxy_targets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[TargetOut]:
    """Verzeichnis bekannter NPC-Ziele (PvE). Sortiert nach Koordinaten.

    Im Vertical Slice sind alle NPCs 'bekannt'; spaeter koppelbar an Spionage/Reichweite."""
    rows = (await session.execute(
        select(NpcEmpire).order_by(NpcEmpire.galaxy, NpcEmpire.system, NpcEmpire.position)
    )).scalars().all()
    out: list[TargetOut] = []
    for npc in rows:
        ships_total = sum(int(v) for v in (npc.fleet or {}).values())
        def_total = sum(int(v) for v in (npc.defenses or {}).values())
        out.append(TargetOut(
            npc_id=str(npc.id),
            name=npc.name,
            galaxy=npc.galaxy,
            system=npc.system,
            position=npc.position,
            coords=f"{npc.galaxy}:{npc.system}:{npc.position}",
            ships_total=ships_total,
            defenses_total=def_total,
        ))
    return out


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
