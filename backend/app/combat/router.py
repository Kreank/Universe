"""Router fuer Combat-Reports (api-contract §10)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import CombatReport, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["combat"])


def serialize_combat_report(report: CombatReport, viewer_id: uuid.UUID) -> dict:
    """Serialisiert einen Kampfbericht aus Sicht des abrufenden Spielers.

    Reicht die volle Engine-Ausgabe (Runden mit Distanz/Fliehen, Ueberlebende,
    gekaperte/gestrandete Schiffe) ans Frontend durch und markiert ueber ``role``,
    welche Seite der Betrachter war (wichtig bei eingehenden Angriffen, an denen der
    Spieler nicht selbst teilnimmt).
    """
    outcome = report.outcome or {}
    role = "attacker" if report.attacker_id == viewer_id else "defender"
    return {
        "id": str(report.id),
        "location": report.location,
        "role": role,
        "npc_name": outcome.get("npc_name"),
        "attacker": outcome.get("attacker_initial", {}),
        "defender": outcome.get("defender_initial", {}),
        "rounds": outcome.get("rounds", []),
        "winner": outcome.get("winner"),
        "attacker_survivors": outcome.get("attacker_survivors", {}),
        "defender_survivors": outcome.get("defender_survivors", {}),
        "attacker_losses": outcome.get("attacker_losses", {}),
        "defender_losses": outcome.get("defender_losses", {}),
        "attacker_fled": outcome.get("attacker_fled", {}),
        "defender_fled": outcome.get("defender_fled", {}),
        "attacker_captured": outcome.get("attacker_captured", {}),
        "defender_captured": outcome.get("defender_captured", {}),
        "attacker_drive_disabled": outcome.get("attacker_drive_disabled", {}),
        "defender_drive_disabled": outcome.get("defender_drive_disabled", {}),
        "loot": report.loot,
        "debris": report.debris,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


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

    return serialize_combat_report(report, player.id)
