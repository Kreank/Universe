"""Router fuer das Universum/Galaxie-Ansicht (api-contract §6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import AsteroidField, NpcEmpire, Planet, Player, PlayerDiscovery, UniverseCell
from app.platform.security import get_current_player

router = APIRouter(tags=["universe"])


class CellOut(BaseModel):
    position: int
    occupant_type: str
    name: str | None = None
    player_id: str | None = None
    player_name: str | None = None  # Imperiumsname des Spielers (fuer Handel/Nachricht)
    npc_id: str | None = None
    discovered: bool = False  # hat dieser Spieler das Ziel schon aufgeklaert?
    trade: dict | None = None  # P2P-Handelsanzeige des Spielers (falls aktiviert)
    asteroid: dict | None = None  # Asteroidenfeld am Ort {richness, mult, metal, crystal} (Restvorrat)


class GalaxyViewOut(BaseModel):
    cells: list[CellOut]


class TargetOut(BaseModel):
    """Ein aufgeklaertes (PvE-)Ziel — erst nach Spionage sichtbar (Doku 04 §6)."""
    npc_id: str | None = None
    name: str
    galaxy: int
    system: int
    position: int
    coords: str
    ships_total: int
    defenses_total: int
    level: int = 1
    discovered_at: str | None = None
    intel: dict | None = None  # voller Aufklaerungs-Schnappschuss (Zusammensetzung/Resschen ab L2/L3)


async def _player_discoveries(
    session: AsyncSession, player_id
) -> dict[tuple[int, int, int], PlayerDiscovery]:
    """Aufgedeckte Ziele eines Spielers, indexiert nach Koordinaten."""
    rows = (await session.execute(
        select(PlayerDiscovery).where(PlayerDiscovery.player_id == player_id)
    )).scalars().all()
    return {(d.galaxy, d.system, d.position): d for d in rows}


@router.get("/galaxy/targets", response_model=list[TargetOut])
async def galaxy_targets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[TargetOut]:
    """Verzeichnis AUFGEKLAERTER Ziele (PvE). Erst nach Spionage sichtbar.

    Liefert nur Ziele, die dieser Spieler per Sonde aufgedeckt hat
    (``player_discoveries``); Staerke/Zusammensetzung stammen aus dem letzten
    Aufklaerungs-Schnappschuss und koennen veraltet sein."""
    discoveries = sorted(
        (await _player_discoveries(session, player.id)).values(),
        key=lambda d: (d.galaxy, d.system, d.position),
    )
    out: list[TargetOut] = []
    for d in discoveries:
        intel = d.intel or {}
        # npc_id fuer den Angriffs-Deep-Link aufloesen (falls Ziel ein NPC ist).
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == d.galaxy,
                NpcEmpire.system == d.system,
                NpcEmpire.position == d.position,
            )
        )).scalar_one_or_none()
        out.append(TargetOut(
            npc_id=str(npc.id) if npc else None,
            name=intel.get("name") or (npc.name if npc else f"{d.galaxy}:{d.system}:{d.position}"),
            galaxy=d.galaxy,
            system=d.system,
            position=d.position,
            coords=f"{d.galaxy}:{d.system}:{d.position}",
            ships_total=int(intel.get("ships_total", 0)),
            defenses_total=int(intel.get("defenses_total", 0)),
            level=d.level,
            discovered_at=d.discovered_at.isoformat() if d.discovered_at else None,
            intel=intel,
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
    discovered = await _player_discoveries(session, player.id)

    cells: list[CellOut] = []
    for pos in range(1, bal.positions_per_system + 1):
        cell = by_pos.get(pos)
        if cell is None or cell.occupant_type == "empty":
            cells.append(CellOut(position=pos, occupant_type="empty"))
            continue
        name = None
        player_id = None
        player_name = None
        npc_id = None
        trade = None
        asteroid = None
        if cell.occupant_type == "asteroid_field" and cell.ref_id:
            field = await session.get(AsteroidField, cell.ref_id)
            if field:
                name = f"Asteroidenfeld ({field.richness})"
                asteroid = {
                    "richness": field.richness,
                    "mult": round(field.mult, 2),
                    "metal": round(field.metal_remaining, 0),
                    "crystal": round(field.crystal_remaining, 0),
                    "metal_max": round(field.metal_max, 0),
                    "crystal_max": round(field.crystal_max, 0),
                }
        elif cell.occupant_type == "player" and cell.ref_id:
            planet = await session.get(Planet, cell.ref_id)
            if planet:
                name = planet.name
                player_id = str(planet.player_id)
                owner = await session.get(Player, planet.player_id)
                if owner:
                    player_name = owner.display_name
                    if owner.trade_enabled:
                        trade = {
                            "offer": owner.trade_offer,
                            "want": owner.trade_want,
                            "rate": owner.trade_rate,
                            "note": owner.trade_note,
                        }
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
            player_name=player_name,
            npc_id=npc_id,
            discovered=(galaxy, system, pos) in discovered,
            trade=trade,
            asteroid=asteroid,
        ))
    return GalaxyViewOut(cells=cells)
