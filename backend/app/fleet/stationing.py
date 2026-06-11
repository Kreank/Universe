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
    roster = get_balance().data.get("combat_roster", {})
    ships = st.ships or {}
    has_interdictor = any(bool(roster.get(t, {}).get("interdictor")) for t in ships)
    return {
        "id": str(st.id),
        "coords": f"{st.galaxy}:{st.system}:{st.position}",
        "galaxy": st.galaxy, "system": st.system, "position": st.position,
        "ships": ships,
        "ships_total": sum(ships.values()),
        "escort_enabled": st.escort_enabled,
        "escort_radius": st.escort_radius,
        "escort_fee_pct": st.escort_fee_pct,
        "intercept_enabled": bool(getattr(st, "intercept_enabled", False)),
        "intercept_radius": int(getattr(st, "intercept_radius", 0) or 0),
        "has_interdictor": has_interdictor,
        "interceptors": int(ships.get("interceptor", 0)),
    }


def intercept_radius_cap(research: dict | None = None) -> int:
    """Maximaler Abfang-Radius = Basis-Cap + Hyperraum-Interdiktion-Forschung."""
    icfg = get_balance().data.get("combat", {}).get("interception", {})
    base = int(icfg.get("max_radius", 5))
    lvl = int((research or {}).get("hyperspace_interdiction", 0))
    return base + int(icfg.get("radius_per_interdiction_level", 0)) * lvl


def set_intercept_mode(st: StationedFleet, enabled: bool, radius: int, max_radius: int | None = None) -> None:
    """Setzt/aktualisiert den Abfang-Modus einer Patrouille (Radius-Cap aus balance + Forschung)."""
    cap = max_radius if max_radius is not None else intercept_radius_cap()
    st.intercept_enabled = bool(enabled)
    st.intercept_radius = max(0, min(int(cap), int(radius or 0)))


async def create_home_patrol(
    session: AsyncSession, player: Player, planet_id, ships_req: dict, radius: int,
    max_radius: int | None = None,
) -> StationedFleet:
    """Stellt Garnisons-Schiffe eines eigenen Planeten SOFORT (ohne Flug) als Abfang-Patrouille
    im EIGENEN System auf. Reuset die StationedFleet-/Abfang-Mechanik (intercept_enabled an)."""
    import uuid as _uuid

    try:
        pid = planet_id if isinstance(planet_id, _uuid.UUID) else _uuid.UUID(str(planet_id))
    except (ValueError, TypeError) as exc:
        raise ValueError("Ungueltige Planeten-ID") from exc
    planet = await session.get(Planet, pid)
    if planet is None or planet.player_id != player.id:
        raise ValueError("Planet nicht gefunden")

    want = {t: int(c) for t, c in (ships_req or {}).items() if int(c) > 0}
    if not want:
        raise ValueError("Keine Schiffe ausgewaehlt")

    rows = (await session.execute(
        select(Ship).where(Ship.planet_id == planet.id, Ship.fleet_id.is_(None))
    )).scalars().all()
    avail = {r.type: r for r in rows}
    moved: dict[str, int] = {}
    for typ, cnt in want.items():
        row = avail.get(typ)
        take = min(cnt, row.count) if row else 0
        if take <= 0:
            continue
        moved[typ] = take
        row.count -= take
        if row.count <= 0:
            await session.delete(row)
    if not moved:
        raise ValueError("Schiffe nicht in der Garnison verfuegbar")

    cap = max_radius if max_radius is not None else intercept_radius_cap()
    st = StationedFleet(
        owner_id=player.id, home_planet_id=planet.id,
        galaxy=planet.galaxy, system=planet.system, position=planet.position,
        ships=moved, intercept_enabled=True, intercept_radius=max(0, min(int(cap), int(radius or 0))),
    )
    session.add(st)
    await session.flush()
    coords = f"{planet.galaxy}:{planet.system}:{planet.position}"
    await create_system_transmission(
        session, player_id=player.id,
        subject=f"Heim-Patrouille aktiv ({coords})",
        body=f"Deine Patrouille bei {coords} fängt durchreisende Feindflotten im Umkreis ab. "
             f"Rückruf bringt die Schiffe zurück in die Garnison.",
        ttype="system",
    )
    log.info("Heim-Patrouille: player=%s %s @ %s", player.id, moved, coords)
    return st


async def recall_station(session: AsyncSession, player: Player, station_id) -> Fleet:
    """Ruft eine stationierte Patrouille zum Heimatplaneten zurueck (Rueckflug)."""
    from app.economy.service import get_research_levels
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
    research = await get_research_levels(session, player.id)
    secs = flight_seconds(dist, slowest_ship_speed(ships, research), 100)
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

