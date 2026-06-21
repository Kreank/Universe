"""Tests fuer die Mk-II-Veredelung (Welle W3 — Endgame-Schiffe).

Geprueft wird die statisch in ``shared/balance.json`` abgelegte Mk-II-Ableitung
(``<typ>_mk2``): korrekte Werte gegen die ``ships._mk2_factors``, Vollstaendigkeit/
Sanity (jedes Mk2 hat einen existierenden Parent, kein Mk2-vom-Mk2, Capstones
ausgenommen) und ein Ranking-Smoke (Mk2 > Mk1 im Imperiumswert). Stil wie
test_chronicle.py / test_npc_diplomacy.py (BALANCE_PATH-Fallback fuers balance-Lesen)."""
import json
import os

from app.ranking.service import _unit_value


def _load_balance() -> dict:
    # balance.json wird im Container ueber BALANCE_PATH gemountet; lokal liegt es unter shared/.
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("BALANCE_PATH") or os.path.normpath(
        os.path.join(here, "..", "..", "shared", "balance.json")
    )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


BALANCE = _load_balance()
SHIPS = BALANCE["ships"]
ROSTER = BALANCE["combat_roster"]
FACTORS = SHIPS["_mk2_factors"]
CAPSTONES = ("flagship", "corsair", "trade_leviathan", "harvest_titan")


def _real_ships() -> dict:
    return {k: v for k, v in SHIPS.items() if not k.startswith("_") and isinstance(v, dict)}


# ----------------------------------------------------------- Faktoren / Ableitung

def test_mk2_factors_present_and_sane():
    for key in ("attack", "shield", "cargo", "speed", "cost", "fuel", "fuel_tank", "antimatter_pct"):
        assert key in FACTORS
    # Nutzen-Werte: +25% besser in der Rolle.
    assert FACTORS["attack"] == 1.25
    assert FACTORS["shield"] == 1.25
    assert FACTORS["cargo"] == 1.25
    assert FACTORS["speed"] == 1.25
    # Nachteile/Kosten.
    assert FACTORS["cost"] == 1.3
    assert FACTORS["fuel"] == 1.3
    assert FACTORS["fuel_tank"] == 1.3
    assert 0 < FACTORS["antimatter_pct"] < 1


def test_derived_values_for_examples():
    """Stichproben: Kampf-, Roll- und zivile Schiffe."""
    f = FACTORS
    for name in ("light_fighter", "battleship", "small_cargo"):
        mk1 = SHIPS[name]
        mk2 = SHIPS[f"{name}_mk2"]

        # Nutzen-Werte: jeder vorhandene ×eigener Faktor (+25% besser in der Rolle).
        assert mk2["attack"] == round(mk1["attack"] * f["attack"])
        assert mk2["shield"] == round(mk1["shield"] * f["shield"])
        assert mk2["cargo"] == round(mk1["cargo"] * f["cargo"])
        assert mk2["speed"] == round(mk1["speed"] * f["speed"])

        for k in ("metal", "crystal", "deuterium"):
            assert mk2["cost"][k] == round(mk1["cost"].get(k, 0) * f["cost"])
        expected_am = round(f["antimatter_pct"] * (mk1["cost"].get("metal", 0) + mk1["cost"].get("crystal", 0)))
        assert mk2["cost"].get("antimatter", 0) == expected_am
        assert mk2["cost"]["antimatter"] > 0

        assert mk2["fuel"] == round(mk1["fuel"] * f["fuel"])
        assert mk2["fuel_tank"] == round(mk1["fuel_tank"] * f["fuel_tank"])

        # rapidfire wird vom Mk1 uebernommen (Mk1-Ziele, kein Remapping).
        assert mk2.get("rapidfire", {}) == mk1.get("rapidfire", {})


def test_mk2_is_better_in_its_role():
    """Kernforderung: Mk2 ist in seiner ROLLE spuerbar besser (nicht nur Kampfwerte)."""
    f = FACTORS
    # Transporter: laedt mehr (cargo) — sonst waere ein Mk2-Transporter nutzlos.
    for name in ("small_cargo", "large_cargo"):
        mk1, mk2 = SHIPS[name], SHIPS[f"{name}_mk2"]
        assert mk2["cargo"] == round(mk1["cargo"] * f["cargo"])
        assert mk2["cargo"] > mk1["cargo"]
        assert mk2["speed"] > mk1["speed"]
    # Kampfschiff: schiesst staerker (attack) und fliegt schneller (speed).
    for name in ("light_fighter", "cruiser", "battleship"):
        mk1, mk2 = SHIPS[name], SHIPS[f"{name}_mk2"]
        assert mk2["attack"] == round(mk1["attack"] * f["attack"])
        assert mk2["attack"] > mk1["attack"]
        assert mk2["speed"] == round(mk1["speed"] * f["speed"])
        assert mk2["speed"] > mk1["speed"]

        # Gate-Forschung + Herkunft.
        assert mk2["requires"].get("veteran_shipyard") == 1
        # Parent-requires (z. B. Antriebs-Tech) bleiben erhalten -> ship_speed greift weiter.
        for rk, rv in mk1.get("requires", {}).items():
            assert mk2["requires"].get(rk) == rv
        assert mk2["mk2_parent"] == name


# ----------------------------------------------------------- Sanity / Vollstaendigkeit

def test_every_non_capstone_ship_has_mk2():
    for name, cfg in _real_ships().items():
        if name.endswith("_mk2") or "mk2_parent" in cfg or cfg.get("capstone"):
            continue
        assert f"{name}_mk2" in SHIPS, f"Mk2 fehlt fuer {name}"


def test_capstones_have_no_mk2():
    for cap in CAPSTONES:
        assert SHIPS[cap].get("capstone")           # weiterhin Capstone
        assert f"{cap}_mk2" not in SHIPS            # keine Veredelung


def test_every_mk2_has_existing_parent_and_no_mk2_of_mk2():
    mk2s = {k: v for k, v in _real_ships().items() if k.endswith("_mk2")}
    assert mk2s, "Keine Mk2-Eintraege gefunden"
    for name, cfg in mk2s.items():
        parent = cfg.get("mk2_parent")
        assert parent in SHIPS, f"{name}: Parent {parent!r} fehlt"
        assert not parent.endswith("_mk2"), f"{name}: Mk2-vom-Mk2 ({parent})"
        assert "mk2_parent" not in SHIPS[parent], f"{name}: Parent ist selbst ein Mk2"
        assert not SHIPS[parent].get("capstone"), f"{name}: Parent ist Capstone"


def test_every_mk2_has_a_combat_roster_entry():
    """Sonst faellt das Mk2 still auf das kinetic/near-Default-Profil zurueck (Combat-Bug)."""
    for name in _real_ships():
        if name.endswith("_mk2"):
            assert name in ROSTER, f"Roster-Profil fehlt fuer {name}"


def test_mk2_roster_matches_parent_profile():
    mk1 = SHIPS["escort_frigate"]  # Rollen-Schiff mit point_defense-Flag
    assert "escort_frigate" in ROSTER
    parent_prof = {k: v for k, v in ROSTER["escort_frigate"].items() if k != "aura"}
    assert ROSTER["escort_frigate_mk2"] == parent_prof
    assert ROSTER["escort_frigate_mk2"].get("point_defense") is True


def test_veteran_shipyard_research_present():
    techs = BALANCE["research"]["techs"]
    assert "veteran_shipyard" in techs
    vs = techs["veteran_shipyard"]
    assert vs["cost"]["metal"] > 0 and vs["cost"]["crystal"] > 0
    assert vs.get("requires"), "veteran_shipyard sollte Endgame-requires haben"


# ----------------------------------------------------------- Ranking-Smoke

def test_mk2_unit_value_higher_than_mk1():
    """Imperiumswert (Ressourcensumme) eines Mk2 > Mk1 — die generische Wertung greift."""
    for name in ("cruiser", "battleship"):
        v1 = _unit_value(SHIPS, name, 1)
        v2 = _unit_value(SHIPS, f"{name}_mk2", 1)
        assert v2 > v1, f"{name}_mk2 sollte hoeher gewertet sein als {name}"
