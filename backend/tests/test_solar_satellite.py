"""Tests fuer die temperaturabhaengige Solarsatelliten-Energie (OGame-Mechanik)."""
from app.economy.service import compute_rates, solar_satellite_energy
from app.platform.balance import get_balance


def _per_sat(temp_max: int) -> int:
    cfg = get_balance().ships["solar_satellite"]["energy_prod"]
    return max(0, (temp_max + int(cfg["temp_offset"])) // int(cfg["divisor"]))


def test_zero_satellites_zero_energy():
    assert solar_satellite_energy(temp_max=100, count=0) == 0.0


def test_hot_planet_produces_more_than_cold():
    # Sonnennah (heiss) > sonnenfern (kalt) bei gleicher Stueckzahl.
    hot = solar_satellite_energy(temp_max=220, count=10)
    cold = solar_satellite_energy(temp_max=-40, count=10)
    assert hot > cold > 0


def test_matches_ogame_formula():
    # floor((temp_max + offset) / divisor) * count.
    assert solar_satellite_energy(temp_max=220, count=7) == _per_sat(220) * 7
    assert solar_satellite_energy(temp_max=-40, count=3) == _per_sat(-40) * 3


def test_never_negative_on_extreme_cold():
    # Hypothetisch sehr kalt -> nie negative Energie.
    assert solar_satellite_energy(temp_max=-1000, count=5) == 0.0


def test_satellites_raise_produced_energy_in_compute_rates():
    buildings = {"metal_mine": 5, "crystal_mine": 5, "solar_plant": 8}
    _r0, e0, _c = compute_rates(buildings, temp_max=200, energy_tech=0)
    _r1, e1, _c = compute_rates(buildings, temp_max=200, energy_tech=0, solar_satellites=20)
    assert e1["produced"] > e0["produced"]
    expected_gain = solar_satellite_energy(200, 20)
    assert abs((e1["produced"] - e0["produced"]) - expected_gain) < 0.05


def test_satellites_help_against_deficit():
    # Energiedefizit: Satelliten heben den Drossel-Faktor.
    buildings = {"metal_mine": 12}  # kein Kraftwerk -> Defizit
    _r0, e0, _c = compute_rates(buildings, temp_max=220, energy_tech=0)
    _r1, e1, _c = compute_rates(buildings, temp_max=220, energy_tech=0, solar_satellites=30)
    assert e1["factor"] > e0["factor"]
