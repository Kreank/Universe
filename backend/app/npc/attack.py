"""Eingehende NPC-Angriffe auf Spieler (Doku 08).

Aggressive NPCs entsenden einen Teil ihrer Garnison gegen ungeschützte Spieler-Planeten.
Bewusst ISOLIERT vom Spieler-Flotten-System: NPCs besitzen keine ``Fleet``-Zeilen, sondern
einen Eintrag in ``npc_attacks`` (im Anflug). Bei Ankunft löst ``resolve_npc_attack`` den
Kampf auf — der Spieler ist Verteidiger (stationierte Schiffe + Verteidigung + Forschung).

Verlauf:
1. ``maybe_launch_attack`` (aus dem NPC-Tick): Ziel wählen, Teilflotte abziehen, npc_attacks
   anlegen, Ankunfts-Job planen, Spieler WARNEN.
2. ``resolve_npc_attack`` (Scheduler-Job): Kampf simulieren, Spieler-Verluste/Beute/Trümmer
   anwenden, NPC-Überlebende heimkehren lassen, Kampfbericht + Benachrichtigung.

Determinismus der Auswahl (Ziel/Commit) ist regelbasiert; nur der Kampf-Seed ist zufällig.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.combat.engine import simulate_battle
from app.economy.service import RESOURCE_KEYS, get_research_levels, refresh_resources
from app.fleet.service import compute_distance, flight_seconds, slowest_ship_speed
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import (
    CombatReport,
    Defense,
    NpcAttack,
    NpcEmpire,
    Planet,
    Player,
    Resource,
    Ship,
    UniverseCell,
)
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.npc.attack")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=dt.timezone.utc)


# -- Reine Helfer (testbar) ---------------------------------------------------

def fleet_power(fleet: dict, ship_catalog: dict) -> float:
    """Summe Angriff*Anzahl über eine Flotte (grober Stärke-Proxy)."""
    total = 0.0
    for typ, count in (fleet or {}).items():
        cfg = ship_catalog.get(typ)
        if cfg:
            total += cfg.get("attack", 0) * count
    return total


def select_commit_fleet(garrison: dict, fraction: float) -> dict[str, int]:
    """Wählt die zu entsendende Teilflotte: floor(count*fraction) je Typ (>0)."""
    commit: dict[str, int] = {}
    for typ, count in (garrison or {}).items():
        n = int(math.floor(int(count) * fraction))
        if n > 0:
            commit[typ] = n
    return commit


def can_attack(
    profile_name: str, cfg: dict, fleet_power_value: float, seconds_since_last: float | None
) -> bool:
    """Reine Entscheidung, ob ein NPC in diesem Tick angreifen darf."""
    if not cfg or profile_name not in cfg.get("enabled_profiles", []):
        return False
    if fleet_power_value < float(cfg.get("min_fleet_power", 0)):
        return False
    cooldown = float(cfg.get("cooldown_seconds", 0))
    if seconds_since_last is not None and seconds_since_last < cooldown:
        return False
    return True


def _merge_fleet(base: dict, add: dict) -> dict[str, int]:
    """Liefert ein NEUES dict base+add (nur positive Beträge)."""
    out = dict(base or {})
    for typ, count in (add or {}).items():
        if count > 0:
            out[typ] = out.get(typ, 0) + int(count)
    return out


# -- Zielsuche ----------------------------------------------------------------

async def _find_attack_target(session: AsyncSession, npc: NpcEmpire, cfg: dict) -> Planet | None:
    """Nächster ungeschützter Spieler-Planet in der eigenen Galaxie (innerhalb Reichweite)."""
    max_sys = int(cfg.get("target_max_systems", 20))
    now = _now()
    rows = (await session.execute(
        select(Planet, Player)
        .join(Player, Planet.player_id == Player.id)
        .where(Player.is_protected.is_(False), Planet.galaxy == npc.galaxy)
    )).all()
    best: Planet | None = None
    best_key: tuple | None = None
    for planet, player in rows:
        vac = _aware(player.vacation_until)
        if vac is not None and vac > now:
            continue  # Urlaubsmodus -> nicht angreifbar
        dsys = abs(planet.system - npc.system)
        if dsys > max_sys:
            continue
        key = (dsys, planet.system, planet.position)
        if best is None or key < best_key:
            best, best_key = planet, key
    return best


# -- Launch (aus dem NPC-Tick) -----------------------------------------------

async def maybe_launch_attack(session: AsyncSession, npc: NpcEmpire, cfg: dict) -> bool:
    """Versucht, einen Angriff zu starten. True, wenn eine Flotte entsandt wurde."""
    bal = get_balance()
    ships = bal.ships
    now = _now()

    last = _aware(npc.last_attack_at)
    secs_since = None if last is None else (now - last).total_seconds()
    if not can_attack(npc.behavior_profile, cfg, fleet_power(npc.fleet or {}, ships), secs_since):
        return False

    target = await _find_attack_target(session, npc, cfg)
    if target is None:
        return False

    commit = select_commit_fleet(npc.fleet or {}, float(cfg.get("commit_fraction", 0.6)))
    if not commit or fleet_power(commit, ships) <= 0:
        return False

    # Teilflotte aus der Garnison abziehen (neues dict).
    garrison = dict(npc.fleet or {})
    for typ, count in commit.items():
        garrison[typ] = garrison.get(typ, 0) - count
        if garrison[typ] <= 0:
            garrison.pop(typ, None)
    npc.fleet = garrison

    distance = compute_distance((npc.galaxy, npc.system, npc.position),
                               (target.galaxy, target.system, target.position))
    secs = max(flight_seconds(distance, slowest_ship_speed(commit), 100),
               float(cfg.get("min_warning_seconds", 600)))
    arrive = now + dt.timedelta(seconds=secs)

    atk = NpcAttack(
        npc_id=npc.id,
        target_player_id=target.player_id,
        target_planet_id=target.id,
        target_galaxy=target.galaxy, target_system=target.system, target_position=target.position,
        fleet=commit, status="incoming", arrive_at=arrive,
    )
    session.add(atk)
    await session.flush()
    npc.last_attack_at = now

    schedule_at(arrive, resolve_npc_attack, str(atk.id), job_id=f"npc-attack:{atk.id}")
    await create_system_transmission(
        session,
        player_id=target.player_id,
        subject="⚠ Feindflotte im Anflug",
        body=(f"Eine feindliche Flotte ({npc.name}) nähert sich {target.galaxy}:{target.system}:"
              f"{target.position}. Voraussichtliches Eintreffen in ca. {int(secs // 60)} Minuten."),
        ttype="system",
    )
    log.info("NPC %s greift %s an -> %d:%d:%d (ETA %ds)",
             npc.name, target.player_id, target.galaxy, target.system, target.position, int(secs))
    return True


# -- Resolve (Scheduler-Job bei Ankunft) -------------------------------------

async def resolve_npc_attack(attack_id_str: str) -> None:
    """Löst einen eingetroffenen NPC-Angriff auf (Spieler = Verteidiger)."""
    from app.combat.service import _cargo_capacity, _compute_loot, _debris

    bal = get_balance()
    notify: dict | None = None  # (player_id, report_id, summary) fuer WS nach dem Commit

    async with session_scope() as session:
        atk = await session.get(NpcAttack, uuid.UUID(attack_id_str))
        if atk is None or atk.status != "incoming":
            return
        atk.status = "resolved"
        npc = await session.get(NpcEmpire, atk.npc_id)
        planet = await session.get(Planet, atk.target_planet_id)
        player = await session.get(Player, atk.target_player_id)
        commit = dict(atk.fleet or {})

        # Ziel verschwunden -> Flotte kehrt zurueck.
        if planet is None or player is None:
            if npc is not None:
                npc.fleet = _merge_fleet(npc.fleet or {}, commit)
            await session.commit()
            return

        loc = f"{planet.galaxy}:{planet.system}:{planet.position}"

        # Neulingsschutz/Urlaub -> Angriff dreht ab, Flotte kehrt zurueck.
        vac = _aware(player.vacation_until)
        if player.is_protected or (vac is not None and vac > _now()):
            if npc is not None:
                npc.fleet = _merge_fleet(npc.fleet or {}, commit)
            await create_system_transmission(
                session, player_id=player.id,
                subject="Feindflotte abgedreht",
                body=f"Eine Feindflotte erreichte {loc}, drehte aber wegen deines Schutzes ab.",
                ttype="system",
            )
            await session.commit()
            return

        # -- Verteidiger aufbauen (stationierte Schiffe + Verteidigung + Forschung) --
        ship_rows = (await session.execute(
            select(Ship).where(Ship.planet_id == planet.id, Ship.fleet_id.is_(None))
        )).scalars().all()
        def_ships = {r.type: r.count for r in ship_rows if r.count > 0}
        def_rows = (await session.execute(
            select(Defense).where(Defense.planet_id == planet.id)
        )).scalars().all()
        def_defenses = {r.type: r.count for r in def_rows if r.count > 0}
        research = await get_research_levels(session, player.id)
        def_tech = {k: research.get(k, 0) for k in ("weapons_tech", "shield_tech", "armor_tech")}

        seed = random.randrange(1, 2 ** 62)
        attacker = {"ships": commit, "tech": dict(bal.npc["attack"].get("npc_tech", {})), "attack_mult": 1.0}
        defender = {"ships": def_ships, "defenses": def_defenses, "tech": def_tech, "attack_mult": 1.0}
        result = simulate_battle(attacker, defender, seed, bal.data)

        winner = result["winner"]
        npc_survivors = result["attacker_survivors"]
        npc_losses = result["attacker_losses"]
        def_survivors = result["defender_survivors"]
        def_losses = result["defender_losses"]

        # -- Spieler-Schiffsverluste anwenden --
        for row in ship_rows:
            surv = def_survivors.get(row.type, 0)
            if surv <= 0:
                await session.delete(row)
            else:
                row.count = surv

        # Entern: vom Spieler (Verteidiger) gekaperte NPC-Schiffe stationieren.
        for typ, n in result.get("defender_captured", {}).items():
            if n > 0:
                session.add(Ship(planet_id=planet.id, fleet_id=None, type=typ, count=int(n)))

        # -- Spieler-Verteidigung: Verluste + 70 % Regen --
        regen = bal.combat["defense_regen_ratio"]
        for row in def_rows:
            lost = def_losses.get(row.type, 0)
            kept = row.count - lost
            row.count = max(0, kept + math.floor(lost * regen))

        # -- Truemmer (nur Schiffe, beide Seiten) am Spieler-Ort persistieren --
        d_atk = _debris(npc_losses)
        d_def = _debris(def_losses)
        debris = {"metal": round(d_atk["metal"] + d_def["metal"], 1),
                  "crystal": round(d_atk["crystal"] + d_def["crystal"], 1)}
        if debris["metal"] > 0 or debris["crystal"] > 0:
            cell = (await session.execute(
                select(UniverseCell).where(
                    UniverseCell.galaxy == planet.galaxy,
                    UniverseCell.system == planet.system,
                    UniverseCell.position == planet.position,
                )
            )).scalar_one_or_none()
            if cell is None:
                cell = UniverseCell(galaxy=planet.galaxy, system=planet.system,
                                    position=planet.position, occupant_type="player", ref_id=planet.id)
                session.add(cell)
            field = dict(cell.debris_field or {})
            field["metal"] = round(field.get("metal", 0) + debris["metal"], 1)
            field["crystal"] = round(field.get("crystal", 0) + debris["crystal"], 1)
            cell.debris_field = field

        # -- Beute (nur bei NPC-Sieg): Spieler-Ressourcen pluendern --
        loot = {"metal": 0.0, "crystal": 0.0, "deuterium": 0.0}
        if winner == "attacker":
            res = await refresh_resources(session, planet)
            available = {k: res[k]["amount"] for k in RESOURCE_KEYS}
            loot = _compute_loot(available, _cargo_capacity(npc_survivors))
            res_rows = (await session.execute(
                select(Resource).where(Resource.planet_id == planet.id, Resource.type.in_(RESOURCE_KEYS))
            )).scalars().all()
            by_type = {r.type: r for r in res_rows}
            for key in RESOURCE_KEYS:
                if key in by_type:
                    by_type[key].amount = max(0.0, by_type[key].amount - loot[key])
            if npc is not None:
                nres = dict(npc.resources or {})
                for key in RESOURCE_KEYS:
                    nres[key] = nres.get(key, 0) + loot[key]
                npc.resources = nres

        # -- NPC-Ueberlebende (+ vom NPC gekaperte Spieler-Schiffe) kehren in die Garnison zurueck --
        if npc is not None:
            npc.fleet = _merge_fleet(_merge_fleet(npc.fleet or {}, npc_survivors),
                                     result.get("attacker_captured", {}))

        # -- Kampfbericht + Benachrichtigung --
        situation = "defense_lost" if winner == "attacker" else (
            "defense_held" if winner == "defender" else "stalemate")
        outcome_json = dict(result)
        outcome_json["situation"] = situation
        outcome_json["attacker_kind"] = "npc"
        outcome_json["npc_name"] = npc.name if npc else None
        report = CombatReport(
            attacker_id=None, defender_id=player.id, location=loc, seed=seed,
            outcome=outcome_json, loot=loot, debris=debris,
        )
        session.add(report)
        await session.flush()
        report_id = report.id

        held = winner != "attacker"
        subject = "🛡 Angriff abgewehrt" if held else "💥 Planet angegriffen!"
        if held:
            body = f"Deine Verteidigung bei {loc} hat den Angriff von {npc.name if npc else 'einer Feindflotte'} gehalten."
        else:
            body = (f"{npc.name if npc else 'Eine Feindflotte'} hat {loc} angegriffen und "
                    f"{int(loot['metal'])} Metall / {int(loot['crystal'])} Kristall / "
                    f"{int(loot['deuterium'])} Deuterium erbeutet.")
        await create_system_transmission(
            session, player_id=player.id, subject=subject, body=body, ttype="combat_report",
        )

        notify = {
            "player_id": str(player.id),
            "report_id": str(report_id),
            "summary": {"location": loc, "winner": winner, "situation": situation},
        }
        await session.commit()

    if notify is not None:
        await event_bus.publish_ws(notify["player_id"], {
            "type": "combat_report",
            "report_id": notify["report_id"],
            "summary": notify["summary"],
        })
    log.info("NPC-Angriff %s aufgeloest", attack_id_str)
