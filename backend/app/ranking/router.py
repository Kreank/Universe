"""Router fuer die Rangliste (OGame-Stil: Reiter Spieler/Allianzen, Kategorie-Wertungen)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_session
from app.platform.models import Alliance, AllianceMember, Player
from app.platform.security import get_current_player
from app.ranking.schemas import RankBoardEntry, RankBoardResponse
from app.ranking.service import (
    CATEGORIES,
    category_values,
    compute_breakdowns,
    ranks_in_category,
)

router = APIRouter(tags=["ranking"])


async def _aggregate_alliances(
    session: AsyncSession, player_values: dict[uuid.UUID, dict[str, int]]
) -> tuple[dict[uuid.UUID, dict[str, int]], dict[uuid.UUID, dict], dict[uuid.UUID, uuid.UUID]]:
    """Summiert die Spieler-Punkte je Allianz (je Kategorie). Liefert (values, meta, alliance_of).
    Allianzen ohne Mitglieder fallen raus."""
    rows = (await session.execute(select(Alliance.id, Alliance.name, Alliance.tag))).all()
    members = (await session.execute(
        select(AllianceMember.player_id, AllianceMember.alliance_id)
    )).all()
    alliance_of = {pid: aid for pid, aid in members}

    values: dict[uuid.UUID, dict[str, int]] = {aid: {c: 0 for c in CATEGORIES} for aid, _, _ in rows}
    counts: dict[uuid.UUID, int] = {aid: 0 for aid, _, _ in rows}
    for pid, vals in player_values.items():
        aid = alliance_of.get(pid)
        if aid in values:
            counts[aid] += 1
            for c in CATEGORIES:
                values[aid][c] += vals[c]

    values = {aid: v for aid, v in values.items() if counts[aid] > 0}
    meta = {
        aid: {"name": name, "tag": tag, "members": counts[aid]}
        for aid, name, tag in rows
        if aid in values
    }
    return values, meta, alliance_of


@router.get("/ranking", response_model=RankBoardResponse)
async def get_ranking(
    board: str = Query(default="players"),
    category: str = Query(default="total"),
    limit: int = Query(default=100, ge=1, le=500),
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> RankBoardResponse:
    """Rangliste nach Kategorie (Gesamt/Gebaeude/Forschung/Flotte/Verteidigung) fuer das gewaehlte
    Board (Spieler oder Allianzen). Frisch berechnet, READ-ONLY (Befund R-1: ein GET committet
    nichts; das Persistieren von ``Player.score`` macht allein der ``score_tick``).

    ``my_ranks`` liefert den eigenen Rang JE Kategorie -> die UI zeigt 'Dein Platz' immer an,
    egal welche Kategorie gerade sortiert ist. ``me`` ist der eigene Eintrag (bzw. die eigene
    Allianz), auch wenn er ausserhalb der Top-``limit`` liegt."""
    if category not in CATEGORIES:
        category = "total"
    if board not in ("players", "alliances"):
        board = "players"

    breakdowns = await compute_breakdowns(session)
    player_values = category_values(breakdowns)

    if board == "alliances":
        values, meta, alliance_of = await _aggregate_alliances(session, player_values)
        self_id: uuid.UUID | None = alliance_of.get(player.id)
    else:
        names = {
            pid: dn
            for pid, dn in (await session.execute(select(Player.id, Player.display_name))).all()
        }
        values = player_values
        meta = {pid: {"name": names.get(pid, "Unbekannt"), "tag": None, "members": None} for pid in values}
        self_id = player.id

    # Eigener Rang je Kategorie (fuer "Dein Platz"); None, wenn man (noch) nicht gewertet ist.
    my_ranks: dict[str, int] | None = None
    if self_id is not None and self_id in values:
        my_ranks = {c: ranks_in_category(values, c)[self_id] for c in CATEGORIES}

    ordered = sorted(values.items(), key=lambda kv: (-kv[1][category], str(kv[0])))

    def entry(rank: int, oid: uuid.UUID, vals: dict[str, int]) -> RankBoardEntry:
        m = meta.get(oid, {})
        return RankBoardEntry(
            rank=rank,
            id=oid,
            name=m.get("name", "Unbekannt"),
            tag=m.get("tag"),
            member_count=m.get("members"),
            is_self=(oid == self_id),
            value=vals[category],
            total=vals["total"],
            buildings=vals["buildings"],
            research=vals["research"],
            fleet=vals["fleet"],
            defense=vals["defense"],
        )

    entries = [entry(rank, oid, vals) for rank, (oid, vals) in enumerate(ordered, start=1)]
    me = next((e for e in entries if e.is_self), None)

    return RankBoardResponse(
        board=board,
        category=category,
        entries=entries[:limit],
        me=me,
        my_ranks=my_ranks,
        total=len(entries),
    )
