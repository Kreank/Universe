"""Tests fuer Treibstoff-Tank-Reichweite (Hin+Rueck) und Round-trip-Spritkosten."""
import math

from app.fleet.service import fleet_max_range, fuel_cost, ship_range
from app.platform.balance import get_balance


def _expected_range(typ: str, round_trip: bool) -> float:
    bal = get_balance()
    cfg = bal.ships[typ]
    sf = bal.fleet["speed_factor"]
    fpu = bal.fleet["fuel_per_distance_unit"]
    legs = 2 if round_trip else 1
    return cfg["fuel_tank"] * sf / (cfg["fuel"] * fpu * legs)


def test_ship_range_matches_formula():
    for typ in ("spy_probe", "battleship", "colony_ship", "light_fighter"):
        assert abs(ship_range(typ, round_trip=True) - _expected_range(typ, True)) < 1e-6


def test_round_trip_halves_range():
    # Einfache Strecke = doppelte Round-trip-Reichweite.
    assert abs(ship_range("battleship", False) - 2 * ship_range("battleship", True)) < 1e-6


def test_immobile_ship_has_infinite_range():
    # Solarsatellit (fuel=0) ist ortsfest -> keine Reichweiten-Begrenzung.
    assert ship_range("solar_satellite") == float("inf")


def test_role_ordering_scouts_and_haulers_outrange_fighters():
    # Sonde/Transporter/Kolonie kommen weiter als leichte Jaeger/Abfangjaeger.
    r = lambda t: ship_range(t, True)
    assert r("spy_probe") > r("battleship") > r("light_fighter")
    assert r("colony_ship") > r("interceptor")


def test_fleet_max_range_picks_weakest_ship():
    # Gemischte Flotte: das schwaechste Schiff (light_fighter) begrenzt die Reichweite.
    ships = {"battleship": 10, "light_fighter": 1}
    rng, limiting = fleet_max_range(ships, round_trip=True)
    assert limiting == "light_fighter"
    assert abs(rng - ship_range("light_fighter", True)) < 1e-6


def test_fleet_max_range_ignores_immobile():
    # Solarsatellit zaehlt nicht in die Reichweite (kann ohnehin nicht fliegen).
    ships = {"battleship": 5, "solar_satellite": 3}
    rng, limiting = fleet_max_range(ships, round_trip=True)
    assert limiting == "battleship"


def test_fleet_max_range_empty_is_infinite():
    rng, limiting = fleet_max_range({}, round_trip=True)
    assert rng == float("inf") and limiting is None


def test_fuel_cost_round_trip_doubles():
    ships = {"battleship": 3}
    one = fuel_cost(ships, 5000, round_trip=False)
    two = fuel_cost(ships, 5000, round_trip=True)
    # Verdopplung (bis auf das ceil/min(1)-Rauschen).
    assert abs(two - 2 * one) <= 1


def test_fuel_cost_scales_with_distance_and_count():
    base = fuel_cost({"battleship": 1}, 1000)
    assert fuel_cost({"battleship": 1}, 2000) > base
    assert fuel_cost({"battleship": 2}, 1000) > base


def test_battleship_cannot_round_trip_across_galaxy_boundary():
    # Schlachtschiff ist galaxie-weit, aber NICHT intergalaktisch (Hin+Rueck).
    bal = get_balance()
    inter_galaxy = bal.fleet["distance"]["inter_galaxy_per_galaxy"]  # 40000
    assert ship_range("battleship", round_trip=True) < inter_galaxy
    # Kolonieschiff hingegen schafft den Galaxienwechsel.
    assert ship_range("colony_ship", round_trip=True) >= inter_galaxy
