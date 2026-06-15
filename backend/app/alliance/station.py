"""Allianz-Station + Einflusszone.

Die Station projiziert die Baum-Spezialisierung der Allianz in eine Zone (Systeme im Radius,
gleiches System-Distanz-Muster wie Abfang-/Phalanx-Radius). Radius = base + research_radius_level
(Cap max_radius). Upkeep zehrt je Tick Deuterium aus ``fuel``; leer -> status 'inactive' (Zone aus).
Eine Station projiziert ihre Zone nur, wenn status='active' UND fuel > 0.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alliance.service import RES_KEYS, _acfg, _require_role
from app.platform.db import session_scope
from app.platform.models import Alliance, AllianceStation
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.alliance.station")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _scfg() -> dict:
    return _acfg().get("station", {})


def zone_radius(station: AllianceStation) -> int:
    cfg = _scfg()
    base = int(cfg.get("base_radius", 1))
    cap = int(cfg.get("max_radius", 5))
    return min(cap, base + int(station.research_radius_level or 0))


def covers(station: AllianceStation, galaxy: int, system: int) -> bool:
    """Liegt (galaxy, system) in der Zone? Aktiv + getankt + gleiche Galaxie + System-Distanz <= Radius."""
    if station.status != "active" or float(station.fuel or 0) <= 0:
        return False
    if station.galaxy != int(galaxy):
        return False
    return abs(station.system - int(system)) <= zone_radius(station)


async def active_station_in_zone(
    session: AsyncSession, alliance_id: uuid.UUID, galaxy: int, system: int
) -> AllianceStation | None:
    """Erste aktive Station der Allianz, deren Zone (galaxy, system) abdeckt (oder None)."""
    rows = (await session.execute(
        select(AllianceStation).where(
            AllianceStation.alliance_id == alliance_id,
            AllianceStation.status == "active",
        )
    )).scalars().all()
    for s in rows:
        if covers(s, galaxy, system):
            return s
    return None


# -- Bau / Tank / Ausbau --------------------------------------------------------

async def build_station(
    session: AsyncSession, player, galaxy: int, system: int, position: int
) -> AllianceStation:
    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    cfg = _scfg()
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()

    existing = (await session.execute(
        select(AllianceStation).where(AllianceStation.alliance_id == al.id)
    )).scalars().all()
    active = [s for s in existing if s.status != "destroyed"]
    if len(active) >= int(cfg.get("max_per_alliance", 1)):
        raise ValueError("Maximale Stationszahl erreicht (Vorposten kommen in einer spaeteren Ausbaustufe).")

    cost = cfg.get("build_cost", {})
    pool = dict(al.pool or {})
    if not all(float(pool.get(k, 0)) >= float(cost.get(k, 0)) for k in RES_KEYS):
        raise ValueError("Der Allianz-Pool hat nicht genug Ressourcen fuer die Station.")
    for k in RES_KEYS:
        pool[k] = round(float(pool.get(k, 0)) - float(cost.get(k, 0)), 2)
    al.pool = pool

    station = AllianceStation(
        alliance_id=al.id, galaxy=int(galaxy), system=int(system), position=int(position),
        research_radius_level=0, fuel=0.0, hp=float(cfg.get("hp", 0)), status="active",
    )
    session.add(station)
    await session.flush()
    # Erste Upkeep-Pruefung einplanen.
    schedule_upkeep(station.id, int(cfg.get("tick_interval_seconds", 3600)))
    return station


async def refuel_station(session: AsyncSession, player, station_id: uuid.UUID, deuterium: float) -> AllianceStation:
    """Fuellt Stations-Treibstoff aus dem Pool (Deuterium). Reaktiviert eine leere Station."""
    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    deuterium = float(deuterium or 0)
    if deuterium <= 0:
        raise ValueError("Tankmenge muss positiv sein.")
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    station = await session.get(AllianceStation, station_id)
    if station is None or station.alliance_id != al.id or station.status == "destroyed":
        raise ValueError("Station nicht gefunden.")
    pool = dict(al.pool or {})
    if float(pool.get("deuterium", 0)) < deuterium:
        raise ValueError("Nicht genug Deuterium im Pool.")
    pool["deuterium"] = round(float(pool.get("deuterium", 0)) - deuterium, 2)
    al.pool = pool
    station.fuel = round(float(station.fuel or 0) + deuterium, 2)
    if station.status == "inactive" and station.fuel > 0:
        station.status = "active"
    return station


async def upgrade_radius(session: AsyncSession, player, station_id: uuid.UUID) -> AllianceStation:
    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    cfg = _scfg()
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    station = await session.get(AllianceStation, station_id)
    if station is None or station.alliance_id != al.id or station.status == "destroyed":
        raise ValueError("Station nicht gefunden.")
    max_extra = int(cfg.get("max_radius", 5)) - int(cfg.get("base_radius", 1))
    if int(station.research_radius_level or 0) >= max_extra:
        raise ValueError("Maximaler Radius erreicht.")
    cost = cfg.get("radius_upgrade_cost", {})
    pool = dict(al.pool or {})
    if not all(float(pool.get(k, 0)) >= float(cost.get(k, 0)) for k in RES_KEYS):
        raise ValueError("Der Allianz-Pool hat nicht genug Ressourcen fuer den Ausbau.")
    for k in RES_KEYS:
        pool[k] = round(float(pool.get(k, 0)) - float(cost.get(k, 0)), 2)
    al.pool = pool
    station.research_radius_level = int(station.research_radius_level or 0) + 1
    return station


# -- Upkeep-Tick (selbst-fortlaufend, wie der Routinen-Zyklus) ------------------

def schedule_upkeep(station_id: uuid.UUID | str, interval_seconds: int) -> None:
    sid = str(station_id)
    schedule_at(_now() + dt.timedelta(seconds=max(60, interval_seconds)),
                station_upkeep_tick, sid, job_id=f"alliance-station-upkeep:{sid}")


async def station_upkeep_tick(station_id: str) -> None:
    """Zehrt Upkeep-Deuterium; leer -> 'inactive' (Zone aus). Plant den naechsten Tick."""
    cfg = _scfg()
    interval = int(cfg.get("tick_interval_seconds", 3600))
    upkeep = float(cfg.get("upkeep_deuterium_per_tick", 0))
    alive = False
    async with session_scope() as session:
        station = await session.get(AllianceStation, uuid.UUID(station_id))
        if station is None or station.status == "destroyed":
            return
        new_fuel = float(station.fuel or 0) - upkeep
        if new_fuel <= 0:
            station.fuel = 0.0
            station.status = "inactive"
        else:
            station.fuel = round(new_fuel, 2)
            station.status = "active"
        station.last_upkeep_at = _now()
        alive = True
        await session.commit()
    if alive:
        schedule_upkeep(station_id, interval)
