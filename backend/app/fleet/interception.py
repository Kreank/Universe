"""Abfangen im Flug (A — strategische Ebene, dedizierte Patrouille + Interdiktor).

Eine ``StationedFleet`` mit ``intercept_enabled`` faengt feindliche Flotten ab, deren
**galaxie-interne** Route ihr System (+/- ``intercept_radius``) kreuzt. Das Flugmodell ist
pro Galaxie linear in der System-Differenz (fleet.service.compute_distance) — der Abfang-
Zeitpunkt liegt also anteilig entlang der Flugzeit am Kreuzungssystem.

- **MIT Interdiktor** (combat_roster.interdictor) in der Patrouille -> sicherer Stopp (Chance 1.0)
  und die abgefangene Flotte kann nicht aus der Schlacht fliehen (Interdiktion).
- **OHNE Interdiktor** -> Chance = base_chance + chance_per_interceptor je Abfangjaeger,
  gedeckelt (balance.combat.interception) — so offen wie moeglich, kein harter Filter.

Die Patrouille ist Aggressor (Angreifer-Seite, kann nicht fliehen); die abgefangene Flotte
ist Verteidiger und darf fliehen. Ueberlebt die Flotte das Gefecht, fliegt sie weiter zu
ihrem urspruenglichen Ziel (die Ankunft ist bereits geplant). Inter-Galaxie-Fluege haben
keinen modellierten Pfad und sind nur am Ziel fangbar (stationing.gather_interception_defenders).
"""
from __future__ import annotations

import datetime as dt
import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import Fleet, Ship, StationedFleet

log = logging.getLogger("universe.interception")

UTC = dt.timezone.utc


def _now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


def _has_interdictor(ships: dict, roster: dict) -> bool:
    return any(bool(roster.get(t, {}).get("interdictor")) for t in ships)


def catch_chance(station_ships: dict, roster: dict, icfg: dict) -> float:
    """Abfang-Chance einer Patrouille. Interdiktor -> 1.0; sonst base + je Abfangjaeger, gedeckelt."""
    if _has_interdictor(station_ships, roster):
        return 1.0
    base = float(icfg.get("base_chance", 0.4))
    per = float(icfg.get("chance_per_interceptor", 0.06))
    cap = float(icfg.get("chance_cap", 0.95))
    interceptors = int(station_ships.get("interceptor", 0))
    return max(0.0, min(cap, base + per * interceptors))


def _frac_time(depart: dt.datetime, arrive: dt.datetime, origin_sys: int, target_sys: int,
               station_sys: int) -> dt.datetime | None:
    """Zeitpunkt, zu dem die Flotte das Stations-System (auf die Strecke geklemmt) kreuzt."""
    if target_sys == origin_sys:
        return None
    lo, hi = sorted((origin_sys, target_sys))
    eff = max(lo, min(hi, station_sys))
    frac = (eff - origin_sys) / (target_sys - origin_sys)
    frac = max(0.05, min(0.95, frac))  # nie exakt an Start/Ziel (die deckt das Ankunfts-Abfangen ab)
    return depart + dt.timedelta(seconds=frac * (arrive - depart).total_seconds())


async def _origin_system(session: AsyncSession, fleet: Fleet) -> int | None:
    from app.platform.models import Planet
    if fleet.origin_planet_id is None:
        return None
    p = await session.get(Planet, fleet.origin_planet_id)
    return p.system if p is not None else None


async def schedule_interceptions_for_fleet(session: AsyncSession, fleet: Fleet) -> int:
    """Beim Flottenstart: feindliche Abfang-Patrouillen auf der Route finden und je einen
    Abfang-Job planen. Galaxie-intern. Liefert die Zahl geplanter Abfaenge. Defensiv —
    Fehler hier duerfen den Flottenstart nicht blockieren (Aufrufer kapselt mit try/except)."""
    from app.platform.scheduler import schedule_at

    icfg = get_balance().data["combat"].get("interception", {})
    if not icfg.get("enabled", False) or fleet.status != "flying":
        return 0
    origin_sys = await _origin_system(session, fleet)
    if origin_sys is None:
        return 0
    target_sys = fleet.target_system
    if target_sys == origin_sys:
        return 0  # gleiches System -> kein Durchflug

    depart = _aware(fleet.depart_at)
    arrive = _aware(fleet.arrive_at)
    if depart is None or arrive is None or arrive <= depart:
        return 0

    max_radius = int(icfg.get("max_radius", 30))
    lo, hi = sorted((origin_sys, target_sys))
    stations = (await session.execute(
        select(StationedFleet).where(
            StationedFleet.galaxy == fleet.target_galaxy,
            StationedFleet.owner_id != fleet.player_id,
            StationedFleet.intercept_enabled.is_(True),
        )
    )).scalars().all()

    now = _now()
    planned = 0
    for st in stations:
        if not (st.ships or {}):
            continue
        r = min(max_radius, int(st.intercept_radius or 0))
        if not (lo - r <= st.system <= hi + r):
            continue
        t_cross = _frac_time(depart, arrive, origin_sys, target_sys, st.system)
        if t_cross is None or t_cross <= now:
            continue
        schedule_at(
            t_cross, resolve_interception, str(fleet.id), str(st.id),
            job_id=f"intercept:{fleet.id}:{st.id}",
        )
        planned += 1
    if planned:
        log.info("Abfang geplant: fleet=%s -> %d Patrouille(n)", fleet.id, planned)
    return planned


async def scan_inflight_for_station(session: AsyncSession, station: StationedFleet) -> int:
    """Beim Aktivieren des Abfang-Modus: bereits fliegende feindliche Flotten erfassen, deren
    Route diese Patrouille kreuzt, und Abfang-Jobs planen. Liefert die Zahl geplanter Abfaenge."""
    from app.platform.models import Planet
    from app.platform.scheduler import schedule_at

    icfg = get_balance().data["combat"].get("interception", {})
    if not icfg.get("enabled", False) or not station.intercept_enabled or not (station.ships or {}):
        return 0
    fleets = (await session.execute(
        select(Fleet).where(
            Fleet.target_galaxy == station.galaxy,
            Fleet.player_id != station.owner_id,
            Fleet.status == "flying",
        )
    )).scalars().all()
    now = _now()
    r = int(station.intercept_radius or 0)
    planned = 0
    for f in fleets:
        if f.origin_planet_id is None:
            continue
        p = await session.get(Planet, f.origin_planet_id)
        if p is None:
            continue
        origin_sys = p.system
        target_sys = f.target_system
        if target_sys == origin_sys:
            continue
        lo, hi = sorted((origin_sys, target_sys))
        if not (lo - r <= station.system <= hi + r):
            continue
        depart = _aware(f.depart_at)
        arrive = _aware(f.arrive_at)
        if depart is None or arrive is None or arrive <= depart:
            continue
        t_cross = _frac_time(depart, arrive, origin_sys, target_sys, station.system)
        if t_cross is None or t_cross <= now:
            continue
        schedule_at(
            t_cross, resolve_interception, str(f.id), str(station.id),
            job_id=f"intercept:{f.id}:{station.id}",
        )
        planned += 1
    return planned


async def resolve_interception(fleet_id: str, station_id: str) -> None:
    """Abfang-Job: prueft Stopp-Chance, fuehrt ggf. die Schlacht Patrouille-vs-Flotte und
    wendet das Ergebnis an. Ueberlebt die Flotte, fliegt sie weiter (Ankunft bleibt geplant)."""
    from app.combat.engine import simulate_battle
    from app.combat.service import _apply_commander, _debris
    from app.economy.service import get_research_levels
    from app.messaging.service import create_system_transmission
    from app.platform.db import session_scope
    from app.platform.eventbus import event_bus
    from app.platform.models import CombatReport, Commander, Player, UniverseCell

    async with session_scope() as session:
        try:
            fleet = await session.get(Fleet, uuid.UUID(fleet_id))
        except (ValueError, TypeError):
            return
        if fleet is None or fleet.status != "flying":
            return  # angekommen, zurueckgerufen oder schon abgefangen/vernichtet
        try:
            station = await session.get(StationedFleet, uuid.UUID(station_id))
        except (ValueError, TypeError):
            return
        if station is None or not station.intercept_enabled:
            return  # Patrouille weg / Abfang aus -> Flotte fliegt durch
        if station.owner_id == fleet.player_id:
            return
        station_ships = {t: int(c) for t, c in (station.ships or {}).items() if c > 0}
        if not station_ships:
            await session.delete(station)
            return
        fleet_rows = (await session.execute(
            select(Ship).where(Ship.fleet_id == fleet.id)
        )).scalars().all()
        fleet_ships = {r.type: r.count for r in fleet_rows if r.count > 0}
        if not fleet_ships:
            return

        bal = get_balance()
        icfg = bal.data["combat"].get("interception", {})
        roster = bal.data.get("combat_roster", {})
        loc = f"{station.galaxy}:{station.system}:{station.position}"

        attacker_player = await session.get(Player, station.owner_id)
        defender_player = await session.get(Player, fleet.player_id)
        atk_name = attacker_player.display_name if attacker_player else "Eine Patrouille"
        def_name = defender_player.display_name if defender_player else "Eine Flotte"

        # -- Stopp-Wurf -------------------------------------------------------
        # Hyperraum-Interdiktion-Forschung des Patrouillen-Besitzers hebt die Fang-Chance.
        owner_research = await get_research_levels(session, station.owner_id)
        interdiction_lvl = int(owner_research.get("hyperspace_interdiction", 0))
        chance = catch_chance(station_ships, roster, icfg)
        if chance < 1.0 and interdiction_lvl > 0:
            chance = min(
                float(icfg.get("chance_cap", 0.95)),
                chance + float(icfg.get("chance_per_interdiction_level", 0.0)) * interdiction_lvl,
            )
        if random.random() >= chance:
            # Durchgerutscht: beide Seiten informieren, Flotte fliegt weiter.
            await create_system_transmission(
                session, player_id=station.owner_id,
                subject=f"Abfang verfehlt ({loc})",
                body=f"Eine durchreisende Flotte von {def_name} ist deiner Patrouille bei {loc} entwischt.",
                ttype="system",
            )
            await create_system_transmission(
                session, player_id=fleet.player_id,
                subject=f"Patrouille umflogen ({loc})",
                body=f"Deine Flotte ist einer feindlichen Patrouille von {atk_name} bei {loc} entkommen.",
                ttype="system",
            )
            log.info("Abfang verfehlt: fleet=%s station=%s chance=%.2f", fleet_id, station_id, chance)
            return

        # -- Schlacht: Patrouille = Angreifer (haelt fest), Flotte = Verteidiger (darf fliehen) --
        atk_research = await get_research_levels(session, station.owner_id)
        def_research = await get_research_levels(session, fleet.player_id)
        tech_keys = ("weapons_tech", "shield_tech", "armor_tech")

        # Commander-Boni der abgefangenen Flotte (defensiv).
        commander = await session.get(Commander, fleet.commander_id) if fleet.commander_id else None
        def_attack_mult = 1.0
        ship_bonuses: dict[str, dict[str, float]] = {}
        if commander is not None:
            from app.combat.service import _commander_mods
            from app.commander.bonuses import base_bonuses, resolve_ship_bonuses
            def_attack_mult = _commander_mods(commander, len(fleet_ships))
            focus = (commander.persona or {}).get("focus")
            cmd_bonuses = base_bonuses(
                commander.specialization, commander.rank, commander.traits or [], focus,
                commander.grade or "C",
            )
            ship_bonuses, _spd = resolve_ship_bonuses(cmd_bonuses, commander.morale, list(fleet_ships.keys()))

        seed = random.randrange(1, 2 ** 62)
        attacker = {
            "ships": station_ships,
            "tech": dict(atk_research),
            "attack_mult": 1.0,
            "allow_disengage": False,
        }
        defender = {
            "ships": fleet_ships,
            "defenses": {},
            "tech": dict(def_research),
            "attack_mult": def_attack_mult,
            "ship_bonuses": ship_bonuses,
            "allow_disengage": True,
        }
        result = simulate_battle(attacker, defender, seed, bal.data)

        patrol_survivors = dict(result["attacker_survivors"])
        for typ, n in result.get("attacker_captured", {}).items():
            if n > 0:
                patrol_survivors[typ] = patrol_survivors.get(typ, 0) + int(n)
        fleet_survivors = dict(result["defender_survivors"])
        atk_losses = result["attacker_losses"]
        def_losses = result["defender_losses"]
        winner = result["winner"]
        fleet_wiped = sum(fleet_survivors.values()) == 0

        # -- Patrouille aktualisieren --
        station.ships = {t: int(c) for t, c in patrol_survivors.items() if c > 0}
        if not station.ships:
            await session.delete(station)

        # -- Flotte aktualisieren --
        for row in fleet_rows:
            surv = fleet_survivors.get(row.type, 0)
            if surv <= 0:
                await session.delete(row)
            else:
                row.count = surv
        for typ, n in result.get("defender_captured", {}).items():
            if n > 0:
                session.add(Ship(planet_id=None, fleet_id=fleet.id, type=typ, count=int(n)))
        if fleet_wiped:
            fleet.status = "done"
            fleet.cargo = {}

        # -- Truemmer am Abfang-Ort (beide Seiten, nur Schiffe) --
        debris_a = _debris(atk_losses)
        debris_d = _debris(def_losses)
        debris = {
            "metal": round(debris_a["metal"] + debris_d["metal"], 1),
            "crystal": round(debris_a["crystal"] + debris_d["crystal"], 1),
        }
        if debris["metal"] > 0 or debris["crystal"] > 0:
            cell = (await session.execute(
                select(UniverseCell).where(
                    UniverseCell.galaxy == station.galaxy,
                    UniverseCell.system == station.system,
                    UniverseCell.position == station.position,
                )
            )).scalar_one_or_none()
            if cell is None:
                cell = UniverseCell(
                    galaxy=station.galaxy, system=station.system,
                    position=station.position, occupant_type="debris",
                )
                session.add(cell)
            field = dict(cell.debris_field or {})
            field["metal"] = round(field.get("metal", 0) + debris["metal"], 1)
            field["crystal"] = round(field.get("crystal", 0) + debris["crystal"], 1)
            cell.debris_field = field

        # -- Commander-Folgen (Flotten-Sicht: Sieg = Patrouille zerschlagen) --
        situation = "defeat" if winner == "attacker" else (
            "crushing_victory" if winner == "defender" and not def_losses else "victory"
        )
        commander_outcome = await _apply_commander(
            session, commander, situation, fleet_survivors, {"metal": 0, "crystal": 0, "deuterium": 0},
            def_research,
        )

        # -- Combat-Report persistieren --
        outcome_json = dict(result)
        outcome_json["situation"] = situation
        outcome_json["commander_outcome"] = commander_outcome
        outcome_json["interception"] = True
        outcome_json["attacker_kind"] = "patrol"
        outcome_json["attacker_name"] = atk_name
        outcome_json["defender_kind"] = "fleet"
        outcome_json["defender_name"] = def_name
        report = CombatReport(
            attacker_id=station.owner_id,
            defender_id=fleet.player_id,
            location=loc,
            seed=seed,
            outcome=outcome_json,
            loot={},
            debris=debris,
        )
        session.add(report)
        await session.flush()
        report_id = str(report.id)

        # -- Transmissionen + WS an beide Seiten --
        fleet_held = winner != "attacker"  # Flotte hat ueberlebt/durchgebrochen
        await create_system_transmission(
            session, player_id=fleet.player_id,
            subject=(f"💥 Flotte abgefangen ({loc})" if fleet_wiped
                     else (f"⚔ Flotte abgefangen — durchgebrochen ({loc})" if fleet_held
                           else f"⚔ Flotte abgefangen ({loc})")),
            body=(f"Die Abfang-Patrouille von {atk_name} hat deine durchreisende Flotte bei {loc} gestellt. "
                  + ("Deine Flotte wurde vernichtet." if fleet_wiped
                     else "Deine Flotte hat sich durchgeschlagen und fliegt weiter.")),
            ttype="combat_report",
            decision_payload={"report_id": report_id, "role": "defender", "winner": winner, "location": loc},
        )
        await create_system_transmission(
            session, player_id=station.owner_id,
            subject=(f"💥 Flotte abgefangen & vernichtet ({loc})" if fleet_wiped
                     else f"⚔ Flotte abgefangen ({loc})"),
            body=(f"Deine Patrouille bei {loc} hat eine durchreisende Flotte von {def_name} abgefangen. "
                  + ("Sie wurde vernichtet." if fleet_wiped
                     else "Sie hat sich durchgeschlagen." if fleet_held
                     else "Das Gefecht hielt sie auf.")),
            ttype="combat_report",
            decision_payload={"report_id": report_id, "role": "attacker", "winner": winner, "location": loc},
        )
        for pid in (fleet.player_id, station.owner_id):
            await event_bus.publish_ws(pid, {
                "type": "combat_report", "report_id": report_id,
                "summary": {"location": loc, "winner": winner, "interception": True},
            })
        log.info("Abfang @ %s: winner=%s fleet_wiped=%s", loc, winner, fleet_wiped)
