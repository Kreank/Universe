"""Tests fuer Endgame-Capstone-Schiffe: Besitz-Cap, Auren (Dedup), Raider-Beute."""
from app.buildings.shipyard import capstone_cap
from app.combat.service import _combat_aura_mult, _raider_loot_mult
from app.platform.balance import get_balance


def test_capstone_data_present():
    b = get_balance()
    for s in ("flagship", "corsair", "trade_leviathan", "harvest_titan"):
        cfg = b.ships[s]
        assert cfg.get("capstone")  # Kommando-Forschung verknuepft
        cost = cfg["cost"]
        # Militaer -> Antimaterie, zivil -> Dunkle Materie.
        assert cost.get("antimatter", 0) > 0 or cost.get("dark_matter", 0) > 0
    # Kommando-Forschungen existieren.
    for t in ("flagship_command", "corsair_command", "leviathan_command", "harvest_command"):
        assert t in b.techs


def test_capstone_cap_default_and_research():
    cfg = get_balance().ships["flagship"]
    assert capstone_cap(cfg, {}) == 1                       # default 1
    assert capstone_cap(cfg, {"flagship_command": 3}) == 4  # +1 je Stufe


def test_combat_aura_present_and_dedup():
    base = _combat_aura_mult({"light_fighter": 100})
    one = _combat_aura_mult({"flagship": 1, "light_fighter": 100})
    many = _combat_aura_mult({"flagship": 5, "light_fighter": 100})
    assert base == 1.0
    assert one > 1.0
    # Auren STAPELN NICHT: 5 Flaggschiffe == 1 Flaggschiff.
    assert many == one


def test_raider_loot_bonus_presence():
    assert _raider_loot_mult({"light_fighter": 50}) == 1.0
    assert _raider_loot_mult({"corsair": 1, "light_fighter": 50}) > 1.0
    # Praesenz-basiert, kein Stapeln.
    assert _raider_loot_mult({"corsair": 4}) == _raider_loot_mult({"corsair": 1})


def test_convoy_aura_only_on_leviathan():
    roster = get_balance().combat_roster
    assert roster["trade_leviathan"].get("aura") == "convoy"
    assert roster["harvest_titan"].get("harvester") is True
    assert roster["corsair"].get("raider") is True
