"""Router fuer Allianzen: Verwaltung, Pool, Forschung, Station."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alliance import research as research_mod
from app.alliance import service as svc
from app.alliance import station as station_mod
from app.platform.db import get_session
from app.platform.models import Alliance, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["alliance"])


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


# -- Lesen ----------------------------------------------------------------------

@router.get("/alliance")
async def my_alliance(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Eigene Allianz (Uebersicht + Forschungs-Katalog + eigene Rolle) ODER offene Einladungen."""
    m = await svc.get_membership(session, player.id)
    if m is None:
        invites = await svc.list_invites_for(session, player.id)
        return {
            "alliance": None,
            "invites": [{"id": str(a.id), "name": a.name, "tag": a.tag} for a in invites],
            "create_cost": svc._acfg().get("create_cost", {}),
            "max_members": int(svc._acfg().get("max_members", 50)),
        }
    alliance = await session.get(Alliance, m.alliance_id)
    ov = await svc.overview(session, alliance)
    ov["my_role"] = m.role
    ov["research_catalog"] = research_mod.research_catalog(alliance, ov["member_count"])
    ov["station_config"] = svc._acfg().get("station", {})
    return {"alliance": ov, "invites": []}


# -- Gruendung / Aufloesung -----------------------------------------------------

class CreateIn(BaseModel):
    name: str
    tag: str


@router.post("/alliance", status_code=201)
async def create(
    body: CreateIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        alliance = await svc.create_alliance(session, player, body.name, body.tag)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return await svc.overview(session, alliance)


@router.post("/alliance/disband")
async def disband(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await svc.disband(session, player)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"ok": True}


# -- Einladungen / Mitgliedschaft ----------------------------------------------

class InviteIn(BaseModel):
    name: str | None = None
    player_id: str | None = None


@router.post("/alliance/invite")
async def invite(
    body: InviteIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    target_id: uuid.UUID
    if body.player_id:
        target_id = uuid.UUID(body.player_id)
    elif body.name:
        target = (await session.execute(
            select(Player).where(func.lower(Player.display_name) == body.name.strip().lower())
        )).scalars().first()
        if target is None:
            raise HTTPException(status_code=404, detail="Spieler nicht gefunden.")
        target_id = target.id
    else:
        raise HTTPException(status_code=422, detail="name oder player_id noetig.")
    try:
        await svc.invite(session, player, target_id)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"ok": True}


@router.post("/alliance/invites/{alliance_id}/accept")
async def accept_invite(
    alliance_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        alliance = await svc.accept_invite(session, player, alliance_id)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return await svc.overview(session, alliance)


@router.post("/alliance/invites/{alliance_id}/decline")
async def decline_invite(
    alliance_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await svc.decline_invite(session, player, alliance_id)
    return {"ok": True}


@router.post("/alliance/leave")
async def leave(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await svc.leave(session, player)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"ok": True}


class TargetIn(BaseModel):
    player_id: str


@router.post("/alliance/kick")
async def kick(
    body: TargetIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await svc.kick(session, player, uuid.UUID(body.player_id))
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"ok": True}


class RoleIn(BaseModel):
    player_id: str
    role: str


@router.post("/alliance/role")
async def set_role(
    body: RoleIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await svc.set_role(session, player, uuid.UUID(body.player_id), body.role)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"ok": True}


@router.post("/alliance/transfer")
async def transfer(
    body: TargetIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        await svc.transfer_leadership(session, player, uuid.UUID(body.player_id))
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"ok": True}


# -- Pool -----------------------------------------------------------------------

class DepositIn(BaseModel):
    planet_id: str
    metal: float = 0
    crystal: float = 0
    deuterium: float = 0


@router.post("/alliance/deposit")
async def deposit(
    body: DepositIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        pool = await svc.deposit(session, player, uuid.UUID(body.planet_id),
                                 {"metal": body.metal, "crystal": body.crystal, "deuterium": body.deuterium})
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"pool": pool}


# -- Forschung ------------------------------------------------------------------

class ResearchIn(BaseModel):
    tree: str
    node: str


@router.post("/alliance/research")
async def research(
    body: ResearchIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        return await research_mod.spend_research(session, player, body.tree, body.node)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc


@router.post("/alliance/research/reset")
async def research_reset(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        return await research_mod.reset_research(session, player)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc


# -- Station --------------------------------------------------------------------

class StationBuildIn(BaseModel):
    galaxy: int
    system: int
    position: int


@router.post("/alliance/station", status_code=201)
async def build_station(
    body: StationBuildIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        st = await station_mod.build_station(session, player, body.galaxy, body.system, body.position)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"id": str(st.id), "coords": f"{st.galaxy}:{st.system}:{st.position}",
            "radius_level": st.research_radius_level, "fuel": st.fuel, "hp": st.hp, "status": st.status}


class RefuelIn(BaseModel):
    deuterium: float


@router.post("/alliance/station/{station_id}/refuel")
async def refuel_station(
    station_id: uuid.UUID,
    body: RefuelIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        st = await station_mod.refuel_station(session, player, station_id, body.deuterium)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"id": str(st.id), "fuel": st.fuel, "status": st.status}


@router.post("/alliance/station/{station_id}/upgrade")
async def upgrade_station(
    station_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        st = await station_mod.upgrade_radius(session, player, station_id)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"id": str(st.id), "radius_level": st.research_radius_level}


class RelocateIn(BaseModel):
    galaxy: int
    system: int
    position: int
    escort: dict[str, int] = {}
    escort_planet_id: uuid.UUID | None = None


@router.post("/alliance/station/{station_id}/relocate")
async def relocate_station(
    station_id: uuid.UUID,
    body: RelocateIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        st = await station_mod.relocate_station(
            session, player, station_id, body.galaxy, body.system, body.position,
            escort=body.escort, escort_planet_id=body.escort_planet_id,
        )
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    tr = st.transit or {}
    return {
        "id": str(st.id), "status": st.status,
        "transit": {
            "target": tr.get("leg_to"),
            "arrive_at": tr.get("arrive_at"),
            "returning": tr.get("returning", False),
        },
    }


class ModuleIn(BaseModel):
    module_type: str
    count: int = 1


@router.post("/alliance/station/{station_id}/module/mount")
async def mount_module(
    station_id: uuid.UUID,
    body: ModuleIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        st = await station_mod.mount_module(session, player, station_id, body.module_type, body.count)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"id": str(st.id), "modules": st.modules or {}}


@router.post("/alliance/station/{station_id}/module/unmount")
async def unmount_module(
    station_id: uuid.UUID,
    body: ModuleIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        st = await station_mod.unmount_module(session, player, station_id, body.module_type, body.count)
    except (ValueError, PermissionError) as exc:
        raise _err(exc) from exc
    return {"id": str(st.id), "modules": st.modules or {}}
