"""Deterministische Kampf-Engine (Doku 04 + Rollen-Kampf 03b).

Eine reine, seed-gesteuerte Funktion ohne DB/IO -> direkt testbar und identisch zum
spaeteren In-Game-Simulator (eine Wahrheit, kein Drift).

Rollen-Kampf (Doku 03b, Phase 1) — drei Achsen:
- **Drei Subsysteme**: Schild (regeneriert pro Runde) · Antrieb (drive, persistenter
  Schaden -> "mission kill"/Strand) · Huelle (HP). Schild schuetzt Antrieb/Huelle, solange >0.
- **Schadenstyp x Subsystem-Matrix** (balance.combat.damage_matrix): jede Waffe (energy/
  kinetic/ion/missile) trifft die drei Subsysteme unterschiedlich. Kinetik prallt weitgehend
  an Schilden ab; Ionen leeren Schild + legen Antrieb lahm (toetet nicht); Energie knackt
  Schilde; Raketen brechen Huelle.
- **Reichweiten-Baender** (balance.combat.range_bands): die Distanz schliesst sich pro Runde
  (far->near). Ein Schiff feuert nur, wenn die Distanz <= seine Reichweite ist; feuert es
  naeher als optimal, greift die Standoff-Strafe (Artillerie schwach im Nahkampf). Verteidigung
  ist stationaer und feuert immer ohne Strafe.

Beibehalten aus v1: Rundenmodell (max 6), Determinismus (Seed), Rapidfire-Ketten (Schwarm-
Wuerze), Schild-Abprall bei Mini-Treffern, Explosion <70 % Huelle, Tech-/Commander-Boni.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

# Standard-Kampfprofil fuer Einheiten ohne combat_roster-Eintrag.
_DEFAULT_PROFILE = {"weapon_type": "kinetic", "drive": 3, "range": "near"}


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
    weapon_type: str | None
    drive_max: float
    range_idx: int
    hull: float = 0.0
    shield: float = 0.0
    drive: float = 0.0

    def __post_init__(self) -> None:
        self.hull = self.hull_max
        self.shield = self.shield_max
        self.drive = self.drive_max


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
    roster = catalogs["roster"]
    order = catalogs["range_order"]
    drive_per_tier = catalogs["drive_per_tier"]
    sb = ship_bonuses or {}

    w = 1.0 + bonus["weapons_per_level"] * tech.get("weapons_tech", 0)
    s = 1.0 + bonus["shield_per_level"] * tech.get("shield_tech", 0)
    a = 1.0 + bonus["armor_per_level"] * tech.get("armor_tech", 0)

    def profile(typ: str) -> dict[str, Any]:
        p = roster.get(typ)
        return p if isinstance(p, dict) else _DEFAULT_PROFILE

    units: list[Unit] = []
    for typ, count in (ships or {}).items():
        cfg = ship_cat.get(typ)
        if cfg is None or count <= 0:
            continue
        cb = sb.get(typ, {})
        attack = cfg.get("attack", 0) * w * attack_mult * (1.0 + cb.get("attack", 0.0))
        shield = cfg.get("shield", 0) * s * attack_mult * (1.0 + cb.get("shield", 0.0))
        hull = _hull_from_cost(cfg["cost"]) * a
        prof = profile(typ)
        drive_max = float(prof.get("drive", 0)) * drive_per_tier
        ridx = order.index(prof["range"]) if prof.get("range") in order else 0
        for _ in range(int(count)):
            units.append(Unit(
                typ, side, attack, shield, hull, dict(cfg.get("rapidfire", {})), False,
                prof.get("weapon_type"), drive_max, ridx,
            ))
    for typ, count in (defenses or {}).items():
        cfg = def_cat.get(typ)
        if cfg is None or count <= 0:
            continue
        cb = sb.get(typ, {})
        attack = cfg.get("attack", 0) * w * attack_mult * (1.0 + cb.get("attack", 0.0))
        shield = cfg.get("shield", 0) * s * attack_mult * (1.0 + cb.get("shield", 0.0))
        hull = _hull_from_cost(cfg["cost"]) * a
        prof = profile(typ)
        ridx = order.index(prof["range"]) if prof.get("range") in order else 0
        for _ in range(int(count)):
            units.append(Unit(
                typ, side, attack, shield, hull, dict(cfg.get("rapidfire_against", {})), True,
                prof.get("weapon_type"), 0.0, ridx,
            ))
    return units


def _counts(units: list[Unit]) -> dict[str, int]:
    out: dict[str, int] = {}
    for u in units:
        out[u.type] = out.get(u.type, 0) + 1
    return out


def _drive_disabled(units: list[Unit]) -> dict[str, int]:
    """Ueberlebende Einheiten mit lahmgelegtem Antrieb (drive 0, drive_max>0) -> 'mission kill'."""
    out: dict[str, int] = {}
    for u in units:
        if u.drive_max > 0 and u.drive <= 0:
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
    matrix = combat["damage_matrix"]

    bands = combat["range_bands"]
    order = bands["order"]
    start_dist = order.index(bands["start"]) if bands["start"] in order else len(order) - 1
    close_per_round = bands.get("close_per_round", 1)
    standoff_penalty = bands.get("standoff_penalty_per_band", 0.5)

    catalogs = {
        "ships": balance["ships"],
        "defenses": balance["defenses"],
        "tech_bonus": balance["tech_bonus"],
        "roster": balance.get("combat_roster", {}),
        "range_order": order,
        "drive_per_tier": combat.get("drive_integrity_per_tier", 100),
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

    def fire(unit: Unit, targets: list[Unit], penalty: float) -> float:
        """Ein Schuss (inkl. Rapidfire-Kette). ``penalty`` skaliert den Schaden (Standoff).
        Liefert den verursachten Gesamtschaden (fuer das Runden-Reporting)."""
        m = matrix.get(unit.weapon_type)
        if m is None:
            return 0.0  # Einheit ohne (gueltigen) Waffentyp feuert nicht
        base = unit.attack * penalty
        dealt = 0.0
        chain = True
        guard = 0
        while chain and targets and guard < 100:
            guard += 1
            target = targets[rng.randrange(len(targets))]
            # --- Treffer ueber die Subsystem-Matrix ---
            effective = False
            if target.shield > 0:
                sd = base * m["shield"]
                if sd <= 0 or sd < bounce_ratio * target.shield_max:
                    frac = 0.0  # prallt ab / wirkungslos auf den Schild
                elif sd <= target.shield:
                    target.shield -= sd
                    frac = 0.0   # Schild absorbiert, schuetzt Antrieb/Huelle
                    effective = True
                else:
                    frac = (sd - target.shield) / sd  # Schild bricht -> Rest penetriert
                    target.shield = 0.0
                    effective = True
            else:
                frac = 1.0
            if frac > 0.0:
                pen = base * frac
                if m["drive"] > 0 and target.drive_max > 0:
                    target.drive = max(0.0, target.drive - pen * m["drive"])
                if m["hull"] > 0:
                    target.hull -= pen * m["hull"]
                effective = True
            if effective:
                dealt += base
            # Rapidfire-Kette gegen den getroffenen Typ.
            rf = unit.rapidfire.get(target.type, 0)
            if rf and rf > 1 and rng.random() < (rf - 1) / rf:
                chain = True
            else:
                chain = False
        return dealt

    def fire_factor(unit: Unit, distance: int) -> float | None:
        """Liefert den Schadensfaktor (Standoff) wenn die Einheit feuern darf, sonst None.

        Verteidigung ist stationaer -> feuert immer ohne Strafe. Schiffe feuern nur, wenn die
        Distanz <= ihrer Reichweite liegt; naeher als optimal -> Standoff-Strafe je Band."""
        if unit.is_defense:
            return 1.0
        if distance > unit.range_idx:
            return None  # noch ausserhalb der eigenen Reichweite
        if distance < unit.range_idx:
            return standoff_penalty ** (unit.range_idx - distance)
        return 1.0

    for rnd in range(1, max_rounds + 1):
        if not atk_units or not def_units:
            break

        distance = max(0, start_dist - (rnd - 1) * close_per_round)

        # Schilde regenerieren zu Rundenbeginn voll (Antrieb/Huelle NICHT).
        for u in atk_units:
            u.shield = u.shield_max
        for u in def_units:
            u.shield = u.shield_max

        attacker_fire = 0.0
        defender_fire = 0.0

        # Alle feuerberechtigten Einheiten feuern (Reihenfolge: Angreifer, dann Verteidiger).
        for u in list(atk_units):
            if not def_units:
                break
            f = fire_factor(u, distance)
            if f is not None:
                attacker_fire += fire(u, def_units, f)
        for u in list(def_units):
            if not atk_units:
                break
            f = fire_factor(u, distance)
            if f is not None:
                defender_fire += fire(u, atk_units, f)

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
            "distance": order[distance],
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
        "attacker_drive_disabled": _drive_disabled(atk_units),
        "defender_drive_disabled": _drive_disabled(def_units),
    }
