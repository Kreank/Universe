"""Megastruktur-Logik: stufenweiser Bau (Echtzeit), nur EIN Projekt gleichzeitig.

Kosten/Stufe = cost_base * cost_growth^level (inkl. Dunkler Materie als Haupt-Sink).
Bauzeit/Stufe = build_hours_base * build_hours_growth^level / speed. Effekte
(``research_speed``, ``mining_speed``) werden imperiumsweit gelesen (s. ``effect_mult``)."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import spend_resources
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Megastructure, Planet
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.megastructure")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _catalog() -> dict:
    return get_balance().data.get("megastructures", {})


def stage_cost(cfg: dict, level: int) -> dict[str, float]:
    """Kosten der NÄCHSTEN Stufe (level -> level+1). dark_matter separat (kontoweit)."""
    growth = float(cfg.get("cost_growth", 2.0)) ** level
    base = cfg.get("cost_base", {})
    return {k: round(float(v) * growth, 2) for k, v in base.items()}


def stage_build_seconds(cfg: dict, level: int) -> int:
    """Echtzeit-Baudauer der nächsten Stufe in Sekunden."""
    speed = get_balance().speed
    hours = float(cfg.get("build_hours_base", 24)) * float(cfg.get("build_hours_growth", 1.8)) ** level
    return max(1, int(round(hours * 3600 / max(speed, 1e-9))))


async def megastructure_levels(session: AsyncSession, player_id: uuid.UUID) -> dict[str, int]:
    rows = (await session.execute(
        select(Megastructure).where(Megastructure.player_id == player_id)
    )).scalars().all()
    return {r.type: r.level for r in rows}


async def effect_mult(session: AsyncSession, player_id: uuid.UUID, effect: str) -> float:
    """Imperiumsweiter Bonus-Faktor (z. B. 1.16) aller Megastrukturen mit ``effect``.

    Summiert ``effect_per_level * level`` über alle passenden Strukturen, +1.0."""
    rows = (await session.execute(
        select(Megastructure).where(Megastructure.player_id == player_id)
    )).scalars().all()
    cat = _catalog()
    bonus = 0.0
    for r in rows:
        cfg = cat.get(r.type, {})
        if cfg.get("effect") == effect:
            bonus += float(cfg.get("effect_per_level", 0.0)) * r.level
    return 1.0 + bonus


async def active_build(session: AsyncSession, player_id: uuid.UUID) -> Megastructure | None:
    """Die gerade im Bau befindliche Megastruktur (max. eine je Spieler) oder None."""
    return (await session.execute(
        select(Megastructure).where(
            Megastructure.player_id == player_id,
            Megastructure.building_until.is_not(None),
        )
    )).scalars().first()


async def _homeworld(session: AsyncSession, player_id: uuid.UUID) -> Planet | None:
    return (await session.execute(
        select(Planet)
        .where(Planet.player_id == player_id, Planet.planet_type != "moon")
        .order_by(Planet.is_homeworld.desc(), Planet.created_at)
    )).scalars().first()


async def options(session: AsyncSession, player) -> list[dict]:
    """Baukatalog mit Stufe, Kosten/Zeit der nächsten Stufe und Baubarkeit je Struktur."""
    levels = await megastructure_levels(session, player.id)
    building = await active_build(session, player.id)
    home = await _homeworld(session, player.id)
    res = None
    if home is not None:
        from app.economy.service import refresh_resources
        res = await refresh_resources(session, home)
    out: list[dict] = []
    for mtype, cfg in _catalog().items():
        if mtype.startswith("_"):
            continue
        level = levels.get(mtype, 0)
        maxed = level >= int(cfg.get("max_level", 99))
        cost = stage_cost(cfg, level)
        dm_cost = cost.get("dark_matter", 0)
        can_afford = res is not None and not maxed and all(
            res[r]["amount"] + 1e-6 >= cost.get(r, 0) for r in ("metal", "crystal", "deuterium")
        ) and float(player.dark_matter or 0) + 1e-6 >= dm_cost
        out.append({
            "type": mtype,
            "name": cfg.get("name", mtype),
            "level": level,
            "max_level": int(cfg.get("max_level", 99)),
            "next_level": level + 1,
            "cost": cost,
            "build_seconds": stage_build_seconds(cfg, level),
            "effect": cfg.get("effect"),
            "effect_per_level": cfg.get("effect_per_level", 0),
            "blurb": cfg.get("blurb", ""),
            "building_until": (
                building.building_until if building and building.type == mtype else None
            ),
            "busy": building is not None,
            "maxed": maxed,
            "can_afford": can_afford,
        })
    return out


async def start_build(session: AsyncSession, player, mtype: str) -> Megastructure:
    """Startet die nächste Ausbaustufe einer Megastruktur (Anti-Snowball: nur 1 Projekt)."""
    cfg = _catalog().get(mtype)
    if not cfg or mtype.startswith("_"):
        raise ValueError("Unbekannte Megastruktur")
    if await active_build(session, player.id) is not None:
        raise RuntimeError("Es laeuft bereits ein Megastruktur-Projekt (eins gleichzeitig)")

    row = (await session.execute(
        select(Megastructure).where(
            Megastructure.player_id == player.id, Megastructure.type == mtype
        )
    )).scalar_one_or_none()
    level = row.level if row else 0
    if level >= int(cfg.get("max_level", 99)):
        raise RuntimeError("Hoechststufe erreicht")

    cost = stage_cost(cfg, level)
    dm_cost = float(cost.get("dark_matter", 0))
    if float(player.dark_matter or 0) + 1e-6 < dm_cost:
        raise RuntimeError("Nicht genug Dunkle Materie")
    home = await _homeworld(session, player.id)
    if home is None:
        raise RuntimeError("Kein Heimatplanet")
    res_cost = {k: cost.get(k, 0) for k in ("metal", "crystal", "deuterium")}
    if not await spend_resources(session, home, res_cost):
        raise RuntimeError("Nicht genug Ressourcen")
    player.dark_matter = float(player.dark_matter or 0) - dm_cost

    if row is None:
        row = Megastructure(player_id=player.id, type=mtype, level=0)
        session.add(row)
    finish = _now() + dt.timedelta(seconds=stage_build_seconds(cfg, level))
    row.building_until = finish
    await session.flush()

    schedule_at(
        finish, complete_megastructure, str(player.id), mtype,
        job_id=f"megastructure:{player.id}",
    )
    return row


async def complete_megastructure(player_id: str, mtype: str) -> None:
    async with session_scope() as session:
        row = (await session.execute(
            select(Megastructure).where(
                Megastructure.player_id == uuid.UUID(player_id), Megastructure.type == mtype
            )
        )).scalar_one_or_none()
        if row is None or row.building_until is None:
            return
        row.level += 1
        row.building_until = None
        new_level = row.level
        await session.commit()

    await event_bus.publish_ws(player_id, {
        "type": "megastructure_complete", "structure": mtype, "level": new_level,
    })
    log.info("Megastruktur fertig: %s lvl %s (player %s)", mtype, new_level, player_id)
