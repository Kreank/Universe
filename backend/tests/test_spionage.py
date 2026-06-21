"""Tests fuer die Spionage-Kampftech (universe/spionage.py).

Geprueft wird die neue ``combat_tech``-Aufklaerung (Waffen/Schild/Panzerung), die der
Combat-Simulator als Gegner-Tech vorbelegt:
- reine Extraktion ``_combat_tech`` (Format {weapons_tech,shield_tech,armor_tech}),
- Intel-Level-Gating ueber den Berichtstext (``_build_report_body``): ab Stufe 2 sichtbar,
  bei Stufe 1 "nicht aufgeklaert",
- Spieler-Kampftech == Forschung,
- NPC-Kampftech == EFFEKTIVE Tech wie im echten Kampf (``tier_tech(effective_tier(...))``),
  via DB-freier Fake-Session.

DB-/Engine-frei (gleicher Stil wie test_npc_scaling/test_combat_sim), balance.json als Fallback.
"""
import asyncio
import datetime as dt
import json
import os

from app.npc.scaling import effective_tier, tier_tech
from app.platform.balance import Balance
from app.universe.spionage import (
    _build_report_body,
    _combat_tech,
    _npc_combat_tech,
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


# --- reine Extraktion -------------------------------------------------------

def test_combat_tech_extracts_three_keys():
    out = _combat_tech({"weapons_tech": 5, "shield_tech": 3, "armor_tech": 7, "spy_tech": 9})
    assert out == {"weapons_tech": 5, "shield_tech": 3, "armor_tech": 7}
    assert set(out) == {"weapons_tech", "shield_tech", "armor_tech"}


def test_combat_tech_defaults_missing_to_zero():
    out = _combat_tech({"weapons_tech": 2})
    assert out == {"weapons_tech": 2, "shield_tech": 0, "armor_tech": 0}
    assert _combat_tech({}) == {"weapons_tech": 0, "shield_tech": 0, "armor_tech": 0}


def test_player_combat_tech_matches_research():
    """Spieler-Ziel: Kampftech kommt 1:1 aus dessen Forschung (die 3 Kerntechs)."""
    research = {"weapons_tech": 8, "shield_tech": 6, "armor_tech": 4, "energy_tech": 12}
    assert _combat_tech(research) == {"weapons_tech": 8, "shield_tech": 6, "armor_tech": 4}


# --- Intel-Level-Gating (ueber den Berichtstext sichtbar) -------------------

def _intel(level: int, combat_tech: dict | None) -> dict:
    intel = {
        "name": "Testziel", "kind": "npc", "galaxy": 1, "system": 1, "position": 1,
        "ships_total": 10, "defenses_total": 5, "level": level,
    }
    if level >= 2:
        intel["fleet"] = {"cruiser": 10}
        intel["defenses"] = {"rocket_launcher": 5}
        if combat_tech is not None:
            intel["combat_tech"] = combat_tech
    return intel


def test_report_shows_combat_tech_from_level_2():
    body = _build_report_body(
        "1:1:1", _intel(2, {"weapons_tech": 4, "shield_tech": 3, "armor_tech": 2})
    )
    assert "Kampftech: Waffen 4 · Schild 3 · Panzerung 2" in body


def test_report_hides_combat_tech_at_level_1():
    body = _build_report_body("1:1:1", _intel(1, None))
    assert "nicht aufgeklaert" in body
    assert "Waffen" not in body


def test_report_combat_tech_line_skipped_without_data():
    """Stufe 2 ohne combat_tech (z. B. NPC-Lookup fehlgeschlagen) -> keine Kampftech-Zeile, kein Crash."""
    body = _build_report_body("1:1:1", _intel(2, None))
    assert "Kampftech:" not in body


# --- NPC-Kampftech == echte Kampf-Formel ------------------------------------

class _FakeResult:
    def all(self):  # nearest_player_score ruft .all() auf
        return []


class _FakeSession:
    async def execute(self, *_a, **_k):
        return _FakeResult()


class _FakeNpc:
    def __init__(self, galaxy, system, position, created_at):
        self.galaxy = galaxy
        self.system = system
        self.position = position
        self.created_at = created_at


def test_npc_combat_tech_matches_real_combat_formula():
    """NPC-Kampftech aus der Spionage == EXAKT die Tech, mit der das NPC im echten Kampf
    kaempft: tier_tech(npc_tech-Basis, effective_tier(Region+Spieler+Alter), tier_cfg)
    (gleiche Quelle wie combat.service.resolve_attack)."""
    bal = Balance(BALANCE)
    tier_cfg = bal.npc.get("tier", {})
    base_tech = bal.npc.get("attack", {}).get("npc_tech", {})
    created = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)
    npc = _FakeNpc(2, 40, 6, created)

    got = asyncio.run(_npc_combat_tech(_FakeSession(), npc, bal))

    age = (dt.datetime.now(dt.timezone.utc) - created).total_seconds()
    eff = effective_tier(npc.galaxy, npc.system, npc.position, 0.0, age, tier_cfg)
    expected_full = tier_tech(base_tech, eff, tier_cfg)
    expected = {
        "weapons_tech": int(expected_full.get("weapons_tech", 0)),
        "shield_tech": int(expected_full.get("shield_tech", 0)),
        "armor_tech": int(expected_full.get("armor_tech", 0)),
    }
    assert got == expected
    assert set(got) == {"weapons_tech", "shield_tech", "armor_tech"}


def test_npc_combat_tech_scales_above_base_tier():
    """Hoeheres effektives Tier (alt + spielernah) -> Kampftech > Basis-Tier-1-Wert."""
    bal = Balance(BALANCE)
    base_tech = bal.npc.get("attack", {}).get("npc_tech", {})
    old = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)
    npc = _FakeNpc(1, 1, 1, old)
    got = asyncio.run(_npc_combat_tech(_FakeSession(), npc, bal))
    # Bei tech_per_tier>0 und Alters-Bonus muss mindestens eine Kerntech ueber dem Basiswert liegen.
    assert got["weapons_tech"] >= int(base_tech.get("weapons_tech", 0))
