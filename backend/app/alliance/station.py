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
from app.platform.models import (
    Alliance,
    AllianceMember,
    AllianceStation,
    Planet,
    Ship,
    UniverseCell,
)
from app.platform.scheduler import cancel_job, schedule_at

log = logging.getLogger("universe.alliance.station")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _scfg() -> dict:
    return _acfg().get("station", {})


def _mcfg() -> dict:
    return _scfg().get("modules", {})


# -- Module (Slots) -------------------------------------------------------------

_TECH_MODULE_KEYS = ("weapons_tech", "shield_tech", "armor_tech")


def station_slots(station: AllianceStation) -> int:
    """Verfuegbare Modul-Slots = base_slots + slot_level (eigener Ausbau, getrennt vom Radius)."""
    cfg = _mcfg()
    total = int(cfg.get("base_slots", 0)) + int(station.slot_level or 0)
    return min(int(cfg.get("max_slots", total)), total)


def station_modules(station: AllianceStation) -> dict[str, int]:
    """Montierte Module {typ: anzahl} (nur > 0)."""
    return {t: int(c) for t, c in (station.modules or {}).items() if int(c) > 0}


def slots_used(station: AllianceStation) -> int:
    return sum(station_modules(station).values())


def module_tech_bonus(station: AllianceStation) -> dict[str, int]:
    """Zusatz-Tech aus montierten Modulen (turret->weapons_tech, shield_generator->shield_tech,
    armor_plating->armor_tech). Wird auf die Abwehr-Tech der Station addiert -> wirkt in BEIDEN
    Kampf-Kontexten (Abfang + Belagerung) ueber die bestehende Kampf-Engine."""
    cat = _mcfg().get("catalog", {})
    out: dict[str, int] = {}
    for typ, count in station_modules(station).items():
        spec = cat.get(typ, {})
        for key in _TECH_MODULE_KEYS:
            if spec.get(key):
                out[key] = out.get(key, 0) + int(spec[key]) * count
    return out


def effective_defense_tech(station: AllianceStation) -> dict[str, int]:
    """Abwehr-Tech der Station: Basis-Stufe (frisch = 1) + Modul-Boni, GEDECKELT auf max_tech (12).
    Eine frische Station kaempft mit Tech 1; Geschuetzturm/Schildgenerator/Panzerplatte heben
    weapons_/shield_/armor_tech bis zum Cap (= 'Tech bis 12 durch Stations-Ausbau')."""
    cfg = _scfg()
    cap = int(cfg.get("max_tech", 12))
    tech = dict(cfg.get("defense_tech", {}))
    for key, bonus in module_tech_bonus(station).items():
        tech[key] = int(tech.get(key, 0)) + int(bonus)
    return {k: max(0, min(cap, int(v))) for k, v in tech.items()}


def station_max_hp(station: AllianceStation) -> float:
    """Maximale HP = Basis (balance.station.hp) + Summe der hull_reinforcement-Module."""
    base = float(_scfg().get("hp", 0))
    cat = _mcfg().get("catalog", {})
    extra = 0.0
    for typ, count in station_modules(station).items():
        extra += float(cat.get(typ, {}).get("max_hp", 0)) * count
    return base + extra


def relocate_speed_mult(station: AllianceStation) -> float:
    """Reisezeit-Faktor (<1 = schneller) aus thruster-Modulen, gedeckelt auf thruster_speed_cap."""
    cfg = _mcfg()
    cat = cfg.get("catalog", {})
    boost = 0.0
    for typ, count in station_modules(station).items():
        boost += float(cat.get(typ, {}).get("relocate_speed_pct", 0)) * count
    boost = min(float(cfg.get("thruster_speed_cap", 0.5)), boost)
    return max(0.0, 1.0 - boost)


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
    """Ortsfeste, nicht-zerstoerte Station an exakt dieser Koordinate (Angriffsziel-/Slot-Lookup).

    Eine Station im Transit (status='transit') ist NICHT ortsfest — sie reist zwischen den Slots,
    gibt ihren alten Slot frei und ist nur unterwegs (per Abfang) angreifbar, nicht an Koordinaten.
    """
    return (await session.execute(
        select(AllianceStation).where(
            AllianceStation.galaxy == int(galaxy),
            AllianceStation.system == int(system),
            AllianceStation.position == int(position),
            AllianceStation.status.notin_(("destroyed", "transit")),
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
    """Verteidiger-Dict fuer die Kampf-Engine: Abwehrbatterien + feste Tech, keine Schiffe.
    Montierte Module heben die effektive Tech (turret/shield_generator/armor_plating)."""
    cfg = _scfg()
    return {
        "ships": {},
        "defenses": station_defenses(station, cfg),
        "tech": effective_defense_tech(station),
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


# -- Slot-Pruefung (Bau + Umstationierungs-Ziel) --------------------------------

async def _slot_blocker(session: AsyncSession, g: int, sy: int, ps: int) -> str | None:
    """Liefert eine Fehlermeldung, wenn der Slot belegt ist (Planet/NPC/Asteroid/Station),
    sonst None (frei). Eine Station im Transit blockiert NICHT (sie ist nicht ortsfest)."""
    if (await session.execute(
        select(Planet).where(Planet.galaxy == g, Planet.system == sy, Planet.position == ps)
    )).scalar_one_or_none() is not None:
        return "Auf dieser Position steht ein Planet — eine Station braucht einen freien Slot."
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == g, UniverseCell.system == sy, UniverseCell.position == ps
        )
    )).scalar_one_or_none()
    if cell is not None and cell.occupant_type not in (None, "empty"):
        return "Diese Position ist belegt — eine Station braucht einen freien Slot."
    if await station_at(session, g, sy, ps) is not None:
        return "Hier steht bereits eine Station."
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

    # Station nur auf einem FREIEN Slot errichten: sonst koennte sie sich mit einem Planeten
    # ueberlagern und waere durch ihn nie direkt angreifbar (Unzerstoerbar-Exploit).
    g, sy, ps = int(galaxy), int(system), int(position)
    blocker = await _slot_blocker(session, g, sy, ps)
    if blocker is not None:
        raise ValueError(blocker)

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


async def upgrade_slots(session: AsyncSession, player, station_id: uuid.UUID) -> AllianceStation:
    """Schaltet einen weiteren Modul-Slot frei (eigener Ausbau, getrennt vom Radius). Pool-Kosten."""
    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    cfg = _mcfg()
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    station = await session.get(AllianceStation, station_id)
    if station is None or station.alliance_id != al.id or station.status == "destroyed":
        raise ValueError("Station nicht gefunden.")
    max_extra = int(cfg.get("max_slots", 0)) - int(cfg.get("base_slots", 0))
    if int(station.slot_level or 0) >= max_extra:
        raise ValueError("Maximale Slot-Zahl erreicht.")
    cost = cfg.get("slot_upgrade_cost", {})
    pool = dict(al.pool or {})
    if not all(float(pool.get(k, 0)) >= float(cost.get(k, 0)) for k in RES_KEYS):
        raise ValueError("Der Allianz-Pool hat nicht genug Ressourcen für einen Slot.")
    for k in RES_KEYS:
        pool[k] = round(float(pool.get(k, 0)) - float(cost.get(k, 0)), 2)
    al.pool = pool
    station.slot_level = int(station.slot_level or 0) + 1
    return station


# -- Module montieren / abbauen -------------------------------------------------

async def mount_module(
    session: AsyncSession, player, station_id: uuid.UUID, module_type: str, count: int = 1
) -> AllianceStation:
    """Montiert ``count`` Module eines Typs in freie Slots (Pool-Kosten). Nicht im Transit."""
    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    cat = _mcfg().get("catalog", {})
    count = int(count)
    if module_type not in cat:
        raise ValueError("Unbekannter Modultyp.")
    if count <= 0:
        raise ValueError("Anzahl muss positiv sein.")
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    station = await session.get(AllianceStation, station_id)
    if station is None or station.alliance_id != al.id or station.status == "destroyed":
        raise ValueError("Station nicht gefunden.")
    if station.status == "transit":
        raise ValueError("Während des Umstationierens lassen sich keine Module montieren.")
    free = station_slots(station) - slots_used(station)
    if count > free:
        raise ValueError(f"Nicht genug freie Slots ({free} frei). Baue den Radius aus für mehr Slots.")
    cost = cat[module_type].get("cost", {})
    pool = dict(al.pool or {})
    if not all(float(pool.get(k, 0)) >= float(cost.get(k, 0)) * count for k in RES_KEYS):
        raise ValueError("Der Allianz-Pool hat nicht genug Ressourcen für das Modul.")
    for k in RES_KEYS:
        pool[k] = round(float(pool.get(k, 0)) - float(cost.get(k, 0)) * count, 2)
    al.pool = pool
    mods = dict(station.modules or {})
    mods[module_type] = int(mods.get(module_type, 0)) + count
    station.modules = mods
    return station


async def unmount_module(
    session: AsyncSession, player, station_id: uuid.UUID, module_type: str, count: int = 1
) -> AllianceStation:
    """Baut ``count`` Module eines Typs ab (Teil-Refund in den Pool). HP wird auf neues max gedeckelt."""
    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    cfg = _mcfg()
    cat = cfg.get("catalog", {})
    count = int(count)
    if module_type not in cat:
        raise ValueError("Unbekannter Modultyp.")
    if count <= 0:
        raise ValueError("Anzahl muss positiv sein.")
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    station = await session.get(AllianceStation, station_id)
    if station is None or station.alliance_id != al.id or station.status == "destroyed":
        raise ValueError("Station nicht gefunden.")
    if station.status == "transit":
        raise ValueError("Während des Umstationierens lassen sich keine Module abbauen.")
    mods = dict(station.modules or {})
    have = int(mods.get(module_type, 0))
    if have < count:
        raise ValueError("So viele Module dieses Typs sind nicht montiert.")
    refund_pct = float(cfg.get("unmount_refund_pct", 0))
    cost = cat[module_type].get("cost", {})
    pool = dict(al.pool or {})
    for k in RES_KEYS:
        pool[k] = round(float(pool.get(k, 0)) + float(cost.get(k, 0)) * count * refund_pct, 2)
    al.pool = pool
    mods[module_type] = have - count
    if mods[module_type] <= 0:
        del mods[module_type]
    station.modules = mods
    # HP auf neues Maximum deckeln (falls hull_reinforcement entfernt wurde).
    station.hp = round(min(float(station.hp or 0), station_max_hp(station)), 1)
    return station


# -- Kampfwerte (Anzeige) -------------------------------------------------------

def station_combat_stats(station: AllianceStation) -> dict:
    """Aggregierte Kampfwerte der Station fuer die Frontend-Anzeige: Abwehrbatterien-Komposition
    + EFFEKTIVE Summen (Angriff/Schild inkl. Tech aus Basis + Modulen), HP/max-HP, Slots/Module,
    Zonen-Radius und der Transit-Tempo-Bonus aus thruster-Modulen."""
    from app.platform.balance import get_balance
    bal = get_balance()
    cfg = _scfg()
    defenses = station_defenses(station, cfg)
    cat = bal.defenses
    tb = bal.data.get("tech_bonus", {})
    # Effektive Tech = Basis-Stufe + Modul-Boni, gedeckelt auf max_tech (12).
    eff_tech = effective_defense_tech(station)
    mods_tech = module_tech_bonus(station)
    w = 1.0 + float(tb.get("weapons_per_level", 0)) * eff_tech.get("weapons_tech", 0)
    s = 1.0 + float(tb.get("shield_per_level", 0)) * eff_tech.get("shield_tech", 0)
    attack = shield = 0.0
    for t, n in defenses.items():
        d = cat.get(t, {}) if isinstance(cat.get(t), dict) else {}
        attack += float(d.get("attack", 0)) * int(n)
        shield += float(d.get("shield", 0)) * int(n)
    return {
        "defenses": defenses,
        "attack_total": round(attack * w, 1),
        "shield_total": round(shield * s, 1),
        "max_hp": station_max_hp(station),
        "zone_radius": zone_radius(station),
        "defense_tech": eff_tech,
        "modules": station_modules(station),
        "slots": station_slots(station),
        "slots_used": slots_used(station),
        "module_tech_bonus": mods_tech,
        "relocate_speed_mult": relocate_speed_mult(station),
    }


# -- Allianz-Benachrichtigung ---------------------------------------------------

async def _notify_alliance(session: AsyncSession, alliance_id, subject: str, body: str) -> None:
    """Systemnachricht an alle Mitglieder der Allianz (best effort)."""
    from app.messaging.service import create_system_transmission
    member_ids = (await session.execute(
        select(AllianceMember.player_id).where(AllianceMember.alliance_id == alliance_id)
    )).scalars().all()
    for pid in member_ids:
        await create_system_transmission(
            session, player_id=pid, subject=subject, body=body, ttype="system",
        )


# -- Umstationieren (Transit) ---------------------------------------------------

def _coords(station: AllianceStation) -> list[int]:
    return [int(station.galaxy), int(station.system), int(station.position)]


async def relocate_station(
    session: AsyncSession,
    player,
    station_id: uuid.UUID,
    galaxy: int,
    system: int,
    position: int,
    escort: dict | None = None,
    escort_planet_id: uuid.UUID | None = None,
) -> AllianceStation:
    """Schickt die Station auf eine SEHR langsame Reise zu einem freien Slot derselben Galaxie.
    Waehrend des Transits ist die Zone aus (status='transit'), und die Station ist unterwegs per
    Abfang verwundbar. Eskorte (Schiffe von einem Planeten des Offiziers) reist mit und kaempft
    im Abfang. Deuterium-Kosten (distanzabhaengig) gehen aus dem Allianz-Pool."""
    from app.fleet.service import compute_distance

    m = await _require_role(session, player, _acfg().get("min_role_for_spend", "officer"))
    cfg = _scfg()
    rcfg = cfg.get("relocate", {})
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    station = await session.get(AllianceStation, station_id)
    if station is None or station.alliance_id != al.id or station.status == "destroyed":
        raise ValueError("Station nicht gefunden.")
    if station.status == "transit":
        raise ValueError("Die Station ist bereits unterwegs.")
    if station.status != "active":
        raise ValueError("Die Station muss aktiv (getankt) sein, um umzustationieren.")

    g, sy, ps = int(galaxy), int(system), int(position)
    if g != int(station.galaxy):
        raise ValueError("Umstationieren geht nur innerhalb derselben Galaxie.")
    if (g, sy, ps) == (int(station.galaxy), int(station.system), int(station.position)):
        raise ValueError("Die Station steht bereits an dieser Position.")
    blocker = await _slot_blocker(session, g, sy, ps)
    if blocker is not None:
        raise ValueError(blocker)

    origin = _coords(station)
    distance = compute_distance((origin[0], origin[1], origin[2]), (g, sy, ps))
    # Schubtriebwerk-Module beschleunigen die Reise (gedeckelt).
    travel_seconds = max(int(rcfg.get("min_seconds", 7200)),
                         int(round(distance * float(rcfg.get("seconds_per_distance", 3)) * relocate_speed_mult(station))))
    deut_cost = max(float(rcfg.get("min_deuterium", 5000)),
                    round(distance * float(rcfg.get("deuterium_per_distance", 5)), 1))
    pool = dict(al.pool or {})
    if float(pool.get("deuterium", 0)) < deut_cost:
        raise ValueError(f"Nicht genug Deuterium im Pool fuer die Reise ({deut_cost:.0f} noetig).")

    # Eskorte vom angegebenen Planeten des Offiziers einsammeln (optional).
    escort = {t: int(c) for t, c in (escort or {}).items() if int(c) > 0}
    escort_planet_uuid = None
    if escort:
        if escort_planet_id is None:
            raise ValueError("Fuer eine Eskorte muss ein Startplanet angegeben werden.")
        eplanet = await session.get(Planet, escort_planet_id)
        if eplanet is None or eplanet.player_id != player.id:
            raise ValueError("Eskort-Planet nicht gefunden.")
        for typ, count in escort.items():
            row = (await session.execute(
                select(Ship).where(
                    Ship.planet_id == eplanet.id, Ship.fleet_id.is_(None), Ship.type == typ
                )
            )).scalar_one_or_none()
            if row is None or row.count < count:
                raise ValueError(f"Nicht genug {typ} auf dem Eskort-Planeten.")
        # Erst nach voller Pruefung abziehen.
        for typ, count in escort.items():
            row = (await session.execute(
                select(Ship).where(
                    Ship.planet_id == eplanet.id, Ship.fleet_id.is_(None), Ship.type == typ
                )
            )).scalar_one()
            row.count -= count
            if row.count <= 0:
                await session.delete(row)
        escort_planet_uuid = str(eplanet.id)

    pool["deuterium"] = round(float(pool.get("deuterium", 0)) - deut_cost, 2)
    al.pool = pool

    now = _now()
    arrive = now + dt.timedelta(seconds=travel_seconds)
    station.status = "transit"
    station.transit = {
        "home": origin,
        "leg_from": origin,
        "leg_to": [g, sy, ps],
        "depart_at": now.isoformat(),
        "arrive_at": arrive.isoformat(),
        "returning": False,
        "escort": escort,
        "escort_planet_id": escort_planet_uuid,
        "escort_owner_id": str(player.id),
        "deuterium": deut_cost,
        "travel_seconds": travel_seconds,
    }
    await session.flush()
    schedule_at(arrive, station_arrive, str(station.id), job_id=f"station-arrive:{station.id}")
    try:
        await schedule_station_interceptions(session, station)
    except Exception:  # noqa: BLE001
        log.exception("Abfang-Planung fuer Stations-Transit %s fehlgeschlagen (ignoriert)", station.id)
    await _notify_alliance(
        session, al.id,
        subject=f"Station umstationiert ({origin[0]}:{origin[1]}:{origin[2]} → {g}:{sy}:{ps})",
        body=(f"Die Allianz-Station hat ihren Anker gelöst und reist zu {g}:{sy}:{ps}. "
              f"Ankunft in ~{travel_seconds // 3600}h {travel_seconds % 3600 // 60}min. "
              "Die Einflusszone ist während der Reise INAKTIV, und die Station ist unterwegs "
              "verwundbar (Abfang). Schickt Eskorte oder Verteidigung mit!"),
    )
    return station


async def schedule_station_interceptions(session: AsyncSession, station: AllianceStation) -> int:
    """Plant Abfang-Jobs feindlicher Patrouillen auf der galaxie-internen Transit-Route der Station.
    Spiegelt fleet.interception.schedule_interceptions_for_fleet. Allianz-eigene Patrouillen fangen
    die eigene Station NICHT. Liefert die Zahl geplanter Abfaenge."""
    from app.fleet.interception import _aware as _iaware, _frac_time
    from app.platform.balance import get_balance
    from app.platform.models import Player, StationedFleet

    icfg = get_balance().data["combat"].get("interception", {})
    tr = station.transit or {}
    if not icfg.get("enabled", False) or station.status != "transit" or not tr:
        return 0
    leg_from = tr.get("leg_from")
    leg_to = tr.get("leg_to")
    if not leg_from or not leg_to:
        return 0
    g = int(leg_from[0])
    origin_sys, target_sys = int(leg_from[1]), int(leg_to[1])
    if target_sys == origin_sys:
        return 0  # Innersystem-Umzug -> kein modellierter Durchflug
    depart = _iaware(_parse_iso(tr.get("depart_at")))
    arrive = _iaware(_parse_iso(tr.get("arrive_at")))
    if depart is None or arrive is None or arrive <= depart:
        return 0

    max_radius = int(icfg.get("max_radius", 30))
    lo, hi = sorted((origin_sys, target_sys))
    patrols = (await session.execute(
        select(StationedFleet).where(
            StationedFleet.galaxy == g,
            StationedFleet.intercept_enabled.is_(True),
        )
    )).scalars().all()
    now = _now()
    planned = 0
    for st in patrols:
        if not (st.ships or {}):
            continue
        owner = await session.get(Player, st.owner_id)
        if owner is not None and owner.alliance_id == station.alliance_id:
            continue  # eigene Allianz faengt die eigene Station nicht
        r = min(max_radius, int(st.intercept_radius or 0))
        if not (lo - r <= st.system <= hi + r):
            continue
        t_cross = _frac_time(depart, arrive, origin_sys, target_sys, st.system)
        if t_cross is None or t_cross <= now:
            continue
        schedule_at(
            t_cross, resolve_station_interception, str(station.id), str(st.id),
            job_id=f"station-intercept:{station.id}:{st.id}",
        )
        planned += 1
    if planned:
        log.info("Stations-Abfang geplant: station=%s -> %d Patrouille(n)", station.id, planned)
    return planned


async def _release_escort(session: AsyncSession, tr: dict) -> None:
    """Setzt die Eskort-Ueberlebenden zurueck auf den Startplaneten (stationiert). Planet weg -> verloren."""
    escort = {t: int(c) for t, c in (tr.get("escort") or {}).items() if int(c) > 0}
    pid = tr.get("escort_planet_id")
    if not escort or not pid:
        return
    try:
        planet = await session.get(Planet, uuid.UUID(pid))
    except (ValueError, TypeError):
        planet = None
    if planet is None:
        return  # Heimatplanet weg -> Eskorte geht verloren
    for typ, count in escort.items():
        row = (await session.execute(
            select(Ship).where(
                Ship.planet_id == planet.id, Ship.fleet_id.is_(None), Ship.type == typ
            )
        )).scalar_one_or_none()
        if row is None:
            session.add(Ship(planet_id=planet.id, fleet_id=None, type=typ, count=count))
        else:
            row.count += count


async def station_arrive(station_id: str) -> None:
    """Ankunfts-Job: Ziel frei -> Station materialisiert (Zone wieder aktiv), Eskorte kehrt heim.
    Ziel belegt -> Rueckkehr zum Ausgangsort (erneute Reisezeit). Ausgangsort dann auch belegt ->
    die Station findet keinen Landeplatz und geht verloren."""
    from app.fleet.service import compute_distance

    cfg = _scfg()
    rcfg = cfg.get("relocate", {})
    async with session_scope() as session:
        try:
            station = await session.get(AllianceStation, uuid.UUID(station_id))
        except (ValueError, TypeError):
            return
        if station is None or station.status != "transit":
            return  # unterwegs zerstoert / schon angekommen
        tr = dict(station.transit or {})
        dest = tr.get("leg_to") or _coords(station)
        g, sy, ps = int(dest[0]), int(dest[1]), int(dest[2])
        returning = bool(tr.get("returning"))
        blocker = await _slot_blocker(session, g, sy, ps)

        if blocker is None:
            # Materialisieren: Anker setzen, Zone wieder aktiv, Eskorte heim.
            station.galaxy, station.system, station.position = g, sy, ps
            station.status = "active"
            await _release_escort(session, tr)
            station.transit = {}
            await session.commit()
            schedule_upkeep(station.id, int(cfg.get("tick_interval_seconds", 3600)))
            await _notify_alliance(
                session, station.alliance_id,
                subject=f"Station angekommen ({g}:{sy}:{ps})",
                body=("Die Allianz-Station hat ihren neuen Standort erreicht und verankert sich — "
                      "die Einflusszone ist wieder aktiv." if not returning else
                      "Das Ziel war belegt — die Station ist zum Ausgangsort zurückgekehrt und wieder aktiv."),
            )
            await session.commit()
            return

        if not returning:
            # Ziel belegt -> Kehrtwende zum Ausgangsort (erneute Reisezeit ab JETZT).
            home = tr.get("home") or dest
            dist = compute_distance((g, sy, ps), (int(home[0]), int(home[1]), int(home[2])))
            travel = max(int(rcfg.get("min_seconds", 7200)),
                         int(round(dist * float(rcfg.get("seconds_per_distance", 3)) * relocate_speed_mult(station))))
            now = _now()
            arrive = now + dt.timedelta(seconds=travel)
            tr["leg_from"] = [g, sy, ps]
            tr["leg_to"] = home
            tr["returning"] = True
            tr["depart_at"] = now.isoformat()
            tr["arrive_at"] = arrive.isoformat()
            station.transit = tr
            await session.flush()
            schedule_at(arrive, station_arrive, str(station.id), job_id=f"station-arrive:{station.id}")
            try:
                await schedule_station_interceptions(session, station)
            except Exception:  # noqa: BLE001
                log.exception("Abfang-Planung (Rueckkehr) fuer Station %s fehlgeschlagen", station.id)
            await _notify_alliance(
                session, station.alliance_id,
                subject=f"Ziel belegt — Station kehrt zurück ({int(home[0])}:{int(home[1])}:{int(home[2])})",
                body=("Der Zielslot war bei Ankunft belegt. Die Station kehrt zum Ausgangsort zurück "
                      f"(~{travel // 3600}h {travel % 3600 // 60}min) und bleibt solange verwundbar."),
            )
            await session.commit()
            return

        # Rueckkehr, aber auch der Ausgangsort ist inzwischen belegt -> kein Landeplatz, Station verloren.
        station.status = "destroyed"
        station.transit = {}
        await session.commit()
        await _notify_alliance(
            session, station.alliance_id,
            subject="Station verloren — kein Landeplatz",
            body=("Die zurückkehrende Station fand auch ihren Ausgangsort belegt und konnte nirgends "
                  "verankern. Sie ist verloren gegangen."),
        )
        await session.commit()


async def resolve_station_interception(station_id: str, patrol_id: str) -> None:
    """Abfang-Job einer reisenden Station: Stopp-Wurf, sonst Gefecht Patrouille vs. (Abwehrbatterien
    + Eskorte). Verliert die Station, ist sie ZERSTOERT; ueberlebt sie, reist sie weiter (Eskort-
    Ueberlebende bleiben, Batterien regenerieren wie bei jeder Festungs-Schlacht)."""
    import random

    from app.combat.engine import simulate_battle
    from app.combat.service import _debris
    from app.economy.service import get_research_levels
    from app.fleet.interception import catch_chance
    from app.messaging.service import create_system_transmission
    from app.platform.balance import get_balance
    from app.platform.eventbus import event_bus
    from app.platform.models import CombatReport, Player, StationedFleet, UniverseCell

    async with session_scope() as session:
        try:
            station = await session.get(AllianceStation, uuid.UUID(station_id))
        except (ValueError, TypeError):
            return
        if station is None or station.status != "transit":
            return  # angekommen / schon zerstoert
        try:
            patrol = await session.get(StationedFleet, uuid.UUID(patrol_id))
        except (ValueError, TypeError):
            return
        if patrol is None or not patrol.intercept_enabled:
            return
        owner = await session.get(Player, patrol.owner_id)
        if owner is not None and owner.alliance_id == station.alliance_id:
            return  # eigene Allianz
        patrol_ships = {t: int(c) for t, c in (patrol.ships or {}).items() if c > 0}
        if not patrol_ships:
            await session.delete(patrol)
            await session.commit()
            return

        bal = get_balance()
        icfg = bal.data["combat"].get("interception", {})
        roster = bal.data.get("combat_roster", {})
        tr = dict(station.transit or {})
        escort = {t: int(c) for t, c in (tr.get("escort") or {}).items() if c > 0}
        loc = f"{patrol.galaxy}:{patrol.system}:{patrol.position}"

        atk_name = owner.display_name if owner is not None else "Eine Patrouille"
        al = await session.get(Alliance, station.alliance_id)
        st_name = f"Station [{al.tag}]" if al is not None else "Allianz-Station"

        # -- Stopp-Wurf (Eskort-Stabilisatoren druecken die Fang-Chance) --
        interdiction_lvl = int((await get_research_levels(session, patrol.owner_id)).get("hyperspace_interdiction", 0))
        escort_stab = sum(
            n for t, n in escort.items()
            if isinstance(roster.get(t), dict) and roster[t].get("stabilizer")
        )
        chance = catch_chance(patrol_ships, icfg, interdiction_lvl, escort_stab)
        if random.random() >= chance:
            await create_system_transmission(
                session, player_id=patrol.owner_id,
                subject=f"Abfang verfehlt ({loc})",
                body=f"Die reisende {st_name} ist deiner Patrouille bei {loc} entwischt.",
                ttype="system",
            )
            await _notify_alliance(
                session, station.alliance_id,
                subject=f"Patrouille umflogen ({loc})",
                body=f"Eure reisende Station ist einer feindlichen Patrouille von {atk_name} bei {loc} entkommen.",
            )
            await session.commit()
            return

        # -- Gefecht: Patrouille = Angreifer; Station (Batterien + Eskorte) = Verteidiger (kein Fliehen) --
        atk_research = await get_research_levels(session, patrol.owner_id)
        # Transit-Malus: unterwegs (nicht verankert) feuern die Batterien nur mit transit_combat_strength
        # -> Umstationieren ist real verwundbar. Module-Tech wirkt weiter ueber station_defender().tech.
        strength = float(_scfg().get("transit_combat_strength", 1.0))
        defenses = {t: max(1, int(round(n * strength))) for t, n in station_defenses(station).items()}
        attacker = {
            "ships": patrol_ships,
            "tech": dict(atk_research),
            "attack_mult": 1.0,
            "allow_disengage": False,
        }
        defender = {
            "ships": escort,
            "defenses": defenses,
            "tech": station_defender(station)["tech"],  # inkl. Modul-Tech-Boni
            "attack_mult": 1.0,
            "allow_disengage": False,
        }
        seed = random.randrange(1, 2 ** 62)
        result = simulate_battle(attacker, defender, seed, bal.data)
        winner = result["winner"]
        atk_losses = result["attacker_losses"]
        def_losses = result["defender_losses"]

        # Patrouille aktualisieren (Ueberlebende + erbeutete Schiffe).
        patrol_survivors = dict(result["attacker_survivors"])
        for typ, n in result.get("attacker_captured", {}).items():
            if n > 0:
                patrol_survivors[typ] = patrol_survivors.get(typ, 0) + int(n)
        patrol.ships = {t: int(c) for t, c in patrol_survivors.items() if c > 0}
        if not patrol.ships:
            await session.delete(patrol)

        station_lost = winner == "attacker"
        if station_lost:
            station.status = "destroyed"
            station.transit = {}
            cancel_job(f"station-arrive:{station.id}")
        else:
            # Eskort-Ueberlebende behalten (nur die Eskort-Schiffstypen), Batterien regenerieren.
            surv = result["defender_survivors"]
            tr["escort"] = {t: int(surv.get(t, 0)) for t in escort if int(surv.get(t, 0)) > 0}
            station.transit = tr

        # Truemmer am Abfang-Ort (beide Seiten).
        debris_a = _debris(atk_losses)
        debris_d = _debris(def_losses)
        debris = {
            "metal": round(debris_a["metal"] + debris_d["metal"], 1),
            "crystal": round(debris_a["crystal"] + debris_d["crystal"], 1),
        }
        if debris["metal"] > 0 or debris["crystal"] > 0:
            cell = (await session.execute(
                select(UniverseCell).where(
                    UniverseCell.galaxy == patrol.galaxy,
                    UniverseCell.system == patrol.system,
                    UniverseCell.position == patrol.position,
                )
            )).scalar_one_or_none()
            if cell is None:
                cell = UniverseCell(
                    galaxy=patrol.galaxy, system=patrol.system,
                    position=patrol.position, occupant_type="debris",
                )
                session.add(cell)
            field = dict(cell.debris_field or {})
            field["metal"] = round(field.get("metal", 0) + debris["metal"], 1)
            field["crystal"] = round(field.get("crystal", 0) + debris["crystal"], 1)
            cell.debris_field = field

        # Combat-Report (Angreifer = Patrouille, Verteidiger = Station-Allianz).
        outcome_json = dict(result)
        outcome_json["interception"] = True
        outcome_json["attacker_kind"] = "patrol"
        outcome_json["attacker_name"] = atk_name
        outcome_json["defender_kind"] = "station"
        outcome_json["defender_name"] = st_name
        outcome_json["station_lost"] = station_lost
        report = CombatReport(
            attacker_id=patrol.owner_id,
            defender_id=None,
            location=loc,
            seed=seed,
            outcome=outcome_json,
            loot={},
            debris=debris,
        )
        session.add(report)
        await session.flush()
        report_id = str(report.id)

        await create_system_transmission(
            session, player_id=patrol.owner_id,
            subject=(f"💥 Reisende Station zerstört ({loc})" if station_lost
                     else f"⚔ Reisende Station gestellt ({loc})"),
            body=(f"Deine Patrouille bei {loc} hat die reisende {st_name} abgefangen. "
                  + ("Sie wurde vernichtet!" if station_lost else "Sie hat sich durchgeschlagen und reist weiter.")),
            ttype="combat_report",
            decision_payload={"report_id": report_id, "role": "attacker", "winner": winner, "location": loc},
        )
        await _notify_alliance(
            session, station.alliance_id,
            subject=(f"💥 Station unterwegs zerstört ({loc})" if station_lost
                     else f"⚔ Station abgefangen — durchgebrochen ({loc})"),
            body=(f"Die reisende Station wurde von einer Patrouille von {atk_name} bei {loc} gestellt. "
                  + ("Sie ist VERLOREN." if station_lost
                     else "Sie hat das Gefecht überstanden und reist weiter.")),
        )
        await event_bus.publish_ws(patrol.owner_id, {
            "type": "combat_report", "report_id": report_id,
            "summary": {"location": loc, "winner": winner, "interception": True},
        })
        log.info("Stations-Abfang @ %s: winner=%s station_lost=%s", loc, winner, station_lost)
        await session.commit()


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
        if station.status == "transit":
            # Waehrend des Umstationierens kein Unterhalt/Regen und KEIN Status-Wechsel
            # (sonst wuerde ein leerer Tank 'transit' faelschlich auf 'inactive' setzen).
            schedule_upkeep(station_id, interval)
            return
        new_fuel = float(station.fuel or 0) - upkeep
        if new_fuel <= 0:
            station.fuel = 0.0
            station.status = "inactive"
        else:
            station.fuel = round(new_fuel, 2)
            station.status = "active"
        # hp-Regen zwischen Belagerungswellen: nur wenn seit dem letzten Treffer Ruhe herrscht.
        max_hp = station_max_hp(station)  # inkl. hull_reinforcement-Module
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
