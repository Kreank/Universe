"""Router fuer den Ziele/Bedrohungen-Screen (Welle 1, Frontend-Konsistenz-Epos).

Liefert die aus der Galaxie ausgelagerten Listen, damit Ziel-Aktionen (Angriff/
Spionage/Diplomatie/Phalanx/Transport/Nachricht) dort gebuendelt werden koennen.
Reuse: PlayerDiscovery (universe.router._player_discoveries), NpcRelation und
list_incoming_attacks (fleet.service). KEINE neue Tabelle, keine Schreibzugriffe."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import Player
from app.platform.security import get_current_player
from app.targets.schemas import NpcTargetOut, PlayerTargetOut, ThreatOut
from app.targets.service import list_npc_targets, list_player_targets, list_threats

router = APIRouter(prefix="/targets", tags=["targets"])


@router.get("/npcs", response_model=list[NpcTargetOut])
async def npc_targets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Entdeckte, angreifbare NPC-Imperien (ohne Handelszentren), feindlich/nah zuerst."""
    return await list_npc_targets(session, player)


@router.get("/players", response_model=list[PlayerTargetOut])
async def player_targets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Entdeckte fremde Spieler-Imperien (leer, wenn keine bekannt), nah zuerst."""
    return await list_player_targets(session, player)


@router.get("/threats", response_model=list[ThreatOut])
async def threats(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Bedrohungen: eingehende Angriffe + feindliche NPCs in der Naehe, Ankunft zuerst."""
    return await list_threats(session, player)
