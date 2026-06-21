"""Tests fuer „Handelszentrum nur Stufe 1, Boni ueber Forschung Handelsnetz".

Geprueft werden (DB-frei wo moeglich, Stubs sonst):
- die generische Maximalstufe (``max_level``): ``building_options`` markiert ein erreichtes
  ``max_level`` als ``maxed`` (kein Ausbau), ``start_upgrade`` lehnt ab Stufe == max_level ab
  (``MaxLevelError`` -> HTTP 400);
- die reinen Forschungs-Skalierungen ``trade_network_margin_reduction`` /
  ``trade_network_hub_margin`` (Wachstum mit der trade_network-Stufe, Caps);
- der Resolver ``resolve_player_hub_trade``: die effektive Hub-Marge waechst mit der
  trade_network-Stufe DES BESITZERS und bleibt <= hub_margin_max (Cap) trotz hoher Forschung;
- ohne Handelszentrum (owns_trade_center False) keine Margen-Reduktion bei eigenen Trades.

Balance-Lade-Logik (Pfad-Suche/BALANCE_PATH-Fallback) wie in ``test_trade_pricing.py``.
"""
import asyncio
import json
import os
import uuid

import pytest

import app.buildings.service as bsvc
import app.fleet.trade as trade_mod
from app.buildings.service import MaxLevelError, building_options, start_upgrade
from app.fleet.trade import (
    clamp_hub_margin,
    resolve_player_hub_trade,
    trade_network_hub_margin,
    trade_network_margin_reduction,
)
from app.fleet.trade_pricing import simulate_swap


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
TC = BALANCE["buildings"]["trade_center"]
EFFECTS = BALANCE["research"]["effects"]
SETPOINT = CFG["default_setpoint"]
RESOURCES = ("metal", "crystal", "deuterium")


def _flat_stock(metal=2_000_000, crystal=1_000_000, deuterium=500_000) -> dict:
    return {"metal": metal, "crystal": crystal, "deuterium": deuterium}


# --- balance-Sanity: neue Keys ----------------------------------------------

def test_balance_trade_center_capped_at_one():
    assert TC["max_level"] == 1
    assert TC["one_per_account"] is True


def test_balance_has_trade_network_scaling_effects():
    assert EFFECTS["trade_network_margin_per_level"] > 0
    assert EFFECTS["trade_network_hub_margin_per_level"] > 0
    assert EFFECTS["trade_network_margin_max"] > 0
    # Reichweite bleibt unveraendert verdrahtet.
    assert EFFECTS["trade_network_range_per_level"] == 1


# --- reine Forschungs-Skalierung der Margen ---------------------------------

def test_margin_reduction_scales_with_research_level():
    base = float(TC["trade_margin_reduction"])
    per = float(EFFECTS["trade_network_margin_per_level"])
    cap = float(EFFECTS["trade_network_margin_max"])
    # Stufe 0 -> nur Basis; jede Stufe +per.
    assert trade_network_margin_reduction(base, 0, per, cap) == pytest.approx(base)
    assert trade_network_margin_reduction(base, 4, per, cap) == pytest.approx(min(base + 4 * per, cap))
    assert trade_network_margin_reduction(base, 4, per, cap) > trade_network_margin_reduction(base, 0, per, cap)


def test_margin_reduction_capped():
    # Riesige Forschungsstufe -> hart auf den Cap geklemmt.
    assert trade_network_margin_reduction(0.015, 9999, 0.005, 0.1) == 0.1


def test_margin_reduction_never_negative():
    assert trade_network_margin_reduction(-1.0, -5, -1.0, 0.1) == 0.0


def test_hub_margin_scales_with_research_level():
    base = float(TC["hub_margin"])
    per = float(EFFECTS["trade_network_hub_margin_per_level"])
    cap = float(TC["hub_margin_max"])
    assert trade_network_hub_margin(base, 0, per, cap) == pytest.approx(base)
    assert trade_network_hub_margin(base, 3, per, cap) == pytest.approx(min(base + 3 * per, cap))
    assert trade_network_hub_margin(base, 3, per, cap) > trade_network_hub_margin(base, 0, per, cap)


def test_hub_margin_capped_despite_high_research():
    cap = float(TC["hub_margin_max"])
    # Sehr hohe Forschung -> Marge bleibt <= hub_margin_max (Anti-Exploit-Cap).
    eff = trade_network_hub_margin(float(TC["hub_margin"]), 9999, 0.01, cap)
    assert eff == cap
    assert eff <= cap


# --- max_level: build_options markiert maxed --------------------------------

class _ScalarsEmpty:
    def all(self):
        return []


class _EmptyResult:
    def scalars(self):
        return _ScalarsEmpty()


class _FakeSession:
    """Minimal-Session: ``execute`` liefert stets ein leeres Ergebnis (one-per-account-Query)."""

    async def execute(self, *args, **kwargs):
        return _EmptyResult()


class _Planet:
    def __init__(self):
        self.id = uuid.uuid4()
        self.player_id = uuid.uuid4()
        self.planet_type = "planet"
        self.position = 4
        self.fields_used = 0
        self.fields_max = 100


def _stub_options_db(monkeypatch, levels):
    async def _levels(session, planet_id):
        return dict(levels)

    async def _research(session, player_id):
        return {}

    async def _resources(session, planet):
        big = 10_000_000_000.0
        return {r: {"amount": big} for r in RESOURCES}

    monkeypatch.setattr(bsvc, "get_building_levels", _levels)
    monkeypatch.setattr(bsvc, "get_research_levels", _research)
    monkeypatch.setattr(bsvc, "refresh_resources", _resources)


def test_build_options_marks_trade_center_maxed(monkeypatch):
    """Handelszentrum auf Stufe 1 -> maxed=True, max_level=1; eine Mine bleibt unbegrenzt."""
    _stub_options_db(monkeypatch, {"trade_center": 1})
    opts = asyncio.run(building_options(_FakeSession(), _Planet()))
    by_type = {o["type"]: o for o in opts}

    tc = by_type["trade_center"]
    assert tc["max_level"] == 1
    assert tc["maxed"] is True

    mine = by_type["metal_mine"]
    assert mine["max_level"] is None
    assert mine["maxed"] is False


def test_build_options_trade_center_not_maxed_at_zero(monkeypatch):
    """Noch nicht gebaut (Stufe 0) -> maxed=False, der erste Bau bleibt moeglich."""
    _stub_options_db(monkeypatch, {})
    opts = asyncio.run(building_options(_FakeSession(), _Planet()))
    tc = {o["type"]: o for o in opts}["trade_center"]
    assert tc["max_level"] == 1
    assert tc["maxed"] is False


# --- max_level: start_upgrade lehnt ab Maximalstufe ab -----------------------

def _stub_start_upgrade_db(monkeypatch, levels):
    async def _no_block(session, planet, btype):
        return False

    async def _no_progress(session, planet_id):
        return False

    async def _levels(session, planet_id):
        return dict(levels)

    monkeypatch.setattr(bsvc, "one_per_account_blocked", _no_block)
    monkeypatch.setattr(bsvc, "is_building_in_progress", _no_progress)
    monkeypatch.setattr(bsvc, "get_building_levels", _levels)


def test_start_upgrade_rejected_at_max_level(monkeypatch):
    """Stufe == max_level (1) -> MaxLevelError (Router: HTTP 400), kein Ausbau."""
    _stub_start_upgrade_db(monkeypatch, {"trade_center": 1})
    with pytest.raises(MaxLevelError):
        asyncio.run(start_upgrade(_FakeSession(), _Planet(), "trade_center"))


def test_start_upgrade_allowed_below_max_level(monkeypatch):
    """Stufe 0 < max_level -> die max_level-Schranke greift NICHT (anderer Fehler/Erfolg ok)."""
    _stub_start_upgrade_db(monkeypatch, {})
    # Wir pruefen nur, dass NICHT der MaxLevelError fliegt (andere DB-Schritte sind hier ungestubt).
    with pytest.raises(Exception) as ei:
        asyncio.run(start_upgrade(_FakeSession(), _Planet(), "trade_center"))
    assert not isinstance(ei.value, MaxLevelError)


# --- Resolver: Hub-Marge waechst mit Forschung des Besitzers + Cap ----------

class _Fleet:
    def __init__(self, player_id, mission_data, target=(1, 2, 3)):
        self.id = uuid.uuid4()
        self.player_id = player_id
        self.target_galaxy, self.target_system, self.target_position = target
        self.mission_data = mission_data
        self.cargo = None


class _Player:
    def __init__(self, pid=None, name="Spieler"):
        self.id = pid or uuid.uuid4()
        self.display_name = name


class _HubPlanet:
    def __init__(self, owner_id):
        self.id = uuid.uuid4()
        self.player_id = owner_id
        self.name = "Hub-Welt"


class _RecordingSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def get(self, model, pk):
        return _Player(pk, name="Trader")


def _patch_hub_resolver(monkeypatch, *, owner_trade_network, capacity=10_000_000.0):
    sent = []
    credited = []

    async def _fake_tx(session, **kw):
        sent.append(kw)

    async def _index_market_for(session, cfg):
        return _flat_stock(), dict(SETPOINT)

    async def _owns_trade_center(session, pid):
        return False  # Trader hat keins -> seine Marge unveraendert; nur Hub-Besitzer zaehlt

    async def _fleet_ships(session, fleet_id):
        return {"cargo_ship": 1}

    async def _add_resources(session, planet, gain):
        credited.append((planet, dict(gain)))

    async def _get_research_levels(session, pid):
        return {"trade_network": owner_trade_network}

    monkeypatch.setattr(trade_mod, "create_system_transmission", _fake_tx)
    monkeypatch.setattr(trade_mod, "index_market_for", _index_market_for)
    monkeypatch.setattr(trade_mod, "owns_trade_center", _owns_trade_center)
    monkeypatch.setattr(trade_mod, "_fleet_ships", _fleet_ships)
    import app.combat.service as combat_service
    import app.economy.service as economy_service
    monkeypatch.setattr(combat_service, "_cargo_capacity", lambda ships: capacity)
    monkeypatch.setattr(economy_service, "add_resources", _add_resources)
    monkeypatch.setattr(economy_service, "get_research_levels", _get_research_levels)
    return sent, credited


def test_hub_margin_grows_with_owner_research(monkeypatch):
    """Hoehere trade_network-Stufe des Besitzers -> hoehere effektive Hub-Marge."""
    order = {"offer_res": "metal", "offer_amount": 50_000, "want_res": "crystal"}

    _patch_hub_resolver(monkeypatch, owner_trade_network=0)
    s0 = asyncio.run(resolve_player_hub_trade(
        _RecordingSession(), _Fleet(uuid.uuid4(), dict(order)), _HubPlanet(uuid.uuid4()), _Player(name="A")))

    _patch_hub_resolver(monkeypatch, owner_trade_network=3)
    s3 = asyncio.run(resolve_player_hub_trade(
        _RecordingSession(), _Fleet(uuid.uuid4(), dict(order)), _HubPlanet(uuid.uuid4()), _Player(name="B")))

    assert s0["hub_margin"] == pytest.approx(float(TC["hub_margin"]))
    assert s3["hub_margin"] > s0["hub_margin"]


def test_hub_margin_resolver_capped(monkeypatch):
    """Sehr hohe Forschung -> effektive Hub-Marge bleibt am Cap (hub_margin_max)."""
    _patch_hub_resolver(monkeypatch, owner_trade_network=9999)
    summary = asyncio.run(resolve_player_hub_trade(
        _RecordingSession(),
        _Fleet(uuid.uuid4(), {"offer_res": "metal", "offer_amount": 50_000, "want_res": "crystal"}),
        _HubPlanet(uuid.uuid4()),
        _Player(name="C"),
    ))
    assert summary["hub_margin"] == clamp_hub_margin(99.0, float(TC["hub_margin_max"]))
    assert summary["hub_margin"] == float(TC["hub_margin_max"])


def test_no_trade_center_no_margin_reduction(monkeypatch):
    """Ohne Handelszentrum (owns_trade_center False) keine eigene Margen-Reduktion (Unlock fehlt)."""
    # Trader-Ware bei owns=False muss der ungekuerzten simulate_swap-Ware (extra_margin=0) entsprechen.
    sent, credited = _patch_hub_resolver(monkeypatch, owner_trade_network=0)
    order = {"offer_res": "metal", "offer_amount": 50_000, "want_res": "crystal"}
    fleet = _Fleet(uuid.uuid4(), dict(order))
    summary = asyncio.run(resolve_player_hub_trade(
        _RecordingSession(), fleet, _HubPlanet(uuid.uuid4()), _Player(name="D")))

    # extra_margin_reduction == 0 (kein Gebaeude) -> received entspricht Basis-Swap * (1 - eff).
    full = simulate_swap("metal", 50_000, "crystal", _flat_stock(), dict(SETPOINT), CFG,
                         reputation_level=0, cargo_capacity=10_000_000.0, extra_margin_reduction=0.0)
    eff = clamp_hub_margin(float(TC["hub_margin"]), float(TC["hub_margin_max"]))
    assert fleet.cargo["crystal"] == pytest.approx(round(full["received"] * (1.0 - eff), 1))
    assert summary is not None
