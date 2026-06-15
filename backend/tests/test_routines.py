"""Tests fuer Farm-Routinen: reine Logik (Cursor-Advance, Forschungs-Limits, Balance-Block).

DB-gebundene Pfade (start_cycle/advance_after_return/loss_check) werden nicht hier, sondern
manuell/integrativ geprueft — die Suite haelt sich an die projektweite Konvention reiner
Logik-Tests."""
from app.fleet.routines import advance_cursor, max_fields_per_route, max_routines
from app.platform.balance import get_balance


# -- Cursor-Logik ---------------------------------------------------------------

def test_cursor_advances_when_field_emptied():
    # Feld 0 leer -> weiter zu Feld 1.
    assert advance_cursor(0, 3, emptied=True) == 1


def test_cursor_stays_when_cargo_full_field_not_empty():
    # Laderaum voll, Feld noch nicht leer -> selbes Feld nochmal.
    assert advance_cursor(0, 3, emptied=False) == 0


def test_cursor_wraps_around_endlessly():
    # Letztes Feld leer -> zurueck zu Feld 0 (endlose Schleife).
    assert advance_cursor(2, 3, emptied=True) == 0


def test_cursor_single_field_loops_on_itself():
    assert advance_cursor(0, 1, emptied=True) == 0
    assert advance_cursor(0, 1, emptied=False) == 0


def test_cursor_empty_route_safe():
    assert advance_cursor(0, 0, emptied=True) == 0


# -- Forschungs-Limits (Default 2, +1 je Stufe) ---------------------------------

def test_default_limits_are_two():
    assert max_routines({}) == 2
    assert max_fields_per_route({}) == 2


def test_fleet_logistics_raises_routine_count():
    assert max_routines({"fleet_logistics": 1}) == 3
    assert max_routines({"fleet_logistics": 5}) == 7


def test_route_planning_raises_fields_per_route():
    assert max_fields_per_route({"route_planning": 1}) == 3
    assert max_fields_per_route({"route_planning": 4}) == 6


def test_limits_are_independent():
    research = {"fleet_logistics": 2, "route_planning": 3}
    assert max_routines(research) == 4
    assert max_fields_per_route(research) == 5


# -- Balance-Block + Techs ------------------------------------------------------

def test_routines_balance_block_present():
    cfg = get_balance().data.get("routines", {})
    assert cfg.get("base_routines") == 2
    assert cfg.get("base_fields_per_route") == 2
    assert cfg.get("routines_research") == "fleet_logistics"
    assert cfg.get("fields_research") == "route_planning"
    assert set(cfg.get("allowed_field_types", [])) == {"asteroid_field", "debris_field"}


def test_routine_techs_repeatable():
    techs = get_balance().techs
    for t in ("fleet_logistics", "route_planning"):
        assert t in techs, f"{t} fehlt in den Forschungen"
        assert techs[t].get("repeatable") is True
