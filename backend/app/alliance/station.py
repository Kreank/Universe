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
from app.platform.models import Alliance, AllianceStation, Planet, UniverseCell
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


async def station_at(
    session: AsyncSession, galaxy: int, system: int, position: int
) -> AllianceStation | None:
    """Nicht-zerstoerte Station an exakt dieser Koordinate (Angriffsziel-Lookup)."""
    return (await session.execute(
        select(AllianceStation).where(
            AllianceStation.galaxy == int(galaxy),
            AllianceStation.system == int(system),
            AllianceStation.position == int(position),
            AllianceStation.status != "destroyed",
        )
    )).scalars().first()


# -- Belagerung (Phase 2): Abwehrbatterien + hp-Chip + >=2-Angreifer-Gate -------

def station_defenses(station: AllianceStation, cfg: dict | None = None) -> dict[str, int]:
    """Feste Abwehrbatterien der Station (skalieren mit dem Ausbau-Radius). Regenerieren je
    Schlacht (Festungs-Selbstreparatur) -> nur die hp sind der dauerhafte Zerstoerungs-Zaehler."""
    cfg = cfg or _scfg()
    base = dict(cfg.get("defense_base", {}))
    per = cfg.get("defense_per_radius", {})
    lvl = int(station.research_radius_level or 0)
    out: dict[str, int] = {}
    for t, n in base.items():
        v = int(n) + int(per.get(t, 0)) * lvl
        if v > 0:
            out[t] = v
    return out


def station_defender(station: AllianceStation) -> dict:
    """Verteidiger-Dict fuer die Kampf-Engine: nur Abwehrbatterien + feste Tech, keine Schiffe."""
    cfg = _scfg()
    return {
        "ships": {},
        "defenses": station_defenses(station, cfg),
        "tech": dict(cfg.get("defense_tech", {})),
        "attack_mult": 1.0,
    }


def _parse_iso(s) -> dt.datetime | None:
    if not s:
        return None
    try:
        t = dt.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    return t.replace(tzinfo=dt.timezone.utc) if t.tzinfo is None else t


def _prune_attackers(siege: dict, now: dt.datetime, window: float) -> dict:
    cutoff = now - dt.timedelta(seconds=window)
    kept: dict = {}
    for pid, info in (siege.get("attackers", {}) or {}).items():
        at = _parse_iso((info or {}).get("at"))
        if at is not None and at >= cutoff:
            kept[pid] = info
    return kept


def record_siege_hit(
    station: AllianceStation, attacker_player_id, damage: float, now: dt.datetime
) -> dict:
    """Verbucht einen Belagerungs-Treffer: chippt hp, merkt den Angreifer (im siege_window).
    Zerstoerung erst wenn hp<=0 UND >=destroy_min_attackers VERSCHIEDENE Spieler beigetragen haben.

    Liefert {destroyed, hp, distinct_attackers, min_attackers, damage}."""
    cfg = _scfg()
    window = float(cfg.get("siege_window_seconds", 86400))
    damage = max(0.0, float(damage or 0))
    siege = dict(station.siege or {})
    attackers = _prune_attackers(siege, now, window)
    pid = str(attacker_player_id)
    prev_dmg = float((attackers.get(pid) or {}).get("damage", 0))
    attackers[pid] = {"damage": round(prev_dmg + damage, 1), "at": now.isoformat()}
    siege["attackers"] = attackers
    siege["last_attack_at"] = now.isoformat()
    station.siege = siege
    station.hp = round(max(0.0, float(station.hp or 0) - damage), 1)
    min_attackers = int(cfg.get("destroy_min_attackers", 2))
    destroyed = station.hp <= 0 and len(attackers) >= min_attackers
    if destroyed:
        station.status = "destroyed"
    return {
        "destroyed": destroyed,
        "hp": station.hp,
        "distinct_attackers": len(attackers),
        "min_attackers": min_attackers,
        "damage": round(damage, 1),
    }


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

    # Station nur auf einem FREIEN Slot errichten: sonst koennte sie sich mit einem Planeten
    # ueberlagern und waere durch ihn nie direkt angreifbar (Unzerstoerbar-Exploit). Planet,
    # belegte Zelle (NPC/Asteroid) und eine bereits vorhandene Station blockieren den Slot.
    g, sy, ps = int(galaxy), int(system), int(position)
    if (await session.execute(
        select(Planet).where(Planet.galaxy == g, Planet.system == sy, Planet.position == ps)
    )).scalar_one_or_none() is not None:
        raise ValueError("Auf dieser Position steht ein Planet — eine Station braucht einen freien Slot.")
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == g, UniverseCell.system == sy, UniverseCell.position == ps
        )
    )).scalar_one_or_none()
    if cell is not None and cell.occupant_type not in (None, "empty"):
        raise ValueError("Diese Position ist belegt — eine Station braucht einen freien Slot.")
    if await station_at(session, g, sy, ps) is not None:
        raise ValueError("Hier steht bereits eine Station.")

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
        # hp-Regen zwischen Belagerungswellen: nur wenn seit dem letzten Treffer Ruhe herrscht.
        max_hp = float(cfg.get("hp", 0))
        regen = float(cfg.get("hp_regen_per_tick", 0))
        if regen > 0 and float(station.hp or 0) < max_hp:
            quiet = float(cfg.get("regen_quiet_seconds", 7200))
            last_hit = _parse_iso((station.siege or {}).get("last_attack_at"))
            if last_hit is None or (_now() - last_hit).total_seconds() >= quiet:
                station.hp = round(min(max_hp, float(station.hp or 0) + regen), 1)
        station.last_upkeep_at = _now()
        alive = True
        await session.commit()
    if alive:
        schedule_upkeep(station_id, interval)
