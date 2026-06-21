"""Forschungs-Logik: Kosten (base*2^(lvl-1)), Zeit, Vorbedingungen, Abschluss.

Genau EINE Forschung pro Spieler gleichzeitig (DB partial unique index + Pruefung)."""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import (
    add_resources,
    get_building_levels,
    get_research_levels,
    refresh_resources,
    spend_resources,
)
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Planet, Research
from app.platform.scheduler import cancel_job, schedule_at

log = logging.getLogger("universe.research")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def cost_for_level(tech_type: str, current_level: int) -> dict[str, float]:
    """Forschungskosten current_level -> current_level+1.

    Normale Techs: ``base * 2^current_level`` (exponentiell, weicher Soft-Cap).
    Repeatable-Techs (``repeatable: true``): ``base * (current_level + 1)`` — linear-
    additiv. Zusammen mit dem additiven Pro-Stufe-Effekt sinkt der Grenznutzen je
    Forschungspunkt stetig (Stellaris-Modell): nie ``fertig``, aber kein Power-Creep,
    und ein Neuling holt fuer dieselbe Stunde mehr Prozent heraus als ein Veteran."""
    cfg = get_balance().techs[tech_type]
    base = cfg["cost"]
    mult = (current_level + 1) if cfg.get("repeatable") else (2 ** current_level)
    return {
        "metal": round(base.get("metal", 0) * mult, 2),
        "crystal": round(base.get("crystal", 0) * mult, 2),
        "deuterium": round(base.get("deuterium", 0) * mult, 2),
        # Endgame-Forschungen kosten zusaetzlich Dunkle Materie (skaliert mit derselben
        # Stufen-Multiplikation wie m/c/d). Techs ohne dark_matter im Basis-Block -> 0.
        "dark_matter": round(base.get("dark_matter", 0) * mult, 2),
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


def requirement_list(
    tech_type: str, research_levels: dict[str, int], building_levels: dict[str, int]
) -> list[dict]:
    """Uebersetzt das ``requires``-Dict einer Tech in eine Liste mit Status je Eintrag."""
    requires = get_balance().techs[tech_type].get("requires", {})
    return [
        {
            "type": key,
            "level": needed,
            "met": research_levels.get(key, building_levels.get(key, 0)) >= needed,
        }
        for key, needed in requires.items()
    ]


def sum_top_labs(lab_levels: list[int], network_level: int) -> int:
    """IGFN-Kernformel (pure): summiert die ``network_level + 1`` hoechsten Laborstufen.

    Ohne Netzwerk (Stufe 0) zaehlt allein das staerkste Labor (top 1). Jede IGFN-Stufe
    koppelt ein weiteres Labor dazu (OGame-Modell)."""
    take = max(1, network_level + 1)
    return sum(sorted(lab_levels, reverse=True)[:take])


async def effective_lab_level(
    session: AsyncSession, player_id: uuid.UUID, network_level: int
) -> int:
    """Effektive Laborstufe fuer die Forschungszeit.

    Mit dem Intergalaktischen Forschungsnetzwerk (IGFN, ``research_network``) summieren
    sich die Forschungslabore der besten ``network_level + 1`` Planeten. Ohne IGFN
    (Stufe 0) zaehlt allein das staerkste Labor. Belohnt breite Expansion, ohne reine
    Ein-Planet-Turtles zu bevorzugen."""
    planets = (await session.execute(
        select(Planet.id).where(Planet.player_id == player_id)
    )).scalars().all()
    labs: list[int] = []
    for pid in planets:
        blevels = await get_building_levels(session, pid)
        labs.append(blevels.get("research_lab", 0))
    return sum_top_labs(labs, network_level)


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
    # IGFN: effektive Laborstufe summiert die besten Labore (research_network+1 Planeten).
    network_level = rlevels.get("research_network", 0)
    lab_lvl = (
        await effective_lab_level(session, player_id, network_level) if lab_planet else 0
    )
    # Megastruktur Forschungs-Nexus: imperiumsweiter Forschungs-Tempo-Bonus.
    from app.megastructure.service import effect_mult
    nexus = await effect_mult(session, player_id, "research_speed")
    resources = await refresh_resources(session, lab_planet) if lab_planet else None

    options: list[dict] = []
    for tech in bal.techs.keys():
        level = rlevels.get(tech, 0)
        cost = cost_for_level(tech, level)
        secs = max(1, int(round(research_seconds(cost, lab_lvl) / nexus)))
        if resources is not None:
            exotic = resources.get("exotic", {})
            can_afford = all(
                resources[r]["amount"] + 1e-6 >= cost[r] for r in ("metal", "crystal", "deuterium")
            ) and (
                exotic.get("dark_matter", {}).get("amount", 0.0) + 1e-6 >= cost.get("dark_matter", 0)
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
            "requirements": requirement_list(tech, rlevels, blevels),
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

    # IGFN: Forschungszeit nutzt die summierte Laborstufe (effective_lab_level).
    network_level = rlevels.get("research_network", 0)
    lab_lvl = await effective_lab_level(session, planet.player_id, network_level)
    from app.megastructure.service import effect_mult
    nexus = await effect_mult(session, planet.player_id, "research_speed")
    from app.events.buffs import buff_mult as _buff_mult
    event_speed = await _buff_mult(session, "research_speed", player_id=planet.player_id)
    # Verwaltungs-Garnitur (Equipment des Gouverneurs auf diesem Planeten): +Forschungstempo.
    gov_speed = 1.0
    if getattr(planet, "governor_commander_id", None):
        from app.commander.equipment import commander_stat_bonus
        from app.platform.models import Commander as _Cmd
        _gov = await session.get(_Cmd, planet.governor_commander_id)
        gov_speed = 1.0 + await commander_stat_bonus(
            session, planet.governor_commander_id, "research_speed", _gov.morale if _gov else 100)
    secs = max(1, int(round(research_seconds(cost, lab_lvl) / (nexus * event_speed * gov_speed))))
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


async def cancel_research(session: AsyncSession, planet: Planet) -> Research | None:
    """Bricht die laufende Forschung des Spielers ab: voller Ressourcen-Refund auf den
    uebergebenen (Labor-)Planeten, Timer + Scheduler-Job entfernt. None ohne laufende Forschung."""
    row = await active_research(session, planet.player_id)
    if row is None:
        raise RuntimeError("Es laeuft keine Forschung")
    await add_resources(session, planet, cost_for_level(row.type, row.level))
    row.finishes_at = None
    await session.flush()
    cancel_job(f"research:{planet.player_id}")
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
