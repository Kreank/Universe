"""Smoke-Tests fuer die deterministische Kampf-Engine.

Laedt balance.json direkt (ohne DB/Config-Abhaengigkeit) -> reine Engine-Pruefung."""
import copy
import json
import os

from app.combat.engine import simulate_battle


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


def test_battle_is_deterministic_with_same_seed():
    attacker = {"ships": {"cruiser": 20}, "tech": {}, "attack_mult": 1.0}
    defender = {
        "ships": {"light_fighter": 40},
        "defenses": {"rocket_launcher": 10},
        "tech": {},
        "attack_mult": 1.0,
    }
    r1 = simulate_battle(attacker, defender, 42, BALANCE)
    r2 = simulate_battle(attacker, defender, 42, BALANCE)
    assert r1 == r2
    assert r1["seed"] == 42
    assert len(r1["rounds"]) <= BALANCE["combat"]["max_rounds"]


def test_strong_attacker_wins():
    attacker = {"ships": {"cruiser": 50}, "tech": {"weapons_tech": 5}, "attack_mult": 1.1}
    defender = {"ships": {"light_fighter": 5}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 7, BALANCE)
    assert result["winner"] == "attacker"
    assert result["defender_survivors"] == {}


def test_result_structure_and_losses_consistency():
    attacker = {"ships": {"light_fighter": 10}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"light_fighter": 10}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 123, BALANCE)
    for key in ("rounds", "winner", "attacker_survivors", "defender_survivors",
                "attacker_initial", "attacker_losses"):
        assert key in result
    # Anfangsbestand = Ueberlebende + Verluste (pro Typ).
    for typ, initial in result["attacker_initial"].items():
        surv = result["attacker_survivors"].get(typ, 0)
        lost = result["attacker_losses"].get(typ, 0)
        assert surv + lost == initial


def test_shield_bounce_protects_against_tiny_hits():
    # Spionagesonden (attack 0) koennen einen Kreuzer nicht beschaedigen -> Sonden verlieren.
    attacker = {"ships": {"spy_probe": 30}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"cruiser": 1}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 99, BALANCE)
    assert result["defender_survivors"].get("cruiser", 0) == 1


# ---- Rollen-Kampf Phase 1 (Doku 03b): Subsysteme, Schadenstyp-Matrix, Reichweite ----

def test_range_far_fires_before_near_engages():
    """Reichweiten-Baender: in Runde 1 (Distanz 'far') feuert nur die Fern-Einheit.
    Artillerie (destroyer, far) trifft, der Nah-Schwarm (light_fighter) kann noch nicht."""
    attacker = {"ships": {"light_fighter": 30}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"destroyer": 5}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 5, BALANCE)
    first = result["rounds"][0]
    assert first["distance"] == "far"
    assert first["attacker_fire"] == 0.0   # Nah-Schiffe ausserhalb der Reichweite
    assert first["defender_fire"] > 0.0     # Fern-Artillerie hat Standoff-Vorteil


def test_ion_disables_drive_without_destroying():
    """Ionen-Waffe (ion_cannon) leert Schild + legt Antrieb lahm, toetet aber NICHT (hull 0).
    Waffenlose Sonden koennen nicht zurueckfeuern -> Antrieb wird lahmgelegt, Huelle bleibt heil."""
    attacker = {"ships": {"spy_probe": 5}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {}, "defenses": {"ion_cannon": 30}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 11, BALANCE)
    # Sonden ueberleben (Ionen macht keinen Huellenschaden) ...
    assert result["attacker_survivors"].get("spy_probe", 0) > 0
    # ... aber ihr Antrieb ist lahmgelegt ("mission kill").
    assert result["attacker_drive_disabled"].get("spy_probe", 0) > 0


def test_energy_cracks_shield_kinetic_bounces():
    """Schadenstyp-Matrix als Konter: gegen eine grosse Schildkuppel (Schild 10000) knackt eine
    Energie-Flotte (cruiser) den Schild und zerstoert sie; eine gleich grosse kinetische Flotte
    (battleship) prallt ab und kommt nicht durch — TROTZ hoeherer Rohgewalt (attack 1000 vs 400).
    Die Matrix, nicht die rohe Feuerkraft, entscheidet."""
    dome = {"ships": {}, "defenses": {"large_shield_dome": 1}, "tech": {}, "attack_mult": 1.0}
    energy = {"ships": {"cruiser": 30}, "tech": {}, "attack_mult": 1.0}
    kinetic = {"ships": {"battleship": 30}, "tech": {}, "attack_mult": 1.0}
    e_res = simulate_battle(energy, dict(dome), 21, BALANCE)
    k_res = simulate_battle(kinetic, dict(dome), 21, BALANCE)
    assert e_res["winner"] == "attacker"               # Energie bricht den Schild -> Kuppel faellt
    assert k_res["defender_survivors"].get("large_shield_dome", 0) == 1  # Kinetik prallt ab


# ---- Rollen-Kampf Phase 2 (Doku 03b §4): Disengage / Antriebs-Stufen / Interdiktion ----

def test_outgunned_attacker_disengages():
    """Eine hoffnungslos unterlegene Angreifer-Flotte zieht sich zurueck (Antrieb intakt) statt
    vernichtet zu werden: einige Jaeger fliehen, ueberleben und gelten nicht als Verlust."""
    attacker = {"ships": {"light_fighter": 6}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"battleship": 50}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 3, BALANCE)
    fled = result["attacker_fled"].get("light_fighter", 0)
    assert fled > 0                                            # Rueckzug fand statt
    surv = result["attacker_survivors"].get("light_fighter", 0)
    lost = result["attacker_losses"].get("light_fighter", 0)
    assert surv + lost == 6 and surv >= fled                   # Geflohene zaehlen als Ueberlebende
    assert result["winner"] == "defender"                      # Verteidiger haelt das Feld


def test_defender_holds_by_default():
    """Verteidiger fliehen standardmaessig NICHT (halten Stellung) -> werden bei Unterlegenheit vernichtet."""
    attacker = {"ships": {"cruiser": 80}, "tech": {"weapons_tech": 6}, "attack_mult": 1.1}
    defender = {"ships": {"light_fighter": 4}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 7, BALANCE)
    assert result["defender_fled"] == {}
    assert result["defender_survivors"].get("light_fighter", 0) == 0


def test_interdictor_suppresses_disengage():
    """Interdiktor-Feld (combat_roster.interdictor) drueckt die Flucht-Chance auf 0:
    dieselbe unterlegene Flotte kann mit genug Interdiktoren nicht mehr entkommen."""
    bal = copy.deepcopy(BALANCE)
    bal["combat_roster"]["battleship"]["interdictor"] = True  # Schlachtschiffe als Fang-Schiffe
    attacker = {"ships": {"light_fighter": 6}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"battleship": 50}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 3, bal)
    assert result["attacker_fled"] == {}                       # Fang-Feld: niemand entkommt


# ---- Rollen-Kampf Phase 3 (Doku 03b §4/§7): Entern / Capture ----

def test_boarder_captures_stranded_ships():
    """Piraterie-Loop: EWAR-Fregatten (Ionen) stranden die Kreuzer (Antrieb 0, Huelle heil),
    Enterschiffe kapern die Gestrandeten -> der Angreifer gewinnt die Schiffe."""
    attacker = {"ships": {"ewar_frigate": 40, "boarder": 10}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"cruiser": 8}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 5, BALANCE)
    captured = result["attacker_captured"].get("cruiser", 0)
    assert captured > 0                                        # es wurde gekapert
    # Gekaperte zaehlen NICHT mehr als Verteidiger-Ueberlebende.
    assert captured + result["defender_survivors"].get("cruiser", 0) <= 8


def test_no_capture_without_boarder():
    """Ohne Enterschiff wird NICHT gekapert: EWAR strandet nur (Antrieb lahm), Kreuzer bleiben."""
    attacker = {"ships": {"ewar_frigate": 40}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"cruiser": 8}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 5, BALANCE)
    assert result["attacker_captured"] == {}
    assert result["defender_survivors"].get("cruiser", 0) == 8     # alle ueberleben ...
    assert result["defender_drive_disabled"].get("cruiser", 0) == 8  # ... aber gestrandet
