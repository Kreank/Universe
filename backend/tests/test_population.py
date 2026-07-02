"""Tests fuer Bevoelkerung & Nahrung (Phase 1, docs/systems/POPULATION_PHASE1.md).

Reine Funktionen der economy.service auf Basis der echten balance.json (get_balance):
- farm_food_production / population_capacity / food_capacity (Formeln + Energie-Drossel)
- governor_satisfaction_shift (Archetyp-Verschiebung)
- population_dynamics (Zufriedenheits-Stufen, Arbeitskraft-Bonus, Wachstum/Schrumpf)
"""
from app.economy.service import (
    farm_food_production,
    food_capacity,
    governor_satisfaction_shift,
    population_capacity,
    population_dynamics,
)
from app.platform.balance import get_balance


def test_farm_food_production_scales_and_throttles():
    bal = get_balance()
    cfg = bal.buildings["farm"]
    lvl = 5
    expected = cfg["food_prod_base"] * lvl * (cfg["food_prod_growth"] ** lvl)
    assert abs(farm_food_production({"farm": lvl}, 1.0) - expected) < 1e-6
    # Energie-Drossel halbiert die Nahrung (wie bei den Minen).
    assert abs(farm_food_production({"farm": lvl}, 0.5) - expected * 0.5) < 1e-6
    # Ohne Farm keine Nahrung.
    assert farm_food_production({}, 1.0) == 0.0


def test_population_capacity_and_food_capacity():
    bal = get_balance()
    h = bal.buildings["housing"]
    base = float(bal.data["population"]["base_pop"])
    lvl = 3
    # Phase 2: pop_cap = Grund-Bevoelkerung + Wohnhaus-Beitrag.
    assert abs(population_capacity({"housing": lvl})
               - (base + h["pop_cap_base"] * lvl * (h["pop_cap_growth"] ** lvl))) < 1e-6
    assert population_capacity({}) == base  # ohne Wohnhaus = Grund-Bevoelkerung
    pc = bal.data["population"]
    assert food_capacity({"farm": 4}) == pc["food_base_cap"] + 4 * pc["food_cap_per_farm_level"]
    assert food_capacity({}) == pc["food_base_cap"]


def test_governor_satisfaction_shift():
    # Verwaltung/Handel heben, Kampf senkt, unbekannt/None = 0.
    assert governor_satisfaction_shift("admin") > 0
    assert governor_satisfaction_shift("combat") < 0
    assert governor_satisfaction_shift(None) == 0.0
    assert governor_satisfaction_shift("does_not_exist") == 0.0


# base_pop = 200; nur Bevoelkerung DARUEBER isst/verhungert. Tests nutzen pop=500 (eaters=300).

def test_dynamics_satt_gives_bonus_and_growth():
    # r=2.0 -> satt: +15% Arbeitskraft, Bevoelkerung waechst Richtung Cap.
    d = population_dynamics(population=500, food_production=30.0, food_stock=500, pop_cap=2000)
    assert d["tier"] == "satt"
    assert abs(d["workforce_mult"] - 1.15) < 1e-9
    assert d["pop_rate"] > 0


def test_dynamics_neutral_small_surplus():
    # r=1.1 (<1.2 satt-Schwelle, >=1) -> neutral: kein Bonus, kein Wachstum.
    d = population_dynamics(population=500, food_production=16.5, food_stock=500, pop_cap=2000)
    assert d["tier"] == "neutral"
    assert d["workforce_mult"] == 1.0
    assert d["pop_rate"] == 0.0


def test_dynamics_eating_reserves_not_yet_starving():
    # Unterdeckung (r<1) ABER Nahrung im Lager -> zehrt Reserven: neutral, kein Schrumpf, food_rate<0.
    d = population_dynamics(population=500, food_production=10.0, food_stock=500, pop_cap=2000)
    assert d["tier"] == "neutral"
    assert d["pop_rate"] == 0.0
    assert d["food_rate"] < 0


def test_dynamics_starving_shrinks_toward_base_and_penalizes():
    # Unterdeckung UND leeres Nahrungslager -> hungernd: -10% Arbeitskraft, Schrumpf NUR der
    # Ueber-Basis-Bevoelkerung (nie unter base_pop).
    d = population_dynamics(population=500, food_production=10.0, food_stock=0.0, pop_cap=2000)
    assert d["tier"] == "hungernd"
    assert abs(d["workforce_mult"] - 0.90) < 1e-9
    assert d["pop_rate"] < 0
    # Schrumpf bezieht sich auf (pop - base_pop) = 300, nicht auf die volle Bevoelkerung.
    assert abs(d["pop_rate"] - (-(500 - 200) * 0.06)) < 1e-9


def test_dynamics_base_population_subsists_without_farm():
    # Genau auf Grund-Bevoelkerung, keine Farm: Basis ernaehrt sich selbst -> neutral, stabil.
    d = population_dynamics(population=200, food_production=0.0, food_stock=0.0, pop_cap=200)
    assert d["tier"] == "neutral"
    assert d["workforce_mult"] == 1.0
    assert d["pop_rate"] == 0.0


def test_dynamics_recovery_below_base():
    # Unter der Grund-Bevoelkerung (z.B. Crew im Kampf verloren) -> waechst ohne Farm zur Basis zurueck.
    d = population_dynamics(population=100, food_production=0.0, food_stock=0.0, pop_cap=200)
    assert d["tier"] == "neutral"
    assert d["workforce_mult"] == 1.0
    assert d["pop_rate"] > 0
    assert abs(d["pop_rate"] - (200 - 100) * 0.05) < 1e-9


def test_dynamics_governor_shift_promotes_neutral_to_satt():
    # r=1.1 ist neutral; ein Verwaltungs-Gouverneur (+0.15) hebt es ueber die satt-Schwelle (1.2).
    shift = governor_satisfaction_shift("admin")
    d = population_dynamics(population=500, food_production=16.5, food_stock=500, pop_cap=2000, satisfaction_shift=shift)
    assert d["tier"] == "satt"
    assert d["workforce_mult"] > 1.0
