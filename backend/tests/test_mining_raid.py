"""Mining-Raid (2026-06-15): geparkte Schuerf-Flotten sind angreifbar und ihre Fracht
(Erz + Exoten) ist erbeutbar. Reine Helfer + Beute-Logik (kein DB-Harness im Slice)."""
import datetime as dt
from types import SimpleNamespace

from app.combat.service import (
    CARGO_LOOT_KEYS,
    _compute_loot,
    _distribute_attacker_loot,
    _greedy_take,
)
from app.fleet.mining import is_parked_mining
from app.fleet.stationing import distribute_losses

UTC = dt.timezone.utc


def _fleet(mission="mine", status="arrived", g=1, s=2, p=3, hold_until=None):
    return SimpleNamespace(
        mission=mission, status=status,
        target_galaxy=g, target_system=s, target_position=p,
        mission_data={"hold_until": hold_until} if hold_until is not None else {},
    )


# ---- 1) Parked-Fleet-Detection ---------------------------------------------

def test_is_parked_mining_true_within_hold_window():
    now = dt.datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    f = _fleet(hold_until=(now + dt.timedelta(hours=1)).isoformat())
    assert is_parked_mining(f, 1, 2, 3, now) is True


def test_is_parked_mining_false_after_hold_until():
    now = dt.datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    f = _fleet(hold_until=(now - dt.timedelta(minutes=1)).isoformat())
    # Nach hold_until fliegt die Flotte heim -> nicht mehr "am Feld" (Abfangen deckt das ab).
    assert is_parked_mining(f, 1, 2, 3, now) is False


def test_is_parked_mining_false_wrong_mission_status_coords_or_no_hold():
    now = dt.datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    hold = (now + dt.timedelta(hours=1)).isoformat()
    assert is_parked_mining(_fleet(mission="attack", hold_until=hold), 1, 2, 3, now) is False
    assert is_parked_mining(_fleet(status="done", hold_until=hold), 1, 2, 3, now) is False
    assert is_parked_mining(_fleet(hold_until=hold), 9, 9, 9, now) is False          # andere Koordinate
    assert is_parked_mining(_fleet(hold_until=None), 1, 2, 3, now) is False          # kein hold_until


def test_is_parked_mining_handles_naive_timestamp():
    now = dt.datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    naive = dt.datetime(2026, 6, 15, 13, 0).isoformat()  # ohne tz -> als UTC interpretiert
    assert is_parked_mining(_fleet(hold_until=naive), 1, 2, 3, now) is True


# ---- 2) Beute der Fracht inkl. Exoten --------------------------------------

def test_greedy_take_includes_exotics_capped_by_capacity():
    cargo = {"metal": 1000, "crystal": 1000, "deuterium": 0, "antimatter": 500, "dark_matter": 300}
    # Kapazitaet 2200: m 1000 + k 1000 + d 0 + antimatter 200 (Rest), dann voll.
    out = _greedy_take(cargo, 2200, CARGO_LOOT_KEYS)
    assert out["metal"] == 1000
    assert out["crystal"] == 1000
    assert out["deuterium"] == 0
    assert out["antimatter"] == 200
    assert out["dark_matter"] == 0
    assert sum(out.values()) == 2200


def test_greedy_take_unlimited_capacity_takes_all_exotics():
    cargo = {"metal": 100, "antimatter": 50, "dark_matter": 25}
    out = _greedy_take(cargo, 10_000, CARGO_LOOT_KEYS)
    assert out["antimatter"] == 50
    assert out["dark_matter"] == 25


def test_compute_loot_unchanged_three_keys_only():
    # _compute_loot bleibt auf Erz beschraenkt (50 % Plunder) — keine Exoten von Planeten/NPC.
    loot = _compute_loot({"metal": 1000, "crystal": 0, "deuterium": 0, "antimatter": 999}, 10_000)
    assert set(loot) == {"metal", "crystal", "deuterium"}
    assert loot["metal"] == 500.0


def test_distribute_attacker_loot_writes_exotics_into_fleet_cargo():
    src = {"obj": SimpleNamespace(cargo={"metal": 10}), "survivors": {"small_cargo": 1}}
    loot = {"metal": 100, "crystal": 0, "deuterium": 0, "antimatter": 30, "dark_matter": 20}
    _distribute_attacker_loot([src], loot)
    cargo = src["obj"].cargo
    assert cargo["metal"] == 110          # bestehende + Beute
    assert cargo["antimatter"] == 30
    assert cargo["dark_matter"] == 20


# ---- 3) Verteidiger-Schiffsverluste + 4) Flotte wiped -> done ---------------

def test_mining_defender_losses_distributed_and_wipe_detected():
    # Zwei schuerfende Flotten als Verteidiger-Quellen; nur 4 von 10 fighter ueberleben gesamt.
    sources = [
        {"kind": "mining", "ships": {"miner": 6, "fighter": 0}},
        {"kind": "mining", "ships": {"fighter": 10}},
    ]
    per = distribute_losses(sources, {"miner": 6, "fighter": 4})
    assert per[0] == {"miner": 6}                  # erste Quelle voll erhalten
    assert per[1] == {"fighter": 4}               # zweite teilweise
    assert sum(per[0].values()) > 0               # ueberlebt
    # Eine restlos vernichtete Quelle -> wiped -> Flotte wird auf 'done' gesetzt.
    wiped = distribute_losses([{"kind": "mining", "ships": {"fighter": 5}}], {})
    assert sum(wiped[0].values()) == 0
