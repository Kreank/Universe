"""Smoke-Tests fuer die deterministische Kampf-Engine.

Laedt balance.json direkt (ohne DB/Config-Abhaengigkeit) -> reine Engine-Pruefung."""
import copy
import json
import os

from app.combat.engine import ambush_detect_chance, simulate_battle


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


def test_warp_stabilizer_counters_interdictor():
    """Warp-Stabilisator (combat_roster.stabilizer) hebt das Interdiktor-Fangfeld auf:
    dieselbe vom Interdiktor festgenagelte Flotte kann mit genug Stabilisatoren wieder fliehen."""
    bal = copy.deepcopy(BALANCE)
    bal["combat_roster"]["battleship"]["interdictor"] = True    # Verteidiger = Fang-Schiffe
    # Ohne Stabilisator: das Fangfeld haelt die unterlegene Flotte fest (Referenz).
    held = simulate_battle(
        {"ships": {"light_fighter": 6}, "tech": {}, "attack_mult": 1.0},
        {"ships": {"battleship": 50}, "defenses": {}, "tech": {}, "attack_mult": 1.0},
        3, bal,
    )
    assert held["attacker_fled"] == {}
    # Mit Stabilisatoren: Interdiktion negiert -> Flucht wieder moeglich.
    relieved = simulate_battle(
        {"ships": {"light_fighter": 6, "warp_stabilizer": 80}, "tech": {}, "attack_mult": 1.0},
        {"ships": {"battleship": 50}, "defenses": {}, "tech": {}, "attack_mult": 1.0},
        3, bal,
    )
    assert relieved["attacker_fled"].get("light_fighter", 0) > 0


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


def test_capture_priority_value_takes_most_valuable_first():
    """A: bei begrenzter Kaper-Kapazität werden die WERTVOLLSTEN gestrandeten Schiffe zuerst
    gekapert (Schlachtschiff teurer als Kreuzer) -> mehr Schlachtschiffe als Kreuzer gekapert."""
    # Viele EWAR stranden alles, wenige Enterer -> Kapazität ist der Engpass, Priorität entscheidet.
    attacker = {"ships": {"ewar_frigate": 200, "boarder": 3}, "tech": {}, "attack_mult": 1.0}
    defender = {"ships": {"battleship": 6, "cruiser": 6}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 5, BALANCE)
    cap = result["attacker_captured"]
    assert cap.get("battleship", 0) > 0
    # Wert-Priorität: nie mehr (billigere) Kreuzer als (teurere) Schlachtschiffe kapern.
    assert cap.get("battleship", 0) >= cap.get("cruiser", 0)


def test_capture_priority_prefers_chosen_type():
    """B: mit capture_priority='cruiser' werden Kreuzer bevorzugt gekapert, obwohl Schlachtschiffe
    wertvoller sind -> mehr Kreuzer als Schlachtschiffe trotz Wert-Nachteil."""
    attacker = {
        "ships": {"ewar_frigate": 200, "boarder": 3}, "tech": {}, "attack_mult": 1.0,
        "capture_priority": "cruiser",
    }
    defender = {"ships": {"battleship": 6, "cruiser": 6}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    result = simulate_battle(attacker, defender, 5, BALANCE)
    cap = result["attacker_captured"]
    assert cap.get("cruiser", 0) > 0
    assert cap.get("cruiser", 0) >= cap.get("battleship", 0)


# ---- Eskorten-Konter (Doku 03b §4): Punktverteidigung + Schild-Tender ----

def test_escort_point_defense_blocks_boarding():
    """Eskort-Fregatten (Punktverteidigung) fangen Enterer ab: dieselbe Pirat-Flotte kapert
    OHNE Eskorte die Kreuzer, MIT genug Eskorten gelingt keine Kaperung."""
    pirates = {"ships": {"ewar_frigate": 40, "boarder": 10}, "tech": {}, "attack_mult": 1.0}
    bare = {"ships": {"cruiser": 8}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    escorted = {"ships": {"cruiser": 8, "escort_frigate": 25}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    r_bare = simulate_battle(pirates, bare, 5, BALANCE)
    r_esc = simulate_battle(pirates, escorted, 5, BALANCE)
    assert r_bare["attacker_captured"].get("cruiser", 0) > 0     # ohne Eskorte: gekapert
    assert r_esc["attacker_captured"] == {}                       # mit Eskorte: abgefangen


def test_shield_tender_counters_stranding():
    """Schild-Tender reparieren Antriebe und verhindern das Ionen-Strand-Fenster:
    OHNE Tender stranden die Kreuzer, MIT genug Tendern bleiben sie manoevrierfaehig."""
    ewar = {"ships": {"ewar_frigate": 12}, "tech": {}, "attack_mult": 1.0}
    bare = {"ships": {"cruiser": 10}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    tended = {"ships": {"cruiser": 10, "shield_tender": 15}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    r_bare = simulate_battle(ewar, bare, 5, BALANCE)
    r_tended = simulate_battle(ewar, tended, 5, BALANCE)
    assert r_bare["defender_drive_disabled"].get("cruiser", 0) >= 5    # ohne Tender: gestrandet
    assert r_tended["defender_drive_disabled"].get("cruiser", 0) < \
        r_bare["defender_drive_disabled"].get("cruiser", 0)            # Tender reduziert Stranding


# ---- Schiff-Sondermechaniken: Stealth-Hinterhalt + Traeger-Drohnen (Doku 03b §9 / 03c) ----

def test_stealth_corvette_opens_with_ambush_round():
    """Tarnkappen-Korvette: der Angreifer eroeffnet mit einer Ueberraschungsrunde (Runde 0),
    in der NUR der Angreifer feuert. Ohne Stealth gibt es diese Runde nicht."""
    pirate = {"ships": {"stealth_corvette": 30}, "tech": {}, "attack_mult": 1.0}
    prey = {"ships": {"cruiser": 5}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    r = simulate_battle(pirate, prey, 5, BALANCE)
    first = r["rounds"][0]
    assert first.get("ambush") is True
    assert first["attacker_fire"] > 0 and first["defender_fire"] == 0.0
    # Ohne Stealth: keine Ueberraschungsrunde.
    r2 = simulate_battle({"ships": {"light_fighter": 30}, "tech": {}, "attack_mult": 1.0}, prey, 5, BALANCE)
    assert r2["rounds"][0].get("ambush") is not True


def test_carrier_drones_are_real_no_ephemeral():
    """Option A (2026-06-10): Traeger spawnen KEINE ephemeren Drohnen mehr. Ein Traeger ohne
    gebaute Drohnen ist nur ein Schiff; ECHTE Drohnen in der Flotte kaempfen mit (echte
    Verluste) und zaehlen als eigene Einheiten. (Das Mitladen aus der Garnison passiert
    in fleet.service.send_fleet und wird dort separat abgedeckt.)"""
    prey = {"ships": {"light_fighter": 60}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    solo = simulate_battle({"ships": {"carrier": 5}, "tech": {}, "attack_mult": 1.0}, prey, 7, BALANCE)
    with_d = simulate_battle({"ships": {"carrier": 5, "drone": 40}, "tech": {}, "attack_mult": 1.0}, prey, 7, BALANCE)
    # Kein ephemerer Schwarm: der Traeger allein richtet deutlich weniger an als mit echten Drohnen.
    assert sum(with_d["defender_losses"].values()) > sum(solo["defender_losses"].values())
    # Echte Drohnen zaehlen als eigene Schiffe; ein Traeger ohne Drohnen hat keine.
    assert with_d["attacker_initial"].get("drone", 0) == 40
    assert "drone" not in solo["attacker_initial"]


# ---- Konter-Dreieck (Doku 03c §6): Artillerie-Glaskanone + Standoff ----

def test_artillery_standoff_beats_line():
    """Artillerie (Destroyer, Fern) ueberreicht die Linie (Schlachtschiff, Mittel) -> Standoff-Sieg."""
    arty = {"ships": {"destroyer": 20}, "tech": {}, "attack_mult": 1.0}
    line = {"ships": {"battleship": 15}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    r = simulate_battle(arty, line, 7, BALANCE)
    assert r["winner"] == "attacker"
    assert r["defender_survivors"].get("battleship", 0) == 0


def test_artillery_is_crackable_glass_cannon():
    """Die Glaskanone (Destroyer: duenner Schild + niedrige Huelle) ist knackbar — seit 03d
    EMERGENT statt per Rapidfire: ein grosser, getechter Jaeger-Schwarm schliesst die Distanz
    und ueberwaeltigt die duenne Huelle durch schiere Masse."""
    swarm = {"ships": {"light_fighter": 400}, "tech": {"weapons_tech": 8}, "attack_mult": 1.0}
    arty = {"ships": {"destroyer": 15}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    r = simulate_battle(swarm, arty, 7, BALANCE)
    assert r["defender_survivors"].get("destroyer", 0) < 15        # nicht mehr unverwundbar


def test_ambush_detect_chance_soft_model():
    """Weiches Entdeckungs-Modell (analog Abfangen): Sensor 1%/Schiff, Cap 90%; spy_tech 0,5%/Stufe
    als reservierte letzte 5%; Gesamt-Cap 95%, nie 100%."""
    cfg = BALANCE["combat"]["ambush"]
    assert ambush_detect_chance(0, 0, cfg) == 0.0
    assert round(ambush_detect_chance(50, 0, cfg), 4) == 0.50
    assert ambush_detect_chance(200, 0, cfg) == 0.90              # Schiffe deckeln bei 90%
    assert ambush_detect_chance(90, 0, cfg) == 0.90              # ohne Forschung nie ueber 90%
    assert round(ambush_detect_chance(50, 10, cfg), 4) == 0.55   # Forschung addiert obendrauf
    assert round(ambush_detect_chance(50, 20, cfg), 4) == 0.55   # Forschungs-Band-Cap (Stufe>10 nutzlos)
    assert ambush_detect_chance(90, 10, cfg) == 0.95             # Gesamt-Cap, letzte 5% nur via Forschung
    assert ambush_detect_chance(200, 40, cfg) == 0.95           # nie 100%


def test_sensor_detection_is_probabilistic():
    """Sensor-Schiffe (Tief-Aufklaerer) entdecken den Hinterhalt mit einer CHANCE statt binaer.
    Viele Sensoren (90 -> 90%) entdecken ueber viele Seeds meist; ohne Sensoren nie."""
    pirate = {"ships": {"stealth_corvette": 30}, "tech": {}, "attack_mult": 1.0}
    guarded = {"ships": {"cruiser": 5, "deep_scout": 90}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    detected = sum(
        1 for s in range(100)
        if simulate_battle(pirate, guarded, s, BALANCE)["rounds"][0].get("ambush") is not True
    )
    assert detected > 60                                          # ~90% erwartet, robust gegen Seed-Varianz
    # Ohne Sensoren: NIE entdeckt -> immer Hinterhalt.
    nosense = {"ships": {"cruiser": 5}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    assert all(
        simulate_battle(pirate, nosense, s, BALANCE)["rounds"][0].get("ambush") is True
        for s in range(20)
    )


# ---- Todesstern-Mondzerstoerung (03d): Chance-Formel ----

def test_moon_destroy_chance_scales_with_deathstars_and_size():
    from app.planets.moon import moon_destroy_chance
    cfg = BALANCE["moon"]["destruction"]
    # Keine Todessterne -> keine Chance.
    assert moon_destroy_chance(0, 10, cfg) == 0.0
    # Mehr Todessterne -> hoehere Chance.
    assert moon_destroy_chance(4, 10, cfg) > moon_destroy_chance(1, 10, cfg)
    # Groesserer Mond (mehr Felder) -> niedrigere Chance.
    assert moon_destroy_chance(3, 30, cfg) < moon_destroy_chance(3, 5, cfg)
    # Cap wird eingehalten.
    assert moon_destroy_chance(100, 1, cfg) <= float(cfg["chance_cap"]) + 1e-9
    # Exakter Wert: 2 RIPs, size_ref 10, mond 10 Felder, chance_per 0.15 -> 0.30.
    assert abs(moon_destroy_chance(2, 10, cfg) - 0.30) < 1e-9


# ---- Determinismus: identisches Ergebnis unabhaengig von der Dict-Reihenfolge (Befund #2) ----

def test_battle_is_invariant_to_ship_dict_order():
    """Die Aufrufer bauen Flotten-Dicts aus ungeordneten DB-Queries. Bei gleichem Seed MUSS das
    Ergebnis identisch sein, egal in welcher Key-Reihenfolge die Schiffe/Verteidigung ankommen
    (sonst koennen Preview und protokollierter Kampf divergieren). _build_units sortiert nach Typ."""
    seed = 123456789
    atk_a = {"ships": {"light_fighter": 60, "cruiser": 12, "battleship": 5}, "tech": {"weapons_tech": 6}, "attack_mult": 1.0}
    # Gleicher Inhalt, andere Insertion-Order:
    atk_b = {"ships": {"battleship": 5, "light_fighter": 60, "cruiser": 12}, "tech": {"weapons_tech": 6}, "attack_mult": 1.0}
    def_a = {"ships": {"heavy_fighter": 30, "destroyer": 4}, "defenses": {"light_laser": 20, "gauss_cannon": 6}, "tech": {}, "attack_mult": 1.0}
    def_b = {"ships": {"destroyer": 4, "heavy_fighter": 30}, "defenses": {"gauss_cannon": 6, "light_laser": 20}, "tech": {}, "attack_mult": 1.0}

    r1 = simulate_battle(atk_a, def_a, seed, BALANCE)
    r2 = simulate_battle(atk_b, def_b, seed, BALANCE)

    for field in ("winner", "attacker_survivors", "defender_survivors",
                  "attacker_losses", "defender_losses"):
        assert r1[field] == r2[field], f"Feld {field} haengt an der Dict-Reihenfolge"
    assert len(r1["rounds"]) == len(r2["rounds"])


# ---- Befund #5/#7: jedes Schiff und jede Verteidigung hat ein combat_roster-Profil ----

def test_every_unit_has_a_combat_roster_entry():
    """Fehlt ein Roster-Eintrag, faellt die Einheit still auf das kinetic/near-Default-Profil
    zurueck (so wurde orbital_gun versehentlich kinetisch, Befund #5). _ -Meta-Keys ausgenommen."""
    roster = BALANCE["combat_roster"]
    missing = []
    for catalog_key in ("ships", "defenses"):
        for typ in BALANCE[catalog_key]:
            if typ.startswith("_"):
                continue
            if typ not in roster:
                missing.append(f"{catalog_key}.{typ}")
    assert not missing, f"Ohne Roster-Profil (stiller kinetic/near-Fallback): {missing}"


def test_roster_weapon_types_exist_in_damage_matrix():
    """Jeder im Roster genutzte weapon_type muss in der damage_matrix definiert sein
    (sonst feuert die Einheit nie -> matrix.get(typ) is None)."""
    matrix = BALANCE["combat"]["damage_matrix"]
    valid = {k for k in matrix if not k.startswith("_")}
    for typ, prof in BALANCE["combat_roster"].items():
        if typ.startswith("_") or not isinstance(prof, dict):
            continue
        wt = prof.get("weapon_type")
        assert wt is None or wt in valid, f"{typ}: unbekannter weapon_type {wt!r}"
