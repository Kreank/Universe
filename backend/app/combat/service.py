"""Kampf-Orchestrierung: laedt Flotte/Verteidiger, wendet Commander-Modifikatoren an,
ruft die Engine, verteilt Beute/Truemmer/Regen, persistiert den Combat-Report und
loest die Sofort-Reaktion (messaging) bzw. einen big_moment-Job aus.

Im Vertical Slice sind die Ziele NPC-Imperien (Tabelle npc_empires); PvP-Verteidiger
(Spielerplanet) werden rudimentaer unterstuetzt."""
from __future__ import annotations

import logging
import math
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.combat.engine import simulate_battle
from app.economy.service import get_research_levels
from app.messaging.service import after_combat_reaction
from app.platform.balance import get_balance
from app.platform.models import (
    CombatReport,
    Commander,
    Fleet,
    NpcEmpire,
    Ship,
    UniverseCell,
)

log = logging.getLogger("universe.combat")


async def _fleet_ships(session: AsyncSession, fleet_id: uuid.UUID) -> dict[str, int]:
    rows = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet_id)
    )).scalars().all()
    return {r.type: r.count for r in rows if r.count > 0}


def _commander_mods(commander: Commander | None, fleet_ship_types: int) -> float:
    """Berechnet den Angriffs-/Schild-Multiplikator aus Moral, Traits und Ueberdehnung.

    Ueberdehnung (Slice-Proxy): Zahl der Schiffstypen im Geschwader ueber span_capacity
    erzeugt je Ueberhang eine Koordinationsstrafe (balance: overstretch_penalty_per_excess).
    """
    bal = get_balance()
    if commander is None:
        return 1.0
    band = bal.morale_band(commander.morale)
    mod = float(band["combat_mod"])
    # Persoenlichkeits-Traits (combat_attack_mod aufsummieren).
    traits_cfg = bal.commander["personality_traits"]
    for trait in (commander.traits or []):
        mod += float(traits_cfg.get(trait, {}).get("combat_attack_mod", 0.0))
    attack_mult = max(0.0, 1.0 + mod)
    # Ueberdehnung.
    span = max(1, commander.span_capacity)
    excess = max(0, fleet_ship_types - span)
    penalty = bal.commander["span"]["overstretch_penalty_per_excess"] * excess
    overstretch_mult = max(0.0, 1.0 - penalty)
    return attack_mult * overstretch_mult


def _debris(losses: dict[str, int]) -> dict[str, float]:
    """Truemmer = 30 % (M+K) der zerstoerten SCHIFFE (Verteidigung erzeugt keine)."""
    bal = get_balance()
    ratio = bal.combat["debris_ratio"]
    metal = crystal = 0.0
    for typ, count in losses.items():
        cfg = bal.ships.get(typ)
        if cfg is None:
            continue  # Verteidigung -> kein Truemmer
        metal += cfg["cost"].get("metal", 0) * count * ratio
        crystal += cfg["cost"].get("crystal", 0) * count * ratio
    return {"metal": round(metal, 1), "crystal": round(crystal, 1)}


def _cargo_capacity(survivors: dict[str, int]) -> float:
    bal = get_balance()
    cap = 0.0
    for typ, count in survivors.items():
        cfg = bal.ships.get(typ)
        if cfg:
            cap += cfg.get("cargo", 0) * count
    return cap


def _compute_loot(npc_resources: dict, capacity: float) -> dict[str, float]:
    """Pluendert bis zu 50 % der ungeschuetzten Rohstoffe, durch Frachtraum begrenzt."""
    bal = get_balance()
    ratio = bal.combat["plunder_ratio"]
    available = {
        "metal": npc_resources.get("metal", 0) * ratio,
        "crystal": npc_resources.get("crystal", 0) * ratio,
        "deuterium": npc_resources.get("deuterium", 0) * ratio,
    }
    loot = {"metal": 0.0, "crystal": 0.0, "deuterium": 0.0}
    remaining = capacity
    for key in ("metal", "crystal", "deuterium"):
        take = min(available[key], remaining)
        loot[key] = round(max(0.0, take), 1)
        remaining -= loot[key]
        if remaining <= 0:
            break
    return loot


def _situation(winner: str, atk_initial: int, atk_lost: int) -> str:
    if winner == "attacker":
        if atk_lost == 0:
            return "crushing_victory"
        if atk_initial > 0 and atk_lost / atk_initial > 0.5:
            return "close_win"
        return "victory"
    return "defeat"


async def resolve_attack(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Berechnet den Kampf einer eintreffenden Angriffsflotte. Liefert eine kurze
    Zusammenfassung (oder None, wenn kein gueltiges Ziel)."""
    bal = get_balance()
    attacker_ships = await _fleet_ships(session, fleet.id)
    if not attacker_ships:
        return None

    commander = None
    if fleet.commander_id:
        commander = await session.get(Commander, fleet.commander_id)

    atk_research = await get_research_levels(session, fleet.player_id)
    atk_tech = {
        "weapons_tech": atk_research.get("weapons_tech", 0),
        "shield_tech": atk_research.get("shield_tech", 0),
        "armor_tech": atk_research.get("armor_tech", 0),
    }
    attack_mult = _commander_mods(commander, len(attacker_ships))

    # Schiffsklassen-spezifische Commander-Boni (Angriff/Schild je Schiffstyp, moral-skaliert).
    ship_bonuses: dict[str, dict[str, float]] = {}
    if commander is not None:
        from app.commander.bonuses import base_bonuses, resolve_ship_bonuses
        focus = (commander.persona or {}).get("focus")
        cmd_bonuses = base_bonuses(
            commander.specialization, commander.rank, commander.traits or [], focus
        )
        ship_bonuses, _speed = resolve_ship_bonuses(
            cmd_bonuses, commander.morale, list(attacker_ships.keys())
        )

    # -- Verteidiger ermitteln (NPC bevorzugt) -------------------------------
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == fleet.target_galaxy,
            UniverseCell.system == fleet.target_system,
            UniverseCell.position == fleet.target_position,
        )
    )).scalar_one_or_none()

    npc: NpcEmpire | None = None
    def_ships: dict[str, int] = {}
    def_defenses: dict[str, int] = {}
    def_tech = {"weapons_tech": 0, "shield_tech": 0, "armor_tech": 0}
    defender_player_id = None
    npc_resources: dict = {}

    if cell and cell.occupant_type == "npc" and cell.ref_id is not None:
        npc = await session.get(NpcEmpire, cell.ref_id)
    if npc is None:
        # Fallback: direkter Lookup nach Koordinaten (falls Zelle fehlt/inkonsistent).
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == fleet.target_galaxy,
                NpcEmpire.system == fleet.target_system,
                NpcEmpire.position == fleet.target_position,
            )
        )).scalar_one_or_none()

    if npc is not None:
        def_ships = dict(npc.fleet or {})
        def_defenses = dict(npc.defenses or {})
        npc_resources = dict(npc.resources or {})
    else:
        # Kein NPC -> kein Kampf (leeres Ziel). Fleet kehrt einfach zurueck.
        return None

    seed = random.randrange(1, 2 ** 62)
    attacker = {
        "ships": attacker_ships,
        "tech": atk_tech,
        "attack_mult": attack_mult,
        "ship_bonuses": ship_bonuses,
    }
    defender = {"ships": def_ships, "defenses": def_defenses, "tech": def_tech, "attack_mult": 1.0}

    result = simulate_battle(attacker, defender, seed, bal.data)

    # -- Ergebnisse anwenden -------------------------------------------------
    atk_survivors = result["attacker_survivors"]
    atk_losses = result["attacker_losses"]
    def_losses = result["defender_losses"]
    winner = result["winner"]
    atk_initial = sum(result["attacker_initial"].values())
    atk_lost = sum(atk_losses.values())
    situation = _situation(winner, atk_initial, atk_lost)

    # Ueberlebende Angreifer-Schiffe in der Flotte aktualisieren.
    fleet_ship_rows = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet.id)
    )).scalars().all()
    for row in fleet_ship_rows:
        surv = atk_survivors.get(row.type, 0)
        if surv <= 0:
            await session.delete(row)
        else:
            row.count = surv

    # Truemmer (beide Seiten, nur Schiffe).
    debris = _debris(atk_losses)
    def_debris = _debris(def_losses)
    debris = {
        "metal": round(debris["metal"] + def_debris["metal"], 1),
        "crystal": round(debris["crystal"] + def_debris["crystal"], 1),
    }

    # Beute (nur bei Sieg des Angreifers).
    loot = {"metal": 0.0, "crystal": 0.0, "deuterium": 0.0}
    if winner == "attacker":
        capacity = _cargo_capacity(atk_survivors)
        loot = _compute_loot(npc_resources, capacity)
        # Fracht der Flotte fuer die Rueckreise erhoehen.
        cargo = dict(fleet.cargo or {})
        for key in ("metal", "crystal", "deuterium"):
            cargo[key] = cargo.get(key, 0) + loot[key]
            npc_resources[key] = max(0.0, npc_resources.get(key, 0) - loot[key])
        fleet.cargo = cargo

    # NPC aktualisieren: Schiffe = Ueberlebende, Verteidigung mit 70 % Regen.
    if npc is not None:
        regen = bal.combat["defense_regen_ratio"]
        new_def: dict[str, int] = {}
        for typ, init in (npc.defenses or {}).items():
            lost = def_losses.get(typ, 0)
            kept = init - lost
            regenerated = math.floor(lost * regen)
            new_def[typ] = max(0, kept + regenerated)
        npc.defenses = new_def
        npc.fleet = {t: c for t, c in result["defender_survivors"].items() if t in (npc.fleet or {})}
        npc.resources = npc_resources

    # -- Commander-Folgen ----------------------------------------------------
    commander_outcome = await _apply_commander(session, commander, situation, atk_survivors, loot, atk_research)

    # -- Combat-Report persistieren -----------------------------------------
    location = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
    outcome_json = dict(result)
    outcome_json["situation"] = situation
    outcome_json["commander_outcome"] = commander_outcome
    report = CombatReport(
        attacker_id=fleet.player_id,
        defender_id=defender_player_id,
        location=location,
        seed=seed,
        outcome=outcome_json,
        loot=loot,
        debris=debris,
    )
    session.add(report)
    await session.flush()
    report_id = report.id

    enemy_name = npc.name if npc else location
    summary = {
        "report_id": str(report_id),
        "location": location,
        "winner": winner,
        "situation": situation,
    }

    # -- Sofort-Reaktion (messaging) + ggf. big_moment -----------------------
    decisive = situation in ("crushing_victory", "close_win", "defeat") or (
        commander_outcome.get("status") in ("dead", "captured", "wounded")
    )
    await after_combat_reaction(
        session,
        player_id=fleet.player_id,
        commander=commander,
        situation=situation,
        context={
            "enemy": enemy_name,
            "planet": location,
            "loot": loot,
            "outcome": "win" if winner == "attacker" else "loss",
        },
        decisive=decisive,
    )

    # WS: Combat-Report ankuendigen.
    from app.platform.eventbus import event_bus
    await event_bus.publish_ws(fleet.player_id, {
        "type": "combat_report",
        "report_id": str(report_id),
        "summary": summary,
    })

    log.info("Kampf @ %s: winner=%s situation=%s", location, winner, situation)
    return summary


async def _apply_commander(
    session: AsyncSession,
    commander: Commander | None,
    situation: str,
    atk_survivors: dict[str, int],
    loot: dict[str, float],
    research: dict[str, int],
) -> dict:
    """Moral-Delta, XP, Rangaufstieg und Permadeath/Evakuierung."""
    if commander is None:
        return {"status": None}

    bal = get_balance()
    deltas = bal.commander["morale"]["deltas"]
    xp_cfg = bal.commander["xp"]

    morale_delta = 0
    xp_gain = 0
    if situation in ("victory", "crushing_victory", "close_win"):
        morale_delta += deltas["victory"]
        if situation == "crushing_victory":
            morale_delta += deltas["crushing_victory"]
        xp_gain += xp_cfg["victory"] + xp_cfg["mission_success"]
        if any(v > 0 for v in loot.values()):
            morale_delta += deltas["loot_gained"]
    else:  # defeat
        morale_delta += deltas["defeat"]

    commander.morale = max(0, min(100, commander.morale + morale_delta))
    commander.xp += xp_gain
    # Rangaufstieg nach XP-Schwellen.
    new_rank = bal.rank_for_xp(commander.xp)
    commander.rank = new_rank["key"]
    commander.span_capacity = max(commander.span_capacity, new_rank["span_contrib"])

    status = "active"
    # Permadeath/Evakuierung nur, wenn die Flotte des Commanders vernichtet ist.
    fleet_wiped = sum(atk_survivors.values()) == 0
    if fleet_wiped:
        evac = bal.combat["evacuation"]
        chance = evac["base_chance"]
        chance += evac["rank_bonus"].get(commander.rank, 0.0)
        chance += evac["logistics_tech_bonus_per_level"] * research.get("logistics_tech", 0)
        # Ohne Ueberlebende kein survivor-Bonus (Doku 04 §8.2).
        if random.random() < chance:
            status = "wounded"
            commander.status = "wounded"
            commander.morale = max(0, commander.morale - abs(deltas["defeat"]) // 2)
        else:
            # Neulingsschutz (GDD §8): unter Schutz kein Permadeath -> nur verwundet.
            from app.platform.models import Player
            player = await session.get(Player, commander.player_id)
            if player is not None and player.is_protected:
                status = "wounded"
                commander.status = "wounded"
            else:
                status = "dead"
                commander.status = "dead"
    return {
        "status": commander.status,
        "morale": commander.morale,
        "morale_delta": morale_delta,
        "xp": commander.xp,
        "rank": commander.rank,
    }
