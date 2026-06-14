"""Tests fuer Wirtschafts-Endgame: Foerdertechnik (Minen-Boost) + Terraforming (Bauplaetze)."""
from types import SimpleNamespace

from app.buildings.service import effective_fields_max
from app.economy.service import compute_rates


def _planet(planet_type="planet", fields_max=100):
    return SimpleNamespace(planet_type=planet_type, fields_max=fields_max)


def test_extraction_tech_boosts_metal_rate():
    bld = {"metal_mine": 10, "crystal_mine": 8, "solar_plant": 12}
    base, _e, _c = compute_rates(bld, temp_max=40, energy_tech=0)
    boosted, _e2, _c2 = compute_rates(bld, temp_max=40, energy_tech=0, extraction_level=10)
    assert boosted["metal"] > base["metal"]


def test_extraction_mastery_stacks_on_top():
    bld = {"metal_mine": 10, "crystal_mine": 8, "solar_plant": 12}
    tech_only, _, _ = compute_rates(bld, temp_max=40, energy_tech=0, extraction_level=10)
    plus_mastery, _, _ = compute_rates(
        bld, temp_max=40, energy_tech=0, extraction_level=10, extraction_mastery_level=20
    )
    assert plus_mastery["metal"] > tech_only["metal"]


def test_terraforming_adds_fields_per_level():
    p = _planet(fields_max=100)
    assert effective_fields_max(p, {}, terraforming_level=0) == 100
    assert effective_fields_max(p, {}, terraforming_level=3) == 115  # +5*3


def test_terraforming_does_not_affect_moons():
    moon = _planet(planet_type="moon")
    # Mond nutzt moon_base-Logik, ignoriert Terraforming.
    assert effective_fields_max(moon, {"moon_base": 0}, terraforming_level=5) == \
        effective_fields_max(moon, {"moon_base": 0}, terraforming_level=0)
