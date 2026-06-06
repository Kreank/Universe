"""Forschungs-Logik: Kosten (base*2^(lvl-1)), Zeit, Vorbedingungen, Abschluss.

Genau EINE Forschung pro Spieler gleichzeitig (DB partial unique index + Pruefung)."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import (
    get_building_levels,
    get_research_levels,
    refresh_resources,
    spend_resources,
)
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Planet, Research
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.research")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def cost_for_level(tech_type: str, current_level: int) -> dict[str, float]:
    """Forschungskosten current_level -> current_level+1 = base * 2^current_level."""
    base = get_balance().techs[tech_type]["cost"]
    mult = 2 ** current_level
    return {
        "metal": round(base.get("metal", 0) * mult, 2),
        "crystal": round(base.get("crystal", 0) * mult, 2),
        "deuterium": round(base.get("deuterium", 0) * mult, 2),
    }


def research_seconds(cost: dict[str, float], lab_lvl: int) -> int:
    """Forschungszeit (Sekunden): (M+K) / (1000*(1+lab)*speed) Stunden."""
    bal = get_balance()
    divisor = bal.data["research"]["divisor"]
    speed = bal.speed
    hours = (cost["metal"] + cost["crystal"]) / (divisor * (1 + lab_lvl) * speed)
    return max(1, int(round(hours * 3600)))


def requirements_met(
    tech_type: str, research_levels: dict[str, int], building_levels: dict[str, int]
) -> bool:
    """Prueft requires-Dict gegen Forschungs- und Gebaeudestufen."""
    requires = get_balance().techs[tech_type].get("requires", {})
    for key, needed in requires.items():
        have = research_levels.get(key, building_levels.get(key, 0))
        if have < needed:
            return False
    return True


async def active_research(session: AsyncSession, player_id: uuid.UUID) -> Research | None:
    return (await session.execute(
        select(Research).where(
            Research.player_id == player_id, Research.finishes_at.is_not(None)
        )
    )).scalar_one_or_none()


async def research_options(session: AsyncSession, player_id: uuid.UUID, lab_planet: Planet | None) -> list[dict]:
    bal = get_balance()
    rlevels = await get_research_levels(session, player_id)
    blevels = await get_building_levels(session, lab_planet.id) if lab_planet else {}
    lab_lvl = blevels.get("research_lab", 0)
    resources = await refresh_resources(session, lab_planet) if lab_planet else None

    options: list[dict] = []
    for tech in bal.techs.keys():
        level = rlevels.get(tech, 0)
        cost = cost_for_level(tech, level)
        secs = research_seconds(cost, lab_lvl)
        if resources is not None:
            can_afford = all(
                resources[r]["amount"] + 1e-6 >= cost[r] for r in ("metal", "crystal", "deuterium")
            )
        else:
            can_afford = False
        options.append({
            "type": tech,
            "next_level": level + 1,
            "cost": cost,
            "research_seconds": secs,
            "can_afford": can_afford,
            "requirements_met": requirements_met(tech, rlevels, blevels),
        })
    return options


async def start_research(session: AsyncSession, planet: Planet, tech_type: str) -> Research:
    """Startet eine Forschung am Labor-Standort ``planet``."""
    bal = get_balance()
    if tech_type not in bal.techs:
        raise ValueError("Unbekannte Technologie")
    if await active_research(session, planet.player_id) is not None:
        raise RuntimeError("Es laeuft bereits eine Forschung (one_at_a_time)")

    rlevels = await get_research_levels(session, planet.player_id)
    blevels = await get_building_levels(session, planet.id)
    if blevels.get("research_lab", 0) < 1:
        raise RuntimeError("Forschungslabor erforderlich")
    if not requirements_met(tech_type, rlevels, blevels):
        raise RuntimeError("Vorbedingungen nicht erfuellt")

    row = (await session.execute(
        select(Research).where(
            Research.player_id == planet.player_id, Research.type == tech_type
        )
    )).scalar_one_or_none()
    if row is None:
        row = Research(player_id=planet.player_id, type=tech_type, level=0)
        session.add(row)
        await session.flush()

    cost = cost_for_level(tech_type, row.level)
    if not await spend_resources(session, planet, cost):
        raise RuntimeError("Nicht genug Ressourcen")

    secs = research_seconds(cost, blevels.get("research_lab", 0))
    finish = _now() + dt.timedelta(seconds=secs)
    row.finishes_at = finish
    await session.flush()

    schedule_at(
        finish,
        complete_research,
        str(planet.player_id),
        tech_type,
        job_id=f"research:{planet.player_id}",
    )
    return row


async def complete_research(player_id: str, tech_type: str) -> None:
    async with session_scope() as session:
        row = (await session.execute(
            select(Research).where(
                Research.player_id == uuid.UUID(player_id), Research.type == tech_type
            )
        )).scalar_one_or_none()
        if row is None or row.finishes_at is None:
            return
        row.level += 1
        row.finishes_at = None
        new_level = row.level
        await session.commit()

    await event_bus.publish_ws(player_id, {
        "type": "research_complete",
        "tech": tech_type,
        "level": new_level,
    })
    log.info("Forschung fertig: %s lvl %s (player %s)", tech_type, new_level, player_id)
