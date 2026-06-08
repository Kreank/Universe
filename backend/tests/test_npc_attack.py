"""Tests fuer die reine NPC-Angriffs-Logik (fleet_power, select_commit_fleet, can_attack)."""
from app.npc.attack import can_attack, fleet_power, select_commit_fleet

CATALOG = {
    "light_fighter": {"attack": 50},
    "cruiser": {"attack": 400},
    "spy_probe": {"attack": 0},
}
CFG = {"enabled_profiles": ["aggressive"], "min_fleet_power": 4000, "cooldown_seconds": 10800}


def test_fleet_power_sums_attack_times_count():
    assert fleet_power({"light_fighter": 10, "cruiser": 5}, CATALOG) == 10 * 50 + 5 * 400
    assert fleet_power({"spy_probe": 99}, CATALOG) == 0
    assert fleet_power({}, CATALOG) == 0


def test_select_commit_fleet_floors_fraction_and_drops_zeros():
    # 0.6: 10->6, 5->3, 1->0 (faellt raus).
    assert select_commit_fleet({"light_fighter": 10, "cruiser": 5, "spy_probe": 1}, 0.6) == {
        "light_fighter": 6, "cruiser": 3,
    }
    assert select_commit_fleet({}, 0.6) == {}


def test_can_attack_requires_profile_power_and_cooldown():
    # Genug Power, kein vorheriger Angriff -> ok.
    assert can_attack("aggressive", CFG, 6000, None) is True
    # Falsches Profil.
    assert can_attack("defensive", CFG, 6000, None) is False
    assert can_attack("expansive", CFG, 6000, None) is False
    # Zu schwach.
    assert can_attack("aggressive", CFG, 3000, None) is False
    # Cooldown nicht abgelaufen.
    assert can_attack("aggressive", CFG, 6000, 3600) is False
    # Cooldown abgelaufen.
    assert can_attack("aggressive", CFG, 6000, 20000) is True
