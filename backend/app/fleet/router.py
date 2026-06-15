"""Router fuer Flotten (api-contract §6)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.fleet.schemas import FleetOut, IncomingAttackOut, SendFleetRequest
from app.fleet.service import fleet_to_dict, jump_fleet, list_incoming_attacks, recall_fleet, send_fleet
from app.platform.db import get_session
from app.platform.models import Fleet, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["fleet"])


@router.get("/fleets", response_model=list[FleetOut])
async def list_fleets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (await session.execute(
        select(Fleet)
        .where(Fleet.player_id == player.id, Fleet.status != "done")
        .order_by(Fleet.created_at.desc())
    )).scalars().all()
    return [await fleet_to_dict(session, f) for f in rows]


@router.get("/incoming-attacks", response_model=list[IncomingAttackOut])
async def incoming_attacks(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await list_incoming_attacks(session, player.id)


@router.post("/fleets/send", status_code=202, response_model=FleetOut)
async def send(
    body: SendFleetRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    cargo = body.cargo
    mission_data: dict = {}
    # Handel: Angebots-Ressource faehrt als Fracht mit; Auftrag in mission_data.
    if body.mission == "trade":
        if body.offer_res is None or body.want_res is None or body.offer_amount is None:
            raise HTTPException(status_code=422, detail="Handel benoetigt offer_res, offer_amount und want_res")
        mission_data = {
            "offer_res": body.offer_res,
            "offer_amount": body.offer_amount,
            "want_res": body.want_res,
            "escort_ids": body.escort_ids or [],
        }
        cargo = {body.offer_res: body.offer_amount}
    if body.ability_keys:
        mission_data["ability_keys"] = body.ability_keys
    if body.mission == "expedition" and body.expedition_hours is not None:
        mission_data["expedition_hours"] = body.expedition_hours
    if body.mission == "intercept" and body.radius is not None:
        mission_data["radius"] = body.radius
    if body.mission == "escort":
        if body.escort_radius is not None:
            mission_data["escort_radius"] = body.escort_radius
        if body.escort_fee_pct is not None:
            mission_data["escort_fee_pct"] = body.escort_fee_pct
    if body.target_type == "moon":
        mission_data["target_type"] = "moon"
    try:
        fleet = await send_fleet(
            session,
            player,
            origin_planet_id=uuid.UUID(body.origin_planet_id),
            target=(body.target.galaxy, body.target.system, body.target.position),
            mission=body.mission,
            ships=body.ships,
            cargo=cargo,
            commander_id=uuid.UUID(body.commander_id) if body.commander_id else None,
            speed_pct=body.speed_pct,
            mission_data=mission_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await fleet_to_dict(session, fleet)


class JumpRequest(BaseModel):
    from_moon_id: str
    to_moon_id: str
    ships: dict[str, int]


@router.post("/fleets/jump")
async def fleet_jump(
    body: JumpRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Sprungtor: Schiffe sofort zwischen zwei eigenen Monden versetzen."""
    try:
        result = await jump_fleet(
            session, player, uuid.UUID(body.from_moon_id), uuid.UUID(body.to_moon_id), body.ships
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return result


@router.post("/fleets/{fleet_id}/recall", response_model=FleetOut)
async def recall(
    fleet_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        fleet = await recall_fleet(session, player, fleet_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await fleet_to_dict(session, fleet)


class EscortOfferRequest(BaseModel):
    enabled: bool
    radius: int = 5
    fee_pct: float = 0.05


class InterceptModeRequest(BaseModel):
    enabled: bool
    radius: int = 0


class HomePatrolRequest(BaseModel):
    ships: dict[str, int]
    radius: int = 0


@router.get("/stationed")
async def list_stationed(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Eigene stationierte Patrouillen (deploy) inkl. Eskort-Angebot."""
    from app.fleet.stationing import station_out
    from app.platform.models import StationedFleet

    rows = (await session.execute(
        select(StationedFleet).where(StationedFleet.owner_id == player.id)
        .order_by(StationedFleet.created_at.desc())
    )).scalars().all()
    return [station_out(s) for s in rows]


@router.post("/stationed/{station_id}/recall")
async def recall_station_endpoint(
    station_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Ruft eine Patrouille zum Heimatplaneten zurueck (Rueckflug)."""
    from app.fleet.stationing import recall_station

    try:
        fleet = await recall_station(session, player, station_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return {"ok": True, "return_at": fleet.return_at.isoformat() if fleet.return_at else None}


@router.put("/stationed/{station_id}/escort")
async def set_escort_endpoint(
    station_id: uuid.UUID,
    body: EscortOfferRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Setzt das Eskort-Angebot einer eigenen Patrouille (Radius + Gebuehr %)."""
    from app.fleet.stationing import set_escort_offer, station_out
    from app.platform.models import StationedFleet

    st = await session.get(StationedFleet, station_id)
    if st is None or st.owner_id != player.id:
        raise HTTPException(status_code=404, detail="Patrouille nicht gefunden")
    set_escort_offer(st, body.enabled, body.radius, body.fee_pct)
    await session.commit()
    return station_out(st)


@router.put("/stationed/{station_id}/intercept")
async def set_intercept_endpoint(
    station_id: uuid.UUID,
    body: InterceptModeRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Setzt den Abfang-Modus einer eigenen Patrouille. Beim Aktivieren werden bereits
    fliegende Feindflotten erfasst, deren Route diese Patrouille kreuzt."""
    from app.economy.service import get_research_levels
    from app.fleet.interception import scan_inflight_for_station
    from app.fleet.service import fleet_slots, used_fleet_slots
    from app.fleet.stationing import intercept_radius_cap, set_intercept_mode, station_out
    from app.platform.models import StationedFleet

    st = await session.get(StationedFleet, station_id)
    if st is None or st.owner_id != player.id:
        raise HTTPException(status_code=404, detail="Patrouille nicht gefunden")
    # Eine NEUE Patrouille (aus->an) belegt einen Flottenslot. Radius aendern oder ausschalten nicht.
    if body.enabled and not st.intercept_enabled:
        if await used_fleet_slots(session, player.id) >= await fleet_slots(session, player.id):
            raise HTTPException(status_code=400, detail="Keine freien Flottenslots fuer eine Patrouille")
    cap = intercept_radius_cap(await get_research_levels(session, player.id))
    set_intercept_mode(st, body.enabled, body.radius, max_radius=cap)
    await session.flush()
    if st.intercept_enabled:
        try:
            await scan_inflight_for_station(session, st)
        except Exception:  # noqa: BLE001
            pass
    await session.commit()
    return station_out(st)


@router.post("/planets/{planet_id}/patrol")
async def patrol_home_endpoint(
    planet_id: uuid.UUID,
    body: HomePatrolRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Stellt Garnisons-Schiffe sofort als Abfang-Patrouille im eigenen System auf."""
    from app.economy.service import get_research_levels
    from app.fleet.interception import scan_inflight_for_station
    from app.fleet.service import fleet_slots, used_fleet_slots
    from app.fleet.stationing import create_home_patrol, intercept_radius_cap, station_out

    # Jede neue Patrouille belegt einen Flottenslot (Anti-Omnipraesenz).
    if await used_fleet_slots(session, player.id) >= await fleet_slots(session, player.id):
        raise HTTPException(status_code=400, detail="Keine freien Flottenslots fuer eine Patrouille")
    cap = intercept_radius_cap(await get_research_levels(session, player.id))
    try:
        st = await create_home_patrol(session, player, planet_id, body.ships, body.radius, max_radius=cap)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        await scan_inflight_for_station(session, st)
    except Exception:  # noqa: BLE001
        pass
    await session.commit()
    return station_out(st)


@router.get("/escort/offers")
async def escort_offers(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Verzeichnis aktiver Eskort-Angebote (alle Patrouillen mit aktiviertem Angebot)."""
    from app.fleet.stationing import station_power
    from app.platform.balance import get_balance
    from app.platform.models import StationedFleet

    bal = get_balance()
    rows = (await session.execute(
        select(StationedFleet).where(StationedFleet.escort_enabled.is_(True))
    )).scalars().all()
    out: list[dict] = []
    for s in rows:
        owner = await session.get(Player, s.owner_id)
        out.append({
            "id": str(s.id),
            "owner": owner.display_name if owner else "Unbekannt",
            "coords": f"{s.galaxy}:{s.system}:{s.position}",
            "galaxy": s.galaxy, "system": s.system,
            "radius": s.escort_radius,
            "fee_pct": s.escort_fee_pct,
            "power": round(station_power(s.ships or {}, bal)),
            "ships_total": sum((s.ships or {}).values()),
        })
    return out


class PhalanxScanRequest(BaseModel):
    galaxy: int
    system: int
    position: int


@router.post("/phalanx/scan")
async def phalanx_scan_endpoint(
    body: PhalanxScanRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Scannt Flottenbewegungen zu/von einer Koordinate (Sensorphalanx in Reichweite noetig)."""
    from app.fleet.phalanx import phalanx_scan

    try:
        result = await phalanx_scan(session, player, body.galaxy, body.system, body.position)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return result


@router.get("/trade/index")
async def trade_index(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Oeffentlicher, immer sichtbarer globaler Handelskurs der Handelszentren.

    Kurs je Ressource (Wert/Einheit) aus dem EMA-geglaetteten Weltvorrat. Damit
    braucht das Handels-UI keine Aufklaerung mehr — der Kurs ist immer abrufbar."""
    from app.fleet.trade_index import get_world_market, index_prices
    from app.platform.balance import get_balance

    wm = await get_world_market(session)
    bal = get_balance()
    prices = index_prices(wm.supply or {}, wm.players or 1, bal.trade)
    return {
        "prices": prices,
        "base_value": bal.trade["base_value"],
        "players": wm.players or 1,
        "updated_at": wm.updated_at.isoformat() if wm.updated_at else None,
    }


_TRADE_RESOURCES = ("metal", "crystal", "deuterium")


class TradeProfileIn(BaseModel):
    """P2P-Handelsprofil-Update (unverbindlicher Werbe-Kurs, klassisch)."""
    enabled: bool
    offer: str | None = None
    want: str | None = None
    rate: float | None = None
    note: str | None = None


class TradeProfileOut(BaseModel):
    enabled: bool
    offer: str | None = None
    want: str | None = None
    rate: float | None = None
    note: str | None = None


def _trade_profile_out(p: Player) -> "TradeProfileOut":
    return TradeProfileOut(
        enabled=p.trade_enabled, offer=p.trade_offer, want=p.trade_want,
        rate=p.trade_rate, note=p.trade_note,
    )


@router.get("/trade/profile", response_model=TradeProfileOut)
async def get_trade_profile(player: Player = Depends(get_current_player)) -> "TradeProfileOut":
    """Eigenes P2P-Handelsprofil."""
    return _trade_profile_out(player)


@router.put("/trade/profile", response_model=TradeProfileOut)
async def put_trade_profile(
    body: TradeProfileIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> "TradeProfileOut":
    """Eigenes P2P-Handelsprofil setzen. Der Kurs ist nur ein unverbindlicher Richtwert;
    ausgehandelt wird per Nachricht, abgewickelt mit normalen Transport-Flotten."""
    if body.enabled:
        if body.offer not in _TRADE_RESOURCES or body.want not in _TRADE_RESOURCES:
            raise HTTPException(status_code=422, detail="Biete/Erhalte muessen Ressourcen sein")
        if body.offer == body.want:
            raise HTTPException(status_code=422, detail="Biete und Erhalte muessen verschieden sein")
        if body.rate is not None and body.rate <= 0:
            raise HTTPException(status_code=422, detail="Kurs muss positiv sein")
    player.trade_enabled = bool(body.enabled)
    player.trade_offer = body.offer
    player.trade_want = body.want
    player.trade_rate = body.rate
    note = (body.note or "").strip()
    player.trade_note = note[:280] or None
    await session.commit()
    return _trade_profile_out(player)


class TradePartnerOut(BaseModel):
    player_id: str
    name: str
    offer: str | None = None
    want: str | None = None
    rate: float | None = None
    note: str | None = None
    coords: str | None = None


@router.get("/trade/partners", response_model=list[TradePartnerOut])
async def trade_partners(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[TradePartnerOut]:
    """Verzeichnis aktiver P2P-Haendler (alle Spieler mit aktiviertem Handelsprofil)."""
    from app.platform.models import Planet

    rows = (await session.execute(
        select(Player).where(Player.trade_enabled.is_(True), Player.id != player.id)
    )).scalars().all()
    out: list[TradePartnerOut] = []
    for p in rows:
        planet = (await session.execute(
            select(Planet).where(Planet.player_id == p.id)
            .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc())
        )).scalars().first()
        coords = f"{planet.galaxy}:{planet.system}:{planet.position}" if planet else None
        out.append(TradePartnerOut(
            player_id=str(p.id), name=p.display_name, offer=p.trade_offer,
            want=p.trade_want, rate=p.trade_rate, note=p.trade_note, coords=coords,
        ))
    return out


# -- Farm-Routinen (automatisiertes Farmen von Asteroiden-/Truemmerfeldern) -----

class RoutineWaypointIn(BaseModel):
    galaxy: int
    system: int
    position: int


class RoutineCreateIn(BaseModel):
    name: str
    home_planet_id: str
    ships: dict[str, int]
    waypoints: list[RoutineWaypointIn]


class RoutineUpdateIn(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    ships: dict[str, int] | None = None
    waypoints: list[RoutineWaypointIn] | None = None


@router.get("/routines")
async def list_routines(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Eigene Farm-Routinen + aktuelle Forschungs-Limits (Anzahl Routinen / Felder pro Route)."""
    from app.economy.service import get_research_levels
    from app.fleet.routines import list_routes, max_fields_per_route, max_routines, route_to_dict

    routes = await list_routes(session, player.id)
    research = await get_research_levels(session, player.id)
    return {
        "routines": [route_to_dict(r) for r in routes],
        "limits": {
            "max_routines": max_routines(research),
            "max_fields_per_route": max_fields_per_route(research),
            "used_routines": len(routes),
        },
    }


@router.post("/routines", status_code=201)
async def create_routine(
    body: RoutineCreateIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.fleet.routines import create_route, route_to_dict, schedule_start

    try:
        route = await create_route(
            session, player,
            name=body.name,
            home_planet_id=uuid.UUID(body.home_planet_id),
            ships=body.ships,
            waypoints=[w.model_dump() for w in body.waypoints],
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    out = route_to_dict(route)
    # Nach dem (auto-)Commit den ersten Zyklus anstossen (kleiner Verzug, damit der Commit landet).
    schedule_start(out["id"], delay_seconds=2.0)
    return out


@router.patch("/routines/{route_id}")
async def update_routine(
    route_id: uuid.UUID,
    body: RoutineUpdateIn,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.fleet.routines import route_to_dict, schedule_start, update_route

    try:
        route, should_start = await update_route(
            session, player, route_id,
            name=body.name,
            enabled=body.enabled,
            ships=body.ships,
            waypoints=[w.model_dump() for w in body.waypoints] if body.waypoints is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    out = route_to_dict(route)
    if should_start:
        schedule_start(out["id"], delay_seconds=2.0)
    return out


@router.delete("/routines/{route_id}")
async def delete_routine(
    route_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.fleet.routines import delete_route

    try:
        await delete_route(session, player, route_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/routines/{route_id}/resume")
async def resume_routine(
    route_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Setzt eine pausierte Routine fort (holt sie aus dem Wartezustand) und stoesst einen Zyklus an."""
    from app.fleet.routines import resume_route, route_to_dict, schedule_start

    try:
        route = await resume_route(session, player, route_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    out = route_to_dict(route)
    schedule_start(out["id"], delay_seconds=2.0)
    return out
