"""Tests fuer die reinen Logiken von Mining (mine_yield) und Expedition (pick_outcome)."""
from app.fleet.expedition import pick_outcome
from app.fleet.mining import mine_yield


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
