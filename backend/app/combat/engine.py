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

Beibehalten aus v1: Rundenmodell (max 8, combat.max_rounds), Determinismus (Seed), Rapidfire-Ketten (Schwarm-
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
    interdictor: bool = False
    boarder: bool = False
    point_defense: bool = False
    shield_projector: bool = False
    stealth: bool = False
    carrier: bool = False
    sensor: bool = False
    stabilizer: bool = False
    launched: bool = False  # vom Traeger gestartete Drohne (ephemer, zaehlt nicht als Schiff)
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

    # Basis-Kampftech (+10%/Stufe) + wiederholbare Meisterschaft (+1%/Stufe, additiv, kein Cap)
    # + Megastruktur Antimaterie-Schmiede (+%/Stufe, antimaterie-befeuert).
    w = 1.0 + bonus["weapons_per_level"] * tech.get("weapons_tech", 0) \
        + bonus.get("weapons_mastery_per_level", 0.0) * tech.get("weapons_mastery", 0) \
        + bonus.get("weapons_forge_per_level", 0.0) * tech.get("antimatter_forge", 0)
    s = 1.0 + bonus["shield_per_level"] * tech.get("shield_tech", 0) \
        + bonus.get("shield_mastery_per_level", 0.0) * tech.get("shield_mastery", 0)
    a = 1.0 + bonus["armor_per_level"] * tech.get("armor_tech", 0) \
        + bonus.get("armor_mastery_per_level", 0.0) * tech.get("armor_mastery", 0)

    def profile(typ: str) -> dict[str, Any]:
        p = roster.get(typ)
        return p if isinstance(p, dict) else _DEFAULT_PROFILE

    units: list[Unit] = []
    # Stabile Iterationsreihenfolge (sortiert nach Typ): die Aufrufer bauen diese Dicts aus
    # ungeordneten DB-Queries -> ohne Sortierung haengt die Unit-/Feuer-/RNG-Reihenfolge an
    # der zufaelligen Heap-Lage der Zeilen und derselbe Seed kann divergieren. Die Engine
    # verspricht Reinheit, also erzwingt sie die Ordnung selbst (Doku: "eine Wahrheit, kein Drift").
    for typ, count in sorted((ships or {}).items()):
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
                bool(prof.get("interdictor", False)), bool(prof.get("boarder", False)),
                bool(prof.get("point_defense", False)), bool(prof.get("shield_projector", False)),
                bool(prof.get("stealth", False)), bool(prof.get("carrier", False)),
                bool(prof.get("sensor", False)), bool(prof.get("stabilizer", False)),
            ))
    # Option A (2026-06-10): Traeger starten KEINE ephemeren Drohnen mehr. Drohnen sind
    # echte Schiffe, die der Traeger beim Flottenstart aus der Garnison mitlaedt
    # (fleet.service.send_fleet) und die hier als normale Einheiten (oben) kaempfen.
    def_integrity = float(catalogs.get("defense_integrity", 0.0))
    for typ, count in sorted((defenses or {}).items()):
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
                prof.get("weapon_type"), def_integrity, ridx, bool(prof.get("interdictor", False)),
            ))
    return units


def _counts(units: list[Unit]) -> dict[str, int]:
    """Zaehlt echte Schiffe je Typ. Ephemere (vom Traeger gestartete) Drohnen zaehlen NICHT."""
    out: dict[str, int] = {}
    for u in units:
        if u.launched:
            continue
        out[u.type] = out.get(u.type, 0) + 1
    return out


def _drive_disabled(units: list[Unit]) -> dict[str, int]:
    """Ueberlebende SCHIFFE mit lahmgelegtem Antrieb (drive 0, drive_max>0) -> 'mission kill'."""
    out: dict[str, int] = {}
    for u in units:
        if u.launched or u.is_defense:
            continue
        if u.drive_max > 0 and u.drive <= 0:
            out[u.type] = out.get(u.type, 0) + 1
    return out


def _defense_disabled(units: list[Unit]) -> dict[str, int]:
    """Ueberlebende VERTEIDIGUNG, deren Integritaet durch Ionen auf 0 ist (feuert nicht mehr)."""
    out: dict[str, int] = {}
    for u in units:
        if u.is_defense and u.drive_max > 0 and u.drive <= 0:
            out[u.type] = out.get(u.type, 0) + 1
    return out


def ambush_detect_chance(sensors: int, spy_tech: int, cfg: dict) -> float:
    """Weiche Entdeckungs-Chance eines Tarnkappen-Hinterhalts (analog interception.catch_chance,
    2026-06-12): Sensor-Schiffe (detect_per_sensor=1%/Schiff, Cap detect_ship_cap=90%) plus
    spy_tech-Forschung (detect_per_research_level=0,5%/Stufe, die reservierten letzten 5% =
    detect_research_cap, Stufe 1-10). Gesamt-Cap detect_cap=95% -- NIE 100%: ein Hinterhalt kann
    immer durchrutschen. Schiffe allein kommen nur bis 90%; die letzten 5% nur ueber Forschung."""
    per = float(cfg.get("detect_per_sensor", 0.01))
    ship_cap = float(cfg.get("detect_ship_cap", 0.90))
    ship_part = min(ship_cap, per * max(0, int(sensors)))
    res_per = float(cfg.get("detect_per_research_level", 0.005))
    res_cap = float(cfg.get("detect_research_cap", 0.05))
    res_part = min(res_cap, res_per * max(0, int(spy_tech)))
    cap = float(cfg.get("detect_cap", 0.95))
    return max(0.0, min(cap, ship_part + res_part))


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
    # Schild-Regeneration pro Runde (03d): <1.0 macht den Schild zum ABNUTZBAREN Puffer statt
    # einer Pro-Runde-Wand — Voraussetzung fuer Letalitaet ohne Rapidfire. 1.0 = altes Verhalten.
    shield_regen = float(combat.get("shield_regen_ratio", 1.0))
    # Globaler Letalitaets-Regler (03d): ersetzt den Schaden-Durchsatz, den frueher Rapidfire lieferte.
    damage_scale = float(combat.get("damage_scale", 1.0))

    bands = combat["range_bands"]
    order = bands["order"]
    start_dist = order.index(bands["start"]) if bands["start"] in order else len(order) - 1
    close_per_round = bands.get("close_per_round", 1)
    standoff_penalty = bands.get("standoff_penalty_per_band", 0.5)

    stages = combat.get("drive_stages", {})
    dis = combat.get("disengage", {})
    dis_enabled = dis.get("enabled", False)
    loser_ratio = dis.get("loser_power_ratio", 1.8)
    dis_base = dis.get("base_chance", 0.45)
    interdiction_per = dis.get("interdiction_per_unit", 0.2)
    interdiction_cap = dis.get("interdiction_cap", 1.0)
    stabilization_per = dis.get("stabilization_per_unit", 0.0)
    # Standardmaessig darf der Angreifer fliehen (Rueckzug), der Verteidiger nicht (haelt Stellung).
    atk_can_flee = dis_enabled and attacker.get("allow_disengage", True)
    def_can_flee = dis_enabled and defender.get("allow_disengage", False)

    escort = combat.get("escort", {})
    pd_block = int(escort.get("boarders_blocked_per_escort", 0))
    drive_repair_per = float(escort.get("drive_repair_per_projector", 0.0))

    ambush_cfg = combat.get("ambush", {})
    ambush_enabled = ambush_cfg.get("enabled", False)
    ambush_dist = order.index(ambush_cfg["distance"]) if ambush_cfg.get("distance") in order else 0

    # Ionen-Lahmlegung von Verteidigung (C): Verteidigung bekommt eine System-Integritaet
    # (wie ein Antriebs-Pool), die Ionen-Treffer herabsetzen; bei <= 0 feuert sie nicht mehr.
    disable_cfg = combat.get("defense_disable", {})
    defense_integrity = (
        float(disable_cfg.get("integrity", 0)) if disable_cfg.get("enabled", False) else 0.0
    )

    # Forschungs-skalierte Kampf-Boni (aus dem per-Seite uebergebenen tech-Dict).
    atk_tech_d = attacker.get("tech", {}) or {}
    def_tech_d = defender.get("tech", {}) or {}
    ion_per = float(disable_cfg.get("ion_disruptor_per_level", 0.0))
    atk_ion_mult = 1.0 + ion_per * int(atk_tech_d.get("ion_disruptors", 0))
    def_ion_mult = 1.0 + ion_per * int(def_tech_d.get("ion_disruptors", 0))

    catalogs = {
        "ships": balance["ships"],
        "defenses": balance["defenses"],
        "tech_bonus": balance["tech_bonus"],
        "roster": balance.get("combat_roster", {}),
        "range_order": order,
        "drive_per_tier": combat.get("drive_integrity_per_tier", 100),
        "carrier_cfg": combat.get("carrier", {}),
        "defense_integrity": defense_integrity,
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
        # Ionen-Disruptoren-Forschung verstaerkt die Ionen-Wirkung (Schild-Strip + Antrieb).
        if unit.weapon_type == "ion":
            mult = atk_ion_mult if unit.side == "attacker" else def_ion_mult
            if mult != 1.0:
                m = {"shield": m["shield"] * mult, "drive": m["drive"] * mult, "hull": m["hull"]}
        base = unit.attack * penalty * damage_scale
        dealt = 0.0
        chain = True
        guard = 0
        while chain and targets and guard < 100:
            guard += 1
            target = targets[rng.randrange(len(targets))]
            # --- Treffer ueber die Subsystem-Matrix ---
            effective = False
            applied = 0.0  # tatsaechlich an Schild/Antrieb/Huelle angewandter Schaden (nur Reporting)
            if target.shield > 0:
                sd = base * m["shield"]
                if sd <= 0 or sd < bounce_ratio * target.shield_max:
                    frac = 0.0  # prallt ab / wirkungslos auf den Schild
                elif sd <= target.shield:
                    target.shield -= sd
                    frac = 0.0   # Schild absorbiert, schuetzt Antrieb/Huelle
                    applied += sd
                    effective = True
                else:
                    applied += target.shield  # Schild voll abgebaut, bevor es bricht
                    frac = (sd - target.shield) / sd  # Schild bricht -> Rest penetriert
                    target.shield = 0.0
                    effective = True
            else:
                frac = 1.0
            if frac > 0.0:
                pen = base * frac
                if m["drive"] > 0 and target.drive_max > 0:
                    _d_before = target.drive
                    target.drive = max(0.0, target.drive - pen * m["drive"])
                    applied += _d_before - target.drive
                if m["hull"] > 0:
                    target.hull -= pen * m["hull"]
                    applied += pen * m["hull"]
                effective = True
            if effective:
                # Reporting: tatsaechlich angewandter Schaden statt rohem ``base`` -> reine
                # Schild-Absorption zaehlt nicht mehr als voller Treffer (Befund #11).
                dealt += applied
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
            # Lahmgelegte Verteidigung (Ionen haben die Integritaet auf 0 gedrueckt) feuert nicht.
            if unit.drive_max > 0 and unit.drive <= 0:
                return None
            return 1.0
        if distance > unit.range_idx:
            return None  # noch ausserhalb der eigenen Reichweite
        if distance < unit.range_idx:
            return standoff_penalty ** (unit.range_idx - distance)
        return 1.0

    def drive_stage(unit: Unit) -> tuple[str, dict[str, Any]]:
        """Antriebs-Integritaets-Stufe (Doku 03b §2). Antrieb 0 -> gestrandet."""
        if unit.drive_max <= 0:
            return "full", stages.get("full", {})
        if unit.drive <= 0:
            return "stranded", stages.get("stranded", {})
        ratio = unit.drive / unit.drive_max
        for name in ("full", "reduced", "crippled"):
            cfg = stages.get(name)
            if cfg is not None and ratio >= cfg.get("min_ratio", 0.0):
                return name, cfg
        return "stranded", stages.get("stranded", {})

    def power(units: list[Unit]) -> float:
        return sum(u.attack for u in units)

    def disengage_phase(fleeing: list[Unit], enemy: list[Unit], fled: list[Unit]) -> tuple[list[Unit], int]:
        """Flucht-Wurf pro Schiff (Doku 03b §4). Gegnerische Interdiktoren druecken die Chance;
        eigene Warp-Stabilisatoren (Konter 2026-06-14) heben sie wieder an: jeder Stabilisator der
        fliehenden Seite negiert einen Interdiktor (stabilization_per). Liefert (verbleibende, geflohen)."""
        interdiction = min(interdiction_cap, sum(1 for u in enemy if u.interdictor) * interdiction_per)
        relief = sum(1 for u in fleeing if u.stabilizer) * stabilization_per
        interdiction = max(0.0, interdiction - relief)
        suppress = max(0.0, 1.0 - interdiction)
        if suppress <= 0.0:
            return fleeing, 0
        remaining: list[Unit] = []
        n_fled = 0
        for u in fleeing:
            if u.is_defense:
                remaining.append(u)
                continue
            _name, cfg = drive_stage(u)
            if not cfg.get("can_flee", False):
                remaining.append(u)  # bewegungsunfaehig/gestrandet -> kann nicht fliehen
                continue
            chance = dis_base * cfg.get("flee_factor", 0.0) * suppress
            if rng.random() < chance:
                fled.append(u)
                n_fled += 1
            else:
                remaining.append(u)
        return remaining, n_fled

    atk_fled: list[Unit] = []
    def_fled: list[Unit] = []

    def resolve(units: list[Unit]) -> tuple[list[Unit], dict[str, int]]:
        """Explosionen/Zerstoerung. Ephemere Drohnen zaehlen NICHT als Verlust."""
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
                if not u.launched:
                    losses[u.type] = losses.get(u.type, 0) + 1
            else:
                survivors.append(u)
        return survivors, losses

    # Hinterhalt (Tarnkappe, Doku 03b §9): hat der Angreifer Stealth-Schiffe, eroeffnet er mit
    # einer Ueberraschungsrunde aus dem Nahbereich -- nur der Angreifer feuert. Konter (weiches
    # Modell): Sensor-Schiffe + spy_tech-Forschung beim Verteidiger entdecken den Hinterhalt mit
    # einer Chance (nie 100%) und negieren ihn. Der Wurf faellt NUR, wenn ueberhaupt ein
    # Tarnkappen-Hinterhalt droht -> kein Stoeren des RNG-Stroms normaler Schlachten.
    _has_stealth = bool(atk_units) and any(u.stealth for u in atk_units)
    _detected = False
    if ambush_enabled and _has_stealth and def_units:
        _sensors = sum(1 for u in def_units if u.sensor)
        _spy = int(defender.get("tech", {}).get("spy_tech", 0))
        _detected = rng.random() < ambush_detect_chance(_sensors, _spy, ambush_cfg)
    if ambush_enabled and not _detected and _has_stealth and def_units:
        # Modell (Design-Entscheidung 2026-06-13): In der Ueberraschungsrunde sind NUR die
        # Tarnkappen-Schiffe schon heran (vorausgeeilt) und eroeffnen das Feuer; der Rest der
        # Flotte trifft erst zu Runde 1 ein und feuert ab da. Der Verteidiger SIEHT die
        # anfliegende Flotte und ist vorbereitet (Schilde oben) -> KEIN Schild-Reset; der
        # Stealth-Vorteil ist allein die einseitige Eroeffnungssalve der Tarnkappen-Schiffe.
        ambush_fire = 0.0
        for u in list(atk_units):
            if not def_units:
                break
            if not u.stealth:
                continue  # nicht-getarnte Schiffe sind in dieser Runde noch im Anflug
            f = fire_factor(u, ambush_dist)
            if f is not None:
                ambush_fire += fire(u, def_units, f)
        def_units, amb_losses = resolve(def_units)
        for t, c in amb_losses.items():
            defender_losses_total[t] = defender_losses_total.get(t, 0) + c
        rounds.append({
            "round": 0, "distance": order[ambush_dist], "ambush": True,
            "attacker_fire": round(ambush_fire, 1), "defender_fire": 0.0,
            "attacker_losses": {}, "defender_losses": amb_losses,
            "attacker_fled": 0, "defender_fled": 0,
        })

    for rnd in range(1, max_rounds + 1):
        if not atk_units or not def_units:
            break

        distance = max(0, start_dist - (rnd - 1) * close_per_round)

        # Schilde regenerieren zu Rundenbeginn TEILWEISE (abnutzbarer Puffer, 03d; Antrieb/Huelle NICHT).
        for u in atk_units:
            u.shield = min(u.shield_max, u.shield + u.shield_max * shield_regen)
        for u in def_units:
            u.shield = min(u.shield_max, u.shield + u.shield_max * shield_regen)

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

        # Schild-Tender reparieren nach der Feuerphase Antriebs-Integritaet der eigenen
        # Seite (kontert das Ionen-/Strand-Fenster; haelt Subsysteme online).
        def repair_drives(units: list[Unit]) -> None:
            repair = sum(1 for u in units if u.shield_projector) * drive_repair_per
            if repair <= 0:
                return
            for u in units:
                if u.drive_max > 0 and u.drive < u.drive_max:
                    u.drive = min(u.drive_max, u.drive + repair)
        repair_drives(atk_units)
        repair_drives(def_units)

        # Explosionen / Zerstoerung abwickeln (resolve ist ausserhalb der Schleife definiert).
        atk_units, atk_losses = resolve(atk_units)
        def_units, def_losses = resolve(def_units)
        for t, c in atk_losses.items():
            attacker_losses_total[t] = attacker_losses_total.get(t, 0) + c
        for t, c in def_losses.items():
            defender_losses_total[t] = defender_losses_total.get(t, 0) + c

        # Disengage: die unterlegene Seite versucht zu fliehen (Antrieb-gated, Interdiktion-gedrosselt).
        atk_fled_now = def_fled_now = 0
        if atk_units and def_units:
            if atk_can_flee and power(def_units) >= loser_ratio * power(atk_units):
                atk_units, atk_fled_now = disengage_phase(atk_units, def_units, atk_fled)
            if def_can_flee and power(atk_units) >= loser_ratio * power(def_units):
                def_units, def_fled_now = disengage_phase(def_units, atk_units, def_fled)

        rounds.append({
            "round": rnd,
            "distance": order[distance],
            "attacker_fire": round(attacker_fire, 1),
            "defender_fire": round(defender_fire, 1),
            "attacker_losses": atk_losses,
            "defender_losses": def_losses,
            "attacker_fled": atk_fled_now,
            "defender_fled": def_fled_now,
        })

        if not atk_units or not def_units:
            break

    # --- Entern (Phase 3): Enterschiffe kapern GESTRANDETE Gegner (Antrieb 0) ---
    # Greift unabhaengig vom Sieger (disable+board). Nur Schiffe; Geflohene sind raus.
    boarding = combat.get("boarding", {})
    cap_base = int(boarding.get("capture_per_boarder", 0))
    cap_per_doc = int(boarding.get("capture_per_doctrine_level", 0))
    # Enter-Doktrin-Forschung der ENTERNDEN Seite erhoeht die Kaper-Kapazitaet je Schiff.
    atk_cap_per = cap_base + cap_per_doc * int(atk_tech_d.get("boarding_doctrine", 0))
    def_cap_per = cap_base + cap_per_doc * int(def_tech_d.get("boarding_doctrine", 0))
    attacker_captured: dict[str, int] = {}
    defender_captured: dict[str, int] = {}

    # Schiffswert (Summe der Baukosten) je Typ -> Kaper-Priorisierung (A: teuerste zuerst).
    # ``balance["ships"]`` kann auch Nicht-Dict-Einträge (z. B. _note) enthalten -> typsicher.
    _ship_costs = balance.get("ships", {})
    ship_values: dict[str, float] = {}
    for _t, _spec in _ship_costs.items():
        if not isinstance(_spec, dict):
            continue
        _cost = _spec.get("cost") if isinstance(_spec.get("cost"), dict) else {}
        ship_values[_t] = sum(float(v) for v in _cost.values())
    # Wunsch-Kaperziel des Angreifers (B): konkreter Schiffstyp wird bevorzugt; sonst rein nach Wert.
    _atk_prefer = attacker.get("capture_priority")
    _atk_prefer = _atk_prefer if _atk_prefer and _atk_prefer != "value" else None

    def board(boarding_units: list[Unit], victim_units: list[Unit], captured: dict[str, int],
              cap_per: int, prefer: str | None = None) -> list[Unit]:
        capacity = sum(1 for u in boarding_units if u.boarder) * cap_per
        # Punktverteidigung der Opfer-Seite (Eskort-Fregatten) faengt Enterer ab.
        capacity -= sum(1 for u in victim_units if u.point_defense) * pd_block
        if capacity <= 0:
            return victim_units
        # Nur GESTRANDETE Gegner (Antrieb auf 0) sind kaperbar; Rest bleibt unangetastet.
        capturable: list[Unit] = []
        kept: list[Unit] = []
        for u in victim_units:
            if not u.launched and not u.is_defense and u.drive_max > 0 and u.drive <= 0:
                capturable.append(u)
            else:
                kept.append(u)
        # Priorisierung: gewuenschter Typ (B) zuerst, dann nach Schiffswert absteigend (A).
        capturable.sort(
            key=lambda u: (1 if (prefer and u.type == prefer) else 0, ship_values.get(u.type, 0.0)),
            reverse=True,
        )
        for u in capturable:
            if capacity > 0:
                captured[u.type] = captured.get(u.type, 0) + 1
                capacity -= 1
            else:
                kept.append(u)
        return kept

    if cap_base > 0 or cap_per_doc > 0:
        def_units = board(atk_units, def_units, attacker_captured, atk_cap_per, _atk_prefer)  # Angreifer entert Verteidiger
        atk_units = board(def_units, atk_units, defender_captured, def_cap_per)   # Verteidiger entert Angreifer

    # Geflohene Einheiten ueberleben (kehren heim), zaehlen aber nicht als "haelt das Feld".
    attacker_survivors = _counts(atk_units + atk_fled)
    defender_survivors = _counts(def_units + def_fled)

    atk_alive = len(atk_units) > 0
    def_alive = len(def_units) > 0
    if atk_alive and not def_alive:
        winner = "attacker"
    elif def_alive and not atk_alive:
        winner = "defender"
    elif not atk_alive and not def_alive:
        winner = "draw"
    else:
        winner = "draw"  # nach max_rounds (Default 8) Runden beide ueberlebt

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
        "defender_defense_disabled": _defense_disabled(def_units),
        "attacker_fled": _counts(atk_fled),
        "defender_fled": _counts(def_fled),
        "attacker_captured": attacker_captured,
        "defender_captured": defender_captured,
    }
