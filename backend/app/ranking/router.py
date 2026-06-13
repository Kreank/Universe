"""Router fuer die Rangliste (Punktesystem)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import Player
from app.platform.security import get_current_player
from app.ranking.schemas import RankingEntryOut, RankingResponse
from app.ranking.service import Breakdown, compute_breakdowns, to_points

router = APIRouter(tags=["ranking"])


@router.get("/ranking", response_model=RankingResponse)
async def get_ranking(
    limit: int = Query(default=100, ge=1, le=500),
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> RankingResponse:
    """Aktuelle Rangliste nach Imperiumswert (frisch berechnet, READ-ONLY).

    Berechnet die Breakdowns nur zur Anzeige und schreibt NICHTS (Befund R-1: ein GET
    darf nicht die ganze players-Tabelle committen — das Persistieren von ``Player.score``
    macht allein der periodische ``score_tick``). Liefert die Top-``limit`` Spieler; der
    eigene Eintrag wird separat als ``me`` immer mitgeschickt (auch ausserhalb der Top-Liste)."""
    breakdowns = await compute_breakdowns(session)
    names: dict[uuid.UUID, str] = {
        pid: dn
        for pid, dn in (await session.execute(select(Player.id, Player.display_name))).all()
    }

    # Hoechster Imperiumswert zuerst; Gleichstand deterministisch nach player_id (Befund R-3),
    # damit Raenge zwischen Abrufen nicht springen.
    ordered = sorted(breakdowns.items(), key=lambda kv: (-kv[1].total, str(kv[0])))

    def entry(rank: int, pid: uuid.UUID, b: Breakdown) -> RankingEntryOut:
        # Komponenten einzeln floored UND als Summe ans Total (Befund R-2: sonst summieren
        # sich die angezeigten Teile nicht zum angezeigten Gesamtwert).
        parts = {
            "buildings": to_points(b.buildings),
            "research": to_points(b.research),
            "fleet": to_points(b.fleet),
            "defense": to_points(b.defense),
        }
        return RankingEntryOut(
            rank=rank,
            player_id=pid,
            display_name=names.get(pid, "Unbekannt"),
            is_self=pid == player.id,
            points=sum(parts.values()),
            **parts,
        )

    entries = [entry(rank, pid, b) for rank, (pid, b) in enumerate(ordered, start=1)]
    me = next((e for e in entries if e.is_self), None)

    return RankingResponse(
        entries=entries[:limit],
        me=me,
        total_players=len(entries),
    )
