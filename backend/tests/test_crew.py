"""Tests fuer Crew/Manpower (Phase 2, docs/systems/CREW_PHASE2.md) — reine Funktionen.

ship_crew: Crew je Schiff aus balance.population.crew (autonome = 0, Mk2 erbt vom Elternschiff).
fleet_crew: Summe crew*Anzahl einer Flotten-Zusammenstellung.
"""
from app.economy.service import fleet_crew, ship_crew
from app.platform.balance import get_balance


def test_ship_crew_from_map():
    crew = get_balance().data["population"]["crew"]
    assert ship_crew("cruiser") == crew["cruiser"]
    assert ship_crew("battleship") == crew["battleship"]
    assert ship_crew("light_fighter") == crew["light_fighter"]


def test_autonomous_ships_have_zero_crew():
    # Spionagesonde, Solarsatellit, Drohne fliegen ohne Besatzung.
    assert ship_crew("spy_probe") == 0.0
    assert ship_crew("solar_satellite") == 0.0
    assert ship_crew("drone") == 0.0


def test_unknown_ship_defaults_zero():
    assert ship_crew("does_not_exist") == 0.0


def test_mk2_inherits_parent_crew():
    # Mk2-Varianten erben die Crew ihres Elternschiffs (mk2_parent).
    bal = get_balance()
    crew = bal.data["population"]["crew"]
    mk2 = [(name, cfg["mk2_parent"]) for name, cfg in bal.ships.items()
           if isinstance(cfg, dict) and cfg.get("mk2_parent")]
    assert mk2, "Es sollte Mk2-Schiffe mit mk2_parent geben"
    for name, parent in mk2:
        if parent in crew:
            assert ship_crew(name) == crew[parent], f"{name} sollte Crew von {parent} erben"


def test_fleet_crew_sums():
    crew = get_balance().data["population"]["crew"]
    ships = {"light_fighter": 10, "cruiser": 5, "spy_probe": 3}
    expected = crew["light_fighter"] * 10 + crew["cruiser"] * 5  # Sonde = 0
    assert fleet_crew(ships) == expected


def test_fleet_crew_empty():
    assert fleet_crew({}) == 0.0
    assert fleet_crew({"spy_probe": 100, "solar_satellite": 50}) == 0.0
