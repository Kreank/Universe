"""Generisches temporäres Buff/Debuff-System für Game-Events.

Ein Buff hat einen ``scope`` (player|planet|system), eine Ablaufzeit und einen ``buff_type``:
- multiplikativ: production, build_speed, research_speed (Produkt aller aktiven magnitudes)
- additiv: morale_adjust (Summe)
- Schalter: scan_block, spionage_block (Existenz = aktiv)

Ablauf rein zeitlich (``expires_at > now``); ein periodischer Tick räumt nur alte Zeilen weg.
Die Abfragen matchen einen Buff, wenn sein scope-Ziel zu EINEM der übergebenen Filter passt
(player_id ODER planet_id ODER (galaxy, system)) — so kann jede Einklink-Stelle einfach die
ihr bekannten IDs übergeben."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import session_scope
from app.platform.models import EventBuff

log = logging.getLogger("universe.events.buffs")

MULTIPLICATIVE = {"production", "build_speed", "research_speed", "mining_speed"}
ADDITIVE = {"morale_adjust"}
SWITCH = {"scan_block", "spionage_block"}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def apply_buff(
    session: AsyncSession,
    *,
    buff_type: str,
    magnitude: float,
    duration_hours: float,
    scope: str,
    player_id: uuid.UUID | None = None,
    planet_id: uuid.UUID | None = None,
    galaxy: int | None = None,
    system: int | None = None,
    source_event_id: uuid.UUID | None = None,
    replace: bool = False,
) -> EventBuff:
    """Legt einen neuen Buff an (NICHT committet — Aufrufer committet).

    ``replace=True`` = nicht-stapelnd: vorhandene aktive Buffs GLEICHEN Typs am selben Ziel werden
    vorher entfernt, statt sich zu multiplizieren. Noetig fuer research_speed (Spieler-Feedback
    2026-06-23: mehrere Forschungs-Durchbrueche stapelten sich multiplikativ — 3× ×2 = 8× = ein
    30-min-Tech in ~3 min). So bleibt es bei „doppelt so schnell", wie der Event-Text verspricht."""
    if replace:
        scope_clause = _scope_filter(player_id, planet_id, galaxy, system)
        if scope_clause is not None:
            await session.execute(
                delete(EventBuff).where(
                    EventBuff.buff_type == buff_type,
                    EventBuff.expires_at > _now(),
                    scope_clause,
                )
            )
    buff = EventBuff(
        source_event_id=source_event_id,
        scope=scope,
        player_id=player_id,
        planet_id=planet_id,
        galaxy=galaxy,
        system=system,
        buff_type=buff_type,
        magnitude=float(magnitude),
        expires_at=_now() + dt.timedelta(hours=float(duration_hours)),
    )
    session.add(buff)
    await session.flush()  # autoflush ist aus -> sofort fuer Folge-Queries derselben TX sichtbar
    return buff


def _scope_filter(
    player_id: uuid.UUID | None,
    planet_id: uuid.UUID | None,
    galaxy: int | None,
    system: int | None,
):
    """ODER-Bedingung: Buff passt, wenn sein scope-Ziel zu einem der Filter passt."""
    clauses = []
    if player_id is not None:
        clauses.append(and_(EventBuff.scope == "player", EventBuff.player_id == player_id))
    if planet_id is not None:
        clauses.append(and_(EventBuff.scope == "planet", EventBuff.planet_id == planet_id))
    if galaxy is not None and system is not None:
        clauses.append(
            and_(EventBuff.scope == "system", EventBuff.galaxy == galaxy, EventBuff.system == system)
        )
    return or_(*clauses) if clauses else None


async def _active(
    session: AsyncSession,
    buff_type: str,
    player_id: uuid.UUID | None = None,
    planet_id: uuid.UUID | None = None,
    galaxy: int | None = None,
    system: int | None = None,
) -> list[EventBuff]:
    scope_clause = _scope_filter(player_id, planet_id, galaxy, system)
    if scope_clause is None:
        return []
    rows = (await session.execute(
        select(EventBuff).where(
            EventBuff.buff_type == buff_type,
            EventBuff.expires_at > _now(),
            scope_clause,
        )
    )).scalars().all()
    return list(rows)


async def buff_mult(session: AsyncSession, buff_type: str, **filters) -> float:
    """Produkt aller aktiven Multiplikatoren dieses Typs (1.0 = neutral)."""
    mult = 1.0
    for b in await _active(session, buff_type, **filters):
        mult *= float(b.magnitude or 1.0)
    return mult


async def buff_sum(session: AsyncSession, buff_type: str, **filters) -> float:
    """Summe aller aktiven additiven Anpassungen dieses Typs (0.0 = neutral)."""
    total = 0.0
    for b in await _active(session, buff_type, **filters):
        total += float(b.magnitude or 0.0)
    return total


async def is_blocked(session: AsyncSession, buff_type: str, *, galaxy: int, system: int) -> bool:
    """True, wenn für (galaxy, system) ein aktiver Schalter-Buff dieses Typs existiert."""
    return bool(await _active(session, buff_type, galaxy=galaxy, system=system))


async def cleanup_expired_buffs() -> None:
    """Periodischer Tick: löscht abgelaufene Buff-Zeilen (rein Hygiene; Abfragen filtern eh)."""
    async with session_scope() as session:
        res = await session.execute(delete(EventBuff).where(EventBuff.expires_at <= _now()))
        await session.commit()
        if res.rowcount:
            log.info("Buff-Cleanup: %d abgelaufene Buffs entfernt", res.rowcount)
