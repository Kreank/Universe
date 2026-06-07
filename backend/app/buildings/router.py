"""Router fuer Gebaeude (api-contract §3)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.buildings.schemas import (
    BuildingOptionOut,
    BuildingsResponse,
    BuildingStateOut,
    BuildQueueItemOut,
    CostOut,
    DemolishResponse,
    RequirementOut,
    ShipOptionOut,
    ShipyardBuildRequest,
    ShipyardBuildResponse,
    ShipyardResponse,
    UpgradeResponse,
)
from app.buildings.service import building_options, demolish_building, start_upgrade
from app.buildings.shipyard import queue_build, shipyard_view
from app.platform.db import get_session
from app.platform.models import Building, Planet, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["buildings"])


async def _owned_planet(session: AsyncSession, player: Player, planet_id: uuid.UUID) -> Planet:
    planet = await session.get(Planet, planet_id)
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    return planet


@router.get("/planets/{planet_id}/buildings", response_model=BuildingsResponse)
async def get_buildings(
    planet_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> BuildingsResponse:
    planet = await _owned_planet(session, player, planet_id)
    rows = (await session.execute(
        select(Building).where(Building.planet_id == planet.id)
    )).scalars().all()
    options = await building_options(session, planet)
    return BuildingsResponse(
        buildings=[
            BuildingStateOut(type=b.type, level=b.level, upgrade_finishes_at=b.upgrade_finishes_at)
            for b in rows
        ],
        available=[
            BuildingOptionOut(
                type=o["type"],
                next_level=o["next_level"],
                cost=CostOut(**o["cost"]),
                build_seconds=o["build_seconds"],
                can_afford=o["can_afford"],
                requirements_met=o["requirements_met"],
                requirements=[RequirementOut(**r) for r in o.get("requirements", [])],
                energy_now=o["energy_now"],
                energy_next=o["energy_next"],
                energy_delta=o["energy_delta"],
            )
            for o in options
        ],
    )


@router.post("/planets/{planet_id}/buildings/{type}/upgrade", status_code=202, response_model=UpgradeResponse)
async def upgrade_building(
    planet_id: uuid.UUID,
    type: str,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> UpgradeResponse:
    planet = await _owned_planet(session, player, planet_id)
    try:
        row = await start_upgrade(session, planet, type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return UpgradeResponse(
        type=row.type,
        level=row.level + 1,  # Stufe, die gerade gebaut wird
        upgrade_finishes_at=row.upgrade_finishes_at,
    )


@router.post("/planets/{planet_id}/buildings/{type}/demolish", response_model=DemolishResponse)
async def demolish_building_route(
    planet_id: uuid.UUID,
    type: str,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> DemolishResponse:
    planet = await _owned_planet(session, player, planet_id)
    try:
        row = await demolish_building(session, planet, type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DemolishResponse(type=row.type, level=row.level)


def _to_ship_options(items: list[dict]) -> list[ShipOptionOut]:
    return [
        ShipOptionOut(
            type=o["type"],
            cost=CostOut(**o["cost"]),
            build_seconds_each=o["build_seconds_each"],
            can_build=o["can_build"],
            requirements_met=o["requirements_met"],
            requirements=[RequirementOut(**r) for r in o.get("requirements", [])],
        )
        for o in items
    ]


@router.get("/planets/{planet_id}/shipyard", response_model=ShipyardResponse)
async def get_shipyard(
    planet_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> ShipyardResponse:
    planet = await _owned_planet(session, player, planet_id)
    view = await shipyard_view(session, planet)
    return ShipyardResponse(
        ships=_to_ship_options(view["ships"]),
        defenses=_to_ship_options(view["defenses"]),
        queue=[BuildQueueItemOut(**q) for q in view["queue"]],
    )


@router.post("/planets/{planet_id}/shipyard/build", status_code=202, response_model=ShipyardBuildResponse)
async def build_shipyard(
    planet_id: uuid.UUID,
    body: ShipyardBuildRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> ShipyardBuildResponse:
    planet = await _owned_planet(session, player, planet_id)
    try:
        queue = await queue_build(session, planet, body.type, body.count, body.category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ShipyardBuildResponse(queue=[BuildQueueItemOut(**q) for q in queue])
