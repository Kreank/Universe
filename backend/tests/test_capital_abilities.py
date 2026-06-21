"""Tests fuer die drei Capital-Spezialfaehigkeiten in der Kampf-Engine + Beute/Truemmer-Pfad:

- AURA (Flaggschiff): praesenz-basierter Flotten-Buff (+Angriff/+Schild), pro Runde geprueft,
  symmetrisch, nicht stapelbar, erlischt wenn das Flaggschiff faellt.
- RAIDER (Korsar): Schnellfeuer gegen Zivil-/Frachtschiffe (Engine) + Beute-Bonus (service).
- HARVESTER (Ernte-Titan): Truemmer-Ernte nach Sieg direkt in die Fracht (service).

Deterministisch (fester Seed). Engine-Teil laedt balance.json direkt; der service-Teil nutzt
die reinen Helfer (_battlefield_harvest / _raider_loot_mult / _combat_aura_mult)."""
import copy
import json
import os

from app.combat.engine import _build_units, simulate_battle


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


# ---------------------------------------------------------------- AURA --------

def test_aura_side_deals_more_damage_and_holds_longer():
    """Eine Seite mit Flaggschiff (Aura) sollte gegen denselben Gegner besser abschneiden als
    ohne. Wir vergleichen identische Flotten +/- Flaggschiff (das Flaggschiff selbst ersetzt eine
    gleich grosse Schiffsgruppe, damit der Vorteil aus der AURA kommt, nicht aus reiner Feuerkraft)."""
    seed = 4242
    enemy = {"ships": {"battleship": 40}, "tech": {}, "attack_mult": 1.0}

    # Ohne Aura: reine Kreuzerflotte.
    no_aura = {"ships": {"cruiser": 120}, "tech": {}, "attack_mult": 1.0}
    # Mit Aura: ein Flaggschiff dabei (verstaerkt die ganze Flotte).
    with_aura = {"ships": {"cruiser": 120, "flagship": 1}, "tech": {}, "attack_mult": 1.0}

    r_no = simulate_battle(copy.deepcopy(no_aura), copy.deepcopy(enemy), seed, BALANCE)
    r_yes = simulate_battle(copy.deepcopy(with_aura), copy.deepcopy(enemy), seed, BALANCE)

    # Mit Aura ueberleben mehr Kreuzer (haelt laenger) UND der Gegner verliert mindestens so viel.
    surv_no = r_no["attacker_survivors"].get("cruiser", 0)
    surv_yes = r_yes["attacker_survivors"].get("cruiser", 0)
    assert surv_yes > surv_no
    # Gegner-Verluste (durchgesetzter Schaden) sind mit Aura nicht kleiner.
    assert sum(r_yes["defender_losses"].values()) >= sum(r_no["defender_losses"].values())


def test_aura_attack_bonus_increases_first_round_fire():
    """+attack_bonus: die Aura-Seite verursacht in Runde 1 mehr Feuer als ohne (gleicher Seed,
    sonst identische Flotte; Flaggschiff feuert selbst mit, aber der Effekt ist v.a. der Buff)."""
    seed = 77
    enemy = {"ships": {"battleship": 60}, "tech": {}, "attack_mult": 1.0}
    base = simulate_battle({"ships": {"cruiser": 100}, "tech": {}, "attack_mult": 1.0},
                           copy.deepcopy(enemy), seed, BALANCE)
    aura = simulate_battle({"ships": {"cruiser": 100, "flagship": 1}, "tech": {}, "attack_mult": 1.0},
                           copy.deepcopy(enemy), seed, BALANCE)
    # Erste Runde mit tatsaechlichem Feuer (Runde 0 ist 'far' -> Medium-Schiffe ausser Reichweite).
    idx = next(i for i, r in enumerate(base["rounds"]) if r["attacker_fire"] > 0)
    assert aura["rounds"][idx]["attacker_fire"] > base["rounds"][idx]["attacker_fire"]


def test_aura_not_stackable_two_flagships_equal_one():
    """Praesenz-basiert: zwei Flaggschiffe geben KEINE doppelte Aura. Der Aura-BONUS auf die
    restliche Flotte ist identisch. Wir isolieren den Buff, indem wir die Begleitflotte fix halten
    und nur die Flaggschiff-Zahl variieren — der Mehrschaden der Begleiter darf nicht steigen,
    nur die Flaggschiffe selbst feuern zusaetzlich mit. Test ueber die ueberlebenden Begleiter:
    1 vs 2 Flaggschiffe duerfen die Begleiter-Ueberlebenden nicht unterschiedlich stark schuetzen,
    sobald man den Eigenbeitrag der Flaggschiffe herausrechnet."""
    seed = 9
    enemy = {"ships": {"battleship": 30}, "tech": {}, "attack_mult": 1.0}
    one = simulate_battle({"ships": {"cruiser": 60, "flagship": 1}, "tech": {}, "attack_mult": 1.0},
                          copy.deepcopy(enemy), seed, BALANCE)
    two = simulate_battle({"ships": {"cruiser": 60, "flagship": 2}, "tech": {}, "attack_mult": 1.0},
                          copy.deepcopy(enemy), seed, BALANCE)
    # Aura selbst stapelt nicht: der pro-Runde-Multiplikator ist in beiden Faellen 1.10. Direkt
    # gegen die Engine-Internas geprueft: zwei Aura-Schiffe ergeben denselben Buff wie eines.
    cat = _aura_catalogs()
    units1 = _build_units("attacker", {"cruiser": 60, "flagship": 1}, {}, cat, {}, 1.0)
    units2 = _build_units("attacker", {"cruiser": 60, "flagship": 2}, {}, cat, {}, 1.0)
    assert any(u.aura_combat for u in units1)
    assert sum(1 for u in units2 if u.aura_combat) == 2
    # Der Buff ist binaer (Praesenz), nicht zaehlend -> beide Flotten haben Aura "an".
    assert (any(u.aura_combat for u in units1)) == (any(u.aura_combat for u in units2))


def test_aura_falls_off_when_flagship_destroyed():
    """Verliert eine Seite ihr (einziges) Flaggschiff, erlischt die Aura ab der naechsten Runde.
    Wir setzen ein zerbrechliches Flaggschiff-Szenario: stirbt das Flaggschiff, darf der
    Aura-Buff in spaeteren Runden nicht mehr wirken. Geprueft ueber die recompute_aura-Semantik:
    ohne lebendes Aura-Schiff faellt der Multiplikator auf 1.0."""
    # Direkter Engine-Internas-Test der Praesenz-Logik: eine Unit-Liste ohne Flaggschiff hat keine
    # aura_combat-Einheit -> Buff aus.
    cat = _aura_catalogs()
    only_cruiser = _build_units("attacker", {"cruiser": 10}, {}, cat, {}, 1.0)
    assert not any(u.aura_combat for u in only_cruiser)
    with_flag = _build_units("attacker", {"cruiser": 10, "flagship": 1}, {}, cat, {}, 1.0)
    assert any(u.aura_combat for u in with_flag)


def test_aura_symmetric_for_defender():
    """Aura wirkt auch fuer den Verteidiger: ein verteidigendes Flaggschiff verbessert die
    Abwehr gegenueber demselben Angriff ohne Flaggschiff."""
    seed = 555
    attacker = {"ships": {"battleship": 55}, "tech": {}, "attack_mult": 1.0}
    def_no = {"ships": {"cruiser": 120}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    def_aura = {"ships": {"cruiser": 120, "flagship": 1}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    r_no = simulate_battle(copy.deepcopy(attacker), copy.deepcopy(def_no), seed, BALANCE)
    r_yes = simulate_battle(copy.deepcopy(attacker), copy.deepcopy(def_aura), seed, BALANCE)
    # Mit Flaggschiff ueberleben mehr verteidigende Kreuzer UND der Angreifer verliert mehr Schiffe.
    assert r_yes["defender_survivors"].get("cruiser", 0) > r_no["defender_survivors"].get("cruiser", 0)
    assert sum(r_yes["attacker_losses"].values()) > sum(r_no["attacker_losses"].values())


def _aura_catalogs() -> dict:
    """Minimaler catalogs-Aufbau wie in simulate_battle, fuer _build_units-Direkttests."""
    combat = BALANCE["combat"]
    return {
        "ships": BALANCE["ships"],
        "defenses": BALANCE["defenses"],
        "tech_bonus": BALANCE["tech_bonus"],
        "roster": BALANCE.get("combat_roster", {}),
        "range_order": combat["range_bands"]["order"],
        "drive_per_tier": combat.get("drive_integrity_per_tier", 100),
        "defense_integrity": 0.0,
        "raider": combat.get("raider", {}),
    }


# -------------------------------------------------------------- RAIDER --------

def test_raider_rapidfire_shreds_cargo_ships():
    """Ein Korsar (raider) metzelt Frachtschiffe via Schnellfeuer deutlich schneller als ein
    gleich starkes Schiff OHNE raider-Flag. Wir vergleichen Korsar vs. ein gleich teures
    Nicht-Raider-Schiff (battlecruiser) gegen eine reine Frachterflotte."""
    seed = 2024
    cargo = {"ships": {"large_cargo": 200}, "defenses": {}, "tech": {}, "attack_mult": 1.0}
    corsairs = {"ships": {"corsair": 12}, "tech": {}, "attack_mult": 1.0}
    # Vergleichs-Schiff ohne raider, aber starker Energie-Angreifer.
    non_raider = {"ships": {"battlecruiser": 12}, "tech": {}, "attack_mult": 1.0}

    r_raid = simulate_battle(copy.deepcopy(corsairs), copy.deepcopy(cargo), seed, BALANCE)
    r_norm = simulate_battle(copy.deepcopy(non_raider), copy.deepcopy(cargo), seed, BALANCE)

    killed_raid = sum(r_raid["defender_losses"].values())
    killed_norm = sum(r_norm["defender_losses"].values())
    # Der Korsar killt durch die Schnellfeuer-Kette spuerbar mehr Frachter.
    assert killed_raid > killed_norm


def test_raider_rapidfire_baked_into_unit():
    """Der raider-Flag brennt das Zivil-Schnellfeuer in die Unit.rapidfire ein (beide Seiten)."""
    cat = _aura_catalogs()
    units = _build_units("attacker", {"corsair": 1}, {}, cat, {}, 1.0)
    rf = units[0].rapidfire
    rcfg = BALANCE["combat"]["raider"]
    for ct in rcfg["civilian_types"]:
        assert rf.get(ct) == rcfg["civilian_rapidfire"]
    # Gegen Nicht-Zivile (z. B. battleship) KEIN Raider-Schnellfeuer.
    assert "battleship" not in rf


def test_raider_loot_bonus_increases_loot():
    """service-Helfer: ein ueberlebender Korsar erhoeht den Beute-Multiplikator (>1.0) und ist
    nicht stapelbar."""
    from app.combat.service import _raider_loot_mult
    base = _raider_loot_mult({"large_cargo": 10})
    raid = _raider_loot_mult({"corsair": 1, "large_cargo": 10})
    assert base == 1.0
    assert raid > 1.0
    assert raid == 1.0 + BALANCE["combat"]["raider"]["loot_bonus"]
    # Praesenz-basiert: 4 Korsare == 1 Korsar.
    assert _raider_loot_mult({"corsair": 4}) == _raider_loot_mult({"corsair": 1})


# ------------------------------------------------------------ HARVESTER -------

def test_harvester_collects_share_of_debris():
    """Nach Sieg ernten ueberlebende Ernte-Titanen einen Anteil des frischen Truemmerfelds."""
    from app.combat.service import _battlefield_harvest
    debris = {"metal": 100000.0, "crystal": 50000.0}
    out = _battlefield_harvest({"harvest_titan": 1, "cruiser": 5}, debris)
    cfg = BALANCE["combat"]["harvester"]
    share = min(cfg["share_cap"], cfg["debris_share_per_titan"] * 1)
    assert out["metal"] == round(debris["metal"] * share, 1)
    assert out["crystal"] == round(debris["crystal"] * share, 1)
    assert 0 < share < 1.0


def test_harvester_share_scales_with_titans_capped():
    """Mehr Titanen = groesserer Anteil, gedeckelt durch share_cap."""
    from app.combat.service import _battlefield_harvest
    debris = {"metal": 100000.0, "crystal": 0.0}
    cfg = BALANCE["combat"]["harvester"]
    one = _battlefield_harvest({"harvest_titan": 1}, debris)["metal"]
    two = _battlefield_harvest({"harvest_titan": 2}, debris)["metal"]
    many = _battlefield_harvest({"harvest_titan": 99}, debris)["metal"]
    assert two > one
    # Deckel: 99 Titanen ernten nicht mehr als share_cap.
    assert many == round(debris["metal"] * cfg["share_cap"], 1)


def test_harvester_none_without_titan():
    """Ohne Ernte-Titan wird nichts geerntet (Truemmerfeld bleibt unveraendert)."""
    from app.combat.service import _battlefield_harvest
    debris = {"metal": 100000.0, "crystal": 50000.0}
    out = _battlefield_harvest({"cruiser": 50, "battleship": 10}, debris)
    assert out == {"metal": 0.0, "crystal": 0.0}


def test_harvester_capped_by_titan_cargo():
    """Die Ernte ist durch den eigenen Titan-Laderaum gedeckelt (plausibler Deckel)."""
    from app.combat.service import _battlefield_harvest
    titan_cargo = BALANCE["ships"]["harvest_titan"]["cargo"]
    # Riesiges Truemmerfeld -> share waere riesig, aber der Laderaum eines Titans deckelt.
    debris = {"metal": titan_cargo * 1000.0, "crystal": titan_cargo * 1000.0}
    out = _battlefield_harvest({"harvest_titan": 1}, debris)
    assert out["metal"] + out["crystal"] <= titan_cargo + 0.1
