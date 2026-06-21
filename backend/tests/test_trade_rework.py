"""Tests fuer den Handels-Umbau (Forschung ``trade_network`` + Gebaeude ``trade_center``).

Geprueft werden (DB-frei wo moeglich, Stubs sonst):
- die reine Reichweiten-Berechnung des Handelsnetzes (Stufe 0 = eigene Galaxie, +1/Stufe,
  + Gebaeude-Bonus) — ``trade_network_reach``;
- der Handelszentrum-Marge-Bonus senkt die effektive Marge / erhoeht die erhaltene Ware
  (``effective_margin`` + ``simulate_swap`` mit ``extra_margin_reduction``);
- die One-per-Account-Validierung (zweiter Bau auf einem anderen Planeten abgelehnt) ueber
  ``one_per_account_blocked`` mit einer Fake-Session;
- die History-Serialisierung (``serialize_trade_log``);
- die Sanity der neuen balance-Bloecke (Tech/Gebaeude/Effekt).

Balance-Lade-Logik (Pfad-Suche) wie in ``test_trade_pricing.py``.
"""
import asyncio
import datetime as dt
import json
import os
import uuid

from app.buildings.service import one_per_account_blocked
from app.fleet.trade import trade_network_reach
from app.fleet.trade_pricing import effective_margin, simulate_swap
from app.fleet.trade_router import serialize_trade_log


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
CFG = BALANCE["trade"]
SETPOINT = CFG["default_setpoint"]


def _flat_stock(metal=2_000_000, crystal=1_000_000, deuterium=500_000) -> dict:
    return {"metal": metal, "crystal": crystal, "deuterium": deuterium}


# --- Reichweite des Handelsnetzes (rein) ----------------------------------

def test_reach_level0_is_home_galaxy_only():
    """Stufe 0 = Reichweite 0 = nur die eigene Galaxie (Handel nie hart gesperrt)."""
    assert trade_network_reach(0, 1, 0) == 0


def test_reach_grows_one_galaxy_per_level():
    assert trade_network_reach(1, 1, 0) == 1
    assert trade_network_reach(3, 1, 0) == 3
    # per_level skaliert linear.
    assert trade_network_reach(2, 2, 0) == 4


def test_reach_building_bonus_adds_on_top():
    # Ohne Forschung, aber mit Handelszentrum: schon +1 Galaxie ueber die eigene hinaus.
    assert trade_network_reach(0, 1, 1) == 1
    assert trade_network_reach(2, 1, 1) == 3


def test_reach_clamps_negatives():
    assert trade_network_reach(-5, 1, 0) == 0
    assert trade_network_reach(1, -1, -1) == 0


# --- Marge-Bonus des Handelszentrums --------------------------------------

def test_effective_margin_extra_reduction_lowers_margin():
    base = effective_margin(0, CFG)
    reduced = effective_margin(0, CFG, extra_reduction=0.02)
    assert reduced == max(0.0, base - 0.02)
    assert reduced < base


def test_effective_margin_never_negative():
    # Riesiger Bonus -> Marge wird auf 0 geklemmt, nie negativ.
    assert effective_margin(0, CFG, extra_reduction=10.0) == 0.0


def test_simulate_swap_margin_bonus_increases_received():
    """Niedrigere Marge -> hoeheres Budget -> mehr erhaltene Ware (gleicher Markt)."""
    stock = _flat_stock()
    baseline = simulate_swap("metal", 10_000, "crystal", stock, SETPOINT, CFG)
    boosted = simulate_swap(
        "metal", 10_000, "crystal", stock, SETPOINT, CFG,
        extra_margin_reduction=float(BALANCE["buildings"]["trade_center"]["trade_margin_reduction"]),
    )
    assert boosted["margin"] < baseline["margin"]
    assert boosted["received"] >= baseline["received"]
    assert boosted["received"] > 0


# --- One-per-Account-Validierung (Fake-Session) ---------------------------

class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeSession:
    """Minimal-Session: ``execute`` liefert eine konfigurierte scalar()-Antwort."""

    def __init__(self, count):
        self._count = count
        self.calls = 0

    async def execute(self, *args, **kwargs):
        self.calls += 1
        return _FakeResult(self._count)


class _FakePlanet:
    def __init__(self):
        self.id = uuid.uuid4()
        self.player_id = uuid.uuid4()


def test_one_per_account_not_blocked_when_none_elsewhere():
    session = _FakeSession(count=0)
    blocked = asyncio.run(one_per_account_blocked(session, _FakePlanet(), "trade_center"))
    assert blocked is False
    assert session.calls == 1  # hat die Zaehl-Abfrage gemacht


def test_one_per_account_blocked_when_exists_elsewhere():
    session = _FakeSession(count=1)
    blocked = asyncio.run(one_per_account_blocked(session, _FakePlanet(), "trade_center"))
    assert blocked is True


def test_non_unique_building_never_blocked_and_no_query():
    """Nicht-einmalige Gebaeude (z.B. metal_mine) -> immer False, ohne DB-Abfrage."""
    session = _FakeSession(count=99)
    blocked = asyncio.run(one_per_account_blocked(session, _FakePlanet(), "metal_mine"))
    assert blocked is False
    assert session.calls == 0  # Kurzschluss vor dem Query


# --- History-Serialisierung -----------------------------------------------

class _FakeLog:
    def __init__(self, **kw):
        self.id = kw.get("id", uuid.uuid4())
        self.partner_kind = kw.get("partner_kind", "npc")
        self.partner_id = kw.get("partner_id")
        self.partner_name = kw.get("partner_name", "Handelszentrum Aurora")
        self.offered_res = kw.get("offered_res", "metal")
        self.offered_amount = kw.get("offered_amount", 1234.56)
        self.received_res = kw.get("received_res", "crystal")
        self.received_amount = kw.get("received_amount", 78.94)
        self.created_at = kw.get("created_at", dt.datetime(2026, 6, 20, tzinfo=dt.timezone.utc))


def test_serialize_trade_log_shape_and_rounding():
    pid = uuid.uuid4()
    rows = [_FakeLog(partner_id=pid, offered_amount=1234.56, received_amount=78.94)]
    out = serialize_trade_log(rows)
    assert len(out) == 1
    e = out[0]
    assert e["partner_kind"] == "npc"
    assert e["partner_id"] == str(pid)
    assert e["partner_name"] == "Handelszentrum Aurora"
    assert e["offered_res"] == "metal" and e["received_res"] == "crystal"
    assert e["offered_amount"] == 1234.6  # auf 1 Nachkommastelle gerundet
    assert e["received_amount"] == 78.9
    assert e["created_at"].startswith("2026-06-20")


def test_serialize_trade_log_handles_null_partner_id():
    out = serialize_trade_log([_FakeLog(partner_id=None)])
    assert out[0]["partner_id"] is None


def test_serialize_trade_log_empty():
    assert serialize_trade_log([]) == []


# --- balance-Sanity --------------------------------------------------------

def test_balance_has_trade_network_tech():
    tech = BALANCE["research"]["techs"]["trade_network"]
    assert "cost" in tech and tech["cost"]["crystal"] > 0
    assert BALANCE["research"]["effects"]["trade_network_range_per_level"] == 1


def test_balance_has_trade_center_building():
    b = BALANCE["buildings"]["trade_center"]
    assert b["one_per_account"] is True
    assert b["cost"]["metal"] > 0 and "factor" in b
    assert b["trade_margin_reduction"] > 0
    assert b["trade_network_range_bonus"] >= 1
    assert b["hub_margin"] >= 0
