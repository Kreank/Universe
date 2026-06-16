"""Router fuer Planet & Wirtschaft (api-contract §2)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.schemas import (
    BuildingStateOut,
    CountOut,
    PlanetDetailOut,
    PlanetOut,
    RenamePlanetRequest,
)
from app.economy.service import refresh_resources
from app.platform.db import get_session
from app.platform.models import Building, Defense, Planet, Player, Ship
from app.platform.security import get_current_player

router = APIRouter(tags=["economy"])


async def _load_owned_planet(session: AsyncSession, player: Player, planet_id: uuid.UUID) -> Planet:
    planet = await session.get(Planet, planet_id)
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    return planet


@router.get("/planets", response_model=list[PlanetOut])
async def list_planets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[Planet]:
    rows = (await session.execute(
        select(Planet).where(Planet.player_id == player.id).order_by(Planet.created_at)
    )).scalars().all()
    return list(rows)


@router.patch("/planets/{planet_id}", response_model=PlanetOut)
async def rename_planet(
    planet_id: uuid.UUID,
    body: RenamePlanetRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> Planet:
    """Benennt einen eigenen Planeten/Mond um (Anzeigename, reine Kosmetik)."""
    planet = await _load_owned_planet(session, player, planet_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name darf nicht leer sein")
    planet.name = name[:40]
    await session.commit()
    await session.refresh(planet)
    return planet


@router.get("/planets/{planet_id}", response_model=PlanetDetailOut)
async def get_planet(
    planet_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> PlanetDetailOut:
    from app.buildings.service import effective_fields_max
    from app.economy.service import get_research_levels

    planet = await _load_owned_planet(session, player, planet_id)
    resources = await refresh_resources(session, planet)

    buildings = (await session.execute(
        select(Building).where(Building.planet_id == planet.id)
    )).scalars().all()
    # Effektive Bauplaetze inkl. Terraforming-Forschung (Mond: moon_base-Stufen).
    _levels = {b.type: b.level for b in buildings}
    _rlevels = await get_research_levels(session, planet.player_id)
    fields_max_eff = effective_fields_max(planet, _levels, _rlevels.get("terraforming", 0))
    ships = (await session.execute(
        select(Ship).where(Ship.planet_id == planet.id, Ship.count > 0)
    )).scalars().all()
    defenses = (await session.execute(
        select(Defense).where(Defense.planet_id == planet.id, Defense.count > 0)
    )).scalars().all()

    return PlanetDetailOut(
        id=planet.id,
        name=planet.name,
        galaxy=planet.galaxy,
        system=planet.system,
        position=planet.position,
        planet_type=planet.planet_type,
        temp_max=planet.temp_max,
        fields_used=planet.fields_used,
        fields_max=fields_max_eff,
        is_homeworld=planet.is_homeworld,
        governor_commander_id=planet.governor_commander_id,
        resources=resources,
        buildings=[
            BuildingStateOut(type=b.type, level=b.level, upgrade_finishes_at=b.upgrade_finishes_at)
            for b in buildings
        ],
        ships=[CountOut(type=s.type, count=s.count) for s in ships],
        defenses=[CountOut(type=d.type, count=d.count) for d in defenses],
        parent_planet_id=planet.parent_planet_id,
        last_jump_at=planet.last_jump_at,
    )
