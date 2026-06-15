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
    moon: dict | None = None  # Mond am Ort {name, player_id, player_name, own} — eigenes Angriffs-/Spionageziel
    station: dict | None = None  # Allianz-Station am Ort {alliance_id, tag, mine, status, hp, max_hp, hp_pct}


class ZoneOut(BaseModel):
    """Allianz-Einflusszone, die dieses System abdeckt (aktive, getankte Station in Reichweite)."""
    alliance_id: str
    tag: str
    center_system: int
    radius: int
    mine: bool  # gehoert die Zone der eigenen Allianz?


class GalaxyViewOut(BaseModel):
    cells: list[CellOut]
    zones: list[ZoneOut] = []  # Allianz-Einflusszonen, die dieses System abdecken


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

    # Asteroidenfelder sind ein OVERLAY (geteilte Position wie ein Mond) -> per Koordinate laden
    # und an die Zelle haengen, unabhaengig vom Belegungstyp (auch auf 'empty'/'player'/'npc').
    ast_rows = (await session.execute(
        select(AsteroidField).where(
            AsteroidField.galaxy == galaxy, AsteroidField.system == system
        )
    )).scalars().all()

    def _asteroid_overlay(pos: int) -> dict | None:
        field = next((f for f in ast_rows if f.position == pos), None)
        if not field:
            return None
        return {
            "richness": field.richness,
            "mult": round(field.mult, 2),
            "metal": round(field.metal_remaining, 0),
            "crystal": round(field.crystal_remaining, 0),
            "metal_max": round(field.metal_max, 0),
            "crystal_max": round(field.crystal_max, 0),
        }

    # Monde sind ein OVERLAY (teilen die Position des Planeten) -> eigenes Angriffs-/Spionageziel.
    moon_rows = (await session.execute(
        select(Planet).where(
            Planet.galaxy == galaxy, Planet.system == system, Planet.planet_type == "moon"
        )
    )).scalars().all()
    moon_by_pos = {m.position: m for m in moon_rows}

    # Allianz-Stationen in diesem System (nicht-zerstoert): als angreifbare Zellen-Overlays.
    from app.platform.models import Alliance as _Alliance
    from app.platform.models import AllianceStation as _AllStation
    _st_rows = (await session.execute(
        select(_AllStation).where(
            _AllStation.galaxy == galaxy, _AllStation.system == system,
            _AllStation.status != "destroyed",
        )
    )).scalars().all()
    station_by_pos: dict[int, dict] = {}
    _max_hp = float(bal.data.get("alliance", {}).get("station", {}).get("hp", 1)) or 1.0
    for _st in _st_rows:
        _al = await session.get(_Alliance, _st.alliance_id)
        station_by_pos[_st.position] = {
            "alliance_id": str(_st.alliance_id),
            "tag": _al.tag if _al else "?",
            "mine": player.alliance_id is not None and _st.alliance_id == player.alliance_id,
            "status": _st.status,
            "hp": round(float(_st.hp or 0), 1),
            "max_hp": _max_hp,
            "hp_pct": max(0.0, round(100.0 * float(_st.hp or 0) / _max_hp, 1)),
        }

    cells: list[CellOut] = []
    for pos in range(1, bal.positions_per_system + 1):
        cell = by_pos.get(pos)
        asteroid = _asteroid_overlay(pos)
        station_info = station_by_pos.get(pos)
        moon_obj = moon_by_pos.get(pos)
        moon = None
        if moon_obj is not None:
            m_owner = await session.get(Player, moon_obj.player_id)
            moon = {
                "name": moon_obj.name,
                "player_id": str(moon_obj.player_id),
                "player_name": m_owner.display_name if m_owner else None,
                "own": moon_obj.player_id == player.id,
            }
        if cell is None or cell.occupant_type == "empty":
            cells.append(CellOut(position=pos, occupant_type="empty", asteroid=asteroid,
                                 moon=moon, station=station_info))
            continue
        name = None
        player_id = None
        player_name = None
        npc_id = None
        trade = None
        if cell.occupant_type == "player" and cell.ref_id:
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
            moon=moon,
            station=station_info,
        ))

    # Galaktische Weiten: synthetischer Deep-Space-Slot (nur per Expedition erreichbar).
    deep = int(bal.data.get("expedition", {}).get("deep_space_position", 0))
    if deep:
        cells.append(CellOut(position=deep, occupant_type="deep_space", name="Galaktische Weiten"))

    # Allianz-Einflusszonen, die dieses System abdecken (aktive + getankte Station in Reichweite).
    from app.alliance.station import covers, zone_radius
    from app.platform.models import Alliance, AllianceStation
    zones: list[ZoneOut] = []
    st_rows = (await session.execute(
        select(AllianceStation).where(
            AllianceStation.galaxy == galaxy, AllianceStation.status == "active"
        )
    )).scalars().all()
    for st in st_rows:
        if not covers(st, galaxy, system):
            continue
        al = await session.get(Alliance, st.alliance_id)
        zones.append(ZoneOut(
            alliance_id=str(st.alliance_id),
            tag=al.tag if al else "?",
            center_system=st.system,
            radius=zone_radius(st),
            mine=(player.alliance_id is not None and st.alliance_id == player.alliance_id),
        ))
    return GalaxyViewOut(cells=cells, zones=zones)
