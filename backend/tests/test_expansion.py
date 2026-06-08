"""Tests fuer die reine NPC-Expansions-Logik (should_expand, first_free_position)."""
from app.npc.expansion import first_free_position, should_expand

CFG = {
    "enabled_profiles": ["expansive"],
    "min_resources": {"metal": 45000, "crystal": 30000, "deuterium": 10000},
    "max_per_system": 4,
}
RICH = {"metal": 50000, "crystal": 31000, "deuterium": 12000}
POOR = {"metal": 50000, "crystal": 20000, "deuterium": 12000}  # Kristall unter Schwelle


def test_expand_when_rich_and_room():
    assert should_expand("expansive", CFG, RICH, system_npc_count=2) is True


def test_no_expand_wrong_profile():
    assert should_expand("defensive", CFG, RICH, system_npc_count=0) is False
    assert should_expand("aggressive", CFG, RICH, system_npc_count=0) is False


def test_no_expand_when_poor():
    assert should_expand("expansive", CFG, POOR, system_npc_count=0) is False


def test_no_expand_when_system_full():
    assert should_expand("expansive", CFG, RICH, system_npc_count=4) is False


def test_first_free_position():
    assert first_free_position({1, 2, 3}, 15) == 4
    assert first_free_position(set(), 15) == 1
    assert first_free_position(set(range(1, 16)), 15) is None
