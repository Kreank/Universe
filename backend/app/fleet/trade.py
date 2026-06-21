"""Handels-Integration (Anfliegen-Modell) rund um den reinen Preis-Kern.

Der Spieler schickt eine Flotte mit einer Angebots-Ressource zu einem Haendler-NPC
(``behavior_profile == 'merchant'``), tauscht dort zu dynamischen Preisen (Slippage,
siehe ``trade_pricing``) gegen die gewuenschte Ware und kehrt mit dieser heim.

Dieses Modul verheiratet den reinen Preis-Kern (``trade_pricing``) mit DB/State:
- ``ensure_market`` / ``market_setpoint``: Markt eines Haendlers (lazy init, persistent;
  auch vom spaeteren Markt-Tick / Spawner wiederverwendbar).
- ``validate_trade_order``: reine, testbare Pruefung der Auftragsdaten.
- ``resolve_trade``: der DB-Resolver, aufgerufen aus ``fleet_arrive`` bei Ankunft.

Vorbild fuer den Resolver-Stil: ``combat.service.resolve_attack`` (NPC-Lookup ueber
UniverseCell mit Koordinaten-Fallback; KEIN eigener Commit — ``fleet_arrive`` committet).
"""
from __future__ import annotations

import datetime as dt
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fleet.trade_index import index_market_for
from app.fleet.trade_pricing import price_of, simulate_swap
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import (
    Building,
    Fleet,
    NpcEmpire,
    Planet,
    Player,
    PlayerDiscovery,
    Ship,
    TradeLog,
    TradeReputation,
    UniverseCell,
)

log = logging.getLogger("universe.trade")

RESOURCES = ("metal", "crystal", "deuterium")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# -- Handelsnetz-Reichweite (Sichtbarkeit der NPC-Handelszentren) -------------

def trade_network_reach(level: int, per_level: int, building_bonus: int = 0) -> int:
    """Sichtbarkeits-Reichweite (Galaxien) der NPC-Handelszentren, rein/testbar.

    Anders als die Ortung (Stufe 1 = Heimat-Galaxie) zeigt das Handelsnetz schon bei
    Stufe 0 die eigene Galaxie (Handel ist nie hart hinter Forschung gesperrt):
    reach = level * per_level. Ein gebautes Handelszentrum erweitert die Reichweite um
    ``building_bonus`` Galaxien zusaetzlich zur Forschung. Reach 0 = nur die Heimat-Galaxie."""
    return max(0, int(level)) * max(0, int(per_level)) + max(0, int(building_bonus))


async def owns_trade_center(session: AsyncSession, player_id) -> bool:
    """True, wenn der Spieler auf irgendeinem Planeten ein gebautes Handelszentrum (Stufe>=1) hat."""
    from sqlalchemy import func
    n = (await session.execute(
        select(func.count()).select_from(Building).join(Planet, Building.planet_id == Planet.id)
        .where(
            Planet.player_id == player_id,
            Building.type == "trade_center",
            Building.level >= 1,
        )
    )).scalar() or 0
    return int(n) > 0


# -- Markt-Helfer (auch vom spaeteren Tick/Spawner wiederverwendbar) ----------

def market_setpoint(spec: str, cfg: dict) -> dict:
    """Sollbestand je Ressource = default_setpoint[res] * specializations[spec][res].

    Spezialisierungen skalieren den Sollbestand und erzeugen so Preis-Differenziale
    zwischen Haendlern (Arbitrage). Unbekannte spec -> 'generalist' (neutral)."""
    defaults = cfg["default_setpoint"]
    specs = cfg["specializations"]
    scale = specs.get(spec) or specs["generalist"]
    return {res: float(defaults[res]) * float(scale[res]) for res in RESOURCES}


def ensure_market(npc, cfg: dict) -> dict:
    """Liefert den Markt eines Haendler-NPC; initialisiert ihn lazy, falls leer.

    market = {"spec": <specialization-key>, "stock": {metal, crystal, deuterium}}.
    Bei Init: spec zufaellig aus cfg['specializations'] waehlen (einmalig, danach
    persistent), stock = setpoint (= default_setpoint * specializations[spec]).
    Setzt ``npc.market`` als NEUES dict (SQLAlchemy-Change-Tracking fuer JSONB)."""
    market = npc.market or {}
    # Schwarzmarkt-Sondermarkt (Event): Kennung + rate_bonus NIE neu wuerfeln. Fehlt der
    # Bestand, fuellen wir ihn aus dem (generalist-)Sollbestand auf, statt die spec zu verlieren.
    if market.get("spec") == "black_market":
        if not market.get("stock"):
            setpoint = market_setpoint(market["spec"], cfg)  # unbekannte spec -> generalist
            stock = {res: round(setpoint[res]) for res in RESOURCES}
            market = {**market, "stock": stock}
            npc.market = market  # neues dict -> Change-Tracking
        return market
    if market.get("spec") and market.get("stock"):
        return market  # bereits initialisiert -> idempotent

    spec = random.choice(list(cfg["specializations"].keys()))
    setpoint = market_setpoint(spec, cfg)
    stock = {res: round(setpoint[res]) for res in RESOURCES}
    market = {"spec": spec, "stock": stock}
    npc.market = market  # neues dict -> Change-Tracking
    return market


def drift_stock(current: float, setpoint: float, regen: float) -> int:
    """Ein-Schritt-Drift eines Bestands Richtung Sollwert (rein, testbar).

    new = current + (setpoint - current) * regen; auf ganze Zahl gerundet.
    Bestand unter Soll steigt, ueber Soll faellt; ueber viele Ticks -> exakt Soll.
    Ausgelagert aus ``market_regen_tick``, damit die Drift-Mathematik DB-frei testbar bleibt."""
    current = float(current)
    setpoint = float(setpoint)
    result = round(current + (setpoint - current) * float(regen))
    # Rundungs-Deadzone ueberwinden: nahe am Soll rundet der Schritt auf 0 und der Bestand
    # bliebe ein paar Einheiten stecken. Dann einen 1er-Schritt Richtung Soll machen ->
    # echte Konvergenz ohne Ueberschwingen (current ist stets ganzzahlig aus dem Vortick).
    if result == round(current) and round(current) != round(setpoint):
        result = round(current) + (1 if setpoint > current else -1)
    return result


def merchant_intel(npc, cfg: dict, now_iso: str) -> dict:
    """Discovery-Intel eines Haendlers: {name, merchant, spec, prices:{r: price_of(...)}, prices_at}.

    Setzt voraus, dass ``npc.market`` initialisiert ist (``ensure_market`` vorher aufrufen).
    Reiner Snapshot der aktuellen Kurse je Ressource aus dem persistierten Bestand;
    DRY-Quelle fuer Resolver (Schritt 10), Spawner-Auto-Discovery und Spionage."""
    market = npc.market or {}
    spec = market["spec"]
    stock = market["stock"]
    setpoint = market_setpoint(spec, cfg)
    prices = {
        r: round(price_of(r, stock[r], setpoint[r], cfg), 3)
        for r in RESOURCES
    }
    return {
        "name": npc.name,
        "merchant": True,
        "spec": spec,
        "prices": prices,
        "prices_at": now_iso,
    }


def route_risk_chance(distance: int, escort_power: float, cargo_value: float, cfg: dict) -> float:
    """Ueberfall-Wahrscheinlichkeit einer Handelsflotte (0..max_chance), rein/testbar.

    raw = base_chance_per_system * distance;
    * (1 + min(1.0, cargo_value/cargo_value_ref))  -> reichere Fracht = fetteres Ziel (bis 2x);
    * escort_power_for_half/(escort_power_for_half + escort_power)  -> Eskorte senkt
      (bei escort_power == escort_power_for_half halbiert sich das Risiko);
    geklemmt auf [0, max_chance]."""
    rc = cfg["route_risk"]
    raw = float(rc["base_chance_per_system"]) * float(distance)
    # Frachtwert-Verstaerkung (bis Faktor 2 bei cargo_value >= cargo_value_ref).
    value_ref = float(rc["cargo_value_ref"])
    if value_ref > 0:
        raw *= 1.0 + min(1.0, max(0.0, float(cargo_value)) / value_ref)
    # Eskort-Daempfung (mehr Kampfkraft -> kleinerer Faktor).
    half = float(rc["escort_power_for_half"])
    escort_power = max(0.0, float(escort_power))
    raw *= half / (half + escort_power)
    return max(0.0, min(float(rc["max_chance"]), raw))


# -- Reine Auftrags-Validierung (testbar, DB-frei) ----------------------------

def validate_trade_order(mission_data: dict | None, cfg: dict) -> tuple[str, float, str] | None:
    """Prueft die Handels-Auftragsdaten und liefert (offer_res, offer_amount, want_res).

    Bei jedem Verstoss (fehlende/unbekannte Ressource, gleiche Ressource, Menge <= 0)
    wird ``None`` zurueckgegeben — der Aufrufer schickt dann einen Funkspruch und bricht
    ab. Rein, ohne DB/IO -> direkt testbar."""
    if not mission_data:
        return None
    offer_res = mission_data.get("offer_res")
    want_res = mission_data.get("want_res")
    base = cfg["base_value"]
    if offer_res not in base or want_res not in base:
        return None
    if offer_res == want_res:
        return None
    try:
        offer_amount = float(mission_data.get("offer_amount", 0))
    except (TypeError, ValueError):
        return None
    if offer_amount <= 0:
        return None
    return offer_res, offer_amount, want_res


# -- DB-Resolver --------------------------------------------------------------

async def _fleet_ships(session: AsyncSession, fleet_id) -> dict[str, int]:
    rows = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet_id)
    )).scalars().all()
    return {r.type: r.count for r in rows if r.count > 0}


async def _trade_npc_at(
    session: AsyncSession, galaxy: int, system: int, position: int
) -> NpcEmpire | None:
    """Liefert den Haendler-NPC (merchant/trade_center) an den Koordinaten, sonst None.

    Zelle bevorzugt (occupant_type 'npc'), Koordinaten-Fallback wie ``resolve_attack``.
    Eine Wahrheit fuer resolve_trade, den Anflug-Dispatcher und die Versand-Validierung."""
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == galaxy,
            UniverseCell.system == system,
            UniverseCell.position == position,
        )
    )).scalar_one_or_none()
    npc: NpcEmpire | None = None
    if cell and cell.occupant_type == "npc" and cell.ref_id is not None:
        npc = await session.get(NpcEmpire, cell.ref_id)
    if npc is None:
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == galaxy,
                NpcEmpire.system == system,
                NpcEmpire.position == position,
            )
        )).scalar_one_or_none()
    if npc is not None and npc.behavior_profile in ("merchant", "trade_center"):
        return npc
    return None


async def find_player_hub(
    session: AsyncSession, galaxy: int, system: int, position: int
) -> tuple[Planet, Player | None] | None:
    """Liefert (planet, owner) eines Spieler-Hubs an den Koordinaten, sonst None.

    Ein Spieler-Hub ist ein PLANET (kein Mond) mit einem gebauten Handelszentrum
    (``trade_center``-Gebaeude, Stufe>=1). Reine Praesenz-Pruefung — die Selbst-Handel-
    Sperre (owner == Trader) liegt im Resolver/der Versand-Validierung, damit der eigene
    Hub fuer die Sichtbarkeits-/Filterlogik weiterhin als Hub erkennbar bleibt."""
    planets = (await session.execute(
        select(Planet).where(
            Planet.galaxy == galaxy,
            Planet.system == system,
            Planet.position == position,
        )
    )).scalars().all()
    for pl in planets:
        if pl.planet_type == "moon":
            continue
        lvl = (await session.execute(
            select(Building.level).where(
                Building.planet_id == pl.id,
                Building.type == "trade_center",
            )
        )).scalar_one_or_none()
        if lvl is not None and int(lvl) >= 1:
            owner = await session.get(Player, pl.player_id)
            return pl, owner
    return None


# -- Reine Hub-Marge-Mathematik (Spieler-Hub-Einkommen, DB-frei testbar) -------

def clamp_hub_margin(hub_margin: float, cap: float) -> float:
    """Effektive Hub-Marge: ``hub_margin`` hart auf [0, cap] geklemmt (Anti-Exploit).

    cap kommt aus balance (``buildings.trade_center.hub_margin_max``). Garantiert eine
    Marge < 1 und damit, dass der Besitzer-Cut nie den getauschten Wert uebersteigt."""
    return max(0.0, min(float(hub_margin), max(0.0, float(cap))))


def hub_visible_to(
    viewer_id, owner_id, hub_galaxy: int, home_galaxy: int, reach: int
) -> bool:
    """Ob ein Spieler-Hub fuer den Betrachter als FREMDES Handelsziel sichtbar ist, rein/testbar.

    True nur, wenn der Hub einem ANDEREN Spieler gehoert (owner != viewer, nie der eigene Hub)
    UND in Handelsnetz-Reichweite liegt (|hub_galaxy - home_galaxy| <= reach). Authoritative
    Filterregel der ``/api/trade/centers``-Hub-Liste (und Doku der Versand-Selbstsperre)."""
    if owner_id is None or owner_id == viewer_id:
        return False
    return abs(int(hub_galaxy) - int(home_galaxy)) <= max(0, int(reach))


def hub_owner_cut(value: float, hub_margin: float, cap: float) -> float:
    """Einkommen des Hub-Besitzers (Markt-WERT) aus einem fremden Hub-Handel, rein/testbar.

    cut = max(0, value) * clamp_hub_margin(hub_margin, cap).
    ``value`` ist der Handelswert (``value_in`` aus ``simulate_swap``, Marktwert des
    Angebots). Da die effektive Marge < 1 ist, gilt stets ``cut <= value`` — der Besitzer
    verdient nie ueber den real getauschten Wert hinaus (Leitplanke)."""
    return max(0.0, float(value)) * clamp_hub_margin(hub_margin, cap)


async def resolve_player_hub_trade(
    session: AsyncSession, fleet: Fleet, hub_planet: Planet, owner: Player | None
) -> dict | None:
    """Wickelt einen Handel an einem fremden Spieler-Hub ab (Anfliegen-Modell).

    Wie ``resolve_trade`` (globaler Index + ``simulate_swap``), aber: (1) KEIN Handel am
    eigenen Hub, (2) der Hub-BESITZER verdient ``hub_margin`` × Handelswert als Einkommen
    (gutgeschrieben auf den Hub-Planeten in der angebotenen Ressource), (3) der Trader
    erhaelt entsprechend um die Marge reduzierte Ware. KEIN eigener Commit (fleet_arrive
    committet). Liefert ein summary-dict oder None (kein gueltiges Ziel/Auftrag)."""
    bal = get_balance()
    cfg = bal.trade
    coords = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"

    # -- Anti-Exploit: kein Handel am EIGENEN Hub (kein Selbst-Einkommen) --
    if owner is None or owner.id == fleet.player_id:
        await create_system_transmission(
            session,
            player_id=fleet.player_id,
            subject=f"Handel fehlgeschlagen ({coords})",
            body=f"Du kannst nicht an deinem eigenen Handels-Knoten ({coords}) handeln. "
                 f"Die Fracht kehrt unveraendert heim.",
            ttype="system",
        )
        log.info("Selbst-Hub-Handel abgelehnt: player=%s coords=%s", fleet.player_id, coords)
        return None

    # -- Auftrag validieren --
    order = validate_trade_order(fleet.mission_data, cfg)
    if order is None:
        await create_system_transmission(
            session,
            player_id=fleet.player_id,
            subject=f"Ungueltiger Handelsauftrag ({coords})",
            body=f"Der Handelsauftrag fuer den Handels-Knoten {coords} war ungueltig. "
                 f"Die Fracht kehrt unveraendert heim.",
            ttype="system",
        )
        return None
    offer_res, offer_amount, want_res = order

    # -- Markt = globaler Index (wie ein NPC-Handelszentrum) --
    stock, setpoint = await index_market_for(session, cfg)

    # -- Trader-Handelszentrum-Bonus: senkt seine eigene Marge (additiv, wie bei NPC) --
    tc_cfg = bal.buildings.get("trade_center", {})
    extra_margin = 0.0
    if await owns_trade_center(session, fleet.player_id):
        extra_margin = float(tc_cfg.get("trade_margin_reduction", 0.0))

    # -- Cargo-Kapazitaet der Flotte --
    from app.combat.service import _cargo_capacity
    ships = await _fleet_ships(session, fleet.id)
    capacity = _cargo_capacity(ships)

    # -- Tausch simulieren (Spieler-Hubs fuehren KEINE NPC-Reputation -> level 0) --
    result = simulate_swap(
        offer_res, offer_amount, want_res, stock, setpoint, cfg,
        reputation_level=0, cargo_capacity=capacity,
        extra_margin_reduction=extra_margin,
    )

    # -- Besitzer-Cut (Marktwert) + um die Marge reduzierte Trader-Ware --
    hub_margin = float(tc_cfg.get("hub_margin", 0.0))
    cap = float(tc_cfg.get("hub_margin_max", hub_margin))
    eff = clamp_hub_margin(hub_margin, cap)
    owner_cut_value = hub_owner_cut(result["value_in"], hub_margin, cap)
    received = round(result["received"] * (1.0 - eff), 1)

    cargo = {want_res: received}
    refund_offer = 0.0
    if result["refund_value"] > 0:
        refund_offer = round(result["refund_value"] / float(cfg["base_value"][offer_res]), 1)
        if refund_offer > 0:
            cargo[offer_res] = cargo.get(offer_res, 0.0) + refund_offer
    fleet.cargo = cargo

    # -- Besitzer-Gutschrift: Cut als angebotene Ressource auf den Hub-Planeten (Lager darf
    #    ueberfuellen, wie jede externe Zufuhr). owner_gain <= offer_amount (eff < 1). --
    owner_gain_offer = round(owner_cut_value / float(cfg["base_value"][offer_res]), 1)
    if owner_gain_offer > 0:
        from app.economy.service import add_resources
        await add_resources(session, hub_planet, {offer_res: owner_gain_offer})

    # -- Handelsbeleg an den Trader --
    await create_system_transmission(
        session,
        player_id=fleet.player_id,
        subject=f"Handelsbeleg — Handels-Knoten {coords}",
        body=(
            f"Handel am Handels-Knoten von {owner.display_name} ({coords}) abgeschlossen.\n"
            f"Angeboten: {int(round(offer_amount))} {offer_res}.\n"
            f"Erhalten: {received:g} {want_res} "
            f"(Hub-Marge {eff * 100:.1f}% an den Besitzer)."
        ),
        ttype="system",
    )

    # -- Einkommens-Funkspruch an den Besitzer (sichtbar ohne History-Abfrage) --
    if owner_gain_offer > 0:
        await create_system_transmission(
            session,
            player_id=owner.id,
            subject=f"💰 Hub-Einkommen ({coords})",
            body=(
                f"Eine fremde Handelsflotte hat an deinem Handels-Knoten ({coords}) gehandelt. "
                f"Deine Marge: {owner_gain_offer:g} {offer_res} (Hub-Marge {eff * 100:.1f}%)."
            ),
            ttype="system",
        )

    # -- Handelshistorie fuer beide Seiten (best-effort: darf den Handel nie stoeren) --
    try:
        session.add(TradeLog(
            player_id=fleet.player_id,
            partner_kind="player",
            partner_id=owner.id,
            partner_name=owner.display_name,
            offered_res=offer_res,
            offered_amount=round(float(offer_amount), 1),
            received_res=want_res,
            received_amount=float(received),
        ))
        if owner_gain_offer > 0:
            trader = await session.get(Player, fleet.player_id)
            session.add(TradeLog(
                player_id=owner.id,
                partner_kind="player",
                partner_id=fleet.player_id,
                partner_name=trader.display_name if trader else None,
                offered_res=want_res,
                offered_amount=0.0,
                received_res=offer_res,
                received_amount=float(owner_gain_offer),
            ))
    except Exception:  # pragma: no cover - reine Absicherung
        log.exception("hub trade_log konnte nicht geschrieben werden (ignoriert)")

    summary = {
        "hub_owner": owner.display_name,
        "location": coords,
        "offer_res": offer_res,
        "offer_amount": round(offer_amount, 1),
        "want_res": want_res,
        "received": received,
        "owner_cut": owner_gain_offer,
        "hub_margin": eff,
        "refund_offer": refund_offer,
    }
    log.info(
        "Hub-Handel: trader=%s owner=%s %s %g->%s %g owner_cut=%g %s",
        fleet.player_id, owner.id, offer_res, offer_amount, want_res, received,
        owner_gain_offer, offer_res,
    )
    return summary


async def resolve_trade_arrival(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Dispatch bei Ankunft einer 'trade'-Flotte: NPC-Haendler ODER Spieler-Hub.

    NPC-Haendler/-Handelszentrum haben Vorrang (bestehendes Verhalten unveraendert). Steht
    am Ziel kein NPC-Haendler, aber ein Spieler-Hub (fremder Planet mit trade_center>=1),
    wird der Hub-Handel aufgeloest. Sonst uebernimmt ``resolve_trade`` die Fehlmeldung."""
    npc = await _trade_npc_at(
        session, fleet.target_galaxy, fleet.target_system, fleet.target_position
    )
    if npc is None:
        hub = await find_player_hub(
            session, fleet.target_galaxy, fleet.target_system, fleet.target_position
        )
        if hub is not None:
            return await resolve_player_hub_trade(session, fleet, hub[0], hub[1])
    return await resolve_trade(session, fleet)


async def resolve_trade(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Wickelt einen Handel bei Ankunft der Flotte ab (Anfliegen-Modell).

    Ablauf (Vorbild resolve_attack): Haendler am Ziel finden -> Markt lazy init ->
    Auftrag validieren -> Reputation/Cargo-Kapazitaet ermitteln -> ``simulate_swap``
    (Slippage) -> Bestand/Reputation/Fracht aktualisieren -> Preis-Snapshot in
    PlayerDiscovery -> Handels-Beleg-Funkspruch. KEIN eigener Commit (fleet_arrive
    committet). Liefert ein kurzes summary-dict oder None (kein gueltiges Ziel/Auftrag)."""
    bal = get_balance()
    cfg = bal.trade
    coords = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"

    # -- 1) Haendler-NPC am Ziel finden (Zelle bevorzugt, Koordinaten-Fallback) --
    npc = await _trade_npc_at(
        session, fleet.target_galaxy, fleet.target_system, fleet.target_position
    )

    if npc is None:
        await create_system_transmission(
            session,
            player_id=fleet.player_id,
            subject=f"Handel fehlgeschlagen ({coords})",
            body=f"Deine Handelsflotte erreichte {coords}, fand dort aber keinen Haendler. "
                 f"Die Fracht kehrt unveraendert heim.",
            ttype="system",
        )
        log.info("Handel ohne Haendler: player=%s coords=%s", fleet.player_id, coords)
        return None

    # -- 2) Markt: Handelszentrum -> globaler Index (synthetischer Markt aus dem
    #        Weltvorrat); Legacy-Haendler -> lokaler Bestand (lazy init) --
    is_center = npc.behavior_profile == "trade_center"
    # Schwarzmarkt-Event-NPC (trade_center mit market.spec == 'black_market'): Sonderkurse.
    # rate_bonus kommt aus dem NPC-Markt (Default 1.5), wird unten an simulate_swap durchgereicht.
    _market_meta = npc.market or {}
    is_black = _market_meta.get("spec") == "black_market"
    rate_bonus = float(_market_meta.get("rate_bonus", 1.5)) if is_black else 1.0
    if is_center:
        stock, setpoint = await index_market_for(session, cfg)
        spec = "black_market" if is_black else "trade_center"
    else:
        market = ensure_market(npc, cfg)
        spec = market["spec"]
        stock = dict(market["stock"])
        setpoint = market_setpoint(spec, cfg)
        if spec == "black_market":
            is_black = True
            rate_bonus = float(market.get("rate_bonus", 1.5))

    # -- 3) Auftrag validieren --
    order = validate_trade_order(fleet.mission_data, cfg)
    if order is None:
        await create_system_transmission(
            session,
            player_id=fleet.player_id,
            subject=f"Ungueltiger Handelsauftrag ({coords})",
            body=f"Der Handelsauftrag fuer {npc.name} ({coords}) war ungueltig. "
                 f"Die Fracht kehrt unveraendert heim.",
            ttype="system",
        )
        log.info("Ungueltiger Handelsauftrag: player=%s coords=%s data=%s",
                 fleet.player_id, coords, fleet.mission_data)
        return None
    offer_res, offer_amount, want_res = order

    # -- 4) Reputation (get-or-create) -> Stufe aus kumuliertem Volumen --
    rep = (await session.execute(
        select(TradeReputation).where(
            TradeReputation.player_id == fleet.player_id,
            TradeReputation.npc_id == npc.id,
        )
    )).scalar_one_or_none()
    if rep is None:
        rep = TradeReputation(player_id=fleet.player_id, npc_id=npc.id, volume=0.0)
        session.add(rep)
    rep_cfg = cfg["reputation"]
    level = min(int(rep_cfg["max_level"]), int(rep.volume // float(rep_cfg["volume_per_level"])))

    # -- 4b) Handelszentrum-Bonus des Besitzers: senkt die eigene Haendler-Marge (additiv
    #        zur Reputation), aktiv solange irgendwo ein Handelszentrum (Stufe>=1) steht. --
    tc_cfg = bal.buildings.get("trade_center", {})
    extra_margin = 0.0
    if await owns_trade_center(session, fleet.player_id):
        extra_margin = float(tc_cfg.get("trade_margin_reduction", 0.0))

    # -- 5) Cargo-Kapazitaet der Flotte (Vorbild combat) --
    from app.combat.service import _cargo_capacity
    ships = await _fleet_ships(session, fleet.id)
    capacity = _cargo_capacity(ships)

    # -- 6) Tausch simulieren (Slippage in beide Richtungen) --
    result = simulate_swap(
        offer_res, offer_amount, want_res, stock, setpoint, cfg,
        reputation_level=level, cargo_capacity=capacity, rate_bonus=rate_bonus,
        extra_margin_reduction=extra_margin,
    )

    # -- 7) Haendler-Bestand aktualisieren (nur Legacy-lokaler Markt; ein Handelszentrum
    #        hat keinen persistenten Bestand -> sein Index folgt im naechsten Tick dem Weltvorrat) --
    if not is_center:
        new_stock = {**stock, **{r: round(v) for r, v in result["new_stock"].items()}}
        new_market = {"spec": spec, "stock": new_stock}
        if is_black:  # Sonderkurs-Kennung erhalten (rate_bonus nicht verlieren)
            new_market["rate_bonus"] = rate_bonus
        npc.market = new_market

    # -- 8) Reputation hochzaehlen --
    rep.volume = float(rep.volume) + float(result["value_in"])
    rep.updated_at = _now()

    # -- 9) Flotten-Fracht setzen (kehrt via fleet_return heim) --
    # Haendler-Garnitur (Equipment des Kommandeurs): +erhaltene Ware, moral-skaliert.
    _trade_bonus = 0.0
    if getattr(fleet, "commander_id", None):
        from app.commander.equipment import commander_stat_bonus
        from app.platform.models import Commander as _Cmd
        _cmd = await session.get(_Cmd, fleet.commander_id)
        _trade_bonus = await commander_stat_bonus(
            session, fleet.commander_id, "trade_margin", _cmd.morale if _cmd else 100)
    received = round(result["received"] * (1.0 + _trade_bonus), 1)
    cargo = {want_res: received}
    # Refund: nicht ausgegebenes Budget (Cargo-/Stock-Limit) als Angebots-Ressource zurueck.
    refund_offer = 0.0
    if result["refund_value"] > 0:
        refund_offer = round(result["refund_value"] / float(cfg["base_value"][offer_res]), 1)
        if refund_offer > 0:
            cargo[offer_res] = cargo.get(offer_res, 0.0) + refund_offer
    fleet.cargo = cargo

    # -- 9b) Routen-Risiko: ungeschuetzte Frachter werden auf dem Rueckweg ueberfallen --
    # Reine Risiko-Rechnung (route_risk_chance) + EIN Zufallswurf (gewollt nicht-deterministisch;
    # die Tests pruefen nur die reine Funktion, nicht diesen Wurf).
    raided = False
    lost: dict[str, int] = {}
    route_cfg = cfg.get("route_risk")
    if route_cfg and cargo:
        # Lazy-Imports -> kein Modul-Zyklus (service/attack importieren trade nur lazy).
        from app.fleet.service import compute_distance
        from app.npc.attack import fleet_power

        # Distanz Origin->Ziel; ohne Origin (z.B. Kolonie aufgeloest) Fallback-Distanz 1.
        distance = 1
        if fleet.origin_planet_id is not None:
            origin = await session.get(Planet, fleet.origin_planet_id)
            if origin is not None:
                distance = compute_distance(
                    (origin.galaxy, origin.system, origin.position),
                    (fleet.target_galaxy, fleet.target_system, fleet.target_position),
                )

        # Eskort-Kampfkraft = eigene bewaffnete Schiffe + gebuchte Patrouillen-Eskorten.
        escort_power = fleet_power(ships, bal.ships)
        escort_power += float((fleet.mission_data or {}).get("escort_power", 0.0))
        # Frachtwert der heimkehrenden Ware (Marktwert ueber base_value).
        cargo_value = received * float(cfg["base_value"][want_res])

        chance = route_risk_chance(distance, escort_power, cargo_value, cfg)
        # Forschung "Konvoi-Taktik" senkt das Routenrisiko.
        from app.economy.service import get_research_levels
        _eff = bal.data["research"]["effects"]
        _convoy = int((await get_research_levels(session, fleet.player_id)).get("convoy_tactics", 0))
        chance *= max(0.0, 1.0 - _convoy * float(_eff.get("convoy_route_risk_reduction_per_level", 0.0)))
        # Handels-Leviathan Konvoi-Schutz-Aura (praesenz-basiert, kein Stapeln).
        _lev_ships = await _fleet_ships(session, fleet.id)
        _roster = bal.combat_roster
        if any((_roster.get(t) or {}).get("aura") == "convoy" and n > 0 for t, n in _lev_ships.items()):
            chance *= max(0.0, 1.0 - float(bal.data.get("capstone", {}).get("convoy_aura", {}).get("risk_reduction", 0.0)))
        if random.random() < chance:
            raided = True
            # Jede Cargo-Position um loss_fraction kuerzen (gerundet), neues dict setzen.
            loss_fraction = float(route_cfg["loss_fraction"])
            new_cargo: dict[str, float] = {}
            for res, amount in cargo.items():
                lost_amt = round(float(amount) * loss_fraction)
                if lost_amt > 0:
                    lost[res] = lost_amt
                new_cargo[res] = round(float(amount) - lost_amt, 1)
            fleet.cargo = new_cargo
            cargo = new_cargo
            # Separater Warn-Funkspruch.
            loss_line = ", ".join(f"{amt:g} {res}" for res, amt in lost.items()) or "keine"
            await create_system_transmission(
                session,
                player_id=fleet.player_id,
                subject=f"⚠ Frachter ueberfallen ({coords})",
                body=(
                    f"Deine ungeschuetzte Handelsflotte wurde auf der Route von {npc.name} "
                    f"({coords}) ueberfallen. Verlorene Fracht: {loss_line}.\n"
                    f"Eine staerkere Eskorte (bewaffnete Schiffe) senkt das Ueberfall-Risiko."
                ),
                ttype="system",
            )
            log.info(
                "Frachter ueberfallen: player=%s coords=%s chance=%.3f lost=%s",
                fleet.player_id, coords, chance, lost,
            )

    # -- 10) Preis-Snapshot in PlayerDiscovery (Upsert, Muster spionage.py) --
    # Kurse aus dem soeben aktualisierten npc.market (Schritt 7) ziehen -> eine Wahrheit
    # (DRY mit Spawner-Auto-Discovery und Spionage ueber merchant_intel).
    now = _now()
    if is_center:
        intel = {
            "name": npc.name,
            "merchant": True,
            "trade_center": True,
            "spec": spec,
            "prices": {r: round(price_of(r, stock[r], setpoint[r], cfg), 3) for r in RESOURCES},
            "prices_at": now.isoformat(),
        }
    else:
        intel = merchant_intel(npc, cfg, now.isoformat())
    disc = (await session.execute(
        select(PlayerDiscovery).where(
            PlayerDiscovery.player_id == fleet.player_id,
            PlayerDiscovery.galaxy == fleet.target_galaxy,
            PlayerDiscovery.system == fleet.target_system,
            PlayerDiscovery.position == fleet.target_position,
        )
    )).scalar_one_or_none()
    if disc is None:
        disc = PlayerDiscovery(
            player_id=fleet.player_id,
            galaxy=fleet.target_galaxy,
            system=fleet.target_system,
            position=fleet.target_position,
        )
        session.add(disc)
    disc.intel = intel
    disc.level = 1
    disc.discovered_at = now

    # -- 11) Handels-Beleg-Funkspruch --
    avg_sell = result["avg_sell_price"]
    avg_buy = result["avg_buy_price"]
    margin_pct = result["margin"] * 100.0
    refund_line = (
        f" Nicht ausgegebenes Budget wurde als {int(round(refund_offer))} {offer_res} erstattet "
        f"(Fracht-/Bestandsgrenze des Haendlers)."
        if refund_offer > 0 else ""
    )
    bonus_line = (
        f"\n🏴 Schwarzmarkt-Sonderkurs aktiv: +{int(round((rate_bonus - 1.0) * 100))}% mehr Ware."
        if is_black else ""
    )
    body = (
        f"Handel mit {npc.name} ({coords}) abgeschlossen.\n"
        f"Angeboten: {int(round(offer_amount))} {offer_res} "
        f"(Durchschnittskurs {avg_sell:.3f}).\n"
        f"Erhalten: {received:g} {want_res} "
        f"(Durchschnittskurs {avg_buy:.3f}).\n"
        f"Haendler-Marge {margin_pct:.1f}% (Reputationsstufe {level}/{rep_cfg['max_level']})."
        f"{refund_line}{bonus_line}"
    )
    await create_system_transmission(
        session,
        player_id=fleet.player_id,
        subject=f"Handelsbeleg — {npc.name} ({coords})",
        body=body,
        ttype="system",
    )

    # Friedlicher Moral-Gewinn + Funkspruch: ein erfolgreicher Handel belohnt + lässt den
    # begleitenden Kommandeur funken.
    if received > 0 and getattr(fleet, "commander_id", None):
        from app.commander.service import reward_commander_activity
        from app.messaging.service import commander_flavor_reaction
        from app.platform.models import Commander as _Cmd2
        await reward_commander_activity(session, fleet.commander_id, "trade_profit")
        _rc = await session.get(_Cmd2, fleet.commander_id)
        await commander_flavor_reaction(
            session, player_id=fleet.player_id, commander=_rc,
            situation="trade_profit", context={"planet": coords})

    # -- 12) Handelshistorie (best-effort: darf den Handel nie stoeren) --
    try:
        session.add(TradeLog(
            player_id=fleet.player_id,
            partner_kind="npc",
            partner_id=npc.id,
            partner_name=npc.name,
            offered_res=offer_res,
            offered_amount=round(float(offer_amount), 1),
            received_res=want_res,
            received_amount=float(received),
        ))
    except Exception:  # pragma: no cover - reine Absicherung
        log.exception("trade_log konnte nicht geschrieben werden (ignoriert)")

    summary = {
        "npc": npc.name,
        "location": coords,
        "offer_res": offer_res,
        "offer_amount": round(offer_amount, 1),
        "want_res": want_res,
        "received": received,
        "refund_offer": refund_offer,
        "reputation_level": level,
        "raided": raided,
        "lost": lost,
    }
    log.info(
        "Handel: player=%s npc=%s %s %g->%s %g rep=%d refund=%g",
        fleet.player_id, npc.name, offer_res, offer_amount, want_res, received, level, refund_offer,
    )
    return summary


# -- Markt-Regen-Tick ---------------------------------------------------------

async def market_regen_tick() -> None:
    """Periodischer Job (balance.trade.market_tick_interval_seconds).

    Laesst jeden Haendler-Bestand langsam zum Sollwert driften (``drift_stock``). Da die
    Bestaende GETEILT sind (alle Spieler handeln am selben Markt), erholt sich ein leer-
    gekaufter Bestand nur langsam -> der Kurs bleibt fuer Stunden verdorben (gewollte
    Vergaenglichkeit/Konkurrenz). Eigener ``session_scope`` mit Commit am Ende; direkt
    aufrufbar (Tests). JSONB als NEUES dict (SQLAlchemy-Change-Tracking)."""
    cfg = get_balance().trade
    regen = float(cfg["stock_regen_per_tick"])
    touched = 0

    async with session_scope() as session:
        npcs = (await session.execute(
            select(NpcEmpire).where(NpcEmpire.behavior_profile == "merchant")
        )).scalars().all()
        for npc in npcs:
            market = ensure_market(npc, cfg)  # lazy init, falls leer
            spec = market["spec"]
            stock = market["stock"]
            setpoint = market_setpoint(spec, cfg)
            new_stock = {
                res: drift_stock(stock[res], setpoint[res], regen) for res in RESOURCES
            }
            npc.market = {"spec": spec, "stock": new_stock}  # neues dict -> Change-Tracking
            touched += 1
        await session.commit()

    log.info("Markt-Regen-Tick: %d Haendler-Markt/Maerkte aktualisiert", touched)
