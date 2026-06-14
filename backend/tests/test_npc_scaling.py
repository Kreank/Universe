"""Tests fuer die reine NPC-Tier-Skalierung (npc/scaling.py)."""
from app.npc.scaling import (
    effective_tier,
    nearest_score_from_rows,
    npc_dev_bonus,
    npc_tier,
    scale_garrison,
    scale_resources,
    tier_strength_mult,
    tier_tech,
)

_CFG = {
    "base": 1.0,
    "region_reference_galaxy": 1,
    "region_reference_system": 1,
    "region_per_galaxy": 2.0,
    "region_per_system": 0.02,
    "player_score_per_tier": 50000,
    "player_weight": 1.0,
    "min_tier": 1.0,
    "max_tier": 12.0,
    "per_tier_strength": 0.5,
    "tech_per_tier": 0.5,
    "development": {"seconds_per_tier": 43200, "max_tier_bonus": 4.0},
}


def test_npc_tier_combines_region_and_player():
    # Am Kern (1:1:1), kein Spieler -> Basis-Tier 1.
    assert npc_tier(1, 1, 1, 0, _CFG) == 1.0
    # Region: 50 Systeme weiter = +50*0.02 = +1.0 Tier.
    assert round(npc_tier(1, 51, 1, 0, _CFG), 4) == 2.0
    # Spieler: Score 100000 = +2 Tier (mitwachsen).
    assert round(npc_tier(1, 1, 1, 100000, _CFG), 4) == 3.0
    # Kombi Region + Spieler.
    assert round(npc_tier(1, 51, 1, 100000, _CFG), 4) == 4.0
    # Andere Galaxie: +2.0 je Galaxie.
    assert round(npc_tier(2, 1, 1, 0, _CFG), 4) == 3.0


def test_npc_tier_clamped():
    assert npc_tier(1, 1, 1, 0, _CFG) == 1.0                       # nie unter min_tier
    assert npc_tier(1, 9999, 1, 9_000_000, _CFG) == 12.0          # nie ueber max_tier


def test_tier_strength_mult():
    assert tier_strength_mult(1.0, _CFG) == 1.0                    # Tier 1 = Template-Niveau
    assert tier_strength_mult(3.0, _CFG) == 2.0                    # +0.5 je Tier
    assert tier_strength_mult(5.0, _CFG) == 3.0


def test_scale_garrison_and_resources():
    base = {"fleet": {"light_fighter": 10, "cruiser": 2}, "defenses": {"rocket_launcher": 6}}
    scaled = scale_garrison(base, 2.0)
    assert scaled["fleet"] == {"light_fighter": 20, "cruiser": 4}
    assert scaled["defenses"] == {"rocket_launcher": 12}
    # Mindestens 1 je vorhandenem Typ (kein Wegrunden auf 0).
    assert scale_garrison({"fleet": {"cruiser": 1}, "defenses": {}}, 0.1)["fleet"] == {"cruiser": 1}
    assert scale_resources({"metal": 800, "crystal": 500}, 2.5) == {"metal": 2000.0, "crystal": 1250.0}


def test_tier_tech_scales_quality():
    base = {"weapons_tech": 4, "shield_tech": 4, "armor_tech": 4}
    assert tier_tech(base, 1.0, _CFG) == base                      # Tier 1 = Basis-Tech
    assert tier_tech(base, 5.0, _CFG) == {"weapons_tech": 6, "shield_tech": 6, "armor_tech": 6}  # +0.5*4=2


def test_npc_dev_bonus_grows_with_age_and_caps():
    # Frisch -> kein Bonus.
    assert npc_dev_bonus(0, _CFG) == 0.0
    # Genau seconds_per_tier Alter -> +1 Tier.
    assert npc_dev_bonus(43200, _CFG) == 1.0
    # Halbe Periode -> +0.5 Tier (linear).
    assert npc_dev_bonus(21600, _CFG) == 0.5
    # Gedeckelt auf max_tier_bonus, egal wie alt.
    assert npc_dev_bonus(43200 * 100, _CFG) == 4.0
    # Negatives/None-Alter -> 0 (kein Absturz).
    assert npc_dev_bonus(-5, _CFG) == 0.0
    assert npc_dev_bonus(None, _CFG) == 0.0


def test_npc_dev_bonus_missing_config_is_zero():
    # Ohne development-Block kein Bonus (Default max_tier_bonus 4, aber 0 Alter -> 0).
    assert npc_dev_bonus(0, {}) == 0.0
    # Mit Alter, aber ohne Config: Default seconds_per_tier 43200, max 4.0.
    assert npc_dev_bonus(43200, {}) == 1.0


def test_effective_tier_adds_age_to_region_player():
    # Am Kern, kein Spieler, frisch -> Basis-Tier 1 (wie npc_tier).
    assert effective_tier(1, 1, 1, 0, 0, _CFG) == 1.0
    # Selber Ort, aber 1 Periode alt -> +1 Tier durch Entwicklung.
    assert round(effective_tier(1, 1, 1, 0, 43200, _CFG), 4) == 2.0
    # Region + Spieler + Alter addieren sich: 1 (basis) +1 (region 50 sys) +2 (score) +1 (alter) = 5.
    assert round(effective_tier(1, 51, 1, 100000, 43200, _CFG), 4) == 5.0


def test_effective_tier_clamped_to_max():
    # Hohes Tier + voller Alters-Bonus bleibt auf max_tier gedeckelt.
    assert effective_tier(1, 9999, 1, 9_000_000, 43200 * 100, _CFG) == 12.0
    # Nie unter min_tier.
    assert effective_tier(1, 1, 1, 0, 0, _CFG) >= 1.0


def test_nearest_score_from_rows():
    rows = [
        (1, 10, 5, 1000),    # selbe Galaxie, System 10
        (1, 60, 1, 9000),    # selbe Galaxie, System 60 (weiter weg)
        (2, 11, 1, 99999),   # andere Galaxie (grosse Strafe -> nie naehester)
    ]
    # NPC bei 1:12:1 -> naechster ist System 10 (Score 1000).
    assert nearest_score_from_rows(rows, 1, 12, 1) == 1000.0
    # NPC bei 1:58:1 -> naechster ist System 60 (Score 9000).
    assert nearest_score_from_rows(rows, 1, 58, 1) == 9000.0
    # Keine Spieler -> 0.
    assert nearest_score_from_rows([], 1, 1, 1) == 0.0
