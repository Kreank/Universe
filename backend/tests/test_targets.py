"""Tests fuer die DETERMINISTISCHE Auswahl-/Sortierlogik des Ziele/Bedrohungen-Screens
(app.targets.service). DB-/Engine-frei: getestet werden die reinen Helfer (Distanz,
Handelszentrum-Ausschluss, Naehe-Schwelle, Eintrag-Aufbau + Feldlisten, NPC-/Spieler-
Sortierung, Bedrohungs-Zusammenstellung). Stil wie test_chronicle.py."""
import datetime as dt

from app.targets.service import (
    HOSTILE_NPC_NEAR_GALAXIES,
    assemble_threats,
    build_npc_item,
    build_player_item,
    galaxy_distance,
    is_attackable_npc,
    is_near_hostile,
    npc_target_sort_key,
    player_target_sort_key,
)


def _utc(h: int) -> dt.datetime:
    return dt.datetime(2026, 6, 21, h, 0, 0, tzinfo=dt.timezone.utc)


# ----------------------------------------------------------------- Distanz

def test_galaxy_distance_basic():
    assert galaxy_distance(3, 7) == 4
    assert galaxy_distance(7, 3) == 4
    assert galaxy_distance(5, 5) == 0


def test_galaxy_distance_no_home():
    assert galaxy_distance(None, 9) is None


# ----------------------------------------------- Handelszentrum-Ausschluss

def test_trade_center_excluded():
    assert is_attackable_npc("trade_center") is False
    assert is_attackable_npc("merchant") is True
    assert is_attackable_npc("aggressive") is True
    assert is_attackable_npc(None) is True  # Default-Profil ist angreifbar


# ----------------------------------------------------------- Naehe-Schwelle

def test_is_near_hostile_threshold():
    assert is_near_hostile(0) is True
    assert is_near_hostile(HOSTILE_NPC_NEAR_GALAXIES) is True
    assert is_near_hostile(HOSTILE_NPC_NEAR_GALAXIES + 1) is False
    assert is_near_hostile(None) is False


def test_is_near_hostile_custom_radius():
    assert is_near_hostile(3, max_distance=3) is True
    assert is_near_hostile(4, max_distance=3) is False


# --------------------------------------------------- Eintrag-Aufbau (Felder)

def test_build_npc_item_field_list_and_intel():
    item = build_npc_item(
        npc_id="npc-1", name="Eiserne Hand", behavior_profile="aggressive",
        galaxy=2, system=44, position=6,
        intel={"name": "Eiserne Hand", "ships_total": 120, "defenses_total": 30},
        level=3, relation_status="hostile",
        discovered_at="2026-06-20T10:00:00+00:00", home_galaxy=2,
    )
    assert set(item) == {
        "npc_id", "name", "behavior_profile", "galaxy", "system", "position",
        "coords", "intel_level", "ships_total", "defenses_total",
        "relation_status", "distance_galaxies", "last_intel_at",
    }
    assert item["coords"] == "2:44:6"
    assert item["ships_total"] == 120 and item["defenses_total"] == 30
    assert item["intel_level"] == 3
    assert item["distance_galaxies"] == 0
    assert item["relation_status"] == "hostile"


def test_build_npc_item_defaults_when_no_intel():
    item = build_npc_item(
        npc_id="x", name="", behavior_profile="", galaxy=1, system=1, position=1,
        intel=None, level=1, relation_status=None, discovered_at=None, home_galaxy=None,
    )
    assert item["name"] == "1:1:1"  # Fallback-Name aus Koordinaten
    assert item["behavior_profile"] == "defensive"  # Profil-Fallback
    assert item["ships_total"] == 0 and item["defenses_total"] == 0
    assert item["distance_galaxies"] is None


def test_build_player_item_field_list():
    item = build_player_item(
        player_id="p-9", name="Nova", galaxy=5, system=10, position=3,
        intel={"ships_total": 80}, level=2, has_trade_offer=True,
        discovered_at="2026-06-19T08:00:00+00:00", home_galaxy=4,
    )
    assert set(item) == {
        "player_id", "name", "galaxy", "system", "position", "coords",
        "intel_level", "ships_total", "has_trade_offer", "distance_galaxies",
        "last_intel_at",
    }
    assert item["coords"] == "5:10:3"
    assert item["ships_total"] == 80
    assert item["has_trade_offer"] is True
    assert item["distance_galaxies"] == 1


# --------------------------------------------------- NPC-Sortierung

def test_npc_sort_hostile_before_neutral_then_near():
    items = [
        {"relation_status": "neutral", "distance_galaxies": 0, "ships_total": 10, "name": "Nah-Neutral"},
        {"relation_status": "hostile", "distance_galaxies": 5, "ships_total": 10, "name": "Fern-Feind"},
        {"relation_status": "hostile", "distance_galaxies": 1, "ships_total": 10, "name": "Nah-Feind"},
        {"relation_status": "allied", "distance_galaxies": 0, "ships_total": 10, "name": "Verbuendet"},
    ]
    items.sort(key=npc_target_sort_key)
    names = [i["name"] for i in items]
    # Feindliche zuerst (nah vor fern), dann neutral, Verbuendete ganz hinten.
    assert names == ["Nah-Feind", "Fern-Feind", "Nah-Neutral", "Verbuendet"]


def test_npc_sort_none_status_treated_as_neutral_and_stronger_first():
    items = [
        {"relation_status": None, "distance_galaxies": 2, "ships_total": 5, "name": "Schwach"},
        {"relation_status": "neutral", "distance_galaxies": 2, "ships_total": 50, "name": "Stark"},
    ]
    items.sort(key=npc_target_sort_key)
    # Gleiche Distanz/Rang -> staerkeres Ziel zuerst.
    assert [i["name"] for i in items] == ["Stark", "Schwach"]


def test_npc_sort_missing_distance_goes_last():
    items = [
        {"relation_status": "hostile", "distance_galaxies": None, "ships_total": 1, "name": "Unbekannt"},
        {"relation_status": "hostile", "distance_galaxies": 9, "ships_total": 1, "name": "Fern"},
    ]
    items.sort(key=npc_target_sort_key)
    assert [i["name"] for i in items] == ["Fern", "Unbekannt"]


# --------------------------------------------------- Spieler-Sortierung

def test_player_sort_near_then_strong():
    items = [
        {"distance_galaxies": 3, "ships_total": 10, "name": "Fern"},
        {"distance_galaxies": 0, "ships_total": 5, "name": "Nah-Schwach"},
        {"distance_galaxies": 0, "ships_total": 99, "name": "Nah-Stark"},
    ]
    items.sort(key=player_target_sort_key)
    assert [i["name"] for i in items] == ["Nah-Stark", "Nah-Schwach", "Fern"]


# --------------------------------------------------- Bedrohungs-Zusammenstellung

def test_threats_incoming_sorted_by_arrival_first():
    incoming = [
        {"attacker": "Spaet", "kind": "npc", "origin": "1:1:1",
         "target": {"galaxy": 2, "system": 2, "position": 2}, "ships_total": 50,
         "arrive_at": _utc(12), "mission": "attack", "intel_level": 2},
        {"attacker": "Frueh", "kind": "player", "origin": "3:3:3",
         "target": {"galaxy": 2, "system": 2, "position": 2}, "ships_total": 80,
         "arrive_at": _utc(9), "mission": "attack", "intel_level": 1},
    ]
    out = assemble_threats(incoming, [])
    assert [t["name"] for t in out] == ["Frueh", "Spaet"]
    assert all(t["kind"] == "incoming" for t in out)
    assert out[0]["attacker_kind"] == "player"
    assert out[0]["priority"] == 0
    assert out[0]["arrive_at"] == _utc(9).isoformat()


def test_threats_incoming_before_hostile_npc():
    incoming = [
        {"attacker": "Angreifer", "kind": "npc", "origin": "1:1:1",
         "target": {"galaxy": 2, "system": 2, "position": 2}, "ships_total": 10,
         "arrive_at": _utc(20), "mission": "attack", "intel_level": 1},
    ]
    hostile = [
        {"kind": "hostile_npc", "name": "Lauernd", "npc_id": "n1",
         "origin": "2:3:4", "ships_total": 5, "intel_level": 1,
         "distance_galaxies": 0, "priority": 1},
    ]
    out = assemble_threats(incoming, hostile)
    # Eingehender Angriff (akut) vor latentem feindlichem NPC — trotz spaeterer Ankunft.
    assert [t["kind"] for t in out] == ["incoming", "hostile_npc"]
    # Aufraeumen: kein internes Sortier-Feld nach aussen.
    assert all("_arrive_epoch" not in t for t in out)


def test_threats_hostile_npc_sorted_by_distance():
    hostile = [
        {"kind": "hostile_npc", "name": "Fern", "distance_galaxies": 3, "ships_total": 1, "priority": 1},
        {"kind": "hostile_npc", "name": "Nah", "distance_galaxies": 0, "ships_total": 1, "priority": 1},
    ]
    out = assemble_threats([], hostile)
    assert [t["name"] for t in out] == ["Nah", "Fern"]


def test_threats_empty():
    assert assemble_threats([], []) == []
