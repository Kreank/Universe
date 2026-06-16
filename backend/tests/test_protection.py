"""Tests fuer die reine Schutz-Logik (A Neulingsschutz + B Bashing-Schutz)."""
from app.platform.protection import (
    bash_blocked,
    newbie_protection_active,
    newbie_threshold,
)

CFG = {
    "newbie_avg_factor": 0.30,
    "bash_band_factor": 5,
    "bash_min_attacker_score": 5000,
}


# -- A: dynamische Schwelle (rein punkte-relativ, kein Floor, keine Zeit) -------
def test_threshold_is_pure_fraction_of_average():
    assert newbie_threshold(0, CFG) == 0                 # junges Universum -> Schwelle 0
    assert newbie_threshold(1_000, CFG) == 300           # 30 % von 1.000
    assert newbie_threshold(50_000, CFG) == 15_000       # 30 % von 50.000


# -- A: Schutz-Status ----------------------------------------------------------
def test_protected_while_below_threshold():
    # Unter 30 % des Schnitts -> geschuetzt.
    assert newbie_protection_active(score=10_000, avg_score=50_000, cfg=CFG) is True


def test_graduates_at_or_above_threshold():
    # Genau auf/ueber der Schwelle (15.000) -> kein Neuling mehr.
    assert newbie_protection_active(score=15_000, avg_score=50_000, cfg=CFG) is False
    assert newbie_protection_active(score=20_000, avg_score=50_000, cfg=CFG) is False


def test_threshold_grows_with_universe():
    # Derselbe 10k-Spieler: bei kleinem Schnitt schon raus, bei grossem Schnitt noch Neuling.
    assert newbie_protection_active(score=10_000, avg_score=20_000, cfg=CFG) is False  # Schwelle 6k
    assert newbie_protection_active(score=10_000, avg_score=50_000, cfg=CFG) is True   # Schwelle 15k


# -- B: Bashing-Schutz ---------------------------------------------------------
def test_bash_blocks_strong_attacker_on_weak_target():
    # Platz 1 (100k) gegen Platz 500 (1k): 100k > 5 * 1k -> gesperrt.
    assert bash_blocked(100_000, 1_000, CFG) is True


def test_bash_allows_within_band():
    # 20k gegen 5k: 20k <= 5 * 5k=25k -> erlaubt.
    assert bash_blocked(20_000, 5_000, CFG) is False


def test_bash_does_not_apply_to_small_attacker():
    # Kleiner Angreifer (< bash_min_attacker_score) darf auch sehr schwache angreifen ...
    assert bash_blocked(4_000, 10, CFG) is False
    # ... und David darf Goliath immer angreifen (Ziel staerker als Angreifer).
    assert bash_blocked(10_000, 100_000, CFG) is False


def test_bash_disabled_when_factor_zero():
    assert bash_blocked(100_000, 1, {**CFG, "bash_band_factor": 0}) is False
