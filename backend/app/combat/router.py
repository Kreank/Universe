"""Router fuer Combat-Reports (api-contract §10)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import CombatReport, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["combat"])


@router.get("/combat-reports/{report_id}")
async def get_combat_report(
    report_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await session.get(CombatReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Combat-Report nicht gefunden")
    if report.attacker_id != player.id and report.defender_id != player.id:
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Report")

    outcome = report.outcome or {}
    return {
        "id": str(report.id),
        "location": report.location,
        "attacker": outcome.get("attacker_initial", {}),
        "defender": outcome.get("defender_initial", {}),
        "rounds": outcome.get("rounds", []),
        "winner": outcome.get("winner"),
        "loot": report.loot,
        "debris": report.debris,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
