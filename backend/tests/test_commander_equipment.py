"""Tests fuer Kommandeurs-Equipment + Gueteklassen-Rework E/D/C/B/A/S.

Reine Logik-Tests (kein DB): Katalog-Integritaet, Equipment-Bonus-Mathematik (Raritaet +
Set-Schwellen), Grade-Normalisierung/Alias, Ausbildungs-Programm-Verteilung, base_bonuses."""
import random

from app.commander.bonuses import base_bonuses
from app.commander.equipment import equipment_bonuses, equipment_cfg, set_progress
from app.commander.service import roll_grade
from app.platform.balance import get_balance
from app.platform.models import CommanderItem


def _item(key: str, rarity: str = "common") -> CommanderItem:
    d = equipment_cfg()["items"][key]
    return CommanderItem(item_key=key, slot=d["slot"], rarity=rarity)


# -- Katalog-Integritaet ------------------------------------------------------
def test_equipment_catalog_wellformed():
    cfg = equipment_cfg()
    slots = set(cfg["slots"])
    assert slots == {"head", "hands", "chest", "legs", "shoes"}  # 5 Slots (Beine ergaenzt)
    items = cfg["items"]
    assert len(items) == 45  # 9 Sets x 5 Slots
    classes = {k for k in get_balance().commander["ship_classes"] if not k.startswith("_")}
    # Schiffs-Kampfstats + Missions-/Planeten-Stats (Spielstil-Sets).
    allowed_stats = (
        "attack", "shield", "speed",
        "mining_yield", "trade_margin", "spy_success", "expedition_yield",
        "research_speed", "production", "shipbuild_speed",
    )
    for key, d in items.items():
        assert d["slot"] in slots
        assert d["set"] in cfg["sets"]
        for b in d["bonuses"]:
            assert b["stat"] in allowed_stats
            assert b["target"] == "all" or b["target"] in classes
    # Jedes Set hat genau 5 Teile (head/hands/chest/legs/shoes).
    for s in cfg["sets"]:
        members = [k for k, d in items.items() if d["set"] == s]
        assert len(members) == 5
        assert {items[k]["slot"] for k in members} == slots


# -- Equipment-Bonus-Mathematik ----------------------------------------------
def test_single_item_bonus():
    bons = equipment_bonuses([_item("fighter_helm")])
    assert bons == [{"stat": "attack", "target": "fighter", "pct": 0.06}]


def test_rarity_multiplies_item_pct():
    common = equipment_bonuses([_item("fighter_helm", "common")])[0]["pct"]
    epic = equipment_bonuses([_item("fighter_helm", "epic")])[0]["pct"]
    mult = equipment_cfg()["rarities"]["epic"]["mult"]
    assert round(common * mult, 4) == epic
    assert epic > common


def test_set_two_piece_threshold():
    # 2 Teile des fighter-Sets -> 2er-Set-Bonus (speed all +0.05) aktiv, 4er noch nicht.
    bons = equipment_bonuses([_item("fighter_helm"), _item("fighter_gloves")])
    by = {(b["stat"], b["target"]): b["pct"] for b in bons}
    assert by[("speed", "all")] == 0.05            # 2er-Set-Bonus
    assert ("attack", "fighter") in by             # Item-Boni summiert (helm+gloves)
    assert by[("attack", "fighter")] == 0.11       # 0.06 + 0.05


def test_set_four_piece_threshold_and_merge():
    full = [_item(k) for k in ("fighter_helm", "fighter_gloves", "fighter_vest", "fighter_boots")]
    by = {(b["stat"], b["target"]): b["pct"] for b in equipment_bonuses(full)}
    # 4er-Set-Bonus: +0.12 Angriff fighter, zusaetzlich zu den Item-Angriffsboni (0.06+0.05).
    assert by[("attack", "fighter")] == round(0.06 + 0.05 + 0.12, 4)
    # 2er-Set (speed all 0.05) + boots-Item (speed all 0.08) summiert.
    assert by[("speed", "all")] == round(0.05 + 0.08, 4)


def test_set_progress_counts():
    items = [_item("fighter_helm"), _item("fighter_gloves"), _item("capital_helm")]
    assert set_progress(items) == {"fighter": 2, "capital": 1}


def test_unknown_item_ignored():
    bogus = CommanderItem(item_key="does_not_exist", slot="head", rarity="common")
    assert equipment_bonuses([bogus]) == []


# -- Gueteklassen-Rework / Normalisierung ------------------------------------
def test_grade_order_and_potency():
    g = get_balance().grades
    assert g["order"] == ["E", "D", "C", "B", "A", "S"]
    assert g["potency"]["C"] == 1.0
    assert g["potency"]["S"] > g["potency"]["A"] > g["potency"]["C"] > g["potency"]["E"]


def test_grade_aliases_normalize():
    bal = get_balance()
    assert bal.normalize_grade("F") == "E"
    assert bal.normalize_grade("SS") == "S"
    assert bal.normalize_grade("SSS") == "S"
    assert bal.normalize_grade("B") == "B"
    assert bal.normalize_grade("unknown") == "C"   # Fallback default
    # Potenz folgt dem Alias.
    assert bal.grade_potency("F") == bal.grade_potency("E")
    assert bal.grade_potency("SSS") == bal.grade_potency("S")


def test_training_programs_smooth_ladder():
    tiers = {t["key"]: set(t["weights"].keys()) for t in get_balance().grades["training_tiers"]}
    assert tiers["standard"] == {"E", "D"}
    assert tiers["gehoben"] == {"D", "C"}
    assert tiers["elite"] == {"C", "B", "A"}
    assert tiers["experimentell"] == {"A", "S"}


def test_roll_grade_stays_within_program():
    for t in get_balance().grades["training_tiers"]:
        allowed = set(t["weights"].keys())
        rng = random.Random(t["key"])
        rolled = {roll_grade(t["weights"], rng) for _ in range(200)}
        assert rolled <= allowed, f"{t['key']} wuerfelte {rolled - allowed} ausserhalb {allowed}"


# -- base_bonuses mit neuen Grades -------------------------------------------
def test_base_bonuses_scales_with_grade():
    low = base_bonuses("combat", "veteran", [], None, "E")
    high = base_bonuses("combat", "veteran", [], None, "S")
    lo = next(b["pct"] for b in low if b["target"] == "all" and b["stat"] == "attack")
    hi = next(b["pct"] for b in high if b["target"] == "all" and b["stat"] == "attack")
    assert hi > lo  # hoehere Gueteklasse = staerkere Boni


def test_base_bonuses_alias_grade_does_not_crash():
    # Alt-Grade (Bestandsdaten) duerfen base_bonuses nicht brechen.
    out = base_bonuses("combat", "officer", [], None, "SSS")
    assert out and all("pct" in b for b in out)
