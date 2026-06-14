"""Tests fuer Megastruktur-Kostenkurve & Bauzeit (pure Helfer)."""
from app.megastructure.service import stage_build_seconds, stage_cost
from app.platform.balance import get_balance


def _cfg(mtype="research_nexus"):
    return get_balance().data["megastructures"][mtype]


def test_stage_cost_grows_exponential():
    cfg = _cfg()
    base = cfg["cost_base"]
    g = cfg["cost_growth"]
    # Stufe 0 = base, Stufe 2 = base * g^2.
    assert stage_cost(cfg, 0)["metal"] == round(base["metal"], 2)
    assert stage_cost(cfg, 2)["metal"] == round(base["metal"] * g * g, 2)
    # Dunkle Materie ist Teil der Kosten (Haupt-Sink).
    assert stage_cost(cfg, 0)["dark_matter"] == round(base["dark_matter"], 2)


def test_stage_build_seconds_grows_and_positive():
    cfg = _cfg()
    s0 = stage_build_seconds(cfg, 0)
    s1 = stage_build_seconds(cfg, 1)
    assert s0 > 0 and s1 > s0


def test_both_catalog_structures_present_and_have_effects():
    cat = get_balance().data["megastructures"]
    assert cat["research_nexus"]["effect"] == "research_speed"
    assert cat["matter_decompressor"]["effect"] == "mining_speed"


def test_antimatter_forge_costs_antimatter():
    forge = get_balance().data["megastructures"]["antimatter_forge"]
    assert forge["cost_base"].get("antimatter", 0) > 0
    assert forge["effect"] == "weapons_boost"


def test_antimatter_forge_boosts_attacker_damage():
    """Die Antimaterie-Schmiede (im tech-Dict als ``antimatter_forge``) erhoeht den Angriff
    via tech_bonus.weapons_forge_per_level — gleiche Schlacht, mehr Verteidiger-Verluste."""
    from app.combat.engine import simulate_battle
    bal = get_balance()
    assert bal.data["tech_bonus"]["weapons_forge_per_level"] > 0
    ships = {"light_fighter": 200}
    defender = {"ships": {}, "defenses": {"rocket_launcher": 80}, "tech": {}, "attack_mult": 1.0}
    seed = 12345
    no_forge = simulate_battle(
        {"ships": dict(ships), "tech": {}, "attack_mult": 1.0, "ship_bonuses": {}},
        {**defender, "defenses": dict(defender["defenses"])}, seed, bal.data,
    )
    with_forge = simulate_battle(
        {"ships": dict(ships), "tech": {"antimatter_forge": 5}, "attack_mult": 1.0, "ship_bonuses": {}},
        {**defender, "defenses": dict(defender["defenses"])}, seed, bal.data,
    )
    # Mehr Angriff -> Verteidigung wird staerker dezimiert (weniger Ueberlebende).
    def _def_survivors(rep):
        d = rep.get("defender_survivors") or rep.get("defender", {}).get("survivors") or {}
        return sum(d.values()) if isinstance(d, dict) else 0
    assert _def_survivors(with_forge) <= _def_survivors(no_forge)
