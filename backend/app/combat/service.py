"""Kampf-Orchestrierung: laedt Flotte/Verteidiger, wendet Commander-Modifikatoren an,
ruft die Engine, verteilt Beute/Truemmer/Regen, persistiert den Combat-Report und
loest die Sofort-Reaktion (messaging) bzw. einen big_moment-Job aus.

Im Vertical Slice sind die Ziele NPC-Imperien (Tabelle npc_empires); PvP-Verteidiger
(Spielerplanet) werden rudimentaer unterstuetzt."""
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
from app.messaging.service import after_combat_reaction, create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import (
    CombatReport,
    Commander,
    Defense,
    Fleet,
    NpcEmpire,
    Planet,
    Player,
    Resource,
    Ship,
    UniverseCell,
)


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

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

    # -- Meuterei: ein illoyaler Kommandeur kann den Angriff verweigern --
    if commander is not None:
        sat = bal.commander.get("satisfaction", {})
        mt = float(sat.get("mutiny_threshold", 30))
        if commander.loyalty < mt:
            chance = (mt - commander.loyalty) / mt
            for tr in (commander.traits or []):
                chance *= float(sat.get("mutiny_trait_mult", {}).get(tr, 1.0))
            if random.random() < max(0.0, min(1.0, chance)):
                commander.morale = max(0, commander.morale - 10)
                commander.loyalty = max(0, commander.loyalty - 5)
                loc = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
                await create_system_transmission(
                    session, player_id=fleet.player_id,
                    subject=f"⚠ Meuterei — Angriff verweigert ({loc})",
                    body=(f"Kommandeur {commander.name} verweigert aus Unmut den Befehl. Die Flotte dreht "
                          f"vor {loc} ab und kehrt unverrichteter Dinge heim. Kümmere dich um seine Treue."),
                    ttype="system",
                )
                log.info("Meuterei: commander=%s loyalty=%d verweigert Angriff", commander.id, commander.loyalty)
                return {"mutiny": True, "location": loc}

    atk_research = await get_research_levels(session, fleet.player_id)
    # Volles Forschungs-Dict an die Engine: deckt Waffen/Schild/Panzerung UND die
    # forschungs-skalierten Kampf-Techs (ion_disruptors, boarding_doctrine, …) ab.
    atk_tech = dict(atk_research)
    attack_mult = _commander_mods(commander, len(attacker_ships))
    # Doktrin-Bonus (z. B. Kriegsherr +10 % Waffenschaden) flottenweit.
    from app.platform.doctrine import combat_attack_mult
    attacker_player = await session.get(Player, fleet.player_id)
    attack_mult *= combat_attack_mult(attacker_player.doctrine if attacker_player else None)

    # Scharfgeschaltete Faehigkeiten (RPG): Kampf-relevante Effekte anwenden.
    armed_loss_reduction = 0.0
    if commander is not None:
        from app.commander.service import effective_ability, mark_ability_used
        now_a = _now_utc()
        for key in (fleet.mission_data or {}).get("ability_keys", []):
            eff = effective_ability(commander, key, bal, now_a)
            if not eff:
                continue
            if eff["kind"] == "attack_pct":
                attack_mult *= (1.0 + eff["magnitude"])
                mark_ability_used(commander, key, now_a)
            elif eff["kind"] == "loss_reduction":
                armed_loss_reduction += eff["magnitude"]
                mark_ability_used(commander, key, now_a)

    # Schiffsklassen-spezifische Commander-Boni (Angriff/Schild je Schiffstyp, moral-skaliert).
    ship_bonuses: dict[str, dict[str, float]] = {}
    if commander is not None:
        from app.commander.bonuses import base_bonuses, resolve_ship_bonuses
        focus = (commander.persona or {}).get("focus")
        cmd_bonuses = base_bonuses(
            commander.specialization, commander.rank, commander.traits or [], focus,
            commander.grade or "C",
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
    def_planet: Planet | None = None
    def_player: Player | None = None
    def_ship_rows: list[Ship] = []
    def_rows: list[Defense] = []
    interception_sources: list[dict] = []
    def_ships: dict[str, int] = {}
    def_defenses: dict[str, int] = {}
    def_tech = {"weapons_tech": 0, "shield_tech": 0, "armor_tech": 0}
    defender_player_id = None
    npc_resources: dict = {}

    if cell and cell.occupant_type == "npc" and cell.ref_id is not None:
        npc = await session.get(NpcEmpire, cell.ref_id)
    if npc is None and not (cell and cell.occupant_type == "player"):
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
        # NPC-Tier (hergeleitet) skaliert auch die VERTEIDIGUNGS-Tech (vorher 0): hoeheres Tier =
        # bessere Waffen/Schild/Panzerung, nicht nur mehr Schiffe.
        from app.npc.scaling import nearest_player_score, npc_tier, tier_tech
        _tier_cfg = bal.npc.get("tier", {})
        _ntier = npc_tier(npc.galaxy, npc.system, npc.position,
                          await nearest_player_score(session, npc.galaxy, npc.system, npc.position), _tier_cfg)
        def_tech = tier_tech(bal.npc.get("attack", {}).get("npc_tech", {}), _ntier, _tier_cfg)
    elif cell is not None and cell.occupant_type == "player" and cell.ref_id is not None:
        # PvP: Spieler-Planet als Verteidiger (Garnison + Verteidigung + Forschung).
        def_planet = await session.get(Planet, cell.ref_id)
        if def_planet is None:
            return None
        def_player = await session.get(Player, def_planet.player_id)
        if def_player is None:
            return None
        # Neulingsschutz/Urlaub -> Angriff dreht ab, Flotte kehrt unveraendert heim.
        vac = def_player.vacation_until
        if def_player.is_protected or (vac is not None and vac > _now_utc()):
            await create_system_transmission(
                session, player_id=fleet.player_id,
                subject=f"Angriff abgedreht ({fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position})",
                body="Das Ziel steht unter Neulingsschutz/Urlaub. Deine Flotte dreht ab und kehrt heim.",
                ttype="system",
            )
            return None
        defender_player_id = def_player.id
        # Wer angreift, verliert seinen eigenen Neulingsschutz (kein risikofreies Angreifen).
        if attacker_player is not None and attacker_player.is_protected:
            attacker_player.is_protected = False
        def_ship_rows = (await session.execute(
            select(Ship).where(Ship.planet_id == def_planet.id, Ship.fleet_id.is_(None))
        )).scalars().all()
        def_ships = {r.type: r.count for r in def_ship_rows if r.count > 0}
        def_rows = (await session.execute(
            select(Defense).where(Defense.planet_id == def_planet.id)
        )).scalars().all()
        def_defenses = {r.type: r.count for r in def_rows if r.count > 0}
        d_research = await get_research_levels(session, def_player.id)
        def_tech = dict(d_research)
        # Mond-Unterstuetzung: Orbitalbatterie + Schildkuppel verteidigen den Planeten mit.
        from app.planets.moon import moon_defense_support
        _extra_def, _shield_bonus = await moon_defense_support(session, def_planet, bal)
        for _t, _n in _extra_def.items():
            def_defenses[_t] = def_defenses.get(_t, 0) + _n
        if _shield_bonus:
            def_tech["shield_tech"] = def_tech.get("shield_tech", 0) + _shield_bonus
    else:
        # Abfangen am Ziel: fangbare durchreisende Flotten (Ankunftsfenster) + Patrouillen.
        from app.fleet.stationing import gather_interception_defenders
        interception_sources = await gather_interception_defenders(
            session, fleet.player_id,
            fleet.target_galaxy, fleet.target_system, fleet.target_position, _now_utc(),
        )
        if not interception_sources:
            return None
        merged: dict[str, int] = {}
        for src in interception_sources:
            for typ, cnt in src["ships"].items():
                merged[typ] = merged.get(typ, 0) + cnt
        def_ships = merged
        first = interception_sources[0]["obj"]
        defender_player_id = getattr(first, "player_id", None) or getattr(first, "owner_id", None)

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
    atk_survivors = dict(result["attacker_survivors"])
    atk_losses = dict(result["attacker_losses"])
    def_losses = result["defender_losses"]
    winner = result["winner"]

    # -- Trait 'cautious': loss_reduction rettet einen Teil der eigenen Verluste --
    if commander is not None:
        traits_cfg = bal.commander["personality_traits"]
        loss_red = armed_loss_reduction
        for tr in (commander.traits or []):
            loss_red += float(traits_cfg.get(tr, {}).get("loss_reduction", 0.0))
        if loss_red > 0:
            for typ, lost in list(atk_losses.items()):
                saved = int(round(lost * min(1.0, loss_red)))
                if saved > 0:
                    atk_survivors[typ] = atk_survivors.get(typ, 0) + saved
                    atk_losses[typ] = lost - saved

    # -- Todesstern-Mondzerstoerung (03d): ueberlebende Todessterne belagern den Ziel-Mond --
    moon_destroyed = None
    if winner == "attacker" and def_planet is not None and int(atk_survivors.get("deathstar", 0)) > 0:
        from app.planets.moon import maybe_destroy_moon
        n_ds = int(atk_survivors.get("deathstar", 0))
        moon_destroyed = await maybe_destroy_moon(session, def_planet, n_ds, random)
        if moon_destroyed:
            bf = int(moon_destroyed.get("backfire", 0))
            if bf > 0:
                atk_survivors["deathstar"] = max(0, n_ds - bf)
                atk_losses["deathstar"] = int(atk_losses.get("deathstar", 0)) + bf
            loc = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
            mn = moon_destroyed["moon_name"]
            bf_txt = f" Rueckschlag: {bf} Todesstern(e) verloren." if bf else ""
            if moon_destroyed["destroyed"]:
                await create_system_transmission(
                    session, player_id=fleet.player_id,
                    subject=f"💥 Mond zerstoert ({loc})",
                    body=f"Deine Todessterne haben den Mond {mn} pulverisiert.{bf_txt}",
                    ttype="system",
                )
                if moon_destroyed["owner_id"]:
                    await create_system_transmission(
                        session, player_id=moon_destroyed["owner_id"],
                        subject=f"💥 Dein Mond wurde zerstoert ({loc})",
                        body=f"Ein Todesstern-Angriff hat deinen Mond {mn} vernichtet.",
                        ttype="system",
                    )
            else:
                await create_system_transmission(
                    session, player_id=fleet.player_id,
                    subject=f"Mondzerstoerung fehlgeschlagen ({loc})",
                    body=f"Der Mond {mn} hat dem Beschuss standgehalten.{bf_txt}",
                    ttype="system",
                )

    atk_initial = sum(result["attacker_initial"].values())
    atk_lost = sum(atk_losses.values())
    situation = _situation(winner, atk_initial, atk_lost)
    # Bashing = Verteidiger deutlich schwaecher als der Angreifer (fuer 'honorable').
    _def_total = sum(result["defender_initial"].values())
    bashing = winner == "attacker" and _def_total < atk_initial * 0.25

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

    # Entern: gekaperte Gegner-Schiffe der Angreifer-Flotte hinzufuegen (kehren heim).
    for typ, n in result.get("attacker_captured", {}).items():
        if n > 0:
            session.add(Ship(planet_id=None, fleet_id=fleet.id, type=typ, count=int(n)))

    # Truemmer (beide Seiten, nur Schiffe).
    debris = _debris(atk_losses)
    def_debris = _debris(def_losses)
    debris = {
        "metal": round(debris["metal"] + def_debris["metal"], 1),
        "crystal": round(debris["crystal"] + def_debris["crystal"], 1),
    }

    # Truemmerfeld am Zielort persistieren (akkumuliert) -> per Recycler einsammelbar.
    if debris["metal"] > 0 or debris["crystal"] > 0:
        tgt_cell = cell
        if tgt_cell is None:
            tgt_cell = UniverseCell(
                galaxy=fleet.target_galaxy, system=fleet.target_system,
                position=fleet.target_position, occupant_type="debris",
            )
            session.add(tgt_cell)
        field = dict(tgt_cell.debris_field or {})
        field["metal"] = round(field.get("metal", 0) + debris["metal"], 1)
        field["crystal"] = round(field.get("crystal", 0) + debris["crystal"], 1)
        tgt_cell.debris_field = field

    # Mond-Entstehung aus dem Truemmerfeld (nur an einem Spieler-Planeten).
    if def_planet is not None and (debris["metal"] > 0 or debris["crystal"] > 0):
        from app.planets.moon import maybe_form_moon
        await maybe_form_moon(session, def_planet, debris["metal"], debris["crystal"])

    # Beute (nur bei Sieg des Angreifers).
    loot = {"metal": 0.0, "crystal": 0.0, "deuterium": 0.0}
    if winner == "attacker":
        capacity = _cargo_capacity(atk_survivors)
        if npc is not None:
            loot = _compute_loot(npc_resources, capacity)
            cargo = dict(fleet.cargo or {})
            for key in ("metal", "crystal", "deuterium"):
                cargo[key] = cargo.get(key, 0) + loot[key]
                npc_resources[key] = max(0.0, npc_resources.get(key, 0) - loot[key])
            fleet.cargo = cargo
        elif def_planet is not None:
            # PvP-Pluenderung: aktuelle Ressourcen des Verteidiger-Planeten abziehen.
            res = await refresh_resources(session, def_planet)
            available = {k: res[k]["amount"] for k in RESOURCE_KEYS}
            loot = _compute_loot(available, capacity)
            res_rows = (await session.execute(
                select(Resource).where(
                    Resource.planet_id == def_planet.id, Resource.type.in_(RESOURCE_KEYS)
                )
            )).scalars().all()
            by_type = {r.type: r for r in res_rows}
            cargo = dict(fleet.cargo or {})
            for key in RESOURCE_KEYS:
                if key in by_type:
                    by_type[key].amount = max(0.0, by_type[key].amount - loot[key])
                cargo[key] = cargo.get(key, 0) + loot[key]
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
        npc_fleet = {t: c for t, c in result["defender_survivors"].items() if t in (npc.fleet or {})}
        # Entern: vom NPC gekaperte Angreifer-Schiffe seiner Garnison hinzufuegen.
        for typ, n in result.get("defender_captured", {}).items():
            if n > 0:
                npc_fleet[typ] = npc_fleet.get(typ, 0) + int(n)
        npc.fleet = npc_fleet
        npc.resources = npc_resources
    elif def_planet is not None:
        # PvP: Spieler-Garnison auf Ueberlebende, Verteidigung mit Regen, Kaperungen stationieren.
        def_survivors = result["defender_survivors"]
        for row in def_ship_rows:
            surv = def_survivors.get(row.type, 0)
            if surv <= 0:
                await session.delete(row)
            else:
                row.count = surv
        for typ, n in result.get("defender_captured", {}).items():
            if n > 0:
                session.add(Ship(planet_id=def_planet.id, fleet_id=None, type=typ, count=int(n)))
        regen = bal.combat["defense_regen_ratio"]
        for row in def_rows:
            lost = def_losses.get(row.type, 0)
            kept = row.count - lost
            row.count = max(0, kept + math.floor(lost * regen))
    elif interception_sources:
        # Abfangen: Verluste greedy auf Quellen verteilen, je Quelle anwenden.
        from app.fleet.stationing import distribute_losses
        loc_str = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
        per = distribute_losses(interception_sources, result["defender_survivors"])
        cargo = dict(fleet.cargo or {})
        loot_acc = {"metal": 0.0, "crystal": 0.0, "deuterium": 0.0}
        for src, surv in zip(interception_sources, per):
            wiped = sum(surv.values()) == 0
            if src["kind"] == "fleet":
                f = src["obj"]
                for row in src["rows"]:
                    s = surv.get(row.type, 0)
                    if s <= 0:
                        await session.delete(row)
                    else:
                        row.count = s
                owner_id = f.player_id
                if wiped:
                    # Gefangene Flotte vernichtet: Fracht erbeutet, Flotte erledigt.
                    for key in ("metal", "crystal", "deuterium"):
                        amt = float((f.cargo or {}).get(key, 0))
                        if amt > 0:
                            loot_acc[key] += amt
                            cargo[key] = cargo.get(key, 0) + amt
                    f.status = "done"
                    f.cargo = {}
                await create_system_transmission(
                    session, player_id=owner_id,
                    subject=f"{'💥 Flotte abgefangen' if wiped else '⚔ Flotte angegriffen'} ({loc_str})",
                    body=(f"{attacker_player.display_name if attacker_player else 'Eine Feindflotte'} hat deine "
                          f"durchreisende Flotte bei {loc_str} "
                          f"{'abgefangen und vernichtet' if wiped else 'angegriffen'}."),
                    ttype="combat_report",
                )
            else:  # station / Patrouille
                st = src["obj"]
                st.ships = {t: surv.get(t, 0) for t in src["ships"] if surv.get(t, 0) > 0}
                owner_id = st.owner_id
                destroyed = not st.ships
                if destroyed:
                    await session.delete(st)  # Eskort-Angebot erlischt automatisch
                await create_system_transmission(
                    session, player_id=owner_id,
                    subject=f"{'💥 Patrouille vernichtet' if destroyed else '⚔ Patrouille angegriffen'} ({loc_str})",
                    body=(f"{attacker_player.display_name if attacker_player else 'Eine Feindflotte'} hat deine "
                          f"stationierte Patrouille bei {loc_str} "
                          f"{'vernichtet' if destroyed else 'angegriffen'}."),
                    ttype="combat_report",
                )
        if winner == "attacker" and any(v > 0 for v in loot_acc.values()):
            loot = {k: round(loot_acc[k], 1) for k in loot_acc}
            fleet.cargo = cargo

    # -- Commander-Folgen ----------------------------------------------------
    commander_outcome = await _apply_commander(
        session, commander, situation, atk_survivors, loot, atk_research, bashing=bashing
    )

    # -- Combat-Report persistieren -----------------------------------------
    location = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
    outcome_json = dict(result)
    outcome_json["situation"] = situation
    outcome_json["commander_outcome"] = commander_outcome
    if def_player is not None:
        outcome_json["defender_kind"] = "player"
        outcome_json["defender_name"] = def_player.display_name
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

    enemy_name = npc.name if npc else (def_player.display_name if def_player else location)
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

    # Postfach: anklickbarer Kampfbericht (offensiv). decision_payload traegt die report_id,
    # damit das Frontend den vollen Report (Runden/Distanz/Verluste) nachladen kann.
    won = winner == "attacker"
    loot_line = (
        f" Beute: {int(loot.get('metal', 0))} Metall / {int(loot.get('crystal', 0))} Kristall"
        f" / {int(loot.get('deuterium', 0))} Deuterium."
        if won and loot else ""
    )
    await create_system_transmission(
        session,
        player_id=fleet.player_id,
        subject=f"Kampfbericht — {'Sieg' if won else 'Niederlage'} bei {location}",
        body=(
            f"Dein Angriff auf {enemy_name} bei {location} endete mit "
            f"{'einem Sieg' if won else 'einer Niederlage'}.{loot_line}"
        ),
        ttype="combat_report",
        decision_payload={
            "report_id": str(report_id),
            "role": "attacker",
            "winner": winner,
            "location": location,
        },
    )

    # WS: Combat-Report ankuendigen.
    from app.platform.eventbus import event_bus
    await event_bus.publish_ws(fleet.player_id, {
        "type": "combat_report",
        "report_id": str(report_id),
        "summary": summary,
    })

    # -- PvP: der angegriffene Spieler bekommt einen eigenen Bericht (offline-fest) --
    if def_player is not None:
        held = winner != "attacker"
        atk_name = attacker_player.display_name if attacker_player else "Eine Feindflotte"
        d_subject = "🛡 Angriff abgewehrt" if held else "💥 Planet angegriffen!"
        d_loot_line = (
            f" Erbeutet: {int(loot.get('metal', 0))} Metall / {int(loot.get('crystal', 0))} Kristall"
            f" / {int(loot.get('deuterium', 0))} Deuterium."
            if not held and loot else ""
        )
        d_body = (
            f"{atk_name} hat deinen Planeten bei {location} angegriffen. "
            + ("Deine Verteidigung hat gehalten." if held else f"Der Planet wurde geplündert.{d_loot_line}")
        )
        await create_system_transmission(
            session,
            player_id=def_player.id,
            subject=f"{d_subject} ({location})",
            body=d_body,
            ttype="combat_report",
            decision_payload={
                "report_id": str(report_id),
                "role": "defender",
                "winner": winner,
                "location": location,
            },
        )
        await event_bus.publish_ws(def_player.id, {
            "type": "combat_report",
            "report_id": str(report_id),
            "summary": {**summary, "role": "defender"},
        })

    log.info("Kampf @ %s: winner=%s situation=%s pvp=%s", location, winner, situation, def_player is not None)
    return summary


async def _apply_commander(
    session: AsyncSession,
    commander: Commander | None,
    situation: str,
    atk_survivors: dict[str, int],
    loot: dict[str, float],
    research: dict[str, int],
    bashing: bool = False,
) -> dict:
    """Moral-Delta, XP, Rangaufstieg und Permadeath/Evakuierung — inkl. Trait-Effekten."""
    if commander is None:
        return {"status": None}

    bal = get_balance()
    deltas = bal.commander["morale"]["deltas"]
    xp_cfg = bal.commander["xp"]
    traits_cfg = bal.commander["personality_traits"]
    ctraits = commander.traits or []

    morale_delta = 0
    xp_gain = 0
    got_loot = any(v > 0 for v in loot.values())
    if situation in ("victory", "crushing_victory", "close_win"):
        morale_delta += deltas["victory"]
        if situation == "crushing_victory":
            morale_delta += deltas["crushing_victory"]
        xp_gain += xp_cfg["victory"] + xp_cfg["mission_success"]
        if got_loot:
            morale_delta += deltas["loot_gained"]
    else:  # defeat
        morale_delta += deltas["defeat"]

    # -- Trait-Effekte (Doku 05 §3): xp_mult, greedy/honorable Moral-Reaktionen --
    xp_mult = 1.0
    # Taktische Akademie (Forschung): +XP-Gewinn je Stufe.
    _aca_per = float(bal.data["research"].get("effects", {}).get("academy_xp_per_level", 0))
    xp_mult *= 1.0 + _aca_per * int(research.get("tactical_academy", 0))
    for tr in ctraits:
        tc = traits_cfg.get(tr, {})
        xp_mult *= float(tc.get("xp_mult", 1.0))
        if got_loot and "morale_on_loot" in tc:
            morale_delta += round(float(tc["morale_on_loot"]) * 100)
        if situation in ("victory", "crushing_victory", "close_win"):
            if bashing and "morale_on_bashing" in tc:
                morale_delta += round(float(tc["morale_on_bashing"]) * 100)
            elif (not bashing) and "morale_on_fair_target" in tc:
                morale_delta += round(float(tc["morale_on_fair_target"]) * 100)
    xp_gain = int(round(xp_gain * xp_mult))

    commander.morale = max(0, min(100, commander.morale + morale_delta))
    commander.xp += xp_gain
    # Einsatz befriedigt: Sieg senkt den Unmut (Zufriedenheits-Oekonomie).
    if situation in ("victory", "crushing_victory", "close_win"):
        relief = float(bal.commander.get("satisfaction", {}).get("relief_on_win", 25))
        commander.unrest = max(0.0, float(getattr(commander, "unrest", 0.0) or 0.0) - relief)
    # Rangaufstieg nach XP-Schwellen -> Skillpunkte (RPG-Entwicklung).
    from app.commander.service import _rank_index
    old_idx = _rank_index(commander.rank, bal)
    new_rank = bal.rank_for_xp(commander.xp)
    commander.rank = new_rank["key"]
    commander.span_capacity = max(commander.span_capacity, new_rank["span_contrib"])
    new_idx = _rank_index(new_rank["key"], bal)
    if new_idx > old_idx:
        prog = bal.commander["ability_progression"]
        gained = (new_idx - old_idx) * int(prog["skill_points_per_rank"])
        grade_order = bal.commander["grades"]["order"]
        if grade_order.index(commander.grade) >= grade_order.index(prog["grade_bonus_from"]):
            gained += int(prog["grade_bonus_points"])
        commander.skill_points = int(commander.skill_points or 0) + gained

    status = "active"
    # Permadeath/Evakuierung nur, wenn die Flotte des Commanders vernichtet ist.
    fleet_wiped = sum(atk_survivors.values()) == 0
    if fleet_wiped:
        evac = bal.combat["evacuation"]
        chance = evac["base_chance"]
        chance += evac["rank_bonus"].get(commander.rank, 0.0)
        chance += evac["logistics_tech_bonus_per_level"] * research.get("logistics_tech", 0)
        # aggressive/draufgaengerisch: hoeheres Eigenrisiko -> geringere Evakuierungschance.
        for tr in ctraits:
            chance -= float(traits_cfg.get(tr, {}).get("self_risk_mod", 0.0))
        chance = max(0.0, chance)
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
