"""Stationierung (deploy) + Eskort-Patrouillen + Abfangen am Ziel.

- ``resolve_deploy``: stationiert die Flotten-Schiffe als persistente Patrouille
  (``StationedFleet``) — fuer den Besitzer gesperrt, bis Rueckruf; kann ein Eskort-
  Angebot tragen; ist ein gueltiges Angriffsziel.
- ``gather_interception_defenders``: am Ziel fangbare Flotten (durchreisend im Ankunfts-
  fenster) + stationierte Patrouillen — werden zur Verteidiger-Seite, wenn dort kein
  Planet/NPC steht (resolve_attack-Branch).
- ``distribute_losses``: reine, testbare Aufteilung aggregierter Ueberlebender auf mehrere
  Verteidiger-Quellen (greedy, in Reihenfolge).
- ``escort_covers`` / ``escort_fee``: Routen-Deckung + Gebuehr (% Frachtwert).
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import Fleet, Planet, Player, Ship, StationedFleet

log = logging.getLogger("universe.stationing")

UTC = dt.timezone.utc


def _now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


# -- Reine Helfer (testbar) ---------------------------------------------------

def distribute_losses(sources: list[dict], survivors: dict[str, int]) -> list[dict[str, int]]:
    """Verteilt aggregierte Ueberlebende (je Schiffstyp) greedy auf die Quellen in Reihenfolge.

    sources: [{"ships": {typ: count}}, ...]; survivors: {typ: gesamt_ueberlebend}.
    Liefert je Quelle ein Ueberlebenden-dict (fruehere Quellen werden zuerst gefuellt)."""
    remaining = {k: int(v) for k, v in survivors.items()}
    out: list[dict[str, int]] = []
    for src in sources:
        s_surv: dict[str, int] = {}
        for typ, cnt in (src.get("ships") or {}).items():
            give = min(int(cnt), remaining.get(typ, 0))
            if give > 0:
                s_surv[typ] = give
            remaining[typ] = remaining.get(typ, 0) - give
        out.append(s_surv)
    return out


def escort_covers(station: StationedFleet, route_systems: tuple[int, int, int, int]) -> bool:
    """Deckt die Patrouille die Route ab? route = (galaxy, sys_a, sys_b, _ignored).

    Gleiche Galaxie und das Stations-System liegt im Intervall [min,max] +/- escort_radius."""
    g, a, b = route_systems[0], route_systems[1], route_systems[2]
    if not station.escort_enabled or station.galaxy != g:
        return False
    lo, hi = min(a, b), max(a, b)
    r = int(station.escort_radius or 0)
    return (lo - r) <= station.system <= (hi + r)


def escort_fee(fee_pct: float, cargo_value: float) -> float:
    return round(max(0.0, float(fee_pct)) * max(0.0, float(cargo_value)), 1)


def station_power(ships: dict, bal) -> float:
    """Angriffsstaerke einer Schiffsmenge (fuer Eskort-Daempfung des Routenrisikos)."""
    total = 0.0
    for typ, count in (ships or {}).items():
        cfg = bal.ships.get(typ)
        if cfg:
            total += float(cfg.get("attack", 0)) * int(count)
    return total


# -- deploy: Stationierung ----------------------------------------------------

async def resolve_deploy(session: AsyncSession, fleet: Fleet) -> bool:
    """Stationiert die Flotten-Schiffe am Ziel als StationedFleet. True = stationiert
    (Flotte ``done``, kehrt nicht zurueck). Cargo wird mit heimgenommen? -> nein, deploy
    ist fuer Schiffe; etwaige Fracht bleibt unberuehrt (Versand sollte keine mitgeben)."""
    rows = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet.id)
    )).scalars().all()
    ships = {r.type: r.count for r in rows if r.count > 0}
    if not ships:
        return False
    coords = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
    st = StationedFleet(
        owner_id=fleet.player_id,
        home_planet_id=fleet.origin_planet_id,
        galaxy=fleet.target_galaxy,
        system=fleet.target_system,
        position=fleet.target_position,
        ships=ships,
    )
    session.add(st)
    for r in rows:
        await session.delete(r)
    fleet.status = "done"
    fleet.cargo = {}
    await create_system_transmission(
        session, player_id=fleet.player_id,
        subject=f"Flotte stationiert ({coords})",
        body=f"Deine Flotte ist bei {coords} stationiert. Sie ist gebunden, bis du sie "
             f"zurueckrufst, und kann als Eskorte angeboten werden (Handel-Tab).",
        ttype="system",
    )
    log.info("Deploy: player=%s stationiert %s @ %s", fleet.player_id, ships, coords)
    return True


# -- Abfangen: Mit-Verteidiger am Ziel ---------------------------------------

async def gather_interception_defenders(
    session: AsyncSession, attacker_player_id, galaxy: int, system: int, position: int, now: dt.datetime
) -> list[dict]:
    """Fangbare Verteidiger an einer Koordinate: durchreisende Flotten im Ankunftsfenster
    + stationierte Patrouillen (jeweils fremd). Liefert geordnete Quellen-Liste."""
    cfg = get_balance().data["phalanx"]
    window = float(cfg["intercept_window_seconds"])
    out: list[dict] = []

    fleets = (await session.execute(
        select(Fleet).where(
            Fleet.target_galaxy == galaxy,
            Fleet.target_system == system,
            Fleet.target_position == position,
            Fleet.player_id != attacker_player_id,
            Fleet.status.in_(("arrived", "returning")),
        )
    )).scalars().all()
    for f in fleets:
        arr = _aware(f.arrive_at)
        if arr is None or not (arr <= now <= arr + dt.timedelta(seconds=window)):
            continue
        rows = (await session.execute(
            select(Ship).where(Ship.fleet_id == f.id)
        )).scalars().all()
        ships = {r.type: r.count for r in rows if r.count > 0}
        if ships:
            out.append({"kind": "fleet", "obj": f, "rows": rows, "ships": ships})

    stations = (await session.execute(
        select(StationedFleet).where(
            StationedFleet.galaxy == galaxy,
            StationedFleet.system == system,
            StationedFleet.position == position,
            StationedFleet.owner_id != attacker_player_id,
        )
    )).scalars().all()
    for st in stations:
        ships = {t: c for t, c in (st.ships or {}).items() if c > 0}
        if ships:
            out.append({"kind": "station", "obj": st, "ships": ships})

    return out


# -- Rueckruf + Eskort-Angebot ------------------------------------------------

def station_out(st: StationedFleet) -> dict:
    return {
        "id": str(st.id),
        "coords": f"{st.galaxy}:{st.system}:{st.position}",
        "galaxy": st.galaxy, "system": st.system, "position": st.position,
        "ships": st.ships or {},
        "ships_total": sum((st.ships or {}).values()),
        "escort_enabled": st.escort_enabled,
        "escort_radius": st.escort_radius,
        "escort_fee_pct": st.escort_fee_pct,
    }


async def recall_station(session: AsyncSession, player: Player, station_id) -> Fleet:
    """Ruft eine stationierte Patrouille zum Heimatplaneten zurueck (Rueckflug)."""
    from app.fleet.service import compute_distance, fleet_return, flight_seconds, slowest_ship_speed
    from app.platform.scheduler import schedule_at

    st = await session.get(StationedFleet, station_id)
    if st is None or st.owner_id != player.id:
        raise ValueError("Patrouille nicht gefunden")
    ships = {t: c for t, c in (st.ships or {}).items() if c > 0}
    if not ships:
        await session.delete(st)
        raise ValueError("Patrouille ist leer")
    home = await session.get(Planet, st.home_planet_id) if st.home_planet_id else None
    if home is None:
        home = (await session.execute(
            select(Planet).where(Planet.player_id == player.id)
            .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc())
        )).scalars().first()
    if home is None:
        raise RuntimeError("Kein Heimatplanet fuer den Rueckruf")

    dist = compute_distance((st.galaxy, st.system, st.position), (home.galaxy, home.system, home.position))
    secs = flight_seconds(dist, slowest_ship_speed(ships), 100)
    now = _now()
    fleet = Fleet(
        player_id=player.id, origin_planet_id=home.id,
        target_galaxy=st.galaxy, target_system=st.system, target_position=st.position,
        mission="deploy", status="returning",
        depart_at=now, arrive_at=now, return_at=now + dt.timedelta(seconds=int(secs)),
        cargo={},
    )
    session.add(fleet)
    await session.flush()
    for typ, count in ships.items():
        session.add(Ship(planet_id=None, fleet_id=fleet.id, type=typ, count=int(count)))
    await session.delete(st)
    schedule_at(fleet.return_at, fleet_return, str(fleet.id), job_id=f"fleet-return:{fleet.id}")
    log.info("Rueckruf: player=%s station %s -> heim in %ds", player.id, station_id, int(secs))
    return fleet


def set_escort_offer(st: StationedFleet, enabled: bool, radius: int, fee_pct: float) -> None:
    """Setzt/aktualisiert das Eskort-Angebot einer Patrouille (mit Validierung gegen Cap)."""
    cap = float(get_balance().data.get("escort", {}).get("max_fee_pct", 0.10))
    st.escort_enabled = bool(enabled)
    st.escort_radius = max(0, int(radius or 0))
    st.escort_fee_pct = max(0.0, min(cap, float(fee_pct or 0.0)))


async def charge_trade_escorts(
    session: AsyncSession, owner_player_id, origin_planet, target: tuple[int, int, int],
    escort_ids: list, cargo_value: float,
) -> float:
    """Bucht gewaehlte, die Route deckende Eskorten: Gebuehr (Deuterium) vom Origin abziehen,
    den Anbietern gutschreiben; liefert die Gesamt-Eskort-Kampfkraft (daempft Routenrisiko).
    Fremde/nicht deckende/eigene IDs werden ignoriert. Wirft RuntimeError bei zu wenig Deuterium."""
    import uuid as _uuid

    from app.economy.service import add_resources, spend_resources

    if not escort_ids:
        return 0.0
    bal = get_balance()
    route = (origin_planet.galaxy, origin_planet.system, target[1], 0)
    total_power = 0.0
    total_fee = 0.0
    credits: list[tuple[StationedFleet, float]] = []
    for sid in escort_ids:
        try:
            st = await session.get(StationedFleet, _uuid.UUID(str(sid)))
        except (ValueError, TypeError):
            continue
        if st is None or not st.escort_enabled or st.owner_id == owner_player_id:
            continue
        if not escort_covers(st, route):
            continue
        total_power += station_power(st.ships or {}, bal)
        fee = escort_fee(st.escort_fee_pct, cargo_value)
        total_fee += fee
        credits.append((st, fee))
    if total_fee > 0:
        if not await spend_resources(session, origin_planet, {"deuterium": total_fee}):
            raise RuntimeError(f"Nicht genug Deuterium fuer die Eskort-Gebuehr ({int(total_fee)})")
        for st, fee in credits:
            if fee <= 0:
                continue
            home = await session.get(Planet, st.home_planet_id) if st.home_planet_id else None
            if home is not None:
                await add_resources(session, home, {"deuterium": fee})
            await create_system_transmission(
                session, player_id=st.owner_id,
                subject="Eskort-Gebuehr erhalten",
                body=f"Du hast {int(fee)} Deuterium Eskort-Gebuehr fuer Geleitschutz erhalten.",
                ttype="system",
            )
    return total_power

