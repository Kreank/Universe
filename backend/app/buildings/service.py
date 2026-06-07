"""Gebaeude-Logik: Kosten/Bauzeit-Formeln, Ausbau starten, Abschluss-Job.

Kosten der naechsten Stufe = base * factor^(aktuelle_stufe). Bauzeit aus balance.json.
Pro Planet darf nur EIN Gebaeude gleichzeitig im Bau sein (api-contract §3, 409)."""
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
from app.platform.models import Building, Planet
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.buildings")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def cost_for_level(building_type: str, current_level: int) -> dict[str, float]:
    """Kosten fuer den Ausbau current_level -> current_level+1."""
    cfg = get_balance().buildings[building_type]
    factor = cfg["factor"]
    mult = factor ** current_level
    base = cfg["cost"]
    return {
        "metal": round(base.get("metal", 0) * mult, 2),
        "crystal": round(base.get("crystal", 0) * mult, 2),
        "deuterium": round(base.get("deuterium", 0) * mult, 2),
    }


def energy_for_level(building_type: str, level: int, energy_tech: int = 0) -> float:
    """Signierte Energiebilanz eines Gebaeudes bei gegebener Stufe.

    Vorzeichen: positiv = erzeugt Energie, negativ = verbraucht, 0 = neutral.
    Nutzt dieselben Formeln wie economy.compute_production_and_energy."""
    if level <= 0:
        return 0.0
    cfg = get_balance().buildings[building_type]
    # Verbraucher (Minen/Synthesizer)
    if "energy_base" in cfg:
        return -round(cfg["energy_base"] * level * (cfg["energy_growth"] ** level), 1)
    # Solarkraftwerk
    if building_type == "solar_plant":
        return round(cfg["energy_prod_base"] * level * (cfg["energy_prod_growth"] ** level), 1)
    # Fusionsreaktor (haengt von Energietechnik ab)
    if building_type == "fusion_reactor":
        return round(cfg["energy_prod_base"] * level * ((1.05 + 0.01 * energy_tech) ** level), 1)
    return 0.0


def build_seconds(cost: dict[str, float], robot_factory_lvl: int, nanite_lvl: int = 0) -> int:
    """Bauzeit (Sekunden): (M+K) / (2500*(1+robot)*2^nanite*speed) Stunden."""
    bal = get_balance()
    divisor = bal.data["build_time"]["divisor"]
    speed = bal.speed
    hours = (cost["metal"] + cost["crystal"]) / (
        divisor * (1 + robot_factory_lvl) * (2 ** nanite_lvl) * speed
    )
    seconds = int(round(hours * 3600))
    return max(bal.data["build_time"]["min_seconds"], seconds)


async def building_options(session: AsyncSession, planet: Planet) -> list[dict]:
    """Berechnet fuer jeden Gebaeudetyp die naechste Ausbau-Option."""
    bal = get_balance()
    levels = await get_building_levels(session, planet.id)
    robot = levels.get("robot_factory", 0)
    research = await get_research_levels(session, planet.player_id)
    energy_tech = research.get("energy_tech", 0)
    resources = await refresh_resources(session, planet)
    options: list[dict] = []
    for btype in bal.buildings.keys():
        level = levels.get(btype, 0)
        cost = cost_for_level(btype, level)
        secs = build_seconds(cost, robot)
        can_afford = all(
            resources[r]["amount"] + 1e-6 >= cost[r] for r in ("metal", "crystal", "deuterium")
        )
        energy_now = energy_for_level(btype, level, energy_tech)
        energy_next = energy_for_level(btype, level + 1, energy_tech)
        options.append({
            "type": btype,
            "next_level": level + 1,
            "cost": cost,
            "build_seconds": secs,
            "can_afford": can_afford,
            "requirements_met": True,  # Gebaeude haben im Slice keine Vorbedingungen
            "requirements": [],  # Gebaeude haben im Slice keine Vorbedingungen
            "energy_now": energy_now,
            "energy_next": energy_next,
            "energy_delta": round(energy_next - energy_now, 1),
        })
    return options


async def is_building_in_progress(session: AsyncSession, planet_id: uuid.UUID) -> bool:
    rows = (await session.execute(
        select(Building).where(
            Building.planet_id == planet_id,
            Building.upgrade_finishes_at.is_not(None),
        )
    )).scalars().all()
    return len(rows) > 0


async def start_upgrade(session: AsyncSession, planet: Planet, building_type: str) -> Building:
    """Startet einen Gebaeudeausbau. Wirft ValueError bei ungueltigem Typ,
    RuntimeError bei laufendem Bau oder fehlenden Ressourcen."""
    bal = get_balance()
    if building_type not in bal.buildings:
        raise ValueError("Unbekannter Gebaeudetyp")
    if await is_building_in_progress(session, planet.id):
        raise RuntimeError("Es laeuft bereits ein Gebaeudeausbau auf diesem Planeten")
    # Feld-Budget erzwingen: jede Gebaeudestufe kostet ein Feld (Modell A, Doku 06a).
    if planet.fields_used >= planet.fields_max:
        raise RuntimeError("Kein Bauplatz frei")

    # Gebaeude-Zeile holen oder anlegen.
    row = (await session.execute(
        select(Building).where(Building.planet_id == planet.id, Building.type == building_type)
    )).scalar_one_or_none()
    if row is None:
        row = Building(planet_id=planet.id, type=building_type, level=0)
        session.add(row)
        await session.flush()

    levels = await get_building_levels(session, planet.id)
    cost = cost_for_level(building_type, row.level)
    if not await spend_resources(session, planet, cost):
        raise RuntimeError("Nicht genug Ressourcen")

    secs = build_seconds(cost, levels.get("robot_factory", 0))
    finish = _now() + dt.timedelta(seconds=secs)
    row.upgrade_finishes_at = finish
    await session.flush()

    schedule_at(
        finish,
        complete_building,
        str(planet.id),
        building_type,
        job_id=f"build:{planet.id}:{building_type}",
    )
    return row


async def demolish_building(session: AsyncSession, planet: Planet, building_type: str) -> Building:
    """Reisst ein Gebaeude eine Stufe ab und gibt das Feld zurueck.

    Stufe -1 (min 0), ``fields_used -= 1`` (min 0). KEIN Ressourcen-Refund —
    die Felder-Erstattung ist der Zweck (Doku 06a §2). Erlaubt nur bei Stufe > 0
    und ohne laufenden Ausbau dieses Gebaeudes. Wirft ValueError/RuntimeError."""
    bal = get_balance()
    if building_type not in bal.buildings:
        raise ValueError("Unbekannter Gebaeudetyp")
    row = (await session.execute(
        select(Building).where(Building.planet_id == planet.id, Building.type == building_type)
    )).scalar_one_or_none()
    if row is None or row.level <= 0:
        raise RuntimeError("Gebaeude hat keine Stufe zum Abreissen")
    if row.upgrade_finishes_at is not None:
        raise RuntimeError("Gebaeude ist gerade im Ausbau")

    # Ressourcen mit aktueller Rate fortschreiben, dann Stufe + Feld zuruecknehmen.
    await refresh_resources(session, planet)
    row.level -= 1
    planet.fields_used = max(0, planet.fields_used - 1)
    # Neue (niedrigere) Produktionsrate wirksam machen.
    await refresh_resources(session, planet)
    await session.flush()
    return row


async def complete_building(planet_id: str, building_type: str) -> None:
    """Scheduler-Callback: erhoeht die Stufe, published WS-Event."""
    async with session_scope() as session:
        planet = await session.get(Planet, uuid.UUID(planet_id))
        if planet is None:
            return
        row = (await session.execute(
            select(Building).where(
                Building.planet_id == planet.id, Building.type == building_type
            )
        )).scalar_one_or_none()
        if row is None or row.upgrade_finishes_at is None:
            return
        # Ressourcen vor dem Stufensprung mit alter Rate fortschreiben.
        await refresh_resources(session, planet)
        row.level += 1
        row.upgrade_finishes_at = None
        planet.fields_used += 1
        # Neue Rate wirksam machen.
        await refresh_resources(session, planet)
        new_level = row.level
        player_id = planet.player_id
        await session.commit()

    await event_bus.publish_ws(player_id, {
        "type": "build_complete",
        "planet_id": planet_id,
        "building": building_type,
        "level": new_level,
    })
    log.info("Gebaeude fertig: %s lvl %s auf %s", building_type, new_level, planet_id)
