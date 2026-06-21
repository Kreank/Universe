"""Router fuer den Handels-Reiter (Handels-Umbau, Vorbild ``/api/mining/fields``).

- ``GET /trade/centers``  : aktive NPC-Handelszentren PLUS fremde Spieler-Hubs in Reichweite
  des Handelsnetzes (Forschung ``trade_network`` + Handelszentrum-Gebaeude-Bonus), mit
  globalen Indexkursen und Range-/Forschungs-Info (analog ``MiningFieldsResponse``).
  Spieler-Hubs stehen separat unter ``player_hubs`` (kind='player_hub', owner_name, hub_margin).
- ``GET /trade/history``  : letzte N abgeschlossene Handel des Spielers (Historie); Hub-
  Einkommen des Besitzers erscheint hier als partner_kind='player'-Zeile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fleet.trade import hub_visible_to, owns_trade_center, trade_network_reach
from app.fleet.trade_index import get_world_market, index_prices
from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import Building, NpcEmpire, Planet, Player, TradeLog
from app.platform.security import get_current_player

router = APIRouter(tags=["trade"])


def serialize_trade_log(rows) -> list[dict]:
    """Reine Serialisierung von TradeLog-Zeilen fuer die History-Antwort (DB-frei testbar)."""
    return [
        {
            "id": str(t.id),
            "partner_kind": t.partner_kind,
            "partner_id": str(t.partner_id) if t.partner_id else None,
            "partner_name": t.partner_name,
            "offered_res": t.offered_res,
            "offered_amount": round(float(t.offered_amount), 1),
            "received_res": t.received_res,
            "received_amount": round(float(t.received_amount), 1),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in rows
    ]


@router.get("/trade/centers")
async def trade_centers(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Aktive NPC-Handelszentren in Reichweite des Handelsnetzes (Vorbild /api/mining/fields).

    Stufe 0 der Forschung ``trade_network`` zeigt bereits die eigene Galaxie (Handel ist nie
    hart gesperrt); jede Stufe erweitert die Reichweite um ``trade_network_range_per_level``
    Galaxien. Ein gebautes Handelszentrum (``trade_center``) erweitert sie um
    ``trade_network_range_bonus`` zusaetzlich. Kurse = globaler Indexkurs (fuer alle gleich)."""
    from app.economy.service import get_research_levels

    bal = get_balance()
    levels = await get_research_levels(session, player.id)
    level = int(levels.get("trade_network", 0))
    per = int(bal.data["research"]["effects"].get("trade_network_range_per_level", 1))

    tc_cfg = bal.buildings.get("trade_center", {})
    has_center = await owns_trade_center(session, player.id)
    building_bonus = int(tc_cfg.get("trade_network_range_bonus", 0)) if has_center else 0
    reach = trade_network_reach(level, per, building_bonus)

    # Heimat-Galaxie (Vorbild mining_fields): Heimatwelt bevorzugt, sonst irgendein Planet.
    home = (await session.execute(
        select(Planet.galaxy).where(Planet.player_id == player.id, Planet.is_homeworld.is_(True)).limit(1)
    )).scalar_one_or_none()
    if home is None:
        home = (await session.execute(
            select(Planet.galaxy).where(Planet.player_id == player.id).limit(1)
        )).scalar_one_or_none()
    if home is None:
        return {
            "trade_network": level, "range": reach, "building_bonus": building_bonus,
            "home_galaxy": None, "centers": [],
        }

    # Globaler Indexkurs (gleich fuer alle Zentren).
    wm = await get_world_market(session)
    prices = index_prices(wm.supply or {}, wm.players or 1, bal.trade)

    rows = (await session.execute(
        select(NpcEmpire)
        .where(
            NpcEmpire.behavior_profile == "trade_center",
            NpcEmpire.galaxy >= home - reach,
            NpcEmpire.galaxy <= home + reach,
        )
        .order_by(NpcEmpire.galaxy, NpcEmpire.system, NpcEmpire.position)
    )).scalars().all()

    centers = []
    for npc in rows:
        centers.append({
            "npc_id": str(npc.id),
            "name": npc.name,
            "galaxy": npc.galaxy, "system": npc.system, "position": npc.position,
            "coords": f"{npc.galaxy}:{npc.system}:{npc.position}",
            "spec": "trade_center",
            "prices": prices,
            "distance_galaxies": abs(int(npc.galaxy) - int(home)),
        })

    # Spieler-Hubs ANDERER in Reichweite: Planeten (kein Mond) mit gebautem Handelszentrum
    # (trade_center>=1), die NICHT dem Betrachter gehoeren. Kurse = globaler Index (wie NPC).
    # Markiert mit kind='player_hub' + owner_name, damit das Frontend sie unterscheiden kann.
    hub_margin = float(tc_cfg.get("hub_margin", 0.0))
    hub_margin = min(hub_margin, float(tc_cfg.get("hub_margin_max", hub_margin)))
    hub_rows = (await session.execute(
        select(Planet, Player.display_name)
        .join(Building, Building.planet_id == Planet.id)
        .join(Player, Player.id == Planet.player_id)
        .where(
            Building.type == "trade_center",
            Building.level >= 1,
            Planet.planet_type != "moon",
            Planet.player_id != player.id,
            Planet.galaxy >= home - reach,
            Planet.galaxy <= home + reach,
        )
        .order_by(Planet.galaxy, Planet.system, Planet.position)
    )).all()
    hubs = []
    for pl, owner_name in hub_rows:
        # Authoritative Filterregel (fremder Besitzer + in Reichweite); die SQL-WHERE oben ist
        # nur Vorfilter -> hier die getestete reine Regel als letzte Instanz.
        if not hub_visible_to(player.id, pl.player_id, pl.galaxy, home, reach):
            continue
        hubs.append({
            "kind": "player_hub",
            "planet_id": str(pl.id),
            "owner_name": owner_name,
            "name": pl.name,
            "galaxy": pl.galaxy, "system": pl.system, "position": pl.position,
            "coords": f"{pl.galaxy}:{pl.system}:{pl.position}",
            "prices": prices,
            "hub_margin": hub_margin,
            "distance_galaxies": abs(int(pl.galaxy) - int(home)),
        })

    return {
        "trade_network": level,
        "range": reach,
        "building_bonus": building_bonus,
        "home_galaxy": home,
        "centers": centers,
        "player_hubs": hubs,
    }


@router.get("/trade/history")
async def trade_history(
    limit: int = Query(30, ge=1, le=200),
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Letzte ``limit`` abgeschlossene Handel des Spielers (neueste zuerst)."""
    rows = (await session.execute(
        select(TradeLog)
        .where(TradeLog.player_id == player.id)
        .order_by(TradeLog.created_at.desc())
        .limit(int(limit))
    )).scalars().all()
    return {"entries": serialize_trade_log(rows)}
