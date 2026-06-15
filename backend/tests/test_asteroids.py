"""Tests fuer die reine Asteroiden-Logik (Reichtum, Vorrat, Regeneration, Foerderung)."""
import random

from app.universe.asteroids import (
    apply_regen,
    field_capacity,
    mine_from_field,
    roll_richness,
)

_CFG = {
    "richness_tiers": [
        {"name": "karg", "weight": 35, "mult": 0.5},
        {"name": "normal", "weight": 40, "mult": 1.0},
        {"name": "reich", "weight": 18, "mult": 1.8},
        {"name": "ergiebig", "weight": 7, "mult": 3.0},
    ],
    "capacity": {"metal": 240000, "crystal": 120000},
    "regen_ratio_per_hour": 0.03,
}
_YIELD = {"metal": 4000, "crystal": 2000}


def test_roll_richness_returns_valid_tier():
    rng = random.Random(42)
    names = {roll_richness(rng, _CFG)[0] for _ in range(500)}
    assert names <= {"karg", "normal", "reich", "ergiebig"}
    # Ueber viele Rolls sollten die haeufigen Tiers auftauchen.
    assert {"karg", "normal"} <= names


def test_roll_richness_weighted_distribution():
    rng = random.Random(7)
    counts: dict[str, int] = {}
    for _ in range(20000):
        name, _ = roll_richness(rng, _CFG)
        counts[name] = counts.get(name, 0) + 1
    # karg+normal (Gewicht 75) klar haeufiger als reich+ergiebig (Gewicht 25).
    common = counts.get("karg", 0) + counts.get("normal", 0)
    rare = counts.get("reich", 0) + counts.get("ergiebig", 0)
    assert common > rare * 2


def test_field_capacity_scales_with_mult():
    assert field_capacity(1.0, _CFG) == (240000, 120000)
    assert field_capacity(3.0, _CFG) == (720000, 360000)
    assert field_capacity(0.5, _CFG) == (120000, 60000)


def test_apply_regen_adds_and_caps():
    m_max, c_max = 240000.0, 120000.0
    # 10h bei 3%/h = +72000 Metall (von 0).
    m, c = apply_regen(0, 0, m_max, c_max, hours=10, regen_ratio_per_hour=0.03)
    assert abs(m - 72000) < 1
    assert abs(c - 36000) < 1
    # Sehr lange -> Deckel auf Max.
    m2, c2 = apply_regen(200000, 100000, m_max, c_max, hours=1000, regen_ratio_per_hour=0.03)
    assert m2 == m_max and c2 == c_max
    # 0h -> unveraendert.
    assert apply_regen(5, 6, m_max, c_max, hours=0, regen_ratio_per_hour=0.03) == (5, 6)


def test_mine_from_field_fills_cargo():
    # Feld praktisch unbegrenzt -> es wird genau der Frachtraum gefuellt (kommt VOLL zurueck).
    gained, m_rem, c_rem = mine_from_field(1e9, 1e9, cargo_capacity=30_000)
    assert abs((gained["metal"] + gained["crystal"]) - 30_000) < 0.5  # Frachtraum voll
    assert abs(gained["metal"] - 15_000) < 0.5 and abs(gained["crystal"] - 15_000) < 0.5  # 1:1 (Feld 1:1)


def test_mine_from_field_capped_by_reserves():
    # Vorrat kleiner als Frachtraum -> nimmt den ganzen Rest, Feld auf 0.
    gained, m_rem, c_rem = mine_from_field(5000, 3000, cargo_capacity=10_000_000)
    assert gained["metal"] == 5000 and gained["crystal"] == 3000
    assert m_rem == 0 and c_rem == 0


def test_mine_from_field_split_by_field_composition():
    # Knappe Fracht (5000) < Vorrat: Metall/Kristall ANTEILIG zur Feld-Zusammensetzung (4:1).
    gained, m_rem, c_rem = mine_from_field(8000, 2000, cargo_capacity=5000)
    assert abs((gained["metal"] + gained["crystal"]) - 5000) < 0.5  # Fracht voll ausgenutzt
    assert abs(gained["metal"] - 4000) < 0.5 and abs(gained["crystal"] - 1000) < 0.5  # 4:1
    assert abs(m_rem - 4000) < 1 and abs(c_rem - 1000) < 1


def test_mine_from_field_empty_field_yields_nothing():
    gained, m_rem, c_rem = mine_from_field(0, 0, cargo_capacity=10_000)
    assert gained == {"metal": 0.0, "crystal": 0.0}
    assert m_rem == 0 and c_rem == 0
