"""Tests fuer die reine Recycler-Harvest-Logik (Truemmer einsammeln, frachtbegrenzt)."""
from app.fleet.harvest import harvest_split


def test_harvest_collects_all_when_capacity_suffices():
    debris = {"metal": 3000.0, "crystal": 2000.0}
    collected, rest = harvest_split(debris, capacity=10000)
    assert collected == {"metal": 3000.0, "crystal": 2000.0}
    assert rest == {"metal": 0.0, "crystal": 0.0}


def test_harvest_fills_metal_first_then_crystal():
    debris = {"metal": 3000.0, "crystal": 2000.0}
    # Kapazitaet 4000: 3000 Metall voll, dann 1000 Kristall.
    collected, rest = harvest_split(debris, capacity=4000)
    assert collected == {"metal": 3000.0, "crystal": 1000.0}
    assert rest == {"metal": 0.0, "crystal": 1000.0}


def test_harvest_zero_capacity_collects_nothing():
    debris = {"metal": 500.0, "crystal": 500.0}
    collected, rest = harvest_split(debris, capacity=0)
    assert collected == {"metal": 0.0, "crystal": 0.0}
    assert rest == {"metal": 500.0, "crystal": 500.0}


def test_harvest_handles_missing_keys():
    collected, rest = harvest_split({"metal": 100.0}, capacity=50)
    assert collected == {"metal": 50.0, "crystal": 0.0}
    assert rest == {"metal": 50.0, "crystal": 0.0}
