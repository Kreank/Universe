"""Expeditions-Mission: Aufbruch in die galaktischen Weiten (Position 16).

Eine Flotte fliegt zum Deep-Space-Slot eines Systems, VERWEILT die gewaehlte Stundenzahl
(1..max, max = min(astrophysics, hour_cap)) und kehrt dann heim. Bei der Aufloesung wird ein
gewichteter Zufalls-Ausgang gezogen:

- ``resources``  — Metall/Kristall/Deuterium (x Ertrags-Multiplikator: expedition_tech-Cap + Dauer),
- ``ships``      — gefundene Schiffe (treten der Flotte bei),
- ``nothing``    — Fehlschlag,
- ``pirates`` / ``aliens`` — echter Kampf gegen eine generierte Gegnerflotte (Kampf-Engine);
  Verluste real, bei Sieg Beute,
- ``delay``      — ein Ereignis verlaengert die Rueckkehr (extra_hours),
- ``blackhole``  — Totalverlust (die Flotte kehrt nie zurueck).

Laenger verweilen = mehr Ertrag (yield_bonus_per_hour) UND mehr Risiko (risk_bonus_per_hour skaliert
die als ``risky`` markierten Gewichte). Reine Helfer sind DB-frei und testbar; ``resolve_expedition``
kapselt Session + Kampf-Engine.
"""
from __future__ import annotations

import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.combat.engine import simulate_battle
from app.platform.balance import get_balance
from app.platform.models import Fleet, Ship

log = logging.getLogger("universe.expedition")


# -- Reine Logik ----------------------------------------------------------------

def max_expedition_hours(astro_level: int, cfg: dict) -> int:
    """Maximale Verweildauer (Std) = astrophysics-Stufe * per_level, gedeckelt; 0 unter Stufe 1."""
    dur = cfg.get("duration", {})
    per = float(dur.get("max_hours_per_astro_level", 1))
    cap = int(dur.get("hour_cap", 24))
    return max(0, min(cap, int(astro_level * per)))


def clamp_hours(requested: int, astro_level: int, cfg: dict) -> int:
    """Gewuenschte Stunden auf [1, max] einklemmen (mind. 1, solange ueberhaupt erlaubt)."""
    mx = max_expedition_hours(astro_level, cfg)
    if mx <= 0:
        return 0
    return max(1, min(int(requested or 1), mx))


def yield_mult(exp_tech_level: int, hours: int, cfg: dict) -> float:
    """Ertrags-Multiplikator = Forschungs-Bonus (gedeckelt bei yield_cap_level) x Dauer-Bonus."""
    per = float(get_balance().data["research"].get("effects", {}).get("expedition_per_level", 0))
    cap_level = int(cfg.get("yield_cap_level", 10))
    research = 1.0 + per * min(int(exp_tech_level), cap_level)
    dur_bonus = float(cfg.get("duration", {}).get("yield_bonus_per_hour", 0)) * max(0, hours - 1)
    return research * (1.0 + dur_bonus)


def scale_outcomes(outcomes: list[dict], hours: int, cfg: dict) -> list[dict]:
    """Skaliert die Gewichte der 'risky'-Ausgaenge mit der Verweildauer (laenger = riskanter)."""
    risk = float(cfg.get("duration", {}).get("risk_bonus_per_hour", 0)) * max(0, hours - 1)
    if risk <= 0:
        return outcomes
    out = []
    for o in outcomes:
        if o.get("risky"):
            o = {**o, "weight": float(o.get("weight", 0)) * (1.0 + risk)}
        out.append(o)
    return out


def pick_outcome(outcomes: list[dict], roll: float) -> dict:
    """Reine Auswahl: ``roll`` in [0, summe_gewichte) -> der getroffene Ausgang."""
    acc = 0.0
    for o in outcomes:
        acc += float(o.get("weight", 0))
        if roll < acc:
            return o
    return outcomes[-1] if outcomes else {"type": "nothing"}


def ship_power(ships: dict[str, int], catalog: dict) -> float:
    """Grobe Kampfwert-Schaetzung einer Flotte = Summe(Schiff-attack * Anzahl)."""
    return sum(float(catalog.get(t, {}).get("attack", 0)) * c for t, c in ships.items())


def generate_enemy_fleet(exp_ships: dict[str, int], enc_cfg: dict, catalog: dict) -> dict[str, int]:
    """Generiert eine Gegnerflotte (Piraten/Aliens), deren Kampfwert ~ power_ratio x Expeditions-
    Kampfwert ist, gleichmaessig ueber das roster verteilt. Deterministisch (kein RNG noetig)."""
    roster = [t for t in enc_cfg.get("roster", []) if t in catalog]
    budget = ship_power(exp_ships, catalog) * float(enc_cfg.get("power_ratio", 1.0))
    if not roster or budget <= 0:
        return {roster[0]: 1} if roster else {}
    per = budget / len(roster)
    out: dict[str, int] = {}
    for t in roster:
        atk = max(1.0, float(catalog[t].get("attack", 1)))
        n = int(per // atk)
        if n > 0:
            out[t] = n
    if not out:
        cheapest = min(roster, key=lambda t: float(catalog[t].get("attack", 1)) or 1)
        out[cheapest] = 1
    return out


def _rand_range(rng: random.Random, span) -> int:
    if isinstance(span, (list, tuple)) and len(span) == 2:
        lo, hi = int(span[0]), int(span[1])
        return rng.randint(min(lo, hi), max(lo, hi))
    return int(span or 0)


def _loot_from_losses(losses: dict[str, int], catalog: dict, ratio: float) -> dict[str, float]:
    """Beute aus zerstoerten Gegnern = ratio x (Metall+Kristall der Schiffskosten)."""
    metal = crystal = 0.0
    for typ, n in losses.items():
        cost = catalog.get(typ, {}).get("cost", {})
        metal += float(cost.get("metal", 0)) * n
        crystal += float(cost.get("crystal", 0)) * n
    return {"metal": round(metal * ratio, 1), "crystal": round(crystal * ratio, 1)}


# -- DB-Resolver ----------------------------------------------------------------

async def resolve_expedition(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Zieht den Expeditions-Ausgang und wendet ihn an. Liefert eine Zusammenfassung; das Feld
    ``extra_hours`` (Verzoegerung) bzw. ``wiped`` (Totalverlust) steuert die Rueckkehr im Aufrufer."""
    bal = get_balance()
    cfg = bal.data.get("expedition", {})
    outcomes = cfg.get("outcomes", [])
    if not outcomes:
        return None

    from app.economy.service import get_research_levels
    research = await get_research_levels(session, fleet.player_id)
    hours = int((fleet.mission_data or {}).get("expedition_hours", 1) or 1)

    rng = random.Random(random.randrange(1, 2 ** 62))
    scaled = scale_outcomes(outcomes, hours, cfg)
    total_w = sum(float(o.get("weight", 0)) for o in scaled)
    outcome = pick_outcome(scaled, rng.random() * total_w)
    otype = outcome.get("type", "nothing")
    result: dict = {
        "location": f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}",
        "outcome": otype,
    }

    if otype == "resources":
        mult = yield_mult(research.get("expedition_tech", 0), hours, cfg)
        gain = {k: int(round(_rand_range(rng, outcome.get(k, 0)) * mult)) for k in ("metal", "crystal", "deuterium")}
        cargo = dict(fleet.cargo or {})
        for k in ("metal", "crystal", "deuterium"):
            cargo[k] = round(cargo.get(k, 0) + gain[k], 1)
        fleet.cargo = cargo
        result["found"] = gain

    elif otype == "ships":
        ship_type = outcome.get("ship", "light_fighter")
        n = _rand_range(rng, outcome.get("count", 0))
        if n > 0 and ship_type in bal.ships:
            session.add(Ship(planet_id=None, fleet_id=fleet.id, type=ship_type, count=n))
            result["found_ships"] = {ship_type: n}

    elif otype in ("pirates", "aliens"):
        await _resolve_encounter(session, fleet, otype, research, result)

    elif otype in ("dark_matter", "antimatter"):
        # Exotische Endgame-Ressource (kontoweit auf dem Spieler, nicht als Fracht).
        amount = float(_rand_range(rng, outcome.get("amount", 0)))
        if amount > 0:
            from app.platform.models import Player
            player = await session.get(Player, fleet.player_id)
            if player is not None:
                setattr(player, otype, float(getattr(player, otype, 0) or 0) + amount)
                result["found_exotic"] = {otype: amount}

    elif otype == "delay":
        result["extra_hours"] = _rand_range(rng, outcome.get("extra_hours", 0))

    elif otype == "blackhole":
        # Totalverlust: alle Schiffe der Flotte vernichtet, keine Rueckkehr.
        rows = (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        lost = {r.type: r.count for r in rows}
        for r in rows:
            await session.delete(r)
        result["lost"] = lost
        result["wiped"] = True

    # Flavor (Phase 2): erzaehlerischer Expeditions-Log-Bericht via ai-worker (additiv, best effort).
    try:
        from app.platform.ai_jobs import enqueue_flavor
        _otype_de = {
            "resources": "Rohstofffund", "ships": "Schiffsfund", "pirates": "Piraten-Begegnung",
            "aliens": "Alien-Begegnung", "delay": "Verzoegerung", "blackhole": "Schwarzes Loch",
            "nothing": "nichts Bemerkenswertes",
        }
        _detail: dict = {}
        if result.get("found"):
            _detail["Funde"] = result["found"]
        if result.get("found_ships"):
            _detail["geborgene Schiffe"] = result["found_ships"]
        if result.get("lost"):
            _detail["Verluste"] = result["lost"]
        if result.get("battle"):
            _detail["Gefecht"] = "gewonnen" if result.get("won") else "verloren"
        await enqueue_flavor(
            fleet.player_id, narrator="expedition_log", situation="Expedition in den galaktischen Weiten",
            planet=result["location"], outcome=_otype_de.get(otype, otype), detail=_detail,
            ttype="routine",
        )
    except Exception:  # noqa: BLE001 — Flavor darf die Expedition nie stoeren
        pass

    log.info("Expedition @ %s [%dh] -> %s", result["location"], hours, otype)
    return result


async def _resolve_encounter(session: AsyncSession, fleet: Fleet, kind: str, research: dict, result: dict) -> None:
    """Echter Kampf gegen eine generierte Piraten-/Alien-Flotte (Kampf-Engine)."""
    bal = get_balance()
    enc = bal.data.get("expedition", {}).get("encounters", {}).get(kind, {})

    rows = (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
    exp_ships = {r.type: r.count for r in rows if r.count > 0}
    if not exp_ships:
        return

    enemy = generate_enemy_fleet(exp_ships, enc, bal.ships)
    enemy_tech_lvl = int(enc.get("tech", 0))
    enemy_tech = {"weapons_tech": enemy_tech_lvl, "shield_tech": enemy_tech_lvl, "armor_tech": enemy_tech_lvl}

    attacker = {"ships": exp_ships, "tech": research, "attack_mult": 1.0}
    defender = {"ships": enemy, "defenses": {}, "tech": enemy_tech, "attack_mult": 1.0}
    seed = random.randrange(1, 2 ** 62)
    battle = simulate_battle(attacker, defender, seed, bal.data)

    survivors = dict(battle["attacker_survivors"])
    losses = dict(battle["attacker_losses"])
    enemy_losses = dict(battle["defender_losses"])

    # Verluste auf die Flotten-Schiffe anwenden.
    for row in rows:
        surv = int(survivors.get(row.type, 0))
        if surv <= 0:
            await session.delete(row)
        else:
            row.count = surv

    result["enemy"] = enemy
    result["lost"] = {t: n for t, n in losses.items() if n > 0}
    result["winner"] = battle["winner"]

    # Bei Sieg: Beute aus zerstoerten Gegnern.
    if battle["winner"] == "attacker" and sum(survivors.values()) > 0:
        loot = _loot_from_losses(enemy_losses, bal.ships, float(enc.get("loot_ratio", 0)))
        if loot["metal"] or loot["crystal"]:
            cargo = dict(fleet.cargo or {})
            cargo["metal"] = round(cargo.get("metal", 0) + loot["metal"], 1)
            cargo["crystal"] = round(cargo.get("crystal", 0) + loot["crystal"], 1)
            fleet.cargo = cargo
            result["loot"] = loot
    if sum(survivors.values()) == 0:
        result["wiped"] = True
