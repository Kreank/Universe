"""Tankschiff-Reichweite (2026-06-22): solange ein Tankschiff mitfliegt, wird der Sprit der
Flotte gebuendelt (fleet_max_range) statt vom schwaechsten Schiff gedeckelt. Nutzt die reale
balance.json (get_balance liest BALANCE_PATH im Testcontainer)."""
from app.fleet.service import _fleet_has_tanker, fleet_max_range, ship_range


def test_no_tanker_uses_weakest_ship():
    rng, limiting = fleet_max_range({"light_fighter": 10}, round_trip=True)
    assert limiting == "light_fighter"
    assert abs(rng - ship_range("light_fighter", True)) < 1e-6


def test_tanker_detected():
    assert _fleet_has_tanker({"light_fighter": 5, "tanker": 1}) is True
    assert _fleet_has_tanker({"light_fighter": 5}) is False
    assert _fleet_has_tanker({"tanker": 0}) is False


def test_tanker_extends_range_for_short_legged_ships():
    base, _ = fleet_max_range({"light_fighter": 100}, round_trip=True)
    pooled, limiting = fleet_max_range({"light_fighter": 100, "tanker": 1}, round_trip=True)
    # Mit Tankschiff kein einzelnes Limit-Schiff mehr, und die Reichweite steigt deutlich.
    assert limiting is None
    assert pooled > base


def test_pooled_never_below_min():
    # Heterogene Flotte: kurzatmige Jaeger + langer Schlachtschiff-Tank + Tankschiff.
    fleet = {"light_fighter": 50, "battleship": 10, "tanker": 1}
    pooled, _ = fleet_max_range(fleet, round_trip=True)
    weakest = min(ship_range(t, True) for t in fleet)
    assert pooled >= weakest


def test_more_tankers_more_range():
    one, _ = fleet_max_range({"light_fighter": 500, "tanker": 1}, round_trip=True)
    five, _ = fleet_max_range({"light_fighter": 500, "tanker": 5}, round_trip=True)
    assert five > one
