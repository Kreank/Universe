"""Tests fuer die reine Expeditions-Logik (Dauer, Ertrags-Cap, Risiko-Skalierung, Gegner-Generierung)."""
from app.fleet.expedition import (
    clamp_hours,
    generate_enemy_fleet,
    max_expedition_hours,
    scale_outcomes,
    ship_power,
    yield_mult,
)
from app.platform.balance import get_balance


def _exp_cfg() -> dict:
    return get_balance().data["expedition"]


def test_max_hours_scales_with_astrophysics_and_caps():
    cfg = _exp_cfg()
    cap = cfg["duration"]["hour_cap"]
    assert max_expedition_hours(0, cfg) == 0           # Stufe 0 -> nicht freigeschaltet
    assert max_expedition_hours(1, cfg) == 1
    assert max_expedition_hours(10, cfg) == 10
    assert max_expedition_hours(99, cfg) == cap        # gedeckelt (24)


def test_clamp_hours_bounds():
    cfg = _exp_cfg()
    assert clamp_hours(5, astro_level=10, cfg=cfg) == 5
    assert clamp_hours(50, astro_level=10, cfg=cfg) == 10   # auf Max
    assert clamp_hours(0, astro_level=10, cfg=cfg) == 1     # mind. 1
    assert clamp_hours(5, astro_level=0, cfg=cfg) == 0      # nicht freigeschaltet


def test_yield_mult_research_caps_at_level_10():
    cfg = _exp_cfg()
    # Ertrag waechst bis Stufe 10, danach kein weiterer Forschungs-Bonus (1h -> kein Dauer-Bonus).
    m10 = yield_mult(10, hours=1, cfg=cfg)
    m20 = yield_mult(20, hours=1, cfg=cfg)
    assert m10 == m20
    assert abs(m10 - 2.0) < 1e-6   # +100% Cap
    # Hoehere Stufe als 0 erhoeht den Ertrag.
    assert yield_mult(5, 1, cfg) > yield_mult(0, 1, cfg)


def test_yield_mult_duration_bonus():
    cfg = _exp_cfg()
    per = cfg["duration"]["yield_bonus_per_hour"]
    base = yield_mult(0, hours=1, cfg=cfg)       # 1h -> kein Dauer-Bonus
    longer = yield_mult(0, hours=11, cfg=cfg)    # 10 Std mehr
    assert abs(longer - base * (1 + per * 10)) < 1e-6


def test_scale_outcomes_raises_only_risky_weights():
    cfg = _exp_cfg()
    outcomes = [
        {"type": "resources", "weight": 30},
        {"type": "pirates", "weight": 10, "risky": True},
    ]
    scaled = scale_outcomes(outcomes, hours=11, cfg=cfg)   # 10 Std ueber Minimum
    by = {o["type"]: o["weight"] for o in scaled}
    assert by["resources"] == 30                            # unveraendert
    risk = cfg["duration"]["risk_bonus_per_hour"]
    assert abs(by["pirates"] - 10 * (1 + risk * 10)) < 1e-6  # riskanter
    # 1h -> keine Aenderung.
    assert scale_outcomes(outcomes, hours=1, cfg=cfg) == outcomes


def test_ship_power_sums_attack():
    cat = {"a": {"attack": 100}, "b": {"attack": 50}}
    assert ship_power({"a": 2, "b": 3}, cat) == 100 * 2 + 50 * 3


def test_generate_enemy_fleet_scales_with_power_ratio():
    bal = get_balance()
    exp = {"battleship": 10}
    pirates = bal.data["expedition"]["encounters"]["pirates"]
    aliens = bal.data["expedition"]["encounters"]["aliens"]
    pf = generate_enemy_fleet(exp, pirates, bal.ships)
    af = generate_enemy_fleet(exp, aliens, bal.ships)
    assert pf and af
    # Aliens (power_ratio 1.2) sind staerker als Piraten (0.7) gegen dieselbe Flotte.
    assert ship_power(af, bal.ships) > ship_power(pf, bal.ships)
    # Nur Roster-Schiffe.
    assert set(pf) <= set(pirates["roster"])
    assert set(af) <= set(aliens["roster"])


def test_generate_enemy_fleet_nonempty_even_for_tiny_fleet():
    bal = get_balance()
    pirates = bal.data["expedition"]["encounters"]["pirates"]
    enemy = generate_enemy_fleet({"light_fighter": 1}, pirates, bal.ships)
    assert sum(enemy.values()) >= 1
