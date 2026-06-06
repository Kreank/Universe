"""Smoke-Tests fuer die deterministische Kampf-Engine.

Laedt balance.json direkt (ohne DB/Config-Abhaengigkeit) -> reine Engine-Pruefung."""
import json
import os

from app.combat.engine import simulate_battle


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


def test_battle_is_deterministic_with_same_seed():
    attacker = {"ships": {"cruiser": 20}, "tech": {}, "attack_mult": 1.0}
    defender = {
        "ships": {"light_fighter": 40},
        "defenses": {"rocket_launcher": 10},
        "tech": {},
        "attack_mult": 1.0,
    }
    r1 = simulate_battle(attacker, defender, 42, BALANCE)
    r2 = simulate_battle(attacker, defender, 42, BALANCE)
    assert r1 == r2
    assert r1["seed"] == 42
    assert len(r1["rounds"]) <= BALANCE["combat"]["max_rounds"]


def test_strong_attacker_wins():
    attacker = {"ships": {"cruiser": 50}, "tech": {"weapons_tech": 5}, "attack_mult": 1.1}
    defender = {"ships": {"light_fighter": 5}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 7, BALANCE)
    assert result["winner"] == "attacker"
    assert result["defender_survivors"] == {}


def test_result_structure_and_losses_consistency():
    attacker = {"ships": {"light_fighter": 10}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"light_fighter": 10}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 123, BALANCE)
    for key in ("rounds", "winner", "attacker_survivors", "defender_survivors",
                "attacker_initial", "attacker_losses"):
        assert key in result
    # Anfangsbestand = Ueberlebende + Verluste (pro Typ).
    for typ, initial in result["attacker_initial"].items():
        surv = result["attacker_survivors"].get(typ, 0)
        lost = result["attacker_losses"].get(typ, 0)
        assert surv + lost == initial


def test_shield_bounce_protects_against_tiny_hits():
    # Spionagesonden (attack 0) koennen einen Kreuzer nicht beschaedigen -> Sonden verlieren.
    attacker = {"ships": {"spy_probe": 30}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"cruiser": 1}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 99, BALANCE)
    assert result["defender_survivors"].get("cruiser", 0) == 1
