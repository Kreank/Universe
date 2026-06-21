"""Tests fuer die DETERMINISTISCHE Logik der „erwachenden Galaxie" (Welle 4, app.awakening.service).

DB-/LLM-frei: getestet werden die reinen Funktionen — die Aggressions-Gewichtung
(compute_aggression_level), die Status-Baender (aggression_status, Grenzen peaceful/tense/war/
apocalypse), die Erwachen-Entscheidung (should_awaken: ueber/unter Schwelle, kein Doppel-Spawn bei
aktivem Waechter, Beruhigungs-Cooldown = Aggressions-Reduktion nach Niederlage) und die Waechter-
Flotten-Skalierung (compute_warden_fleet) — plus die Sanity des balance-Blocks ``awakening``.
Stil wie test_chronicle.py (BALANCE_PATH-Fallback fuers balance-Lesen)."""
import datetime as dt
import json
import os

from app.awakening.service import (
    aggression_status,
    compute_aggression_level,
    compute_warden_fleet,
    should_awaken,
)

# Kompakter, fuer die Tests selbst definierter Balance-Ausschnitt (entkoppelt von balance.json).
CFG = {
    "threshold": 60.0,
    "weights": {"combat": 1.0, "debris": 0.001, "attackers": 2.0},
    "status_bands": [
        {"status": "peaceful", "min": 0.0},
        {"status": "tense", "min": 20.0},
        {"status": "war", "min": 40.0},
        {"status": "apocalypse", "min": 60.0},
    ],
    "warden": {
        "base_fleet": {"battleship": 60, "destroyer": 40},
        "fleet_per_level": {},
        "fleet_top_player_scale": 0.0,
        "max_fleet_mult": 4.0,
    },
}


def _now() -> dt.datetime:
    return dt.datetime(2026, 6, 20, 12, 0, tzinfo=dt.timezone.utc)


# --------------------------------------------------------- compute_aggression_level

def test_aggression_level_weighted_sum():
    # 10*1 + 5000*0.001 + 3*2 = 10 + 5 + 6 = 21.
    level, status = compute_aggression_level(10, 5000.0, 3, CFG)
    assert level == 21.0
    assert status == "tense"  # 20 <= 21 < 40


def test_aggression_level_zero_is_peaceful():
    level, status = compute_aggression_level(0, 0.0, 0, CFG)
    assert level == 0.0
    assert status == "peaceful"


# ------------------------------------------------------------- aggression_status

def test_status_band_boundaries():
    assert aggression_status(0.0, CFG) == "peaceful"
    assert aggression_status(19.9, CFG) == "peaceful"
    assert aggression_status(20.0, CFG) == "tense"      # untere Grenze inklusiv
    assert aggression_status(39.9, CFG) == "tense"
    assert aggression_status(40.0, CFG) == "war"
    assert aggression_status(59.9, CFG) == "war"
    assert aggression_status(60.0, CFG) == "apocalypse"
    assert aggression_status(10_000.0, CFG) == "apocalypse"


def test_status_no_bands_falls_back_peaceful():
    assert aggression_status(999.0, {"status_bands": []}) == "peaceful"


# --------------------------------------------------------------- should_awaken

def test_should_awaken_at_and_below_threshold():
    now = _now()
    assert should_awaken(60.0, 60.0, False, None, now) is True   # genau Schwelle
    assert should_awaken(80.0, 60.0, False, None, now) is True
    assert should_awaken(59.9, 60.0, False, None, now) is False  # darunter


def test_should_not_awaken_when_warden_active():
    now = _now()
    # Selbst weit ueber der Schwelle: kein zweiter Waechter, solange einer aktiv ist.
    assert should_awaken(10_000.0, 60.0, True, None, now) is False


def test_should_not_awaken_during_calm_period():
    now = _now()
    # Nach Niederlage/Rueckzug ist das Universum beruhigt (calm_until in der Zukunft) ->
    # trotz hoher Aggression erwacht keiner (Aggressions-Reduktion / Selbstregulativ).
    future = now + dt.timedelta(hours=24)
    assert should_awaken(10_000.0, 60.0, False, future, now) is False
    # Ist die Beruhigungsphase vorbei, kann er wieder erwachen.
    past = now - dt.timedelta(hours=1)
    assert should_awaken(10_000.0, 60.0, False, past, now) is True


def test_should_awaken_handles_naive_calm_until():
    now = _now()
    naive_future = dt.datetime(2026, 6, 21, 12, 0)  # ohne tzinfo
    assert should_awaken(10_000.0, 60.0, False, naive_future, now) is False


# --------------------------------------------------------- compute_warden_fleet

def test_warden_fleet_equals_base_at_threshold():
    # level == threshold, keine Top-Spieler -> exakt base_fleet.
    fleet = compute_warden_fleet(60.0, [], CFG)
    assert fleet == {"battleship": 60, "destroyer": 40}


def test_warden_fleet_scales_with_level():
    # level = 2*threshold -> Multiplikator 2.
    fleet = compute_warden_fleet(120.0, [], CFG)
    assert fleet == {"battleship": 120, "destroyer": 80}


def test_warden_fleet_multiplier_capped():
    # level = 10*threshold, aber max_fleet_mult = 4 -> gedeckelt auf 4x.
    fleet = compute_warden_fleet(600.0, [], CFG)
    assert fleet == {"battleship": 240, "destroyer": 160}


def test_warden_fleet_scales_with_top_players():
    cfg = json.loads(json.dumps(CFG))
    cfg["warden"]["fleet_top_player_scale"] = 0.0001
    # top_sum = 10000 -> top_mult = 1 + 0.0001*10000 = 2 ; level == threshold -> mult 1.
    fleet = compute_warden_fleet(60.0, [10000.0], cfg)
    assert fleet == {"battleship": 120, "destroyer": 80}


def test_warden_fleet_per_level_adds_units_over_threshold():
    cfg = json.loads(json.dumps(CFG))
    cfg["warden"]["fleet_per_level"] = {"battleship": 1.0}
    # over = level-threshold = 10 -> +10 Schlachtschiffe ueber den skalierten Grundstock.
    fleet = compute_warden_fleet(70.0, [], cfg)
    # mult = 70/60 ~ 1.1667 -> battleship round(60*1.1667)=70, +10 = 80 ; destroyer round(40*1.1667)=47.
    assert fleet["battleship"] == 80
    assert fleet["destroyer"] == 47


# ------------------------------------------------------------- balance sanity

def test_awakening_block_present_in_balance():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    a = data["awakening"]
    assert a["enabled"] is True
    assert a["tick_interval_hours"] > 0
    assert a["lookback_hours"] > 0
    assert a["threshold"] > 0
    assert a["warning_hours"] > 0
    assert a["lifetime_hours"] > 0
    assert a["respawn_dormant_hours"] > 0
    # Gewichte + Baender vorhanden und konsistent.
    for key in ("combat", "debris", "attackers"):
        assert key in a["weights"]
    bands = a["status_bands"]
    assert [b["status"] for b in bands] == ["peaceful", "tense", "war", "apocalypse"]
    # Waechter-Flotte referenziert echte Schiffstypen aus dem ships-Katalog.
    for stype in a["warden"]["base_fleet"]:
        assert stype in data["ships"]
    for dtype in a["warden"]["defenses"]:
        assert dtype in data["defenses"]
    assert a["warden"]["model"] == "qwen3.5:9b"
    # Aggregierte Sanity: bei level == threshold ergibt sich genau die Grund-Flotte.
    fleet = compute_warden_fleet(float(a["threshold"]), [], a)
    assert fleet == {k: int(v) for k, v in a["warden"]["base_fleet"].items()}
