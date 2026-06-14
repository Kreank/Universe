"""Tests fuer die Flotten-Upkeep-Bremse (pure Helfer)."""
from app.fleet.upkeep import supply_capacity, upkeep_deut
from app.platform.balance import get_balance


def _cfg():
    return get_balance().data["fleet"]["upkeep"]


def test_capacity_scales_with_planets():
    cfg = _cfg()
    base = cfg["supply_base"]
    per = cfg["supply_per_planet"]
    assert supply_capacity(0, cfg) == base
    assert supply_capacity(3, cfg) == base + 3 * per


def test_no_upkeep_below_capacity():
    cfg = _cfg()
    cap = supply_capacity(1, cfg)
    # Neuling-Flotte unter Kapazitaet -> 0 Deuterium Upkeep.
    assert upkeep_deut(cap - 1, cap, cfg) == 0
    assert upkeep_deut(cap, cap, cfg) == 0


def test_upkeep_only_on_excess():
    cfg = _cfg()
    cap = supply_capacity(1, cfg)
    rate = cfg["deut_per_excess_unit_per_hour"]
    # 100 Schiffe ueber Kapazitaet -> 100 * rate.
    assert upkeep_deut(cap + 100, cap, cfg) == round(100 * rate, 2)


def test_upkeep_enabled_flag_present():
    assert _cfg().get("enabled") is True
