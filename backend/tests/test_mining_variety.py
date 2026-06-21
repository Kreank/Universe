"""Tests fuer die Bergbau-Erweiterungen (reine, DB-/RNG-kontrollierte Logik):

- Asteroiden-KOMPOSITION: gewichtete Variante verschiebt das Metall:Kristall-Verhaeltnis.
- field_capacity mit Kompositions-Multiplikatoren.
- Deuterium-Zufalls-Fund: chance=1 -> immer im Bereich, chance=0 -> nie; Forschung
  (deuterium_prospecting) erhoeht Chance UND Menge.
"""
import random

from app.fleet.mining import deuterium_params, roll_deuterium_find
from app.universe.asteroids import field_capacity, roll_composition

_AST_CFG = {
    "capacity": {"metal": 240000, "crystal": 120000},
    "composition_variants": [
        {"name": "metal_rich", "weight": 30, "metal_mult": 2.0, "crystal_mult": 0.5},
        {"name": "balanced", "weight": 40, "metal_mult": 1.0, "crystal_mult": 1.0},
        {"name": "crystal_rich", "weight": 30, "metal_mult": 0.5, "crystal_mult": 2.0},
    ],
}

_MINING_CFG = {
    "deuterium_find_chance": 0.15,
    "deuterium_find_min": 0.02,
    "deuterium_find_max": 0.06,
    "deuterium_chance_cap": 0.9,
}

_EFFECTS = {
    "deuterium_chance_bonus_per_level": 0.25,
    "deuterium_yield_bonus_per_level": 0.15,
}


# -- Komposition ----------------------------------------------------------------

def test_roll_composition_returns_valid_variant():
    rng = random.Random(1)
    names = {roll_composition(rng, _AST_CFG)[0] for _ in range(500)}
    assert names <= {"metal_rich", "balanced", "crystal_rich"}
    assert {"metal_rich", "crystal_rich"} <= names


def test_roll_composition_produces_distinct_ratios():
    """Ueber viele Rolls treten BEIDE Extreme auf: ein Feld mit metal>crystal und eins mit
    crystal>metal -> die Komposition erzeugt wirklich verschiedene Verhaeltnisse."""
    rng = random.Random(7)
    saw_metal_heavy = saw_crystal_heavy = False
    for _ in range(2000):
        name, m_mult, c_mult = roll_composition(rng, _AST_CFG)
        metal, crystal = field_capacity(1.0, _AST_CFG, m_mult, c_mult)
        if name == "metal_rich":
            assert metal > crystal  # deutlich metalllastig
            saw_metal_heavy = True
        elif name == "crystal_rich":
            assert crystal > metal  # deutlich kristalllastig
            saw_crystal_heavy = True
        elif name == "balanced":
            assert metal == 240000 and crystal == 120000  # = reine richness-Skalierung
    assert saw_metal_heavy and saw_crystal_heavy


def test_field_capacity_applies_composition_mults():
    # Default 1.0/1.0 -> unveraendert (Alt-Verhalten).
    assert field_capacity(1.0, _AST_CFG) == (240000, 120000)
    # metal_rich (2.0/0.5): Metall verdoppelt, Kristall halbiert.
    assert field_capacity(1.0, _AST_CFG, 2.0, 0.5) == (480000, 60000)
    # crystal_rich kombiniert mit Reichtum 3.0.
    assert field_capacity(3.0, _AST_CFG, 0.5, 2.0) == (360000, 720000)


def test_roll_composition_falls_back_without_block():
    rng = random.Random(3)
    name, m, c = roll_composition(rng, {})
    assert name == "balanced" and m == 1.0 and c == 1.0


# -- Deuterium-Fund -------------------------------------------------------------

def test_deuterium_find_always_when_chance_one():
    rng = random.Random(11)
    for _ in range(200):
        amt = roll_deuterium_find(rng, ore_total=10000, chance=1.0,
                                  min_frac=0.02, max_frac=0.06, yield_mult=1.0)
        # Fund im erwarteten Bereich 2%..6% von 10000 = 200..600.
        assert 200.0 <= amt <= 600.0


def test_deuterium_find_never_when_chance_zero():
    rng = random.Random(11)
    for _ in range(200):
        assert roll_deuterium_find(rng, ore_total=10000, chance=0.0,
                                   min_frac=0.02, max_frac=0.06) == 0.0


def test_deuterium_find_zero_without_ore():
    rng = random.Random(5)
    assert roll_deuterium_find(rng, ore_total=0, chance=1.0, min_frac=0.02, max_frac=0.06) == 0.0


def test_deuterium_find_frequency_matches_chance():
    rng = random.Random(99)
    hits = sum(
        1 for _ in range(5000)
        if roll_deuterium_find(rng, 10000, chance=0.3, min_frac=0.02, max_frac=0.06) > 0
    )
    # ~30% Fund-Rate (Toleranzband).
    assert 0.25 < hits / 5000 < 0.35


def test_deuterium_params_base_level_zero():
    dp = deuterium_params(0, _MINING_CFG, _EFFECTS)
    assert dp["chance"] == 0.15
    assert dp["yield_mult"] == 1.0
    assert dp["min_frac"] == 0.02 and dp["max_frac"] == 0.06


def test_deuterium_params_research_increases_chance_and_yield():
    base = deuterium_params(0, _MINING_CFG, _EFFECTS)
    lvl3 = deuterium_params(3, _MINING_CFG, _EFFECTS)
    # Chance: 0.15 x (1 + 0.25*3) = 0.15 x 1.75 = 0.2625
    assert abs(lvl3["chance"] - 0.2625) < 1e-9
    assert lvl3["chance"] > base["chance"]
    # Menge: 1 + 0.15*3 = 1.45
    assert abs(lvl3["yield_mult"] - 1.45) < 1e-9
    assert lvl3["yield_mult"] > base["yield_mult"]


def test_deuterium_params_chance_capped():
    # Sehr hohe Stufe -> Chance gedeckelt bei chance_cap (0.9).
    dp = deuterium_params(100, _MINING_CFG, _EFFECTS)
    assert dp["chance"] == 0.9


def test_research_yields_more_deuterium_on_average():
    """Hoehere Forschung -> im Mittel mehr Deuterium pro Fund (yield_mult skaliert die Menge)."""
    def avg_find(level: int) -> float:
        dp = deuterium_params(level, _MINING_CFG, _EFFECTS)
        rng = random.Random(level + 1)
        # chance=1 erzwingen -> nur die Mengen-Skalierung messen.
        vals = [roll_deuterium_find(rng, 10000, 1.0, dp["min_frac"], dp["max_frac"], dp["yield_mult"])
                for _ in range(3000)]
        return sum(vals) / len(vals)
    assert avg_find(4) > avg_find(0)
