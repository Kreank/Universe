"""Verifiziert die reinen Handels-Helfer (``app.fleet.trade``).

DB-/Auth-frei: getestet werden ausschliesslich die reinen Funktionen
``market_setpoint``, ``ensure_market`` (mit einem Fake-NPC, der nur ein
``.market``-Attribut hat) und ``validate_trade_order``. Die DB-abhaengigen
Pfade (resolve_trade, send_fleet) bleiben bewusst aussen vor.

Lade-Logik (balance.json per Pfad-Suche) wie in ``test_trade_pricing.py``.
"""
import json
import os

from app.fleet.trade import ensure_market, market_setpoint, validate_trade_order


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
RESOURCES = ("metal", "crystal", "deuterium")


class _FakeNpc:
    """Minimaler Ersatz fuer NpcEmpire: nur das ``market``-Attribut wird gebraucht."""

    def __init__(self, market=None):
        self.market = market or {}


# --- market_setpoint ------------------------------------------------------

def test_market_setpoint_scales_per_specialization():
    defaults = CFG["default_setpoint"]
    metal_world = market_setpoint("metal_world", CFG)
    deut_refinery = market_setpoint("deuterium_refinery", CFG)

    # Setpoint = default * Spezialisierungs-Skala.
    specs = CFG["specializations"]
    assert metal_world["metal"] == defaults["metal"] * specs["metal_world"]["metal"]
    assert deut_refinery["deuterium"] == defaults["deuterium"] * specs["deuterium_refinery"]["deuterium"]

    # Die Raffinerie hat einen hoeheren Deuterium-Sollbestand als die Metallwelt.
    assert deut_refinery["deuterium"] > metal_world["deuterium"]
    # ... und die Metallwelt einen hoeheren Metall-Sollbestand.
    assert metal_world["metal"] > deut_refinery["metal"]


def test_market_setpoint_unknown_spec_falls_back_to_generalist():
    generalist = market_setpoint("generalist", CFG)
    unknown = market_setpoint("does_not_exist", CFG)
    assert unknown == generalist


# --- ensure_market --------------------------------------------------------

def test_ensure_market_initialises_spec_and_stock():
    npc = _FakeNpc()
    market = ensure_market(npc, CFG)

    assert market["spec"] in CFG["specializations"]
    # Bestand entspricht dem Sollbestand der gewaehlten Spezialisierung (gerundet).
    setpoint = market_setpoint(market["spec"], CFG)
    for res in RESOURCES:
        assert market["stock"][res] == round(setpoint[res])
    # Markt wurde am NPC persistiert.
    assert npc.market == market


def test_ensure_market_is_idempotent():
    npc = _FakeNpc()
    first = ensure_market(npc, CFG)
    # Zweiter Aufruf darf nichts veraendern (gleiche spec + gleicher Bestand).
    second = ensure_market(npc, CFG)
    assert second["spec"] == first["spec"]
    assert second["stock"] == first["stock"]


def test_ensure_market_keeps_existing_market():
    # Ein bereits gesetzter (auch abweichender) Markt bleibt unangetastet.
    preset = {"spec": "crystal_hub", "stock": {"metal": 1, "crystal": 2, "deuterium": 3}}
    npc = _FakeNpc(market=dict(preset))
    market = ensure_market(npc, CFG)
    assert market == preset


# --- validate_trade_order -------------------------------------------------

def test_validate_trade_order_accepts_valid():
    order = validate_trade_order(
        {"offer_res": "metal", "offer_amount": 1000, "want_res": "deuterium"}, CFG
    )
    assert order == ("metal", 1000.0, "deuterium")


def test_validate_trade_order_rejects_same_resource():
    assert validate_trade_order(
        {"offer_res": "metal", "offer_amount": 1000, "want_res": "metal"}, CFG
    ) is None


def test_validate_trade_order_rejects_non_positive_amount():
    assert validate_trade_order(
        {"offer_res": "metal", "offer_amount": 0, "want_res": "crystal"}, CFG
    ) is None
    assert validate_trade_order(
        {"offer_res": "metal", "offer_amount": -5, "want_res": "crystal"}, CFG
    ) is None


def test_validate_trade_order_rejects_unknown_resource():
    assert validate_trade_order(
        {"offer_res": "antimatter", "offer_amount": 10, "want_res": "crystal"}, CFG
    ) is None


def test_validate_trade_order_rejects_missing_or_empty():
    assert validate_trade_order(None, CFG) is None
    assert validate_trade_order({}, CFG) is None
    assert validate_trade_order(
        {"offer_res": "metal", "want_res": "crystal"}, CFG
    ) is None  # offer_amount fehlt -> 0 -> abgelehnt
