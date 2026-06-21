"""Tests fuer die DETERMINISTISCHE Gedaechtnis-/Eigenleben-Logik (app.commander.memory, Welle 2).

DB-/LLM-frei: getestet werden die reinen Leitplanken-Funktionen, die die KI einrahmen —
Sentiment-Ableitung, Meinungs-Update-Regeln (Respekt/Verachtung/Furcht), Meinungs-Verschmelzung,
Beziehungs-Stärke-Deltas, Grievance-Severity + Akkumulation, offene-Grievance-Summe (mit Decay)
sowie die Meuterei-Schwellen-Logik (unter/ueber Schwelle, Cooldown, defect vs. refuse) — plus die
Sanity des balance-Blocks ``commander.memory/opinions/relationships/grievances/mutiny``.

Balance wird per ``BALANCE_PATH`` (Container) bzw. Pfad-Suche (lokal) geladen — wie test_npc_diplomacy.py.
"""
import datetime as dt
import json
import os

from app.commander.memory import (
    accumulate_grievance,
    derive_sentiment,
    evaluate_opinion,
    grievance_severity,
    is_hated,
    merge_opinion,
    mutiny_decision,
    open_grievance_sum,
    relationship_delta,
)


def _load_balance() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


BAL = _load_balance()
CMD = BAL["commander"]
MEM = CMD["memory"]
OP = CMD["opinions"]
REL = CMD["relationships"]
GR = CMD["grievances"]
MUT = CMD["mutiny"]


def _now() -> dt.datetime:
    return dt.datetime(2026, 6, 20, 12, 0, tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------- derive_sentiment

def test_derive_sentiment_from_table():
    assert derive_sentiment("combat_victory", MEM) == "positive"
    assert derive_sentiment("combat_defeat", MEM) == "negative"
    assert derive_sentiment("demand_ignored", MEM) == "negative"


def test_derive_sentiment_unknown_is_neutral():
    assert derive_sentiment("irgendwas_unbekanntes", MEM) == "neutral"


# ---------------------------------------------------------------- evaluate_opinion

def test_opinion_win_over_strong_is_respect():
    ev = evaluate_opinion("win", strength_ratio=1.5, prior_losses=0, op_cfg=OP)
    assert ev["opinion_type"] == "respects"
    assert ev["delta"] == OP["respect_delta"]


def test_opinion_win_over_weak_is_despise():
    ev = evaluate_opinion("win", strength_ratio=0.4, prior_losses=0, op_cfg=OP)
    assert ev["opinion_type"] == "despises"


def test_opinion_win_against_equal_is_none():
    # Zwischen despise- und respect-Ratio -> keine ausgepraegte Meinung.
    assert evaluate_opinion("win", strength_ratio=1.0, prior_losses=0, op_cfg=OP) is None


def test_opinion_first_loss_is_aufkeimende_furcht():
    ev = evaluate_opinion("loss", strength_ratio=1.0, prior_losses=0, op_cfg=OP)
    assert ev["opinion_type"] == "fears"
    assert ev["delta"] == OP["grudge_delta"]


def test_opinion_repeated_losses_escalate_fear():
    ev = evaluate_opinion("loss", strength_ratio=1.0, prior_losses=OP["fear_after_losses"], op_cfg=OP)
    assert ev["opinion_type"] == "fears"
    assert ev["delta"] == OP["fear_delta"]
    # Wiederholte Niederlagen wiegen schwerer als die erste.
    assert OP["fear_delta"] > OP["grudge_delta"]


# ----------------------------------------------------------------- merge_opinion

def test_merge_opinion_same_type_accumulates_capped():
    typ, strength = merge_opinion("respects", 0.9, "respects", 0.25, OP["max_strength"])
    assert typ == "respects"
    assert strength == OP["max_strength"]  # gedeckelt


def test_merge_opinion_from_empty():
    typ, strength = merge_opinion(None, 0.0, "fears", 0.22, 1.0)
    assert typ == "fears"
    assert abs(strength - 0.22) < 1e-9


def test_merge_opinion_different_type_weakens_then_flips():
    # Schwache Gegen-Meinung -> alte bleibt, nur geschwaecht.
    typ, strength = merge_opinion("fears", 0.5, "respects", 0.2, 1.0)
    assert typ == "fears"
    assert abs(strength - 0.3) < 1e-9
    # Starke Gegen-Meinung kippt die Meinung.
    typ2, _ = merge_opinion("fears", 0.1, "respects", 0.3, 1.0)
    assert typ2 == "respects"


# ----------------------------------------------------------------- is_hated

def test_is_hated_only_for_strong_negative():
    assert is_hated("fears", 0.6, OP) is True
    assert is_hated("despises", OP["hated_threshold"], OP) is True
    assert is_hated("fears", 0.1, OP) is False
    assert is_hated("respects", 0.99, OP) is False  # Respekt ist kein Hass


# ------------------------------------------------------------- relationship_delta

def test_relationship_delta_maps_events():
    assert relationship_delta("co_battle", REL) == ("bond", REL["co_battle_bond_delta"])
    assert relationship_delta("shared_enemy", REL) == ("respect", REL["shared_enemy_respect_delta"])
    assert relationship_delta("promotion_rivalry", REL) == ("rivalry", REL["promotion_rivalry_delta"])


def test_relationship_delta_unknown_is_none():
    assert relationship_delta("nichtsdergleichen", REL) is None


# --------------------------------------------------------------- grievances

def test_grievance_severity_from_balance():
    assert grievance_severity("denied_promotion", GR) == GR["severity"]["denied_promotion"]
    assert grievance_severity("ignored_demand", GR) == GR["severity"]["ignored_demand"]


def test_grievance_severity_unknown_defaults_to_one():
    assert grievance_severity("voellig_unbekannt", GR) == 1


def test_accumulate_grievance_caps_severity_and_counts():
    max_sev = GR["max_severity_per_grievance"]
    sev, count = accumulate_grievance(max_sev - 1, 3, 5, max_sev)
    assert sev == max_sev          # gedeckelt
    assert count == 4              # Count++


def test_open_grievance_sum_ignores_resolved_and_expired():
    now = _now()
    recent = now - dt.timedelta(days=1)
    old = now - dt.timedelta(days=GR["decay_days"] + 5)
    grievances = [
        (3, recent, None),      # offen + frisch -> zaehlt
        (4, recent, now),       # beigelegt -> zaehlt nicht
        (5, old, None),         # verjaehrt -> zaehlt nicht
    ]
    assert open_grievance_sum(grievances, now, GR["decay_days"]) == 3


# --------------------------------------------------------------- mutiny_decision

def _mut(loyalty, unrest, grievance_sum, *, traits=None, last=None, rng=0.0):
    return mutiny_decision(
        loyalty=loyalty, unrest=unrest, grievance_sum=grievance_sum,
        traits=traits or [], last_check_at=last, now=_now(), rng_value=rng, mut_cfg=MUT,
    )


def test_mutiny_none_for_content_commander():
    d = _mut(loyalty=90, unrest=10, grievance_sum=0)
    assert d["action"] == "none"


def test_mutiny_warns_before_escalating():
    # Treue niedrig + Kraenkungen ueber Warnschwelle, aber Unmut noch unter der Meuterei-Schwelle.
    d = _mut(loyalty=20, unrest=10, grievance_sum=MUT["warning_grievance_sum"])
    assert d["action"] == "warn"
    assert d["outcome"] is None


def test_mutiny_fires_when_all_thresholds_crossed():
    # Alle Schwellen ueberschritten + Wuerfel faellt (rng=0) -> echte Meuterei.
    d = _mut(loyalty=10, unrest=80, grievance_sum=MUT["grievance_sum_threshold"], rng=0.0)
    assert d["action"] == "mutiny"
    # Sehr niedrige Treue -> Desertion.
    assert d["outcome"] == "defect"


def test_mutiny_refuse_when_loyalty_above_defect_threshold():
    d = _mut(loyalty=MUT["defect_threshold"] + 5, unrest=90, grievance_sum=20, rng=0.0)
    assert d["action"] == "mutiny"
    assert d["outcome"] == "refuse"


def test_mutiny_does_not_fire_when_dice_high():
    # Alle Schwellen ueberschritten, aber Wuerfel haelt -> nur Warnung, keine Folge.
    d = _mut(loyalty=10, unrest=90, grievance_sum=20, rng=0.99)
    assert d["action"] == "warn"


def test_mutiny_respects_cooldown():
    recent = _now() - dt.timedelta(hours=1)  # < mutiny_cooldown_hours
    d = _mut(loyalty=10, unrest=90, grievance_sum=20, last=recent, rng=0.0)
    assert d["action"] == "none"


def test_mutiny_trait_mult_raises_chance():
    # hot_tempered erhoeht die Chance -> bei einem Wuerfel zwischen Basis- und erhoehter Chance
    # meutert der jaehzornige, der loyale (Daempfung) nicht.
    base = float(MUT["mutiny_chance_per_day"]) / 24.0
    hot = base * float(MUT["trait_mult"]["hot_tempered"])
    mid = (base + hot) / 2.0
    d_hot = _mut(loyalty=10, unrest=90, grievance_sum=20, traits=["hot_tempered"], rng=mid)
    d_calm = _mut(loyalty=10, unrest=90, grievance_sum=20, traits=["loyal"], rng=mid)
    assert d_hot["action"] == "mutiny"
    assert d_calm["action"] == "warn"


# ------------------------------------------------------------- balance sanity

def test_balance_block_present_and_sane():
    assert MEM["digest_trigger_count"] > 0
    assert isinstance(MEM["sentiment"], dict)
    assert OP["respect_strength_ratio"] > OP["despise_strength_ratio"]
    assert 0 < OP["max_strength"] <= 1.0
    assert MUT["unrest_threshold"] > 0
    assert MUT["grievance_sum_threshold"] >= MUT["warning_grievance_sum"]
    assert MUT["loyalty_threshold"] >= MUT["defect_threshold"]
    assert MUT["mutiny_cooldown_hours"] > 0
    # alle Grievance-Typen haben eine Severity hinterlegt.
    for gt in ("ignored_demand", "risky_missions", "denied_promotion", "combat_neglect"):
        assert GR["severity"][gt] > 0
