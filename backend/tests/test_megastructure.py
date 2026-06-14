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
