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

from app.fleet.trade_pricing import price_of, simulate_swap
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import (
    Fleet,
    NpcEmpire,
    PlayerDiscovery,
    Ship,
    TradeReputation,
    UniverseCell,
)

log = logging.getLogger("universe.trade")

RESOURCES = ("metal", "crystal", "deuterium")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


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
    if market.get("spec") and market.get("stock"):
        return market  # bereits initialisiert -> idempotent

    spec = random.choice(list(cfg["specializations"].keys()))
    setpoint = market_setpoint(spec, cfg)
    stock = {res: round(setpoint[res]) for res in RESOURCES}
    market = {"spec": spec, "stock": stock}
    npc.market = market  # neues dict -> Change-Tracking
    return market


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
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == fleet.target_galaxy,
            UniverseCell.system == fleet.target_system,
            UniverseCell.position == fleet.target_position,
        )
    )).scalar_one_or_none()

    npc: NpcEmpire | None = None
    if cell and cell.occupant_type == "npc" and cell.ref_id is not None:
        npc = await session.get(NpcEmpire, cell.ref_id)
    if npc is None:
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == fleet.target_galaxy,
                NpcEmpire.system == fleet.target_system,
                NpcEmpire.position == fleet.target_position,
            )
        )).scalar_one_or_none()

    if npc is None or npc.behavior_profile != "merchant":
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

    # -- 2) Markt (lazy init) --
    market = ensure_market(npc, cfg)
    spec = market["spec"]
    stock = dict(market["stock"])
    setpoint = market_setpoint(spec, cfg)

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

    # -- 5) Cargo-Kapazitaet der Flotte (Vorbild combat) --
    from app.combat.service import _cargo_capacity
    ships = await _fleet_ships(session, fleet.id)
    capacity = _cargo_capacity(ships)

    # -- 6) Tausch simulieren (Slippage in beide Richtungen) --
    result = simulate_swap(
        offer_res, offer_amount, want_res, stock, setpoint, cfg,
        reputation_level=level, cargo_capacity=capacity,
    )

    # -- 7) Haendler-Bestand aktualisieren (neues dict, ganze Zahlen) --
    new_stock = {**stock, **{r: round(v) for r, v in result["new_stock"].items()}}
    npc.market = {"spec": spec, "stock": new_stock}

    # -- 8) Reputation hochzaehlen --
    rep.volume = float(rep.volume) + float(result["value_in"])
    rep.updated_at = _now()

    # -- 9) Flotten-Fracht setzen (kehrt via fleet_return heim) --
    received = round(result["received"], 1)
    cargo = {want_res: received}
    # Refund: nicht ausgegebenes Budget (Cargo-/Stock-Limit) als Angebots-Ressource zurueck.
    refund_offer = 0.0
    if result["refund_value"] > 0:
        refund_offer = round(result["refund_value"] / float(cfg["base_value"][offer_res]), 1)
        if refund_offer > 0:
            cargo[offer_res] = cargo.get(offer_res, 0.0) + refund_offer
    fleet.cargo = cargo

    # -- 10) Preis-Snapshot in PlayerDiscovery (Upsert, Muster spionage.py) --
    now = _now()
    prices = {
        r: round(price_of(r, new_stock[r], setpoint[r], cfg), 3)
        for r in RESOURCES
    }
    intel = {
        "name": npc.name,
        "merchant": True,
        "spec": spec,
        "prices": prices,
        "prices_at": now.isoformat(),
    }
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
    body = (
        f"Handel mit {npc.name} ({coords}) abgeschlossen.\n"
        f"Angeboten: {int(round(offer_amount))} {offer_res} "
        f"(Durchschnittskurs {avg_sell:.3f}).\n"
        f"Erhalten: {received:g} {want_res} "
        f"(Durchschnittskurs {avg_buy:.3f}).\n"
        f"Haendler-Marge {margin_pct:.1f}% (Reputationsstufe {level}/{rep_cfg['max_level']})."
        f"{refund_line}"
    )
    await create_system_transmission(
        session,
        player_id=fleet.player_id,
        subject=f"Handelsbeleg — {npc.name} ({coords})",
        body=body,
        ttype="system",
    )

    summary = {
        "npc": npc.name,
        "location": coords,
        "offer_res": offer_res,
        "offer_amount": round(offer_amount, 1),
        "want_res": want_res,
        "received": received,
        "refund_offer": refund_offer,
        "reputation_level": level,
    }
    log.info(
        "Handel: player=%s npc=%s %s %g->%s %g rep=%d refund=%g",
        fleet.player_id, npc.name, offer_res, offer_amount, want_res, received, level, refund_offer,
    )
    return summary
