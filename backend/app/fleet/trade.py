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
    Fleet,
    NpcEmpire,
    Planet,
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

    if npc is None or npc.behavior_profile not in ("merchant", "trade_center"):
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
    if is_center:
        stock, setpoint = await index_market_for(session, cfg)
        spec = "trade_center"
    else:
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

    # -- 7) Haendler-Bestand aktualisieren (nur Legacy-lokaler Markt; ein Handelszentrum
    #        hat keinen persistenten Bestand -> sein Index folgt im naechsten Tick dem Weltvorrat) --
    if not is_center:
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
            "spec": "trade_center",
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

    # Friedlicher Moral-Gewinn: ein erfolgreicher Handel belohnt den begleitenden Kommandeur.
    if received > 0 and getattr(fleet, "commander_id", None):
        from app.commander.service import reward_commander_activity
        await reward_commander_activity(session, fleet.commander_id, "trade_profit")

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
