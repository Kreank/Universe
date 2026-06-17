"""Tests fuer die Nanitenfabrik: senkt Gebaeude-Bauzeit (-25%/Stufe) und Schiff-Bauzeit (-5%/Stufe),
beides multiplikativ. DB-frei (reine Formel-Funktionen, Balance per Pfad geladen)."""
from app.buildings.service import build_seconds
from app.buildings.shipyard import build_seconds_each
from app.platform.balance import get_balance

# Grosse Kosten -> Bauzeit weit ueber min_seconds, damit Verhaeltnisse nicht von Rundung/Floor verfaelscht werden.
_BIG = {"metal": 1_000_000_000, "crystal": 0}


def test_nanite_factory_requires_robot_factory_12():
    cfg = get_balance().buildings["nanite_factory"]
    assert cfg["requires"]["robot_factory"] == 12


def test_building_time_unchanged_at_nanite_zero():
    # Ohne Nanitenfabrik (Stufe 0) identisch zur Basis-Formel (0.75^0 = 1).
    assert build_seconds(_BIG, robot_factory_lvl=5, nanite_lvl=0) == build_seconds(_BIG, robot_factory_lvl=5)


def test_building_time_quarter_off_per_level():
    base = build_seconds(_BIG, robot_factory_lvl=3, nanite_lvl=0)
    one = build_seconds(_BIG, robot_factory_lvl=3, nanite_lvl=1)
    two = build_seconds(_BIG, robot_factory_lvl=3, nanite_lvl=2)
    factor = float(get_balance().data["build_time"]["nanite_building_factor"])
    assert factor == 0.75
    assert abs(one / base - 0.75) < 0.001        # -25% je Stufe
    assert abs(two / base - 0.75 ** 2) < 0.001   # multiplikativ (0.5625)
    assert two < one < base                       # streng schneller je Stufe


def test_ship_time_five_percent_off_per_level():
    base = build_seconds_each(_BIG, building_lvl=4, nanite_lvl=0)
    one = build_seconds_each(_BIG, building_lvl=4, nanite_lvl=1)
    three = build_seconds_each(_BIG, building_lvl=4, nanite_lvl=3)
    factor = float(get_balance().data["build_time"]["nanite_ship_factor"])
    assert factor == 0.95
    assert abs(one / base - 0.95) < 0.001         # -5% je Stufe
    assert abs(three / base - 0.95 ** 3) < 0.001  # multiplikativ
    assert build_seconds_each(_BIG, building_lvl=4, nanite_lvl=0) == build_seconds_each(_BIG, building_lvl=4)


def test_nanite_negative_level_is_safe():
    # Defensive: negatives Level -> wie Stufe 0 (kein Absturz, kein laengerer Bau).
    assert build_seconds(_BIG, robot_factory_lvl=3, nanite_lvl=-2) == build_seconds(_BIG, robot_factory_lvl=3, nanite_lvl=0)
