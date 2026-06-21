"""Tests fuer die DETERMINISTISCHE Diplomatie-Leitplanken-Logik (app.npc.diplomacy).

DB-/LLM-frei: getestet werden die reinen Funktionen, die die KI-Entscheidung einrahmen —
Klemmung der Konditionen (Caps + Spieler-Bestand), Aufloesung accept/counter/reject, die
Statusuebergaenge (neutral->allied/ceasefire), der Angriffs-Schutz (allied/ceasefire) sowie
die Sanity des balance-Blocks ``diplomacy``."""
import datetime as dt
import json
import os

from app.npc.diplomacy import (
    apply_decision,
    clamp_terms,
    diplomacy_caps,
    relation_blocks_attack,
    resolve_terms,
)
from app.platform.balance import Balance

CAPS = {
    "tribute_max": 500000,
    "ceasefire_max_hours": 168,
    "tribute_cycle_hours": 24,
    "negotiate_cooldown_minutes": 60,
}


def _now() -> dt.datetime:
    return dt.datetime(2026, 6, 20, 12, 0, tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------- clamp_terms

def test_clamp_terms_caps_tribute_and_hours():
    out = clamp_terms("tribute", {"tribute_metal": 9_999_999, "ceasefire_hours": 9999}, CAPS)
    assert out["tribute_metal"] == 500000
    assert out["ceasefire_hours"] == 168


def test_clamp_terms_respects_player_stock():
    # Kein Tribut ueber den aktuellen Bestand (Exploit-/Bestand-Schutz).
    out = clamp_terms("tribute", {"tribute_metal": 400000}, CAPS, player_metal=100000)
    assert out["tribute_metal"] == 100000


def test_clamp_terms_floors_negative_to_zero():
    out = clamp_terms("ceasefire", {"tribute_metal": -50, "ceasefire_hours": -10}, CAPS)
    assert out == {"tribute_metal": 0, "ceasefire_hours": 0}


# -------------------------------------------------------------- resolve_terms

def test_resolve_terms_accept_uses_clamped_offer():
    offered = {"tribute_metal": 200000, "ceasefire_hours": 48}
    out = resolve_terms("tribute", "accept", offered, {}, CAPS)
    assert out == {"tribute_metal": 200000, "ceasefire_hours": 48}


def test_resolve_terms_counter_uses_npc_demand_clamped():
    llm = {"tribut_gefordert": 10_000_000, "ceasefire_stunden": 9999}
    out = resolve_terms("ceasefire", "counter", {}, llm, CAPS)
    assert out == {"tribute_metal": 500000, "ceasefire_hours": 168}


def test_resolve_terms_reject_is_empty():
    out = resolve_terms("alliance", "reject", {"tribute_metal": 100}, {"tribut_gefordert": 100}, CAPS)
    assert out == {"tribute_metal": 0, "ceasefire_hours": 0}


# -------------------------------------------------------------- apply_decision

def test_apply_decision_alliance_accept():
    now = _now()
    s = apply_decision({"status": "neutral", "positive_actions": 2}, "alliance", "accept", {}, now, CAPS)
    assert s["status"] == "allied"
    assert s["alliance_since"] == now
    assert s["tribute_metal_per_cycle"] == 0.0
    assert s["positive_actions"] == 3
    assert s["last_decision_at"] == now


def test_apply_decision_ceasefire_sets_window():
    now = _now()
    s = apply_decision({"status": "neutral"}, "ceasefire", "accept", {"ceasefire_hours": 48}, now, CAPS)
    assert s["status"] == "ceasefire"
    assert s["ceasefire_until"] == now + dt.timedelta(hours=48)


def test_apply_decision_ceasefire_zero_hours_falls_back_to_cap():
    now = _now()
    s = apply_decision({"status": "neutral"}, "ceasefire", "accept", {"ceasefire_hours": 0}, now, CAPS)
    assert s["ceasefire_until"] == now + dt.timedelta(hours=CAPS["ceasefire_max_hours"])


def test_apply_decision_tribute_sets_recurring_and_window():
    now = _now()
    s = apply_decision({"status": "neutral"}, "tribute", "accept", {"tribute_metal": 50000}, now, CAPS)
    assert s["status"] == "ceasefire"
    assert s["tribute_metal_per_cycle"] == 50000
    assert s["tribute_last_paid"] == now
    assert s["ceasefire_until"] == now + dt.timedelta(hours=CAPS["tribute_cycle_hours"])


def test_apply_decision_counter_and_reject_do_not_change_status():
    now = _now()
    for choice in ("counter", "reject"):
        s = apply_decision({"status": "neutral", "positive_actions": 1}, "alliance", choice, {}, now, CAPS)
        assert s["status"] == "neutral"
        assert s["positive_actions"] == 1  # keine positive Aktion bei Nicht-Annahme
        assert s["last_decision_at"] == now


# --------------------------------------------------------- relation_blocks_attack

def test_relation_blocks_attack_allied_and_active_ceasefire():
    now = _now()
    assert relation_blocks_attack("allied", None, now) is True
    assert relation_blocks_attack("ceasefire", now + dt.timedelta(hours=1), now) is True


def test_relation_blocks_attack_expired_or_hostile():
    now = _now()
    assert relation_blocks_attack("ceasefire", now - dt.timedelta(hours=1), now) is False
    assert relation_blocks_attack("ceasefire", None, now) is False
    assert relation_blocks_attack("neutral", None, now) is False
    assert relation_blocks_attack("hostile", None, now) is False
    assert relation_blocks_attack("broken_pact", None, now) is False


def test_relation_blocks_attack_handles_naive_datetime():
    # ceasefire_until ohne tzinfo (DB-Edge) darf nicht crashen.
    now = _now()
    naive_future = dt.datetime(2026, 6, 21, 12, 0)
    assert relation_blocks_attack("ceasefire", naive_future, now) is True


# ------------------------------------------------------------- balance sanity

def test_diplomacy_caps_present_in_balance():
    # balance.json wird im Container über BALANCE_PATH gemountet; lokal liegt es unter shared/.
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    caps = diplomacy_caps(Balance(data=data))
    assert caps["decision_model"] == "qwen3.5:9b"
    assert caps["tribute_max"] > 0
    assert caps["ceasefire_max_hours"] > 0
    assert caps["negotiate_cooldown_minutes"] > 0
