"""Tests fuer Bevoelkerung Phase 3 (Automatisierungs-/Habitattechnik, docs/systems/CREW_PHASE2.md).

Reine Funktionen der economy.service auf Basis der echten balance.json:
- automation_crew_mult / fleet_crew(automation_level): Roboter senken den Crew-Bedarf (Floor).
- population_capacity(habitat_level): Habitattechnik hebt NUR den Wohnhaus-Beitrag.
- habitat_satt_bonus + population_dynamics(satt_workforce_extra): Extra-Bonus nur im Tier 'satt'.
"""
from app.economy.service import (
    automation_crew_mult,
    base_population,
    fleet_crew,
    habitat_satt_bonus,
    population_capacity,
    population_dynamics,
)
from app.platform.balance import get_balance


def _eff() -> dict:
    return get_balance().data["research"]["effects"]


def test_automation_crew_mult_scales_and_floors():
    per = _eff()["automation_crew_reduction_per_level"]
    floor = _eff()["automation_crew_floor"]
    assert automation_crew_mult(0) == 1.0
    assert abs(automation_crew_mult(4) - (1.0 - 4 * per)) < 1e-9
    # Sehr hohe Stufe: nie unter den Floor (Roboter ersetzen die Crew nie komplett).
    assert automation_crew_mult(100) == floor


def test_fleet_crew_with_automation():
    crew = get_balance().data["population"]["crew"]
    ships = {"light_fighter": 10, "cruiser": 5}
    raw = crew["light_fighter"] * 10 + crew["cruiser"] * 5
    assert fleet_crew(ships) == raw  # Default: keine Reduktion
    assert abs(fleet_crew(ships, 2) - raw * automation_crew_mult(2)) < 1e-9
    assert fleet_crew(ships, 2) < raw
    # Autonome Schiffe bleiben 0, auch mit Automatisierung.
    assert fleet_crew({"spy_probe": 100}, 5) == 0.0


def test_population_capacity_habitat_boosts_housing_only():
    h = get_balance().buildings["housing"]
    per = _eff()["habitat_pop_cap_per_level"]
    lvl = 3
    housing_part = h["pop_cap_base"] * lvl * (h["pop_cap_growth"] ** lvl)
    expected = base_population() + housing_part * (1.0 + per * 5)
    assert abs(population_capacity({"housing": lvl}, habitat_level=5) - expected) < 1e-6
    # Ohne Wohnhaus hebt Habitattechnik NICHTS (Grund-Bevoelkerung ist Subsistenz).
    assert population_capacity({}, habitat_level=10) == base_population()


def test_habitat_satt_bonus_capped():
    per = _eff()["habitat_satt_bonus_per_level"]
    cap = _eff()["habitat_satt_bonus_max"]
    assert habitat_satt_bonus(0) == 0.0
    assert abs(habitat_satt_bonus(5) - min(5 * per, cap)) < 1e-9
    assert habitat_satt_bonus(1000) == cap


def test_dynamics_satt_extra_only_when_satt():
    wb = get_balance().data["population"]["workforce_bonus"]
    # satt (r=2.0): Extra-Bonus addiert sich auf den satt-Bonus.
    d = population_dynamics(population=500, food_production=30.0, food_stock=500,
                            pop_cap=2000, satt_workforce_extra=0.05)
    assert d["tier"] == "satt"
    assert abs(d["workforce_mult"] - (1.0 + wb["satt"] + 0.05)) < 1e-9
    # neutral (r=1.1): kein Extra-Bonus.
    d = population_dynamics(population=500, food_production=16.5, food_stock=500,
                            pop_cap=2000, satt_workforce_extra=0.05)
    assert d["tier"] == "neutral"
    assert d["workforce_mult"] == 1.0
    # hungernd (keine Produktion, kein Lager): Malus bleibt unveraendert.
    d = population_dynamics(population=500, food_production=0.0, food_stock=0.0,
                            pop_cap=2000, satt_workforce_extra=0.05)
    assert d["tier"] == "hungernd"
    assert abs(d["workforce_mult"] - (1.0 + wb["hungernd"])) < 1e-9


def test_new_techs_defined_in_balance():
    techs = get_balance().data["research"]["techs"]
    for key in ("automation_tech", "habitat_tech"):
        assert key in techs, f"{key} fehlt in balance.research.techs"
        assert techs[key]["cost"]["metal"] >= 0
        assert techs[key].get("requires"), f"{key} sollte Voraussetzungen haben"
