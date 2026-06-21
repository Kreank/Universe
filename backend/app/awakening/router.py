"""API der „erwachenden Galaxie" (Welle 4): aktuelles Aggressionsniveau + Wächter-Status.

Liest-nur, für die Dashboard-Anzeige (Aggressions-Barometer + Wächter-Banner). Keine
Schreibzugriffe — der Lebenszyklus läuft serverseitig im stündlichen ``aggression_tick``."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.awakening.service import compute_aggression_level
from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import AggressionHistory, AwakeningWarden, CombatReport, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["awakening"])


class WardenOut(BaseModel):
    status: str
    coords: str | None = None
    aggression_level: float
    spawned_at: str | None = None
    expires_at: str | None = None
    fleet: dict = {}
    participants: int = 0


class AwakeningStatusOut(BaseModel):
    enabled: bool
    level: float
    status: str            # peaceful | tense | war | apocalypse
    threshold: float
    combat_count: int
    total_debris: float
    unique_attackers: int
    status_bands: list = []
    warden: WardenOut | None = None
    history: list = []     # juengste aggression_history-Zeilen (Verlauf fuers Barometer)


def _iso(t: dt.datetime | None) -> str | None:
    return t.isoformat() if t else None


@router.get("/awakening/status", response_model=AwakeningStatusOut)
async def awakening_status(
    history_limit: int = Query(default=24, ge=1, le=168),
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> AwakeningStatusOut:
    """Aktuelles Aggressionsniveau (live aus dem Fenster gerechnet) + Wächter-Status + Verlauf."""
    cfg = get_balance().awakening
    lookback_h = float(cfg.get("lookback_hours", 6))
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=lookback_h)

    reports = (await session.execute(
        select(CombatReport).where(CombatReport.created_at >= cutoff)
    )).scalars().all()
    total_debris = 0.0
    attackers: set = set()
    for rep in reports:
        d = rep.debris or {}
        total_debris += float(d.get("metal", 0)) + float(d.get("crystal", 0))
        if rep.attacker_id is not None:
            attackers.add(rep.attacker_id)
    combat_count = len(reports)
    level, status = compute_aggression_level(combat_count, total_debris, len(attackers), cfg)

    warden_row = (await session.execute(
        select(AwakeningWarden).where(AwakeningWarden.status == "active")
        .order_by(AwakeningWarden.spawned_at.desc()).limit(1)
    )).scalar_one_or_none()
    warden_out: WardenOut | None = None
    if warden_row is not None:
        data = warden_row.data or {}
        warden_out = WardenOut(
            status=warden_row.status,
            coords=data.get("coords"),
            aggression_level=float(warden_row.aggression_level),
            spawned_at=_iso(warden_row.spawned_at),
            expires_at=_iso(warden_row.expires_at),
            fleet=warden_row.fleet or {},
            participants=len(data.get("participants", [])),
        )

    hist_rows = (await session.execute(
        select(AggressionHistory).order_by(AggressionHistory.hour.desc()).limit(history_limit)
    )).scalars().all()
    history = [
        {
            "hour": _iso(h.hour), "level": h.level, "status": h.status,
            "combat_count": h.combat_count, "total_debris": h.total_debris,
            "unique_attackers": h.unique_attackers,
        }
        for h in reversed(hist_rows)
    ]

    return AwakeningStatusOut(
        enabled=bool(cfg.get("enabled", False)),
        level=level, status=status, threshold=float(cfg.get("threshold", 0)),
        combat_count=combat_count, total_debris=total_debris, unique_attackers=len(attackers),
        status_bands=cfg.get("status_bands", []),
        warden=warden_out, history=history,
    )
