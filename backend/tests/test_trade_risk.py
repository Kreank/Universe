"""Verifiziert die reinen Risiko-/Regen-Helfer des Handelssystems (``app.fleet.trade``).

DB-/Auth-frei, Stil ``test_trade.py``: getestet werden ausschliesslich die reinen
Funktionen ``route_risk_chance`` (Routen-Ueberfall-Wahrscheinlichkeit) und
``drift_stock`` (Ein-Schritt-Markt-Regen). Die DB-abhaengigen Pfade (resolve_trade,
market_regen_tick) und der Zufallswurf des Ueberfalls bleiben bewusst aussen vor.

Lade-Logik (balance.json per Pfad-Suche) wie in ``test_trade.py``.
"""
import json
import os

from app.fleet.trade import drift_stock, route_risk_chance


def _load_balance() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(6):
        candidate = os.path.join(d, "shared", "balance.json")
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                return json.load(fh)
        d = os.path.dirname(d)
    raise FileNotFoundError("balance.json nicht gefunden")


BALANCE = _load_balance()
CFG = BALANCE["trade"]
RC = CFG["route_risk"]


# --- route_risk_chance ----------------------------------------------------

def test_route_risk_zero_distance_is_zero():
    # Ohne Distanz kein Risiko (raw = base * 0 = 0).
    assert route_risk_chance(0, escort_power=0.0, cargo_value=0.0, cfg=CFG) == 0.0


def test_route_risk_increases_with_distance():
    near = route_risk_chance(2, escort_power=0.0, cargo_value=0.0, cfg=CFG)
    far = route_risk_chance(10, escort_power=0.0, cargo_value=0.0, cfg=CFG)
    assert 0.0 < near < far


def test_route_risk_escort_lowers_chance():
    no_escort = route_risk_chance(5, escort_power=0.0, cargo_value=0.0, cfg=CFG)
    with_escort = route_risk_chance(5, escort_power=10000.0, cargo_value=0.0, cfg=CFG)
    assert with_escort < no_escort


def test_route_risk_escort_for_half_halves_chance():
    # Bei escort_power == escort_power_for_half halbiert sich das Risiko (Faktor 0.5).
    half_power = float(RC["escort_power_for_half"])
    base = route_risk_chance(3, escort_power=0.0, cargo_value=0.0, cfg=CFG)
    halved = route_risk_chance(3, escort_power=half_power, cargo_value=0.0, cfg=CFG)
    assert halved == 0.5 * base


def test_route_risk_richer_cargo_raises_chance():
    poor = route_risk_chance(4, escort_power=0.0, cargo_value=0.0, cfg=CFG)
    rich = route_risk_chance(4, escort_power=0.0, cargo_value=float(RC["cargo_value_ref"]), cfg=CFG)
    # Reiche Fracht (>= cargo_value_ref) verdoppelt den Risiko-Faktor (1 + 1.0).
    assert rich == 2.0 * poor


def test_route_risk_cargo_value_factor_capped_at_double():
    # cargo_value weit ueber dem Referenzwert verstaerkt nicht ueber Faktor 2 hinaus.
    at_ref = route_risk_chance(2, escort_power=0.0, cargo_value=float(RC["cargo_value_ref"]), cfg=CFG)
    way_over = route_risk_chance(
        2, escort_power=0.0, cargo_value=float(RC["cargo_value_ref"]) * 100, cfg=CFG
    )
    assert way_over == at_ref


def test_route_risk_clamped_to_max_chance():
    # Riesige Distanz + reiche Fracht ohne Eskorte -> auf max_chance gedeckelt.
    chance = route_risk_chance(
        10000, escort_power=0.0, cargo_value=float(RC["cargo_value_ref"]) * 10, cfg=CFG
    )
    assert chance == float(RC["max_chance"])


def test_route_risk_huge_escort_approaches_zero():
    # Enorme Eskorte drueckt das Risiko gegen 0 (aber >= 0).
    chance = route_risk_chance(10, escort_power=1e12, cargo_value=0.0, cfg=CFG)
    assert 0.0 <= chance < 1e-6


def test_route_risk_never_negative():
    chance = route_risk_chance(5, escort_power=1e9, cargo_value=0.0, cfg=CFG)
    assert chance >= 0.0


# --- drift_stock (Markt-Regen-Mathematik) ---------------------------------

def test_drift_stock_below_setpoint_rises():
    # Bestand unter Soll steigt Richtung Soll.
    new = drift_stock(current=1000, setpoint=2000, regen=0.1)
    assert 1000 < new <= 2000


def test_drift_stock_above_setpoint_falls():
    # Bestand ueber Soll faellt Richtung Soll.
    new = drift_stock(current=3000, setpoint=2000, regen=0.1)
    assert 2000 <= new < 3000


def test_drift_stock_at_setpoint_stays():
    assert drift_stock(current=2000, setpoint=2000, regen=0.1) == 2000


def test_drift_stock_converges_to_setpoint():
    # Nach vielen Ticks liegt der Bestand praktisch beim Sollwert.
    setpoint = 2000.0
    stock = 100.0
    for _ in range(500):
        stock = drift_stock(stock, setpoint, 0.1)
    assert abs(stock - setpoint) <= 1
