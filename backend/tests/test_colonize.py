"""Tests fuer die reine Kolonisierungs-Entscheidung (colonize_check)."""
from app.planets.colonize import colonize_check


def test_colonize_ok_on_empty_cell():
    assert colonize_check(occupant_type="empty", planet_count=1, max_planets=9, colony_ships=1) == (True, "ok")


def test_colonize_ok_on_debris_only_cell():
    # Reines Truemmerfeld (kein Eigentuemer) darf besiedelt werden.
    assert colonize_check("debris", planet_count=2, max_planets=9, colony_ships=2)[0] is True


def test_colonize_blocked_when_occupied():
    assert colonize_check("player", 1, 9, 1) == (False, "besetzt")
    assert colonize_check("npc", 1, 9, 1) == (False, "besetzt")


def test_colonize_blocked_at_limit():
    assert colonize_check("empty", planet_count=9, max_planets=9, colony_ships=1) == (False, "limit_erreicht")


def test_colonize_requires_colony_ship():
    assert colonize_check("empty", 1, 9, colony_ships=0) == (False, "kein_kolonieschiff")
