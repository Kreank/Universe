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
    add_resources,
    get_building_levels,
    get_research_levels,
    refresh_resources,
    spend_resources,
)
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Building, Planet
from app.platform.scheduler import cancel_job, schedule_at

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


def effective_fields_max(
    planet: Planet, levels: dict[str, int], terraforming_level: int = 0
) -> int:
    """Bauplaetze: Planet = gespeichert + Terraforming-Bonus; Mond = base_fields +
    moon_base-Level * pro Stufe (Monde profitieren NICHT von Terraforming)."""
    bal = get_balance()
    if planet.planet_type != "moon":
        per_tf = int(bal.data["research"].get("effects", {}).get("terraforming_fields_per_level", 0))
        return planet.fields_max + terraforming_level * per_tf
    base = int(bal.data["moon"]["base_fields"])
    per = int(bal.buildings["moon_base"].get("moon_fields_per_level", 3))
    return base + levels.get("moon_base", 0) * per


async def building_options(session: AsyncSession, planet: Planet) -> list[dict]:
    """Berechnet fuer jeden (am Koerpertyp erlaubten) Gebaeudetyp die naechste Ausbau-Option."""
    bal = get_balance()
    levels = await get_building_levels(session, planet.id)
    robot = levels.get("robot_factory", 0)
    research = await get_research_levels(session, planet.player_id)
    energy_tech = research.get("energy_tech", 0)
    resources = await refresh_resources(session, planet)
    is_moon = planet.planet_type == "moon"
    options: list[dict] = []
    for btype, bcfg in bal.buildings.items():
        # Mond-Gebaeude nur auf Monden, Nicht-Mond-Gebaeude nur auf Planeten.
        if bool(bcfg.get("moon_only", False)) != is_moon:
            continue
        # Gravitationslabor: Mondbasis Voraussetzung (sonst sinnlos)
        level = levels.get(btype, 0)
        cost = cost_for_level(btype, level)
        secs = build_seconds(cost, robot)
        can_afford = all(
            resources[r]["amount"] + 1e-6 >= cost[r] for r in ("metal", "crystal", "deuterium")
        )
        req = bcfg.get("requires", {})
        req_list = [
            {"type": rt, "level": rl, "met": levels.get(rt, 0) >= rl} for rt, rl in req.items()
        ]
        req_met = all(item["met"] for item in req_list)
        energy_now = energy_for_level(btype, level, energy_tech)
        energy_next = energy_for_level(btype, level + 1, energy_tech)
        # Positions-gebundene Gebaeude (Exo-Minen): nur auf den erlaubten Slots baubar. Wird gelistet,
        # aber auf falscher Position als nicht-baubar markiert (Discoverability statt Verstecken).
        allowed_pos = bcfg.get("allowed_positions")
        position_ok = True if not allowed_pos else (planet.position in [int(p) for p in allowed_pos])
        options.append({
            "type": btype,
            "next_level": level + 1,
            "cost": cost,
            "build_seconds": secs,
            "can_afford": can_afford,
            "requirements_met": req_met,
            "requirements": req_list,
            "energy_now": energy_now,
            "energy_next": energy_next,
            "energy_delta": round(energy_next - energy_now, 1),
            "position_ok": position_ok,
            "allowed_positions": [int(p) for p in allowed_pos] if allowed_pos else [],
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
    # Mond-Gebaeude nur auf Monden, Nicht-Mond-Gebaeude nur auf Planeten.
    is_moon = planet.planet_type == "moon"
    if bool(bal.buildings[building_type].get("moon_only", False)) != is_moon:
        raise ValueError("Dieses Gebaeude ist hier nicht baubar")
    # Positions-Gate (Exo-Minen): nur auf den erlaubten System-Slots baubar.
    allowed_pos = bal.buildings[building_type].get("allowed_positions")
    if allowed_pos and planet.position not in [int(p) for p in allowed_pos]:
        raise ValueError(
            f"Dieses Gebaeude ist nur auf Position {', '.join(str(int(p)) for p in allowed_pos)} baubar"
        )
    if await is_building_in_progress(session, planet.id):
        raise RuntimeError("Es laeuft bereits ein Gebaeudeausbau auf diesem Planeten")
    # Feld-Budget erzwingen: jede Gebaeudestufe kostet ein Feld (Modell A, Doku 06a).
    levels0 = await get_building_levels(session, planet.id)
    req = bal.buildings[building_type].get("requires", {})
    if not all(levels0.get(rt, 0) >= rl for rt, rl in req.items()):
        raise RuntimeError("Voraussetzung nicht erfuellt")
    rlevels0 = await get_research_levels(session, planet.player_id)
    if planet.fields_used >= effective_fields_max(planet, levels0, rlevels0.get("terraforming", 0)):
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


async def cancel_upgrade(session: AsyncSession, planet: Planet, building_type: str) -> Building:
    """Bricht den laufenden Ausbau dieses Gebaeudes ab: voller Ressourcen-Refund (die Stufe
    wurde noch nicht erhoeht), Timer + Scheduler-Job entfernt. Wirft RuntimeError ohne Ausbau."""
    bal = get_balance()
    if building_type not in bal.buildings:
        raise ValueError("Unbekannter Gebaeudetyp")
    row = (await session.execute(
        select(Building).where(Building.planet_id == planet.id, Building.type == building_type)
    )).scalar_one_or_none()
    if row is None or row.upgrade_finishes_at is None:
        raise RuntimeError("Kein laufender Ausbau dieses Gebaeudes")
    # Voller Refund der investierten Kosten (cost_for_level der NOCH aktuellen Stufe).
    await add_resources(session, planet, cost_for_level(building_type, row.level))
    row.upgrade_finishes_at = None
    await session.flush()
    cancel_job(f"build:{planet.id}:{building_type}")
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
        # Mondbasis hebt die Bauplatz-Decke des Mondes.
        if planet.planet_type == "moon" and building_type == "moon_base":
            bal = get_balance()
            planet.fields_max = int(bal.data["moon"]["base_fields"]) + row.level * int(
                bal.buildings["moon_base"].get("moon_fields_per_level", 3)
            )
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
