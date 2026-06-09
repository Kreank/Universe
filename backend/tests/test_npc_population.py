"""Verifiziert den NPC-Populations-Spawner (npc/population.py).

DB-/Auth-frei: getestet werden die reinen Hilfsfunktionen (gewichtete Profilwahl,
Dichte-/Spawn-Plan, eindeutige Namensvergabe) sowie die Config-Sanity der Templates
(alle Profile vorhanden, alle Schiff-/Defense-Typen existieren im Katalog -- faengt
Tippfehler in shared/balance.json ab). Balance wird per Pfad-Suche geladen (wie
test_combat_sim.py)."""
import json
import os

from app.npc.population import (
    _density_deficit,
    _pick_name,
    _underserved_players,
    _weighted_profile,
)


def _load_balance() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(6):
        candidate = os.path.join(d, "shared", "balance.json")
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as fh:
                return json.load(fh)
        d = os.path.dirname(d)
    raise FileNotFoundError("balance.json nicht gefunden")


BALANCE = _load_balance()
POP = BALANCE["npc"]["population"]


# -- _weighted_profile -------------------------------------------------------

def test_weighted_profile_picks_first_at_zero():
    """rnd=0 -> erstes Profil mit positivem Gewicht."""
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    assert _weighted_profile(weights, 0.0) == "a"


def test_weighted_profile_picks_last_near_one():
    """rnd -> 1 faellt ins letzte Band."""
    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    assert _weighted_profile(weights, 0.9999) == "c"


def test_weighted_profile_middle_band():
    """rnd in der Mitte des ersten Bandes -> erstes Profil; knapp darueber -> zweites."""
    weights = {"a": 0.5, "b": 0.5}
    assert _weighted_profile(weights, 0.4) == "a"
    assert _weighted_profile(weights, 0.6) == "b"


def test_weighted_profile_robust_to_unnormalized_sum():
    """Gewichts-Summe != 1.0 wird normiert (Band-Grenzen anteilig)."""
    weights = {"a": 2.0, "b": 1.0}  # Summe 3.0 -> a deckt 0..2/3
    assert _weighted_profile(weights, 0.5) == "a"
    assert _weighted_profile(weights, 0.8) == "b"


def test_weighted_profile_empty_falls_back():
    """Keine positiven Gewichte -> defensiver Fallback statt Crash."""
    assert _weighted_profile({}, 0.5) == "defensive"
    assert _weighted_profile({"x": 0.0}, 0.5) == "defensive"


# -- _density_deficit / _underserved_players ---------------------------------

_CFG = {"radius_systems": 10, "target_per_player": 6, "max_spawns_per_tick": 3}


def test_deficit_zero_when_density_full():
    """Genug NPCs im Umkreis -> kein Spawn-Bedarf."""
    player_systems = [50]
    npc_systems = [45, 46, 47, 48, 49, 51]  # 6 im Umkreis -> Ziel erreicht
    assert _density_deficit(player_systems, npc_systems, _CFG) == 0
    assert _underserved_players(player_systems, npc_systems, _CFG) == []


def test_deficit_capped_when_empty_neighbourhood():
    """Leere Nachbarschaft -> Defizit = target, aber gedeckelt durch max_spawns_per_tick."""
    player_systems = [50]
    npc_systems: list[int] = []
    # target=6, cap=3 -> 3
    assert _density_deficit(player_systems, npc_systems, _CFG) == 3
    assert _underserved_players(player_systems, npc_systems, _CFG) == [50]


def test_deficit_ignores_far_npcs():
    """NPCs ausserhalb des Radius zaehlen nicht zur Dichte."""
    player_systems = [50]
    npc_systems = [10, 90]  # beide ausserhalb radius 10
    assert _density_deficit(player_systems, npc_systems, _CFG) == 3  # cap


def test_deficit_no_players_is_zero():
    """Keine Spieler -> nichts zu beleben."""
    assert _density_deficit([], [1, 2, 3], _CFG) == 0


# -- _pick_name --------------------------------------------------------------

def test_pick_name_unique_across_calls():
    """Mehrfache Aufrufe mit demselben Pool erzeugen keine Duplikate."""
    templates = POP["templates"]
    used: set[str] = set()
    names = [
        _pick_name("aggressive", templates, used, designation=i)
        for i in range(10)
    ]
    assert len(names) == len(set(names)), "Namens-Duplikat erzeugt"
    # Alle wurden registriert.
    assert used == set(names)


def test_pick_name_unknown_profile_falls_back():
    """Profil ohne Pool -> Fallback-Basis statt Crash."""
    used: set[str] = set()
    name = _pick_name("ghost", {}, used, designation=42)
    assert name and name not in (set() - {name})


# -- Config-Sanity (faengt Template-Tippfehler ab) ---------------------------

def test_population_templates_cover_all_profiles():
    """Alle vier Profile haben ein Template."""
    templates = POP["templates"]
    for profile in ("aggressive", "defensive", "merchant", "expansive"):
        assert profile in templates, f"Template fehlt: {profile}"
        assert templates[profile]["name_pool"], f"name_pool leer: {profile}"


def test_population_template_ship_and_defense_types_exist():
    """Alle in Templates referenzierten Schiff-/Defense-Typen existieren im Katalog."""
    ships = BALANCE["ships"]
    defenses = BALANCE["defenses"]
    for profile, tpl in POP["templates"].items():
        for stype in tpl.get("fleet", {}):
            assert stype in ships, f"unbekannter Schiffstyp '{stype}' in {profile}"
        for dtype in tpl.get("defenses", {}):
            assert dtype in defenses, f"unbekannter Defense-Typ '{dtype}' in {profile}"


def test_population_profile_weights_match_templates():
    """Gewichtete Profile haben ein passendes Template (keine Waisen)."""
    for profile in POP["profile_weights"]:
        assert profile in POP["templates"], f"Gewicht ohne Template: {profile}"
