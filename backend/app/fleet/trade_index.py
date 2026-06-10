"""Globaler Handelsindex der unangreifbaren Handelszentren (``behavior_profile == 'trade_center'``).

Anders als die alten lokalen Haendler-Maerkte (``trade.py`` / ``trade_pricing.price_of``
ueber lokalen Bestand) preisen Handelszentren einen **universumsweiten** Kurs je Ressource:

    Kurs_r = base_value_r * (neutral_r + V_r) / (vorrat_r + V_r)

- ``vorrat_r``  = liquider Spieler-Weltvorrat (Summe ueber alle Spieler-Planeten),
  EMA-geglaettet ueber Ticks (``world_market``-Singleton).
- ``neutral_r`` = ``neutral_per_player_r * aktive_spieler`` -> skaliert mit Population,
  damit kein einzelner Spieler den Index dominiert.
- ``V_r``       = ``virtual_reserve`` (gross gegenueber Fruehphasen-Vorrat): haelt den Kurs
  bei wenig Spielern nahe ``base_value`` und stabil, und wirkt zugleich als **Order-Tiefe**
  (Slippage einer Grossorder laeuft gegen ``vorrat+V``).

Eleganz-Trick: Der Index laesst sich **als synthetischer Markt** in den vorhandenen
Preis-Kern speisen — ``setpoint = neutral+V``, ``stock = vorrat+V`` -> ``price_of`` liefert
exakt den Index, und ``simulate_swap`` macht die Order-Slippage unveraendert. Es wird KEIN
Bestand mutiert: ein Handel veraendert die Spieler-Ressourcen, die im naechsten Tick den
Weltvorrat (und damit den Index) verschieben -> der Rueckkopplungs-Loop entsteht von selbst.

Reine Funktionen (Formel, synthetischer Markt, EMA) sind DB-frei und direkt testbar.
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fleet.trade_pricing import price_of
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import Player, Resource, WorldMarket

log = logging.getLogger("universe.trade_index")

RESOURCES = ("metal", "crystal", "deuterium")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# -- Reine Index-Mathematik (DB-frei, testbar) --------------------------------

def synthetic_market(supply: dict, players: int, cfg: dict) -> tuple[dict, dict]:
    """Liefert (stock, setpoint) eines Handelszentrums fuer den globalen Index.

    setpoint_r = neutral_per_player_r * max(players, 1) + V_r
    stock_r    = max(supply_r, 0) + V_r
    Eingespeist in ``price_of``/``simulate_swap`` ergibt das den Index-Kurs samt Slippage.
    """
    idx = cfg["index"]
    neutral = idx["neutral_per_player"]
    reserve = idx["virtual_reserve"]
    p = max(int(players), 1)
    setpoint = {r: float(neutral[r]) * p + float(reserve[r]) for r in RESOURCES}
    stock = {r: max(0.0, float(supply.get(r, 0.0))) + float(reserve[r]) for r in RESOURCES}
    return stock, setpoint


def index_prices(supply: dict, players: int, cfg: dict) -> dict[str, float]:
    """Aktueller globaler Kurs je Ressource (Wert je Einheit), geclamped wie ``price_of``."""
    stock, setpoint = synthetic_market(supply, players, cfg)
    return {r: round(price_of(r, stock[r], setpoint[r], cfg), 3) for r in RESOURCES}


def ema(prev: dict | None, current: dict, alpha: float) -> dict:
    """EMA-Glaettung des Weltvorrats je Ressource. Ohne Vorwert -> aktueller Wert."""
    if not prev:
        return {r: float(current.get(r, 0.0)) for r in RESOURCES}
    a = float(alpha)
    return {
        r: a * float(current.get(r, 0.0)) + (1.0 - a) * float(prev.get(r, current.get(r, 0.0)))
        for r in RESOURCES
    }


# -- DB-Helfer ----------------------------------------------------------------

async def compute_supply(session: AsyncSession) -> dict[str, float]:
    """Liquider Weltvorrat je Ressource = SUM(amount) ueber alle Spieler-Planeten.

    In-Transit-Fracht ist beim Flottenstart abgebucht und hier bewusst NICHT enthalten
    (kehrt bei Rueckkehr zurueck). Verbautes Material (Gebaeude/Schiffe) ist ohnehin aus
    dem Umlauf — genau der liquide Bestand, der den Kurs setzen soll."""
    rows = (await session.execute(
        select(Resource.type, func.coalesce(func.sum(Resource.amount), 0.0))
        .where(Resource.type.in_(RESOURCES))
        .group_by(Resource.type)
    )).all()
    supply = {r: 0.0 for r in RESOURCES}
    for rtype, total in rows:
        supply[rtype] = float(total or 0.0)
    return supply


async def count_active_players(session: AsyncSession) -> int:
    n = (await session.execute(select(func.count(Player.id)))).scalar_one()
    return int(n or 0)


async def get_world_market(session: AsyncSession) -> WorldMarket:
    """Liest den Singleton; legt ihn lazy aus dem aktuellen Ist-Stand an, falls leer.

    So liefert der Index auch vor dem ersten Tick einen korrekten Kurs."""
    wm = await session.get(WorldMarket, 1)
    if wm is None:
        supply = await compute_supply(session)
        players = await count_active_players(session)
        wm = WorldMarket(id=1, supply=supply, players=max(players, 1), updated_at=_now())
        session.add(wm)
    return wm


async def index_market_for(session: AsyncSession, cfg: dict) -> tuple[dict, dict]:
    """(stock, setpoint) des globalen Index aus dem Singleton — fuer ``resolve_trade``."""
    wm = await get_world_market(session)
    return synthetic_market(wm.supply or {}, wm.players or 1, cfg)


# -- Index-Tick ---------------------------------------------------------------

async def index_tick() -> None:
    """Periodischer Job (balance.trade.index.tick_interval_seconds).

    Berechnet den liquiden Weltvorrat + die aktive Spielerzahl neu und schreibt den
    EMA-geglaetteten Vorrat in den ``world_market``-Singleton. Eigener ``session_scope``
    mit Commit; direkt aufrufbar (Tests)."""
    cfg = get_balance().trade
    alpha = float(cfg["index"]["smoothing_alpha"])

    async with session_scope() as session:
        current = await compute_supply(session)
        players = await count_active_players(session)
        wm = await get_world_market(session)
        smoothed = ema(wm.supply, current, alpha)
        wm.supply = smoothed
        wm.players = max(players, 1)
        wm.updated_at = _now()
        await session.commit()

    log.info("Index-Tick: Weltvorrat geglaettet=%s spieler=%d", smoothed, max(players, 1))
