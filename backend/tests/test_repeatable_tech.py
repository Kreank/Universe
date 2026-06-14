"""Tests fuer wiederholbare Forschungen (Repeatable Techs, ewiger Motor)."""
from app.platform.balance import get_balance
from app.research.service import cost_for_level


def test_repeatable_cost_grows_linear():
    bal = get_balance()
    base = bal.techs["weapons_mastery"]["cost"]
    # Stufe 0->1 = base*1, 1->2 = base*2, 9->10 = base*10 (linear-additiv).
    assert cost_for_level("weapons_mastery", 0)["metal"] == round(base["metal"], 2)
    assert cost_for_level("weapons_mastery", 1)["metal"] == round(base["metal"] * 2, 2)
    assert cost_for_level("weapons_mastery", 9)["metal"] == round(base["metal"] * 10, 2)


def test_normal_tech_cost_grows_exponential():
    bal = get_balance()
    base = bal.techs["weapons_tech"]["cost"]
    # Nicht-repeatable bleibt bei base * 2^level.
    assert cost_for_level("weapons_tech", 3)["metal"] == round(base["metal"] * 8, 2)


def test_repeatable_marginal_cost_below_exponential_at_high_levels():
    # Bei Stufe 20 ist die lineare Repeatable-Kurve drastisch billiger als 2^20 —
    # genau deshalb bleibt sie ewig erforschbar (sinkender Grenznutzen statt Mauer).
    rep = cost_for_level("weapons_mastery", 20)["metal"]
    base = get_balance().techs["weapons_mastery"]["cost"]["metal"]
    assert rep == round(base * 21, 2)


def test_mastery_flagged_repeatable():
    bal = get_balance()
    for t in ("weapons_mastery", "shield_mastery", "armor_mastery"):
        assert bal.techs[t].get("repeatable") is True
