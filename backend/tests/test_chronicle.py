"""Tests fuer die DETERMINISTISCHE Chronik-Auswahl-Logik (app.chronicle.service.build_key_events).

DB-/LLM-frei: getestet wird die reine Sammel-/Auswahl-Funktion, die die erzaehlwuerdigen Fakten
eines Zeitfensters bestimmt (groesste Schlachten korrekt + gedeckelt, Score-Delta ggü. Vorsnapshot,
neuer Verrat, min_events-Fallback, Snapshot-Struktur) — plus die Sanity des balance-Blocks
``chronicle``. Stil wie test_npc_diplomacy.py (BALANCE_PATH-Fallback fuers balance-Lesen)."""
import json
import os

from app.chronicle.service import build_key_events

CFG = {"max_battles": 3, "max_movers": 2, "min_battle_debris": 1000, "min_events": 1}


def _build(**over):
    """Ruft build_key_events mit leeren Defaults + Overrides auf."""
    kwargs = dict(
        battles=[], standings=[], prev_snapshot=None, reputations=[],
        diplomacy=[], cosmic_events=[], cfg=CFG,
    )
    kwargs.update(over)
    return build_key_events(**kwargs)


def _of_type(events, t):
    return [e for e in events if e.get("type") == t]


# ----------------------------------------------------------------- Schlachten

def test_biggest_battles_chosen_sorted_and_capped():
    battles = [
        {"scale": 5000, "attacker": "A", "defender": "D1", "location": "1:1:1", "winner": "attacker"},
        {"scale": 90000, "attacker": "B", "defender": "D2", "location": "2:2:2", "winner": "defender"},
        {"scale": 30000, "attacker": "C", "defender": "D3", "location": "3:3:3", "winner": "attacker"},
        {"scale": 12000, "attacker": "E", "defender": "D4", "location": "4:4:4", "winner": "attacker"},
    ]
    events, _ = _build(battles=battles)
    chosen = _of_type(events, "battle")
    assert len(chosen) == 3  # max_battles
    # Absteigend nach Truemmer: 90000, 30000, 12000.
    assert [b["debris"] for b in chosen] == [90000, 30000, 12000]
    assert chosen[0]["attacker"] == "B" and chosen[0]["defender"] == "D2"
    assert chosen[0]["outcome"] == "die Verteidigung hielt stand"


def test_min_battle_debris_filters_small():
    battles = [
        {"scale": 500, "attacker": "A", "defender": "D", "location": "1:1:1", "winner": "attacker"},
        {"scale": 999, "attacker": "B", "defender": "D", "location": "1:1:2", "winner": "attacker"},
    ]
    events, _ = _build(battles=battles)
    assert _of_type(events, "battle") == []
    # Nichts erzaehlwuerdig -> Fallback "quiet".
    assert _of_type(events, "quiet")


# ------------------------------------------------------------- Auf-/Abstieg

def test_power_excludes_zero_and_ranks_top():
    standings = [
        {"player_id": "p1", "name": "Alpha", "score": 100},
        {"player_id": "p2", "name": "Beta", "score": 300},
        {"player_id": "p3", "name": "Gamma", "score": 0},
    ]
    events, _ = _build(standings=standings)
    powers = _of_type(events, "power")
    assert len(powers) == 2  # max_movers, Gamma (0) faellt raus
    assert powers[0]["name"] == "Beta" and powers[0]["rank"] == 1
    assert powers[1]["name"] == "Alpha" and powers[1]["rank"] == 2


def test_rise_and_fall_vs_prev_snapshot():
    standings = [
        {"player_id": "p1", "name": "Alpha", "score": 500},   # +400
        {"player_id": "p2", "name": "Beta", "score": 100},    # -200
        {"player_id": "p3", "name": "Gamma", "score": 50},    # neu, kein Delta
    ]
    prev = {"scores": {"p1": 100, "p2": 300}, "betrayals": {}}
    events, _ = _build(standings=standings, prev_snapshot=prev)
    rises = _of_type(events, "rise")
    falls = _of_type(events, "fall")
    assert len(rises) == 1 and rises[0]["name"] == "Alpha" and rises[0]["delta"] == 400
    assert len(falls) == 1 and falls[0]["name"] == "Beta" and falls[0]["delta"] == -200


def test_first_run_has_no_rise_fall():
    standings = [{"player_id": "p1", "name": "Alpha", "score": 500}]
    events, _ = _build(standings=standings, prev_snapshot=None)
    assert _of_type(events, "rise") == []
    assert _of_type(events, "fall") == []
    assert _of_type(events, "power")  # aktueller Stand erscheint trotzdem


# ------------------------------------------------------------------- Verrat

def test_betrayal_first_run_lists_known_traitors():
    reps = [{"player_id": "p1", "name": "Verraeter", "betrayals": 2},
            {"player_id": "p2", "name": "Treu", "betrayals": 0}]
    events, _ = _build(reputations=reps, prev_snapshot=None)
    betr = _of_type(events, "betrayal")
    assert len(betr) == 1
    assert betr[0]["name"] == "Verraeter"
    assert betr[0]["new_betrayals"] == 2 and betr[0]["total_betrayals"] == 2


def test_betrayal_only_new_on_subsequent_run():
    reps = [{"player_id": "p1", "name": "Verraeter", "betrayals": 3}]
    prev = {"scores": {}, "betrayals": {"p1": 2}}
    events, _ = _build(reputations=reps, prev_snapshot=prev)
    betr = _of_type(events, "betrayal")
    assert len(betr) == 1 and betr[0]["new_betrayals"] == 1 and betr[0]["total_betrayals"] == 3


def test_no_new_betrayal_when_count_unchanged():
    reps = [{"player_id": "p1", "name": "Verraeter", "betrayals": 2}]
    prev = {"scores": {}, "betrayals": {"p1": 2}}
    events, _ = _build(reputations=reps, prev_snapshot=prev)
    assert _of_type(events, "betrayal") == []


# ---------------------------------------------------------- Diplomatie / Welt

def test_diplomacy_and_cosmic_events_pass_through():
    dip = [{"npc_name": "Eiserne Hand", "player_name": "Alpha", "offer_type": "alliance", "choice": "accept"}]
    cos = [{"event_type": "wandering_comet", "label": "ein wandernder Komet", "coords": "1:2:3"}]
    events, _ = _build(diplomacy=dip, cosmic_events=cos)
    d = _of_type(events, "diplomacy")
    c = _of_type(events, "cosmic_event")
    assert len(d) == 1 and d[0]["npc"] == "Eiserne Hand" and d[0]["offer"] == "ein Bündnis"
    assert len(c) == 1 and c[0]["coords"] == "1:2:3"


# ----------------------------------------------------------- min_events / Snapshot

def test_min_events_fallback_quiet():
    events, _ = _build()  # nichts passiert
    assert _of_type(events, "quiet")
    assert len(events) >= CFG["min_events"]


def test_snapshot_structure():
    standings = [{"player_id": "p1", "name": "Alpha", "score": 500}]
    reps = [{"player_id": "p1", "name": "Alpha", "betrayals": 1}]
    _, snap = _build(standings=standings, reputations=reps)
    assert snap["scores"] == {"p1": 500}
    assert snap["betrayals"] == {"p1": 1}


# ------------------------------------------------------------- balance sanity

def test_chronicle_block_present_in_balance():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    c = data["chronicle"]
    assert c["enabled"] is True
    assert c["model"] == "qwen3.5:9b"
    assert c["narrator"] == "historian"
    assert c["interval_hours"] > 0
    assert c["lookback_hours"] > 0
    assert c["max_battles"] > 0
    assert c["max_movers"] > 0
