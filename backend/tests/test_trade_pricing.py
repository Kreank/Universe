"""Verifiziert den reinen Preis-Kern des Handelssystems (``app.fleet.trade_pricing``).

DB-/Auth-frei: getestet werden ausschliesslich die reinen Funktionen ``price_of``,
``effective_margin`` und ``simulate_swap``. Der Fokus liegt auf der KORREKTEN RICHTUNG
der Slippage (grosse Order bewegt den Kurs gegen den Spieler), dem Clamping, der
Spezialisierungs-Arbitrage, Marge/Reputation, Caps/Floor und der Budget-Bilanz.

Lade-Logik (balance.json per Pfad-Suche) wie in ``test_combat_sim.py``.
"""
import json
import os

import pytest

from app.fleet.trade_pricing import effective_margin, price_of, simulate_swap


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
SETPOINT = CFG["default_setpoint"]


def _flat_stock(metal=2_000_000, crystal=1_000_000, deuterium=500_000) -> dict:
    return {"metal": metal, "crystal": crystal, "deuterium": deuterium}


# --- price_of -------------------------------------------------------------

def test_price_high_stock_cheap_low_stock_expensive():
    """Hoher Bestand -> niedriger Preis; knapper Bestand -> hoher Preis."""
    sp = SETPOINT["metal"]
    cheap = price_of("metal", 10 * sp, sp, CFG)
    fair = price_of("metal", sp, sp, CFG)
    dear = price_of("metal", sp / 10, sp, CFG)
    assert cheap < fair < dear
    # Am Sollbestand ist der Preis exakt der Basiswert.
    assert fair == pytest.approx(CFG["base_value"]["metal"])


def test_price_clamping_min_and_max():
    """Clamp greift an beiden Enden: nie unter base*min_mult, nie ueber base*max_mult."""
    base = CFG["base_value"]["crystal"]
    sp = SETPOINT["crystal"]
    lo = base * CFG["price_min_mult"]
    hi = base * CFG["price_max_mult"]
    # Riesiger Bestand -> Preis auf Minimum geklemmt.
    assert price_of("crystal", sp * 1_000_000, sp, CFG) == pytest.approx(lo)
    # Winziger Bestand -> Preis auf Maximum geklemmt (robust gegen stock=0).
    assert price_of("crystal", 0, sp, CFG) == pytest.approx(hi)
    assert price_of("crystal", 1, sp, CFG) == pytest.approx(hi)


# --- Slippage Verkauf -----------------------------------------------------

def test_slippage_sell_avg_below_start_and_grows_with_size():
    """Verkauf bewegt den Kurs nach unten: avg_sell_price < Startpreis, und die
    doppelte Menge drueckt den Durchschnitt weiter (mehr Slippage)."""
    st = _flat_stock()
    start = price_of("metal", st["metal"], SETPOINT["metal"], CFG)
    small = simulate_swap("metal", 200_000, "crystal", st, SETPOINT, CFG)
    big = simulate_swap("metal", 400_000, "crystal", st, SETPOINT, CFG)
    assert small["avg_sell_price"] < start
    assert big["avg_sell_price"] < small["avg_sell_price"]
    # value_in steigt monoton mit der Menge (aber unterproportional wegen Slippage).
    assert big["value_in"] > small["value_in"]
    assert big["avg_sell_price"] < start


# --- Slippage Kauf --------------------------------------------------------

def test_slippage_buy_avg_above_start():
    """Kauf leert den Bestand -> Preis steigt: avg_buy_price > Startpreis der want_res."""
    st = _flat_stock()
    start_buy = price_of("crystal", st["crystal"], SETPOINT["crystal"], CFG)
    res = simulate_swap("metal", 300_000, "crystal", st, SETPOINT, CFG)
    assert res["received"] > 0
    assert res["avg_buy_price"] > start_buy


# --- Spezialisierung / Arbitrage -----------------------------------------

def test_specialization_creates_price_differential():
    """Ein Deuterium-Refinery (hoher Deuterium-Sollbestand, entsprechend bevorrateter)
    verkauft Deuterium guenstiger als eine Metallwelt -> der Spieler erhaelt fuer denselben
    Metall-Einsatz mehr Deuterium (Arbitrage-Potenzial)."""
    mw = CFG["specializations"]["metal_world"]
    dr = CFG["specializations"]["deuterium_refinery"]
    sp_mw = {k: SETPOINT[k] * mw[k] for k in SETPOINT}
    sp_dr = {k: SETPOINT[k] * dr[k] for k in SETPOINT}
    # Jeder Haendler haelt seinen eigenen Sollbestand (am Ziel-Lager).
    st_mw = dict(sp_mw)
    st_dr = dict(sp_dr)
    buy_mw = simulate_swap("metal", 300_000, "deuterium", st_mw, sp_mw, CFG)
    buy_dr = simulate_swap("metal", 300_000, "deuterium", st_dr, sp_dr, CFG)
    assert buy_dr["received"] > buy_mw["received"]
    assert buy_dr["avg_buy_price"] < buy_mw["avg_buy_price"]


# --- Marge / Reputation ---------------------------------------------------

def test_effective_margin_decreases_and_never_negative():
    """Reputation senkt die Marge linear, deckelt rep_level auf max_level, nie < 0."""
    rep = CFG["reputation"]
    base = CFG["margin"]
    assert effective_margin(0, CFG) == pytest.approx(base)
    assert effective_margin(1, CFG) == pytest.approx(base - rep["margin_reduction_per_level"])
    # Ueber max_level wird gedeckelt (kein weiterer Rabatt).
    capped = effective_margin(rep["max_level"], CFG)
    assert effective_margin(rep["max_level"] + 99, CFG) == pytest.approx(capped)
    # Nie negativ.
    assert effective_margin(10_000, CFG) >= 0.0


def test_higher_reputation_yields_more_received():
    """Hoehere Reputation -> geringere Marge -> mehr Budget -> mehr received."""
    st = _flat_stock()
    low = simulate_swap("metal", 150_000, "crystal", st, SETPOINT, CFG, reputation_level=0)
    high = simulate_swap("metal", 150_000, "crystal", st, SETPOINT, CFG, reputation_level=3)
    assert high["margin"] < low["margin"]
    assert high["received"] > low["received"]


# --- Sonderkurs / rate_bonus (Schwarzmarkt-Event) -------------------------

def test_rate_bonus_default_is_neutral():
    """Ohne rate_bonus == mit rate_bonus=1.0 -> normaler Haendler unveraendert."""
    st = _flat_stock()
    base = simulate_swap("metal", 150_000, "crystal", st, SETPOINT, CFG)
    one = simulate_swap("metal", 150_000, "crystal", st, SETPOINT, CFG, rate_bonus=1.0)
    assert base == one


def test_rate_bonus_yields_more_received_in_magnitude():
    """Schwarzmarkt (rate_bonus=1.5) liefert beim IDENTISCHEN Tausch deutlich mehr
    received als ein normaler Haendler (generalist) — in der Groessenordnung von +50%
    (durch milde Slippage minimal darunter)."""
    # generalist == default_setpoint; Bestand am Soll (fairer Ausgangskurs).
    st = _flat_stock()
    normal = simulate_swap("metal", 100_000, "crystal", st, SETPOINT, CFG)
    black = simulate_swap("metal", 100_000, "crystal", st, SETPOINT, CFG, rate_bonus=1.5)
    assert black["received"] > normal["received"]
    ratio = black["received"] / normal["received"]
    # ~+50% (Slippage druckt minimal, aber spuerbar besser als jeder normale Haendler).
    assert 1.35 < ratio <= 1.5 + 1e-9
    assert ratio == pytest.approx(1.5, rel=0.12)


def test_rate_bonus_floored_to_one():
    """rate_bonus < 1.0 wird auf 1.0 geklemmt (kein Schlechterstellen des Spielers)."""
    st = _flat_stock()
    base = simulate_swap("metal", 120_000, "crystal", st, SETPOINT, CFG)
    worse = simulate_swap("metal", 120_000, "crystal", st, SETPOINT, CFG, rate_bonus=0.5)
    assert worse["received"] == pytest.approx(base["received"])


def test_rate_bonus_refund_not_exploitable_when_cargo_capped():
    """Geschenkter Bonus wird NICHT miterstattet: bei Cargo-Limit darf refund_value den
    echten Eigenanteil des Spielers (value_in*(1-margin)) nie ueberschreiten."""
    st = _flat_stock()
    cap = 10_000.0
    black = simulate_swap(
        "metal", 100_000, "crystal", st, SETPOINT, CFG, cargo_capacity=cap, rate_bonus=1.5
    )
    base_budget = black["value_in"] * (1.0 - black["margin"])
    assert black["refund_value"] <= base_budget + 1e-6


# --- Caps / Floor ---------------------------------------------------------

def test_cargo_capacity_limits_received():
    """cargo_capacity deckelt die erhaltene Menge; nicht genutztes Budget -> refund_value."""
    st = _flat_stock()
    cap = 40_000.0
    res = simulate_swap("metal", 1_000_000, "crystal", st, SETPOINT, CFG, cargo_capacity=cap)
    assert res["received"] <= cap + 1e-6
    assert res["received"] == pytest.approx(cap, rel=1e-6)
    # Budget blieb uebrig, weil die Fracht limitierte.
    assert res["refund_value"] > 0


def test_min_stock_floor_protects_seller_stock():
    """Ein Leerkauf kann den want-Bestand nie unter min_stock_floor druecken."""
    floor = CFG["min_stock_floor"]
    st = _flat_stock(crystal=floor + 5_000)
    # Riesiges Angebot -> Budget weit ueber dem, was der knappe Bestand hergibt.
    res = simulate_swap("metal", 10_000_000, "crystal", st, SETPOINT, CFG)
    assert res["new_stock"]["crystal"] >= floor - 1e-6
    # Da der Bestand limitierte, bleibt Budget als refund_value uebrig.
    assert res["refund_value"] > 0


# --- Erhaltung / Bilanz ---------------------------------------------------

def test_budget_balance_spent_plus_refund_equals_net_value():
    """value_in*(1-margin) == spent + refund_value (Budget geht nicht verloren)."""
    st = _flat_stock()
    res = simulate_swap("metal", 250_000, "crystal", st, SETPOINT, CFG, reputation_level=2)
    net = res["value_in"] * (1.0 - res["margin"])
    assert res["spent"] + res["refund_value"] == pytest.approx(net, rel=1e-9)
    # avg_buy_price entspricht spent/received.
    assert res["avg_buy_price"] == pytest.approx(res["spent"] / res["received"], rel=1e-9)


def test_input_stock_not_mutated_and_new_stock_moves():
    """stock/setpoint werden nicht mutiert; new_stock: offer hoch, want runter."""
    st = _flat_stock()
    snapshot = dict(st)
    res = simulate_swap("metal", 200_000, "crystal", st, SETPOINT, CFG)
    assert st == snapshot  # Eingabe unberuehrt
    assert res["new_stock"]["metal"] > snapshot["metal"]    # Haendler hat mehr Metall
    assert res["new_stock"]["crystal"] < snapshot["crystal"]  # weniger Kristall


# --- Sonderfaelle ---------------------------------------------------------

def test_same_resource_raises():
    with pytest.raises(ValueError):
        simulate_swap("metal", 100_000, "metal", _flat_stock(), SETPOINT, CFG)


def test_non_positive_amount_raises():
    with pytest.raises(ValueError):
        simulate_swap("metal", 0, "crystal", _flat_stock(), SETPOINT, CFG)
    with pytest.raises(ValueError):
        simulate_swap("metal", -5, "crystal", _flat_stock(), SETPOINT, CFG)


def test_unknown_resource_raises():
    with pytest.raises(ValueError):
        simulate_swap("antimatter", 100_000, "crystal", _flat_stock(), SETPOINT, CFG)
    with pytest.raises(ValueError):
        simulate_swap("metal", 100_000, "antimatter", _flat_stock(), SETPOINT, CFG)
    with pytest.raises(ValueError):
        price_of("antimatter", 1000, 1000, CFG)


def test_deterministic():
    """Zwei identische Aufrufe liefern bit-identische Ergebnisse (keine Zufaelligkeit)."""
    st = _flat_stock()
    a = simulate_swap("deuterium", 50_000, "metal", st, SETPOINT, CFG)
    b = simulate_swap("deuterium", 50_000, "metal", st, SETPOINT, CFG)
    assert a == b
