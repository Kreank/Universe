"""Tests fuer „Handelszentrum-Einkommen" (Spieler-Hub-Handel, ``app.fleet.trade``).

ANDERE Spieler koennen am Handelszentrum eines Spielers handeln; der BESITZER verdient
daran eine Marge (``hub_margin``, gedeckelt durch ``hub_margin_max``). Geprueft werden
DB-/Auth-frei wo moeglich:

- die reine Hub-Marge-Mathematik (``clamp_hub_margin``, ``hub_owner_cut``) + Caps + die
  Leitplanke „Gutschrift nie ueber dem getauschten Wert";
- die Komposition aus ``simulate_swap``: der Trader bekommt die um die Marge reduzierte
  Ware, der Besitzer verdient > 0;
- der vollstaendige Resolver ``resolve_player_hub_trade`` mit gestubbten DB-Abhaengigkeiten
  (Besitzer-Einkommen > 0, reduzierte Trader-Ware, Selbst-Handel verboten, History);
- die Sichtbarkeits-/Filterregel ``hub_visible_to`` (eigener Hub nie als fremdes Ziel,
  nur in Reichweite).

Balance-Lade-Logik (Pfad-Suche) wie in ``test_trade_pricing.py``.
"""
import asyncio
import json
import os
import uuid

import app.fleet.trade as trade_mod
from app.fleet.trade import (
    clamp_hub_margin,
    hub_owner_cut,
    hub_visible_to,
    resolve_player_hub_trade,
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
SETPOINT = CFG["default_setpoint"]
RESOURCES = ("metal", "crystal", "deuterium")


def _flat_stock(metal=2_000_000, crystal=1_000_000, deuterium=500_000) -> dict:
    return {"metal": metal, "crystal": crystal, "deuterium": deuterium}


# --- clamp_hub_margin -----------------------------------------------------

def test_clamp_hub_margin_passes_through_within_cap():
    assert clamp_hub_margin(0.02, 0.1) == 0.02


def test_clamp_hub_margin_hard_caps_from_balance():
    # Eine viel zu grosse Marge wird hart auf den Cap geklemmt (Anti-Exploit).
    assert clamp_hub_margin(0.9, 0.1) == 0.1
    assert clamp_hub_margin(5.0, TC["hub_margin_max"]) == TC["hub_margin_max"]


def test_clamp_hub_margin_never_negative():
    assert clamp_hub_margin(-0.5, 0.1) == 0.0
    assert clamp_hub_margin(0.02, -1.0) == 0.0


def test_balance_hub_margin_config_sane():
    assert TC["hub_margin"] > 0
    assert TC["hub_margin_max"] >= TC["hub_margin"]
    # effektive Marge < 1 -> Besitzer-Cut kann nie den getauschten Wert uebersteigen.
    assert TC["hub_margin_max"] < 1.0


# --- hub_owner_cut --------------------------------------------------------

def test_hub_owner_cut_is_margin_times_value():
    assert hub_owner_cut(100_000.0, 0.02, 0.1) == 100_000.0 * 0.02


def test_hub_owner_cut_respects_cap():
    # Marge ueber Cap -> mit Cap gerechnet.
    assert hub_owner_cut(100_000.0, 0.9, 0.1) == 100_000.0 * 0.1


def test_hub_owner_cut_never_exceeds_traded_value():
    """Leitplanke: der Besitzer verdient nie ueber den real getauschten Wert hinaus."""
    value = 250_000.0
    cut = hub_owner_cut(value, 5.0, TC["hub_margin_max"])
    assert 0 < cut <= value


def test_hub_owner_cut_clamps_negative_value():
    assert hub_owner_cut(-100.0, 0.02, 0.1) == 0.0
    assert hub_owner_cut(0.0, 0.02, 0.1) == 0.0


# --- Komposition: reduzierte Trader-Ware + Besitzer-Einkommen -------------

def test_hub_trade_reduces_trader_ware_and_pays_owner():
    """Die Formel des Resolvers: Trader-Ware = received*(1-eff), Besitzer-Cut = value_in*eff > 0."""
    stock = _flat_stock()
    result = simulate_swap("metal", 50_000, "crystal", stock, SETPOINT, CFG)
    eff = clamp_hub_margin(TC["hub_margin"], TC["hub_margin_max"])

    trader_received = result["received"] * (1.0 - eff)
    owner_cut_value = hub_owner_cut(result["value_in"], TC["hub_margin"], TC["hub_margin_max"])

    assert eff > 0
    # Trader bekommt weniger als die volle (margenfreie) Ware.
    assert trader_received < result["received"]
    assert trader_received > 0
    # Besitzer verdient ein echtes, positives Einkommen.
    assert owner_cut_value > 0
    # ... aber nie ueber dem Handelswert.
    assert owner_cut_value <= result["value_in"]


# --- hub_visible_to (Sichtbarkeits-/Filterregel) --------------------------

def test_hub_visible_foreign_in_range():
    viewer, owner = uuid.uuid4(), uuid.uuid4()
    assert hub_visible_to(viewer, owner, hub_galaxy=4, home_galaxy=5, reach=2) is True


def test_hub_own_hub_never_visible_as_foreign_target():
    me = uuid.uuid4()
    # Eigener Hub (owner == viewer) -> nie als fremdes Ziel, selbst in Reichweite.
    assert hub_visible_to(me, me, hub_galaxy=5, home_galaxy=5, reach=9) is False


def test_hub_out_of_range_not_visible():
    viewer, owner = uuid.uuid4(), uuid.uuid4()
    assert hub_visible_to(viewer, owner, hub_galaxy=9, home_galaxy=5, reach=2) is False


def test_hub_none_owner_not_visible():
    assert hub_visible_to(uuid.uuid4(), None, 5, 5, 5) is False


# --- Resolver: Selbst-Handel verboten -------------------------------------

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


class _Planet:
    def __init__(self, owner_id):
        self.id = uuid.uuid4()
        self.player_id = owner_id
        self.name = "Hub-Welt"


class _RecordingSession:
    """Minimal-Session: ``add`` sammelt Objekte, ``get`` liefert einen Fake-Player."""

    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def get(self, model, pk):
        return _Player(pk, name="Trader")


def _patch_transmissions(monkeypatch):
    sent = []

    async def _fake_tx(session, **kw):
        sent.append(kw)

    monkeypatch.setattr(trade_mod, "create_system_transmission", _fake_tx)
    return sent


def test_self_hub_trade_rejected(monkeypatch):
    """Anti-Exploit: kein Handel am EIGENEN Hub -> None + Fehl-Funkspruch, keine Gutschrift."""
    sent = _patch_transmissions(monkeypatch)
    me = _Player()
    fleet = _Fleet(me.id, {"offer_res": "metal", "offer_amount": 1000, "want_res": "crystal"})
    hub_planet = _Planet(owner_id=me.id)

    out = asyncio.run(resolve_player_hub_trade(_RecordingSession(), fleet, hub_planet, me))

    assert out is None
    assert len(sent) == 1
    assert sent[0]["player_id"] == me.id
    assert "eigenen" in sent[0]["body"]


def _patch_resolver_db(monkeypatch, *, capacity=10_000_000.0):
    """Stubt die DB-/IO-Abhaengigkeiten von ``resolve_player_hub_trade``."""
    sent = _patch_transmissions(monkeypatch)
    credited = []

    async def _index_market_for(session, cfg):
        return _flat_stock(), dict(SETPOINT)

    async def _owns_trade_center(session, pid):
        return False

    async def _fleet_ships(session, fleet_id):
        return {"cargo_ship": 1}

    async def _add_resources(session, planet, gain):
        credited.append((planet, dict(gain)))

    monkeypatch.setattr(trade_mod, "index_market_for", _index_market_for)
    monkeypatch.setattr(trade_mod, "owns_trade_center", _owns_trade_center)
    monkeypatch.setattr(trade_mod, "_fleet_ships", _fleet_ships)
    # lazily importierte Namen am Ursprungsmodul patchen.
    import app.combat.service as combat_service
    import app.economy.service as economy_service
    monkeypatch.setattr(combat_service, "_cargo_capacity", lambda ships: capacity)
    monkeypatch.setattr(economy_service, "add_resources", _add_resources)
    return sent, credited


def test_hub_trade_pays_owner_and_reduces_trader_ware(monkeypatch):
    """Ein Hub-Trade: Besitzer-Einkommen > 0, Trader bekommt um die Marge reduzierte Ware."""
    sent, credited = _patch_resolver_db(monkeypatch)
    trader_id = uuid.uuid4()
    owner = _Player(name="Hub-Besitzer")
    fleet = _Fleet(trader_id, {"offer_res": "metal", "offer_amount": 50_000, "want_res": "crystal"})
    hub_planet = _Planet(owner_id=owner.id)

    summary = asyncio.run(
        resolve_player_hub_trade(_RecordingSession(), fleet, hub_planet, owner)
    )

    # Erwartete (ungekuerzte) Ware aus demselben Markt.
    full = simulate_swap("metal", 50_000, "crystal", _flat_stock(), dict(SETPOINT), CFG)
    eff = clamp_hub_margin(TC["hub_margin"], TC["hub_margin_max"])

    assert summary is not None
    # Trader-Ware (crystal) ist um die Marge reduziert.
    received = fleet.cargo["crystal"]
    assert received == round(full["received"] * (1.0 - eff), 1)
    assert received < full["received"]
    assert received > 0

    # Besitzer-Einkommen > 0, auf dem HUB-Planeten, in der angebotenen Ressource (metal).
    assert len(credited) == 1
    planet, gain = credited[0]
    assert planet is hub_planet
    assert gain.get("metal", 0) > 0
    # Leitplanke: Gutschrift (Wert) nie ueber dem getauschten Wert.
    owner_value = gain["metal"] * CFG["base_value"]["metal"]
    assert owner_value <= full["value_in"] + 1e-6
    assert summary["owner_cut"] == gain["metal"]

    # Funksprueche: Beleg an den Trader + Einkommen an den Besitzer.
    recipients = {tx["player_id"] for tx in sent}
    assert trader_id in recipients
    assert owner.id in recipients


def test_hub_trade_writes_history_for_both_sides(monkeypatch):
    """trade_log: Trader-Zeile (partner_kind 'player', Partner = Besitzer) + Besitzer-Zeile."""
    _patch_resolver_db(monkeypatch)
    trader_id = uuid.uuid4()
    owner = _Player(name="Hub-Besitzer")
    fleet = _Fleet(trader_id, {"offer_res": "metal", "offer_amount": 50_000, "want_res": "crystal"})
    hub_planet = _Planet(owner_id=owner.id)
    session = _RecordingSession()

    asyncio.run(resolve_player_hub_trade(session, fleet, hub_planet, owner))

    logs = [o for o in session.added if o.__class__.__name__ == "TradeLog"]
    assert len(logs) == 2
    trader_log = next(o for o in logs if o.player_id == trader_id)
    owner_log = next(o for o in logs if o.player_id == owner.id)
    assert trader_log.partner_kind == "player"
    assert trader_log.partner_id == owner.id
    assert owner_log.partner_kind == "player"
    assert owner_log.partner_id == trader_id
    assert owner_log.received_amount > 0


def test_hub_trade_invalid_order_rejected(monkeypatch):
    """Ungueltiger Auftrag (gleiche Ressource) -> None, kein Einkommen."""
    sent, credited = _patch_resolver_db(monkeypatch)
    owner = _Player()
    fleet = _Fleet(uuid.uuid4(), {"offer_res": "metal", "offer_amount": 1000, "want_res": "metal"})
    hub_planet = _Planet(owner_id=owner.id)

    out = asyncio.run(resolve_player_hub_trade(_RecordingSession(), fleet, hub_planet, owner))
    assert out is None
    assert credited == []
