"""Deterministische Kampf-Engine (Doku 04).

Eine reine, seed-gesteuerte Funktion ohne DB/IO -> direkt testbar und identisch zum
spaeteren In-Game-Simulator (eine Wahrheit, kein Drift). Mechanik:
- bis zu 6 Runden, jede Einheit feuert auf ein zufaelliges Ziel (seeded RNG)
- Schaden trifft erst Schild, dann Huelle; Schild regeneriert pro Runde voll
- Schild-Abprall, wenn Schaden < 1 % des Ziel-Schilds
- Rapidfire-Kette mit Wahrscheinlichkeit (rf-1)/rf
- Explosionschance unter 70 % Huelle = 1 - Resthuelle/Maxhuelle
- Modifikatoren (Moral, Traits, Ueberdehnung) wirken auf Angriff & Schild des Angreifers
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Unit:
    """Eine einzelne Kampfeinheit (Schiff oder Verteidigung)."""
    type: str
    side: str  # "attacker" | "defender"
    attack: float
    shield_max: float
    hull_max: float
    rapidfire: dict[str, int]
    is_defense: bool
    hull: float = 0.0
    shield: float = 0.0

    def __post_init__(self) -> None:
        self.hull = self.hull_max
        self.shield = self.shield_max


def _hull_from_cost(cost: dict[str, float]) -> float:
    """Huelle = (Metall + Kristall) / 10 (Doku 04 / balance.json)."""
    return (cost.get("metal", 0) + cost.get("crystal", 0)) / 10.0


def _build_units(
    side: str,
    ships: dict[str, int],
    defenses: dict[str, int],
    catalogs: dict[str, Any],
    tech: dict[str, int],
    attack_mult: float,
    ship_bonuses: dict[str, dict[str, float]] | None = None,
) -> list[Unit]:
    """Expandiert Stueckzahlen zu Einzel-Einheiten und wendet Tech-/Mod-Boni an.

    ``ship_bonuses`` sind die schiffstyp-spezifischen Commander-Boni, bereits
    aufgeloest pro Schiffstyp: {typ: {"attack": pct, "shield": pct}} (additiv auf 1.0).
    Sie wirken ZUSAETZLICH zum globalen ``attack_mult`` (Moral-Band)."""
    ship_cat = catalogs["ships"]
    def_cat = catalogs["defenses"]
    bonus = catalogs["tech_bonus"]
    sb = ship_bonuses or {}

    w = 1.0 + bonus["weapons_per_level"] * tech.get("weapons_tech", 0)
    s = 1.0 + bonus["shield_per_level"] * tech.get("shield_tech", 0)
    a = 1.0 + bonus["armor_per_level"] * tech.get("armor_tech", 0)

    units: list[Unit] = []
    for typ, count in (ships or {}).items():
        cfg = ship_cat.get(typ)
        if cfg is None or count <= 0:
            continue
        cb = sb.get(typ, {})
        attack = cfg.get("attack", 0) * w * attack_mult * (1.0 + cb.get("attack", 0.0))
        shield = cfg.get("shield", 0) * s * attack_mult * (1.0 + cb.get("shield", 0.0))
        hull = _hull_from_cost(cfg["cost"]) * a
        for _ in range(int(count)):
            units.append(Unit(typ, side, attack, shield, hull, dict(cfg.get("rapidfire", {})), False))
    for typ, count in (defenses or {}).items():
        cfg = def_cat.get(typ)
        if cfg is None or count <= 0:
            continue
        cb = sb.get(typ, {})
        attack = cfg.get("attack", 0) * w * attack_mult * (1.0 + cb.get("attack", 0.0))
        shield = cfg.get("shield", 0) * s * attack_mult * (1.0 + cb.get("shield", 0.0))
        hull = _hull_from_cost(cfg["cost"]) * a
        for _ in range(int(count)):
            units.append(Unit(typ, side, attack, shield, hull, dict(cfg.get("rapidfire_against", {})), True))
    return units


def _counts(units: list[Unit]) -> dict[str, int]:
    out: dict[str, int] = {}
    for u in units:
        out[u.type] = out.get(u.type, 0) + 1
    return out


def simulate_battle(
    attacker: dict[str, Any],
    defender: dict[str, Any],
    seed: int,
    balance: dict[str, Any],
) -> dict[str, Any]:
    """Fuehrt eine Schlacht durch und liefert ein vollstaendiges Ergebnis-Dict.

    attacker/defender erwarten:
      ships: {type:count}, defenses: {type:count} (nur defender), tech: {weapons,shield,armor},
      attack_mult: float (Moral*Traits*Ueberdehnung -> Angriff & Schild).
    """
    rng = random.Random(seed)
    combat = balance["combat"]
    bounce_ratio = combat["shield_bounce_ratio"]
    explosion_threshold = combat["explosion_threshold_hull_pct"]
    max_rounds = combat["max_rounds"]

    catalogs = {
        "ships": balance["ships"],
        "defenses": balance["defenses"],
        "tech_bonus": balance["tech_bonus"],
    }

    atk_units = _build_units(
        "attacker", attacker.get("ships", {}), {}, catalogs,
        attacker.get("tech", {}), attacker.get("attack_mult", 1.0),
        attacker.get("ship_bonuses"),
    )
    def_units = _build_units(
        "defender", defender.get("ships", {}), defender.get("defenses", {}), catalogs,
        defender.get("tech", {}), defender.get("attack_mult", 1.0),
        defender.get("ship_bonuses"),
    )

    attacker_initial = _counts(atk_units)
    defender_initial = _counts(def_units)
    attacker_losses_total: dict[str, int] = {}
    defender_losses_total: dict[str, int] = {}

    rounds: list[dict[str, Any]] = []

    def fire(unit: Unit, targets: list[Unit]) -> float:
        """Ein Schuss (inkl. Rapidfire-Kette). Liefert verursachten Gesamtschaden."""
        dealt = 0.0
        chain = True
        guard = 0
        while chain and targets and guard < 100:
            guard += 1
            target = targets[rng.randrange(len(targets))]
            dmg = unit.attack
            # Schild-Abprall: zu schwacher Schuss verpufft.
            if target.shield_max > 0 and dmg < bounce_ratio * target.shield_max:
                pass  # Treffer prallt ab
            else:
                dealt += dmg
                if dmg <= target.shield:
                    target.shield -= dmg
                else:
                    rest = dmg - target.shield
                    target.shield = 0.0
                    target.hull -= rest
            # Rapidfire-Kette gegen den getroffenen Typ.
            rf = unit.rapidfire.get(target.type, 0)
            if rf and rf > 1 and rng.random() < (rf - 1) / rf:
                chain = True
            else:
                chain = False
        return dealt

    for rnd in range(1, max_rounds + 1):
        if not atk_units or not def_units:
            break

        # Schilde regenerieren zu Rundenbeginn voll.
        for u in atk_units:
            u.shield = u.shield_max
        for u in def_units:
            u.shield = u.shield_max

        attacker_fire = 0.0
        defender_fire = 0.0

        # Alle Einheiten beider Seiten feuern (Reihenfolge: Angreifer, dann Verteidiger).
        for u in list(atk_units):
            if not def_units:
                break
            attacker_fire += fire(u, def_units)
        for u in list(def_units):
            if not atk_units:
                break
            defender_fire += fire(u, atk_units)

        # Explosionen / Zerstoerung abwickeln.
        def resolve(units: list[Unit]) -> tuple[list[Unit], dict[str, int]]:
            survivors: list[Unit] = []
            losses: dict[str, int] = {}
            for u in units:
                destroyed = False
                if u.hull <= 0:
                    destroyed = True
                elif u.hull < explosion_threshold * u.hull_max:
                    if rng.random() < (1.0 - u.hull / u.hull_max):
                        destroyed = True
                if destroyed:
                    losses[u.type] = losses.get(u.type, 0) + 1
                else:
                    survivors.append(u)
            return survivors, losses

        atk_units, atk_losses = resolve(atk_units)
        def_units, def_losses = resolve(def_units)
        for t, c in atk_losses.items():
            attacker_losses_total[t] = attacker_losses_total.get(t, 0) + c
        for t, c in def_losses.items():
            defender_losses_total[t] = defender_losses_total.get(t, 0) + c

        rounds.append({
            "round": rnd,
            "attacker_fire": round(attacker_fire, 1),
            "defender_fire": round(defender_fire, 1),
            "attacker_losses": atk_losses,
            "defender_losses": def_losses,
        })

        if not atk_units or not def_units:
            break

    attacker_survivors = _counts(atk_units)
    defender_survivors = _counts(def_units)

    atk_alive = len(atk_units) > 0
    def_alive = len(def_units) > 0
    if atk_alive and not def_alive:
        winner = "attacker"
    elif def_alive and not atk_alive:
        winner = "defender"
    elif not atk_alive and not def_alive:
        winner = "draw"
    else:
        winner = "draw"  # nach 6 Runden beide ueberlebt

    return {
        "seed": seed,
        "rounds": rounds,
        "winner": winner,
        "attacker_initial": attacker_initial,
        "defender_initial": defender_initial,
        "attacker_survivors": attacker_survivors,
        "defender_survivors": defender_survivors,
        "attacker_losses": attacker_losses_total,
        "defender_losses": defender_losses_total,
    }
