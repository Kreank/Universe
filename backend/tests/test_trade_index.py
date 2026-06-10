"""Verifiziert die reinen Funktionen des globalen Handelsindex (``app.fleet.trade_index``).

DB-frei: ``synthetic_market``, ``index_prices`` und ``ema``. Fokus auf die zugesicherten
Eigenschaften des Modells: Neutralpunkt (Vorrat == Soll -> Kurs == base_value), Richtung
(Ueberfluss -> billiger, Knappheit -> teurer), Stabilitaet bei wenig Spielern (virtual
reserve dominiert -> Kurs nahe base), Skalierung mit Spielerzahl und EMA-Glaettung.
"""
import json
import os

from app.fleet.trade_index import ema, index_prices, synthetic_market

RESOURCES = ("metal", "crystal", "deuterium")


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


CFG = _load_balance()["trade"]
IDX = CFG["index"]
BASE = CFG["base_value"]
NEUTRAL = IDX["neutral_per_player"]


# --- Neutralpunkt: Vorrat == neutral_per_player*players -> Kurs == base_value ---

def test_neutral_point_equals_base_value():
    # players=1, Vorrat exakt = neutral_per_player -> Kurs == base_value je Ressource.
    supply = {r: float(NEUTRAL[r]) for r in RESOURCES}
    prices = index_prices(supply, players=1, cfg=CFG)
    for r in RESOURCES:
        assert prices[r] == BASE[r]


# --- Richtung: Ueberfluss billiger, Knappheit teurer --------------------------

def test_glut_is_cheaper_scarcity_is_pricier():
    glut = {r: float(NEUTRAL[r]) * 4 for r in RESOURCES}
    scarce = {r: float(NEUTRAL[r]) * 0.1 for r in RESOURCES}
    p_glut = index_prices(glut, players=1, cfg=CFG)
    p_scarce = index_prices(scarce, players=1, cfg=CFG)
    for r in RESOURCES:
        assert p_glut[r] < BASE[r] < p_scarce[r]


# --- Selbst-begrenzend: mehr Vorrat -> niedrigerer Kurs (monoton) -------------

def test_price_monotonic_decreasing_in_supply():
    low = index_prices({r: float(NEUTRAL[r]) * 0.5 for r in RESOURCES}, 1, CFG)
    high = index_prices({r: float(NEUTRAL[r]) * 2.0 for r in RESOURCES}, 1, CFG)
    for r in RESOURCES:
        assert high[r] < low[r]


# --- Stabilitaet bei wenig Spielern: V dominiert -> Kurs nahe base ------------

def test_low_player_count_is_stable_near_base():
    # Ein einzelner Spieler haelt nur wenig: Kurs soll dicht an base_value liegen,
    # und ein kleiner Bestandswechsel darf den Kurs kaum bewegen.
    s1 = {r: float(NEUTRAL[r]) * 0.2 for r in RESOURCES}
    s2 = {r: float(NEUTRAL[r]) * 0.3 for r in RESOURCES}
    p1 = index_prices(s1, players=1, cfg=CFG)
    p2 = index_prices(s2, players=1, cfg=CFG)
    for r in RESOURCES:
        # nahe base (innerhalb 40 %) und nur kleine Bewegung zwischen s1/s2 (< 15 %).
        assert abs(p1[r] - BASE[r]) / BASE[r] < 0.4
        assert abs(p2[r] - p1[r]) / p1[r] < 0.15


# --- Skalierung mit Spielerzahl: mehr Spieler -> hoeherer Neutralpunkt --------

def test_neutral_scales_with_players():
    # Gleicher absoluter Vorrat, aber mehr Spieler -> Vorrat ist *relativ* knapper
    # (Neutralpunkt steigt) -> Kurs hoeher. Kein Einzelner dominiert den Index.
    supply = {r: float(NEUTRAL[r]) for r in RESOURCES}
    p1 = index_prices(supply, players=1, cfg=CFG)
    p5 = index_prices(supply, players=5, cfg=CFG)
    for r in RESOURCES:
        assert p5[r] > p1[r]


# --- synthetischer Markt: setpoint = neutral*players + V, stock = supply + V --

def test_synthetic_market_shape():
    supply = {r: 123456.0 for r in RESOURCES}
    stock, setpoint = synthetic_market(supply, players=3, cfg=CFG)
    V = IDX["virtual_reserve"]
    for r in RESOURCES:
        assert setpoint[r] == float(NEUTRAL[r]) * 3 + float(V[r])
        assert stock[r] == supply[r] + float(V[r])


# --- EMA-Glaettung ------------------------------------------------------------

def test_ema_without_prev_returns_current():
    cur = {r: 100.0 * (i + 1) for i, r in enumerate(RESOURCES)}
    assert ema(None, cur, 0.25) == cur
    assert ema({}, cur, 0.25) == cur


def test_ema_blends_towards_current():
    prev = {r: 0.0 for r in RESOURCES}
    cur = {r: 100.0 for r in RESOURCES}
    out = ema(prev, cur, 0.25)
    for r in RESOURCES:
        assert out[r] == 25.0  # 0.25*100 + 0.75*0
