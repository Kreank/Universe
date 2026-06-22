"""Reine Helfer der Flottenslot-Kapazitaetsanzeige (``app.fleet.service``).

Die Slot-Uebersicht (max/used/free + breakdown) wird ueber reine Funktionen berechnet, daher
ohne DB testbar (Stub-Missionslisten). Garantie-Invarianten: used == Summe breakdown,
free == max - used (>= 0), Gruppierung nach Mission korrekt."""
from app.fleet.service import (
    SLOT_CATEGORIES,
    max_expedition_slots,
    max_mining_slots,
    slot_breakdown,
    summarize_slots,
)


def test_breakdown_groups_by_mission():
    missions = ["attack", "transport", "expedition", "expedition", "mine", "recycle", "spy"]
    bd = slot_breakdown(missions, patrols=0)
    assert bd["expeditions"] == 2
    assert bd["mining"] == 1
    assert bd["recycling"] == 1
    # attack + transport + spy fallen unter 'flights'
    assert bd["flights"] == 3
    assert bd["patrols"] == 0


def test_breakdown_counts_patrols():
    bd = slot_breakdown(["attack"], patrols=3)
    assert bd["patrols"] == 3
    assert bd["flights"] == 1


def test_breakdown_sum_equals_used():
    missions = ["attack", "mine", "expedition", "recycle", "trade", "intercept"]
    patrols = 2
    bd = slot_breakdown(missions, patrols)
    assert sum(bd.values()) == len(missions) + patrols


def test_breakdown_has_all_categories():
    bd = slot_breakdown([], 0)
    assert set(bd.keys()) == set(SLOT_CATEGORIES)
    assert all(v == 0 for v in bd.values())


def test_summary_used_equals_breakdown_sum():
    s = summarize_slots(["attack", "mine", "expedition"], patrols=1, max_slots=10)
    assert s["used"] == sum(s["breakdown"].values())
    assert s["used"] == 4


def test_summary_free_is_max_minus_used():
    s = summarize_slots(["attack", "mine"], patrols=1, max_slots=10)
    assert s["max"] == 10
    assert s["free"] == 10 - s["used"]
    assert s["free"] == 7


def test_summary_free_never_negative():
    # Mehr belegt als verfuegbar (z.B. nach Doktrin-Wechsel) -> free wird auf 0 geklemmt.
    s = summarize_slots(["attack", "mine", "expedition", "recycle"], patrols=2, max_slots=3)
    assert s["used"] == 6
    assert s["free"] == 0


# -- Per-Kategorie-Caps (2026-06-22) ----------------------------------------

def test_expedition_slots_sqrt_astrophysics():
    cfg = {"base": 0}
    assert max_expedition_slots(0, 20, cfg) == 0
    assert max_expedition_slots(1, 20, cfg) == 1
    assert max_expedition_slots(4, 20, cfg) == 2
    assert max_expedition_slots(9, 20, cfg) == 3
    assert max_expedition_slots(16, 20, cfg) == 4


def test_expedition_slots_capped_by_total():
    # ⌊√100⌋ = 10, aber nur 3 Flottenslots -> gedeckelt auf 3.
    assert max_expedition_slots(100, 3, {"base": 0}) == 3


def test_mining_slots_base_plus_prospecting():
    cfg = {"base": 1, "per_prospecting": 0.5}
    assert max_mining_slots(0, 20, cfg) == 1
    assert max_mining_slots(2, 20, cfg) == 2
    assert max_mining_slots(4, 20, cfg) == 3


def test_mining_slots_capped_by_total():
    assert max_mining_slots(100, 2, {"base": 1, "per_prospecting": 0.5}) == 2
