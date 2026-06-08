"""Tests fuer die reinen Doktrin-Boni-Helfer (datengetrieben aus balance.doctrines)."""
from app.platform.doctrine import (
    combat_attack_mult,
    fleet_slot_bonus,
    is_valid,
    options,
    signature_mult,
)


def test_valid_doctrines():
    assert is_valid("warlord") and is_valid("trader") and is_valid("pirate") and is_valid("pioneer")
    assert not is_valid("foo")
    assert not is_valid(None)


def test_warlord_bonuses():
    assert fleet_slot_bonus("warlord") == 1
    assert abs(combat_attack_mult("warlord") - 1.10) < 1e-9


def test_other_doctrines_no_slot_no_attack():
    for key in ("trader", "pirate", "pioneer"):
        assert fleet_slot_bonus(key) == 0
        assert abs(combat_attack_mult(key) - 1.0) < 1e-9
    # Keine Doktrin -> neutrale Werte.
    assert fleet_slot_bonus(None) == 0
    assert abs(combat_attack_mult(None) - 1.0) < 1e-9


def test_signature_discount_only_for_signature_ships():
    # Freibeuter verguenstigt Piraterie-Schiffe ...
    assert signature_mult("pirate", "interdictor") == (0.85, 0.85)
    # ... aber nicht fremde Linien.
    assert signature_mult("pirate", "battleship") == (1.0, 1.0)
    # Pionier verguenstigt Kolonieschiff staerker.
    assert signature_mult("pioneer", "colony_ship") == (0.80, 0.80)


def test_options_lists_all_four():
    keys = {o["key"] for o in options()}
    assert keys == {"warlord", "trader", "pirate", "pioneer"}
