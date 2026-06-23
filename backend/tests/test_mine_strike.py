"""Minen-Streik: gewichtete Schwere-Stufen (2026-06-22, Spieler-Feedback). Testet den reinen
Stufen-Wuerfel ``pick_strike_tier`` (DB-freier Helfer) und die Doppel-Streik-Sperre
(2026-06-23, Spieler-Feedback: Streiks stapelten sich auf demselben Planeten)."""
import asyncio
import uuid
from types import SimpleNamespace

from app.events.personal import pick_strike_tier, trigger_mine_strike

TIERS = [
    {"key": "unruhe", "weight": 40, "bribe_deuterium": 12000},
    {"key": "streik", "weight": 40, "bribe_deuterium": 30000},
    {"key": "aufstand", "weight": 20, "bribe_deuterium": 60000},
]


def test_empty_tiers_returns_empty():
    assert pick_strike_tier([], 0.5) == {}
    assert pick_strike_tier([{"weight": 0}], 0.5) == {}


def test_roll_zero_picks_first():
    assert pick_strike_tier(TIERS, 0.0)["key"] == "unruhe"


def test_roll_bands_select_correct_tier():
    # Gesamtgewicht 100: [0,40)=unruhe, [40,80)=streik, [80,100)=aufstand.
    assert pick_strike_tier(TIERS, 0.2)["key"] == "unruhe"   # 20
    assert pick_strike_tier(TIERS, 0.5)["key"] == "streik"   # 50
    assert pick_strike_tier(TIERS, 0.9)["key"] == "aufstand"  # 90


def test_roll_near_one_picks_last():
    assert pick_strike_tier(TIERS, 0.999)["key"] == "aufstand"


def test_higher_price_couples_with_severity_in_balance():
    # Balance-Sanity: hoeherer Bestechungspreis -> staerkerer Einbruch (kleinerer mult)
    # + hoeherer Moralverlust (gekoppelt, wie vom Spieler gewuenscht).
    import json
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(6):
        cand = os.path.join(d, "shared", "balance.json")
        if os.path.isfile(cand):
            bal = json.load(open(cand, encoding="utf-8"))
            break
        d = os.path.dirname(d)
    tiers = bal["events"]["personal"]["mine_strike"]["tiers"]
    ordered = sorted(tiers, key=lambda t: t["bribe_deuterium"])
    prices = [t["bribe_deuterium"] for t in ordered]
    mults = [t["production_mult"] for t in ordered]
    morale = [t["force_morale_penalty"] for t in ordered]
    assert prices == sorted(prices)
    assert mults == sorted(mults, reverse=True)   # teurer -> kleinerer mult (mehr Verlust)
    assert morale == sorted(morale)               # teurer -> mehr Moralverlust


# -- Doppel-Streik-Sperre ----------------------------------------------------

class _Result:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _GuardSession:
    """Minimal-Session: ``execute`` liefert einen Treffer (= bereits aktiver Streik am Planeten).
    ``add`` wird mitgeschrieben, um zu pruefen, dass KEIN neues Event angelegt wird."""

    def __init__(self, hit):
        self._hit = hit
        self.added = []

    async def execute(self, *_a, **_k):
        return _Result(("vorhandener-streik",) if self._hit else None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


def test_mine_strike_skips_when_already_active():
    # Laeuft auf dem Planeten schon ein Streik, darf kein zweiter angelegt werden (sonst
    # stapeln sich Produktions-Debuffs und bezahlst du einen, bleibt der andere aktiv).
    planet = SimpleNamespace(id=uuid.uuid4(), galaxy=1, system=89, position=2, name="Testwelt")
    player = SimpleNamespace(id=uuid.uuid4())
    session = _GuardSession(hit=True)
    out = asyncio.run(trigger_mine_strike(session, player, planet, {}))
    assert out is False
    assert session.added == []  # kein neues CosmicEvent angelegt
