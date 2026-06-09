"""Verifiziert die Kampfbericht-Serialisierung (Read-Path fuers Frontend).

Baut aus echtem ``simulate_battle``-Output einen ``CombatReport`` und prueft, dass
``serialize_combat_report`` die volle Engine-Ausgabe perspektiv-korrekt durchreicht --
inklusive der reichen Felder, die das Frontend-Viewer rendert."""
import datetime as dt
import json
import os
import uuid

from app.combat.engine import simulate_battle
from app.combat.router import serialize_combat_report
from app.platform.models import CombatReport


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

RICH_KEYS = (
    "attacker", "defender", "rounds", "winner",
    "attacker_survivors", "defender_survivors",
    "attacker_losses", "defender_losses",
    "attacker_fled", "defender_fled",
    "attacker_captured", "defender_captured",
    "attacker_drive_disabled", "defender_drive_disabled",
    "loot", "debris", "role", "npc_name", "location", "id", "created_at",
)


def _report() -> tuple[CombatReport, uuid.UUID, uuid.UUID]:
    attacker = {"ships": {"cruiser": 20}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"light_fighter": 40}, "defenses": {"rocket_launcher": 10},
                "tech": {}, "attack_mult": 1.0}
    outcome = simulate_battle(attacker, defender, 42, BALANCE)
    outcome["npc_name"] = "Piraten-Aussenposten K17"
    atk_id, def_id = uuid.uuid4(), uuid.uuid4()
    report = CombatReport(
        id=uuid.uuid4(), attacker_id=atk_id, defender_id=def_id,
        location="1:58:4", seed=42, outcome=outcome,
        loot={"metal": 1200, "crystal": 600, "deuterium": 0},
        debris={"metal": 300, "crystal": 150}, created_at=dt.datetime.now(dt.timezone.utc),
    )
    return report, atk_id, def_id


def test_serializer_exposes_all_rich_keys():
    report, atk_id, _ = _report()
    out = serialize_combat_report(report, atk_id)
    for key in RICH_KEYS:
        assert key in out, f"fehlendes Feld: {key}"


def test_role_is_relative_to_viewer():
    report, atk_id, def_id = _report()
    assert serialize_combat_report(report, atk_id)["role"] == "attacker"
    assert serialize_combat_report(report, def_id)["role"] == "defender"


def test_rich_fields_pass_through_engine_output():
    report, atk_id, _ = _report()
    out = serialize_combat_report(report, atk_id)
    oc = report.outcome
    assert out["winner"] == oc["winner"]
    assert out["attacker"] == oc["attacker_initial"]
    assert out["defender"] == oc["defender_initial"]
    assert out["attacker_survivors"] == oc["attacker_survivors"]
    assert out["defender_losses"] == oc["defender_losses"]
    assert out["rounds"] == oc["rounds"]
    assert out["npc_name"] == "Piraten-Aussenposten K17"
    assert out["loot"]["metal"] == 1200
    assert out["debris"]["crystal"] == 150


def test_rounds_carry_distance_band():
    report, atk_id, _ = _report()
    out = serialize_combat_report(report, atk_id)
    # Mindestens eine Nicht-Hinterhalt-Runde traegt ein Distanz-Band (near/medium/far).
    bands = {rd.get("distance") for rd in out["rounds"] if not rd.get("ambush")}
    assert bands & {"near", "medium", "far"}
