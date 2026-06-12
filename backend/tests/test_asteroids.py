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


def test_mine_from_field_richness_scales_yield():
    cap = 10_000_000  # Fracht praktisch unbegrenzt
    poor, _m, _c = mine_from_field(1, _YIELD, 0.5, 1e9, 1e9, cap)
    rich, _m, _c = mine_from_field(1, _YIELD, 3.0, 1e9, 1e9, cap)
    assert rich["metal"] == 4000 * 3.0
    assert poor["metal"] == 4000 * 0.5
    assert rich["metal"] > poor["metal"]


def test_mine_from_field_depletes_stock():
    # Vorrat kleiner als gewuenschter Ertrag -> nimmt nur den Rest, Feld auf 0.
    gained, m_rem, c_rem = mine_from_field(10, _YIELD, 1.0, metal_remaining=5000,
                                           crystal_remaining=3000, cargo_capacity=10_000_000)
    assert gained["metal"] == 5000  # Restvorrat begrenzt (Wunsch waere 40000)
    assert gained["crystal"] == 3000
    assert m_rem == 0 and c_rem == 0


def test_mine_from_field_capped_by_cargo_metal_first():
    # Knappe Fracht (5000): Metall zuerst voll, Rest fuer Kristall.
    gained, m_rem, c_rem = mine_from_field(1, _YIELD, 1.0, metal_remaining=1e9,
                                           crystal_remaining=1e9, cargo_capacity=5000)
    assert gained["metal"] == 4000
    assert gained["crystal"] == 1000
    # Vorrat wurde um die Foerderung reduziert.
    assert abs(m_rem - (1e9 - 4000)) < 1
    assert abs(c_rem - (1e9 - 1000)) < 1


def test_mine_from_field_empty_field_yields_nothing():
    gained, m_rem, c_rem = mine_from_field(5, _YIELD, 2.0, 0, 0, cargo_capacity=10_000)
    assert gained == {"metal": 0.0, "crystal": 0.0}
    assert m_rem == 0 and c_rem == 0
