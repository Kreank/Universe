"""Commander-Kampfboni: schiffsklassen-spezifische % auf Angriff/Schild/Tempo.

Abgeleitet aus Spezialisierung (Profil) + Rang (Skalierung) + Traits + persona.focus.
Im Kampf werden die Boni mit der Moral skaliert. So entstehen distinkte Commander-
Profile (Offensive / Defensive / Speed), mit denen Spieler ihre Flotten ausrichten.

Bonus-Form: {"stat": "attack|shield|speed", "target": "all|<schiffsklasse>", "pct": float}.
"""
from __future__ import annotations

from app.platform.balance import get_balance

# Stabile Anzeigereihenfolge.
_STAT_ORDER = {"attack": 0, "shield": 1, "speed": 2}


def base_bonuses(
    specialization: str,
    rank: str,
    traits: list[str] | None,
    focus: str | None = None,
    grade: str = "C",
) -> list[dict]:
    """Liefert die *Basis*-Boni (ohne Moral-Skalierung) eines Commanders — fuer Anzeige
    und als Grundlage der Kampf-Aufloesung.

    ``grade`` (Gueteklasse F..SSS) skaliert alle Boni ueber den potency-Faktor
    (C = 1.0 Baseline, SSS ~2x). So ist die Magnitude an das Potenzial gekoppelt."""
    bal = get_balance()
    cb = bal.commander["combat_bonuses"]
    profiles = cb["profiles"]
    prof = profiles.get(specialization, profiles["combat"])
    scale = cb["rank_scale"].get(rank, 1.0)
    base = cb["base"]
    fav_class = focus or prof["favored_class"]
    # Grad-Potenz (angeborenes Potenzial, Doku 05a) skaliert ALLE Boni einheitlich.
    potency = bal.grade_potency(grade)

    raw: list[dict] = [
        {"stat": prof["primary"], "target": "all", "pct": base["primary_pct"] * scale},
        {"stat": prof["secondary"], "target": "all", "pct": base["secondary_pct"] * scale},
        {"stat": prof["primary"], "target": fav_class, "pct": base["favored_class_pct"] * scale},
    ]
    # Traits (flach, nicht rang-skaliert).
    trait_mods = cb["trait_mods"]
    for t in traits or []:
        for stat, pct in trait_mods.get(t, {}).items():
            if stat.startswith("_"):
                continue
            raw.append({"stat": stat, "target": "all", "pct": float(pct)})

    # Gleiche (stat, target) zusammenfassen.
    merged: dict[tuple[str, str], float] = {}
    for b in raw:
        key = (b["stat"], b["target"])
        merged[key] = merged.get(key, 0.0) + b["pct"]

    result = [
        {"stat": stat, "target": target, "pct": round(pct * potency, 3)}
        for (stat, target), pct in merged.items()
        if abs(pct) > 1e-9
    ]
    result.sort(key=lambda b: (_STAT_ORDER.get(b["stat"], 9), b["target"] != "all", b["target"]))
    return result


def morale_factor(morale: int) -> float:
    """Skaliert Boni mit der Moral: floor .. 1.0 (Moral 0 -> floor, Moral 100 -> voll)."""
    cb = get_balance().commander["combat_bonuses"]
    floor = cb["morale_scale"]["floor"]
    m = max(0, min(100, morale))
    return floor + (1.0 - floor) * (m / 100.0)


def resolve_ship_bonuses(
    bonuses: list[dict],
    morale: int,
    ship_types: list[str],
) -> tuple[dict[str, dict[str, float]], float]:
    """Loest Boni fuer konkrete Schiffstypen auf (moral-skaliert).

    Rueckgabe: ({schiffstyp: {"attack": pct, "shield": pct}}, speed_pct_flottenweit).
    'all' wirkt auf alle vorhandenen Typen, Klassen-Targets nur auf ihre Mitglieder."""
    bal = get_balance()
    classes = bal.commander["ship_classes"]
    mf = morale_factor(morale)

    per: dict[str, dict[str, float]] = {}
    speed = 0.0
    for b in bonuses:
        pct = b["pct"] * mf
        stat = b["stat"]
        if stat == "speed":
            # Tempo wirkt flottenweit (langsamstes Schiff bestimmt das Tempo).
            speed += pct
            continue
        target = b["target"]
        if target == "all":
            targets = ship_types
        else:
            members = classes.get(target, [])
            targets = [t for t in ship_types if t in members]
        for t in targets:
            slot = per.setdefault(t, {})
            slot[stat] = slot.get(stat, 0.0) + pct
    # Runden.
    for t in per:
        for stat in per[t]:
            per[t][stat] = round(per[t][stat], 4)
    return per, round(speed, 4)
