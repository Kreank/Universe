"""Verifiziert den Kampf-Simulator (POST /api/combat/simulate).

Geprueft werden zwei DB-/Auth-freie Pfade:
- die reine Validierungs-/Bereinigungsfunktion ``_prepare_sim_input`` (Caps, unbekannte
  Typen, 0-Filter, Mindesteinheiten) und
- die Ergebnis-Form, die der Handler aus ``simulate_battle`` ableitet (gleiche Keys wie
  der Viewer erwartet).
"""
import json
import os

import pytest
from fastapi import HTTPException

from app.combat.engine import simulate_battle
from app.combat.router import MAX_SIM_UNITS, _prepare_sim_input


def _load_balance() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(6):
        candidate = os.path.join(d, "shared", "balance.json")
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                return json.load(fh)
        d = os.path.dirname(d)
    raise FileNotFoundError("balance.json nicht gefunden")


BALANCE = _load_balance()

# Schluessel, die der Frontend-Viewer (CombatReport) aus der Sim-Antwort liest.
RESULT_KEYS = (
    "seed", "rounds", "winner",
    "attacker_initial", "defender_initial",
    "attacker_survivors", "defender_survivors",
    "attacker_losses", "defender_losses",
    "attacker_fled", "defender_fled",
    "attacker_captured", "defender_captured",
    "attacker_drive_disabled", "defender_drive_disabled",
)


def test_engine_result_has_expected_shape():
    """Engine liefert alle vom Handler/Viewer erwarteten Felder; winner ist gueltig."""
    attacker = {"ships": {"cruiser": 10}, "tech": {}, "attack_mult": 1.0, "ship_bonuses": {}}
    defender = {"ships": {"light_fighter": 30}, "defenses": {"rocket_launcher": 5},
                "tech": {"weapons_tech": 0, "shield_tech": 0, "armor_tech": 0}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 123, BALANCE)
    for key in RESULT_KEYS:
        assert key in result, f"fehlendes Feld: {key}"
    assert result["winner"] in {"attacker", "defender", "draw"}
    assert result["seed"] == 123


def test_prepare_sim_input_cleans_and_validates():
    """0-Eintraege fallen raus, gueltige Typen bleiben erhalten."""
    o_ships, o_def, e_ships, e_def = _prepare_sim_input(
        {"cruiser": 5, "light_fighter": 0},
        {},
        {"light_fighter": 20},
        {"rocket_launcher": 0, "light_laser": 3},
        BALANCE["ships"], BALANCE["defenses"],
    )
    assert o_ships == {"cruiser": 5}
    assert o_def == {}
    assert e_ships == {"light_fighter": 20}
    assert e_def == {"light_laser": 3}  # 0-Eintrag entfernt


def test_prepare_sim_input_rejects_cap_and_unknown_and_empty():
    """Cap-Verletzung, unbekannter Typ und fehlende Einheiten loesen jeweils 400 aus."""
    # Cap: Summe > MAX_SIM_UNITS.
    with pytest.raises(HTTPException) as exc:
        _prepare_sim_input(
            {"light_fighter": MAX_SIM_UNITS}, {}, {"light_fighter": 1}, {},
            BALANCE["ships"], BALANCE["defenses"],
        )
    assert exc.value.status_code == 400

    # Unbekannter Schiffstyp.
    with pytest.raises(HTTPException) as exc:
        _prepare_sim_input(
            {"flux_kanone": 1}, {}, {"light_fighter": 1}, {},
            BALANCE["ships"], BALANCE["defenses"],
        )
    assert exc.value.status_code == 400

    # Kein Gegner -> beide Seiten brauchen eine Einheit.
    with pytest.raises(HTTPException) as exc:
        _prepare_sim_input(
            {"cruiser": 1}, {}, {}, {},
            BALANCE["ships"], BALANCE["defenses"],
        )
    assert exc.value.status_code == 400
