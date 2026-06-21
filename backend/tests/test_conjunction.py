"""Tests fuer die DETERMINISTISCHE Konjunktions-Logik (app.fleet.conjunction).

DB-/zeit-frei: getestet wird die reine Distanz-Modulation (Determinismus, Schranken, gleiche
Position -> 1.0, Konjunktions-Erkennung, next_conjunction strikt+monoton in der Zukunft,
enabled=false -> Faktor 1.0, effective_distance-Rundung) plus die Sanity des balance-Blocks
``conjunction``. Stil wie test_chronicle.py (BALANCE_PATH-Fallback fuers balance-Lesen)."""
import json
import os

from app.fleet.conjunction import (
    active_window_end,
    distance_factor,
    effective_distance,
    is_conjunction,
    next_conjunction,
)
from app.fleet.service import compute_distance

CFG = {
    "enabled": True,
    "cycle_hours": 6.0,
    "conjunction_window_hours": 0.5,
    "max_discount": 0.7,
    "max_surcharge": 1.15,
    "radius": 12,
    "max_upcoming": 12,
    "inter_galaxy_enabled": False,
}

O = (1, 1, 1)
T = (1, 5, 1)  # gleiches Galaxie, anderes System -> Konjunktion moeglich
T2 = (3, 20, 7)  # andere Galaxie


# ------------------------------------------------------------- Determinismus

def test_distance_factor_deterministic():
    for at in (0.0, 1234.5, 1_000_000.0, 1_700_000_000.0):
        a = distance_factor(O, T, at, CFG)
        b = distance_factor(O, T, at, CFG)
        assert a == b


# ----------------------------------------------------------------- Schranken

def test_factor_within_bounds_over_many_epochs():
    # Ueber mehrere Zyklen abtasten -> nie unter max_discount, nie ueber max_surcharge.
    period = CFG["cycle_hours"] * 3600
    n = 2000
    for i in range(n):
        at = i * (period * 3 / n)  # 3 Zyklen
        f = distance_factor(O, T, at, CFG)
        assert CFG["max_discount"] - 1e-9 <= f <= CFG["max_surcharge"] + 1e-9


def test_factor_at_conjunction_center_equals_max_discount():
    # Im Zentrum (next_conjunction-Zeitpunkt) ist der Faktor exakt max_discount.
    center = next_conjunction(O, T, 0.0, CFG)
    assert center is not None
    f = distance_factor(O, T, center, CFG)
    assert abs(f - CFG["max_discount"]) < 1e-9
    assert is_conjunction(O, T, center, CFG)


# ------------------------------------------------------- Gleiche Position/System

def test_same_position_factor_one():
    assert distance_factor(O, O, 12345.0, CFG) == 1.0


def test_same_system_other_position_factor_one():
    # Nur die Position differiert (Innersystem) -> keine Konjunktion.
    assert distance_factor((1, 1, 1), (1, 1, 9), 12345.0, CFG) == 1.0
    assert not is_conjunction((1, 1, 1), (1, 1, 9), 12345.0, CFG)


# ----------------------------------------------------------------- Inter-Galaxie

def test_inter_galaxy_disabled_factor_one():
    assert distance_factor(O, T2, 12345.0, CFG) == 1.0
    assert next_conjunction(O, T2, 0.0, CFG) is None


def test_inter_galaxy_enabled_can_modulate():
    cfg = {**CFG, "inter_galaxy_enabled": True}
    center = next_conjunction(O, T2, 0.0, cfg)
    assert center is not None
    f = distance_factor(O, T2, center, cfg)
    assert abs(f - cfg["max_discount"]) < 1e-9


# --------------------------------------------------------- next_conjunction

def test_next_conjunction_strictly_future_and_monotonic():
    base = 1_700_000_000.0
    nc1 = next_conjunction(O, T, base, CFG)
    assert nc1 is not None and nc1 > base
    # Monoton: spaeterer Start -> nie frueheres Ergebnis.
    nc2 = next_conjunction(O, T, base + 7200, CFG)
    assert nc2 is not None and nc2 >= nc1


def test_active_window_end_only_when_active():
    # Ausserhalb einer Konjunktion -> None.
    center = next_conjunction(O, T, 0.0, CFG)
    period = CFG["cycle_hours"] * 3600
    outside = center + period / 2  # Anti-Punkt -> sicher kein Fenster
    assert not is_conjunction(O, T, outside, CFG)
    assert active_window_end(O, T, outside, CFG) is None
    # Innerhalb -> Ende liegt in der Zukunft.
    end = active_window_end(O, T, center, CFG)
    assert end is not None and end > center


# ----------------------------------------------------------------- enabled=false

def test_disabled_factor_one():
    cfg = {**CFG, "enabled": False}
    for at in (0.0, 12345.0, next_conjunction(O, T, 0.0, CFG)):
        assert distance_factor(O, T, at, cfg) == 1.0
    assert not is_conjunction(O, T, 12345.0, cfg)
    assert next_conjunction(O, T, 0.0, cfg) is None


# --------------------------------------------------------- effective_distance

def test_effective_distance_rounds_factor():
    center = next_conjunction(O, T, 0.0, CFG)
    base = compute_distance(O, T)
    factor = distance_factor(O, T, center, CFG)
    assert effective_distance(O, T, center, CFG) == max(1, int(round(base * factor)))


def test_effective_distance_disabled_equals_static():
    cfg = {**CFG, "enabled": False}
    for at in (0.0, 12345.0, 1_700_000_000.0):
        assert effective_distance(O, T, at, cfg) == compute_distance(O, T)


def test_effective_distance_never_below_one():
    assert effective_distance((1, 1, 1), (1, 1, 1), 0.0, CFG) >= 1


# ------------------------------------------------------------- balance sanity

def test_conjunction_block_present_in_balance():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    c = data["conjunction"]
    assert c["enabled"] is True
    assert c["cycle_hours"] > 0
    assert c["conjunction_window_hours"] > 0
    assert 0 < c["max_discount"] <= 1.0
    assert c["max_surcharge"] >= 1.0
    assert c["radius"] > 0
