"""Routen-Ueberfall als echtes Gefecht (2026-06-22): verifiziert den reinen Raeuber-
Geschwader-Generator ``generate_raider_fleet``. Der DB-Resolver (resolve_trade) und der
Kampf selbst bleiben — wie der Rest des Handels-Slice — ohne DB-Harness aussen vor; die
Balance-Kalibrierung des Gefechts wurde separat gegen die Engine geprueft.

Lade-Logik (balance.json per Pfad-Suche) wie in ``test_trade_risk.py``.
"""
import json
import os

from app.fleet.trade import generate_raider_fleet


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
CATALOG = BALANCE["ships"]
RC = BALANCE["trade"]["route_risk"]


def _power(fleet: dict) -> float:
    return sum(float(CATALOG.get(t, {}).get("attack", 0)) * c for t, c in fleet.items())


# --- Grundverhalten ----------------------------------------------------------

def test_empty_roster_yields_no_raider():
    rc = {**RC, "raid_roster": []}
    assert generate_raider_fleet(100000, rc, CATALOG) == {}


def test_only_known_ships_appear():
    rc = {**RC, "raid_roster": ["light_fighter", "does_not_exist"]}
    out = generate_raider_fleet(100000, rc, CATALOG)
    assert set(out).issubset(set(CATALOG))
    assert "does_not_exist" not in out


def test_deterministic():
    a = generate_raider_fleet(123456, RC, CATALOG)
    b = generate_raider_fleet(123456, RC, CATALOG)
    assert a == b


# --- Skalierung mit dem Frachtwert ------------------------------------------

def test_power_scales_with_cargo_value():
    small = generate_raider_fleet(50000, RC, CATALOG)
    big = generate_raider_fleet(400000, RC, CATALOG)
    assert _power(big) > _power(small)


def test_floor_applies_for_tiny_value():
    # Selbst bei winzigem Frachtwert steht ein Mindest-Raeuber (raid_power_min) -> echter Bericht.
    out = generate_raider_fleet(0, RC, CATALOG)
    assert sum(out.values()) >= 1
    assert _power(out) > 0


def test_cap_limits_power_for_huge_value():
    rc = {**RC, "raid_power_per_value": 0.01, "raid_power_max": 2000}
    out = generate_raider_fleet(10_000_000, rc, CATALOG)
    # Budget waere 100000, gedeckelt auf 2000 -> Kampfwert bleibt in der Naehe des Caps.
    assert _power(out) <= 2000 * 1.0  # Verteilung kann den Cap nicht ueberschreiten


def test_min_overrides_low_per_value():
    rc = {**RC, "raid_power_per_value": 0.0, "raid_power_min": 200}
    out = generate_raider_fleet(100000, rc, CATALOG)
    assert _power(out) > 0  # Floor greift trotz per_value 0
