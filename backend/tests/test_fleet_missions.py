"""Tests fuer die reinen Logiken von Mining (mine_yield), Expedition (pick_outcome) und
Reise-Antrieben (ship_speed/slowest_ship_speed/flight_seconds)."""
from app.fleet.expedition import pick_outcome
from app.fleet.mining import mine_yield
from app.fleet.service import carrier_drone_capacity, flight_seconds, ship_speed, slowest_ship_speed

_CARRIER_CFG = {
    "capacity_by_type": {"carrier": 8, "deathstar": 50},
    "deathstar_capacity_per_computer_level": 5,
    "deathstar_capacity_max": 100,
}


def test_carrier_drone_capacity_per_type_and_deathstar_research():
    cap = carrier_drone_capacity
    assert cap({"carrier": 3}, 0, _CARRIER_CFG) == 24            # 3 Traeger x 8
    assert cap({"deathstar": 1}, 0, _CARRIER_CFG) == 50          # Todesstern Basis 50
    assert cap({"deathstar": 1}, 4, _CARRIER_CFG) == 70          # +5 je computer_tech
    assert cap({"deathstar": 1}, 10, _CARRIER_CFG) == 100        # erreicht Maximum
    assert cap({"deathstar": 1}, 30, _CARRIER_CFG) == 100        # gedeckelt
    assert cap({"deathstar": 2, "carrier": 1}, 4, _CARRIER_CFG) == 70 * 2 + 8   # gemischt
    assert cap({"light_fighter": 100}, 5, _CARRIER_CFG) == 0     # keine Traeger
    # Fallback auf drone_capacity (alte Config ohne capacity_by_type).
    assert carrier_drone_capacity({"carrier": 2}, 0, {"drone_capacity": 8}) == 16


def test_mine_yield_scales_with_miners_and_caps_at_capacity():
    yc = {"metal": 4000, "crystal": 2000}
    # 1 Bergbauschiff, viel Kapazitaet -> voller Ertrag.
    assert mine_yield(1, yc, 15000) == {"metal": 4000.0, "crystal": 2000.0}
    # 3 Bergbauschiffe -> 3x Ertrag.
    assert mine_yield(3, yc, 100000) == {"metal": 12000.0, "crystal": 6000.0}
    # Knappe Kapazitaet: Metall zuerst, dann Rest-Kristall.
    assert mine_yield(1, yc, 5000) == {"metal": 4000.0, "crystal": 1000.0}
    assert mine_yield(1, yc, 0) == {"metal": 0.0, "crystal": 0.0}


def test_pick_outcome_selects_by_weight_band():
    outcomes = [
        {"weight": 35, "type": "resources"},
        {"weight": 20, "type": "ships"},
        {"weight": 30, "type": "nothing"},
        {"weight": 15, "type": "hazard"},
    ]
    assert pick_outcome(outcomes, 0)["type"] == "resources"      # [0, 35)
    assert pick_outcome(outcomes, 34.9)["type"] == "resources"
    assert pick_outcome(outcomes, 35)["type"] == "ships"         # [35, 55)
    assert pick_outcome(outcomes, 54.9)["type"] == "ships"
    assert pick_outcome(outcomes, 55)["type"] == "nothing"       # [55, 85)
    assert pick_outcome(outcomes, 85)["type"] == "hazard"        # [85, 100)
    assert pick_outcome(outcomes, 99.9)["type"] == "hazard"


def test_ship_speed_scales_with_drive_research():
    # Ohne Forschung: Grundtempo aus balance.ships.
    assert ship_speed("light_fighter", {}) == 12500.0
    assert ship_speed("light_fighter", None) == 12500.0
    # light_fighter fliegt mit Verbrennungsantrieb (+10% je Stufe): Stufe 5 -> 12500*1.5.
    assert ship_speed("light_fighter", {"combustion_drive": 5}) == 18750.0
    # battleship fliegt mit Hyperraumantrieb (+30% je Stufe): Stufe 3 -> 10000*1.9.
    assert ship_speed("battleship", {"hyperspace_drive": 3}) == 19000.0
    # escort_frigate hat keinen Reiseantrieb in requires -> kein Bonus, egal welche Forschung.
    assert ship_speed("escort_frigate", {"combustion_drive": 10, "impulse_drive": 10}) == 10000.0


def test_slowest_ship_speed_uses_research_per_ship():
    fleet = {"light_fighter": 1, "battleship": 1}
    # Ohne Forschung bestimmt das Schlachtschiff (10000) das Flottentempo.
    assert slowest_ship_speed(fleet, {}) == 10000.0
    # Nur Verbrennung erforscht -> Schlachtschiff bleibt Bremser.
    assert slowest_ship_speed(fleet, {"combustion_drive": 5}) == 10000.0
    # Hyperraum 3 hebt das Schlachtschiff (19000) ueber den Jaeger (12500) -> Jaeger bremst.
    assert slowest_ship_speed(fleet, {"hyperspace_drive": 3}) == 12500.0


def test_drive_research_reduces_eta():
    fleet = {"light_fighter": 1}
    distance = 95
    base = flight_seconds(distance, slowest_ship_speed(fleet, {}), 100)
    fast = flight_seconds(distance, slowest_ship_speed(fleet, {"combustion_drive": 5}), 100)
    # Hoehere Antriebsstufe -> schnellere Flotte -> kuerzere Flugzeit.
    assert fast < base
