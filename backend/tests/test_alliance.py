"""Tests fuer Allianzen: reine Logik (Forschungskosten, Bonus-Resolver-Magnitude + Kontext,
Station-Zone, Balance-Block). DB-gebundene Pfade (Pool/Verwaltung) integrativ geprueft."""
from app.alliance import research as R
from app.alliance import station as S
from app.alliance.bonus import _lever_index, magnitude_for
from app.platform.balance import get_balance
from app.platform.models import Alliance, AllianceStation


# -- Forschungskosten -----------------------------------------------------------

def test_repeatable_node_cost_linear():
    cfg = R.find_node("piracy", "raid_loot")  # repeatable
    assert cfg["repeatable"] is True
    base = cfg["cost"]
    # member_count=1 -> kein Mitglieder-Aufschlag; linear base*(level+1).
    c0 = R.cost_for_next_level(cfg, 0, 1)
    c2 = R.cost_for_next_level(cfg, 2, 1)
    assert c0["metal"] == round(base["metal"], 2)
    assert c2["metal"] == round(base["metal"] * 3, 2)


def test_nonrepeatable_node_cost_exponential():
    cfg = R.find_node("piracy", "pack_hunt")  # nicht repeatable
    assert not cfg.get("repeatable")
    base = cfg["cost"]
    c3 = R.cost_for_next_level(cfg, 3, 1)
    assert c3["metal"] == round(base["metal"] * 8, 2)


def test_member_scaling_increases_cost():
    cfg = R.find_node("economy", "extraction_zone")
    solo = R.cost_for_next_level(cfg, 0, 1)["metal"]
    big = R.cost_for_next_level(cfg, 0, 11)["metal"]  # +10 Mitglieder
    factor = get_balance().data["alliance"]["research"]["member_cost_factor_per_member"]
    assert big == round(solo * (1 + factor * 10), 2)
    assert big > solo


def test_level_of_reads_research_levels():
    al = Alliance(research_levels={"piracy.raid_loot": 4})
    assert R.level_of(al, "piracy", "raid_loot") == 4
    assert R.level_of(al, "economy", "extraction_zone") == 0


# -- Bonus-Resolver (Magnitude + Kontext) ---------------------------------------

def test_lever_index_unique_and_complete():
    idx = _lever_index()
    trees = get_balance().data["alliance"]["research"]["trees"]
    total = sum(len(t["nodes"]) for t in trees.values())
    assert len(idx) == total == 20  # 4 Baeume x 5 Knoten, Lever eindeutig


def test_magnitude_scales_with_level():
    al = Alliance(research_levels={"piracy.raid_loot": 3})
    mag, ctx = magnitude_for(al, "raid_loot_mult")
    assert ctx == "coop"
    assert abs(mag - 0.15) < 1e-9  # 3 * per_level 0.05


def test_magnitude_zero_when_unresearched():
    al = Alliance(research_levels={})
    mag, ctx = magnitude_for(al, "mining_yield_zone")
    assert mag == 0.0
    assert ctx == "zone"


def test_unknown_lever_is_zero():
    al = Alliance(research_levels={"piracy.raid_loot": 5})
    assert magnitude_for(al, "does_not_exist") == (0.0, "")


# -- Station-Zone ---------------------------------------------------------------

def _station(**kw):
    base = dict(status="active", fuel=100.0, galaxy=1, system=50, research_radius_level=0)
    base.update(kw)
    return AllianceStation(**base)


def test_zone_radius_base_and_upgrade():
    cfg = get_balance().data["alliance"]["station"]
    assert S.zone_radius(_station(research_radius_level=0)) == cfg["base_radius"]
    # Cap greift bei hoher Stufe.
    assert S.zone_radius(_station(research_radius_level=99)) == cfg["max_radius"]


def test_covers_within_radius_same_galaxy():
    st = _station(research_radius_level=0)  # Radius 1
    assert S.covers(st, 1, 50) is True
    assert S.covers(st, 1, 51) is True
    assert S.covers(st, 1, 52) is False
    assert S.covers(st, 2, 50) is False  # andere Galaxie


def test_covers_requires_active_and_fueled():
    assert S.covers(_station(fuel=0.0), 1, 50) is False
    assert S.covers(_station(status="inactive"), 1, 50) is False
    assert S.covers(_station(status="destroyed"), 1, 50) is False


# -- Balance-Block --------------------------------------------------------------

def test_alliance_balance_block():
    a = get_balance().data["alliance"]
    assert a["max_members"] == 50
    assert set(a["research"]["trees"]) == {"piracy", "economy", "trade", "protection"}
    assert a["station"]["base_radius"] == 1 and a["station"]["max_radius"] == 5
    assert a["station"]["destroy_min_attackers"] == 2


# -- Phase 2: Koop-Kampf + Stations-Belagerung ----------------------------------

import datetime as dt  # noqa: E402

from app.alliance import coop as C  # noqa: E402


def test_phase2_balance_block():
    a = get_balance().data["alliance"]
    assert a["coop"]["stage_window_seconds"] > 0
    st = a["station"]
    assert st["hp_regen_per_tick"] > 0
    assert st["siege_window_seconds"] > 0
    assert st["siege_damage_factor"] > 0
    assert "plasma_turret" in st["defense_base"]
    assert "weapons_tech" in st["defense_tech"]


def test_split_loot_by_capacity_proportional():
    parts = C.split_loot_by_capacity([100.0, 300.0], {"metal": 400.0, "crystal": 0.0, "deuterium": 0.0})
    assert parts[0]["metal"] == 100.0
    assert parts[1]["metal"] == 300.0


def test_split_loot_zero_capacity_drops_loot():
    parts = C.split_loot_by_capacity([0.0, 0.0], {"metal": 50.0})
    assert parts == [{"metal": 0.0}, {"metal": 0.0}]


def test_merge_ships_sums_across_sources():
    src = [{"ships": {"cruiser": 3}}, {"ships": {"cruiser": 2, "drone": 5}}]
    assert C.merge_ships(src) == {"cruiser": 5, "drone": 5}


class _Obj:
    def __init__(self, pid):
        self.player_id = pid


def test_distinct_players_dedups():
    src = [{"obj": _Obj("a")}, {"obj": _Obj("a")}, {"obj": _Obj("b")}]
    assert len(C.distinct_players(src)) == 2


def test_station_defenses_scale_with_radius():
    cfg = get_balance().data["alliance"]["station"]
    base = S.station_defenses(_station(research_radius_level=0))
    up = S.station_defenses(_station(research_radius_level=3))
    assert base["plasma_turret"] == cfg["defense_base"]["plasma_turret"]
    assert up["plasma_turret"] > base["plasma_turret"]


def test_station_defender_shape():
    d = S.station_defender(_station())
    assert d["ships"] == {}
    assert d["defenses"]
    assert d["tech"]["weapons_tech"] > 0
    assert d["attack_mult"] == 1.0


def test_siege_requires_min_distinct_attackers():
    now = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    st = _station(hp=1000.0, position=8, siege={})
    r1 = S.record_siege_hit(st, "p1", 5000.0, now)  # bringt hp auf 0
    assert st.hp == 0
    assert r1["destroyed"] is False and r1["distinct_attackers"] == 1
    assert st.status != "destroyed"
    r2 = S.record_siege_hit(st, "p2", 100.0, now)   # zweiter Spieler -> Zerstoerung
    assert r2["destroyed"] is True and r2["distinct_attackers"] == 2
    assert st.status == "destroyed"


def test_siege_window_prunes_old_attacker():
    cfg = get_balance().data["alliance"]["station"]
    window = float(cfg["siege_window_seconds"])
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    st = _station(hp=100000.0, siege={})
    S.record_siege_hit(st, "p1", 10.0, t0)
    later = t0 + dt.timedelta(seconds=window + 10)
    r = S.record_siege_hit(st, "p2", 10.0, later)  # p1 ist aus dem Fenster gefallen
    assert r["distinct_attackers"] == 1


def test_siege_same_attacker_accumulates_damage():
    now = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    st = _station(hp=1000.0, siege={})
    S.record_siege_hit(st, "p1", 300.0, now)
    S.record_siege_hit(st, "p1", 200.0, now)
    assert st.siege["attackers"]["p1"]["damage"] == 500.0
    assert st.hp == 500.0
    assert len(st.siege["attackers"]) == 1
