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


def station_upkeep(ships: dict, bal) -> float:
    """Treibstoff-Unterhalts-Basis pro Tick (vor upkeep_ratio): Summe(Schiff-fuel * Anzahl).
    Pure Funktion fuer Tuning/Tests."""
    return float(sum(bal.ships.get(t, {}).get("fuel", 0) * int(c) for t, c in (ships or {}).items()))


def starter_reserve(ships: dict, bal) -> float:
    """Starter-Treibstoff-Tank fuer Patrouillen ohne mitgefuehrtes Deuterium (z.B. Sofort-Heim-
    Patrouille aus der Garnison). = starter_reserve_factor * station_upkeep. Fuer echte Ausdauer
    laedt man stattdessen Deuterium (Transporter) als Fracht der Deploy-Flotte mit."""
    cfg = bal.fleet.get("station_fuel", {})
    return station_upkeep(ships, bal) * float(cfg.get("starter_reserve_factor", 0.5))


# -- deploy: Stationierung ----------------------------------------------------

async def _land_at_own_planet(
    session: AsyncSession,
    fleet: Fleet,
    planet: Planet,
    ship_rows: list,
    ships: dict,
    cargo: dict,
    coords: str,
) -> None:
    """Landet eine stationierende Flotte auf dem eigenen Ziel-Planeten/-Mond: Schiffe werden
    Teil der Planeten-Garnison (mit gleichartigen Zeilen verschmolzen) und die komplette Fracht
    wird gutgeschrieben (Lager darf ueberfuellt werden, wie beim Transport)."""
    from app.economy.service import add_resources

    for r in ship_rows:
        existing = (await session.execute(
            select(Ship).where(
                Ship.planet_id == planet.id, Ship.fleet_id.is_(None), Ship.type == r.type
            )
        )).scalars().all()
        if existing:
            dest = existing[0]
            dest.count += r.count
            for extra in existing[1:]:  # etwaige Duplikate konsolidieren
                dest.count += extra.count
                await session.delete(extra)
            await session.delete(r)
        else:
            r.planet_id = planet.id   # bestehende Schiff-Zeile umhaengen statt neu anlegen
            r.fleet_id = None

    if cargo:
        await add_resources(session, planet, cargo)
    # Phase 2 (Q3): Crew der gelandeten Schiffe geht in die ZIEL-Planeten-Bevoelkerung (Einbahn),
    # gedeckelt auf die mitgeflogene Crew. Alt-Flotten ohne embarked_crew -> 0 (keine Gratis-Pop).
    from app.economy.service import add_population, fleet_crew
    embarked = float((fleet.mission_data or {}).get("embarked_crew", 0) or 0)
    land_crew = min(fleet_crew(ships), embarked)
    if land_crew > 0:
        await add_population(session, planet, land_crew)

    fleet.status = "done"
    fleet.cargo = {}
    parts = ", ".join(
        f"{int(v):,}".replace(",", ".") + " " + k for k, v in cargo.items()
    ) or "keine Fracht"
    await create_system_transmission(
        session, player_id=fleet.player_id,
        subject=f"🛬 Flotte gelandet ({coords})",
        body=(f"Deine Flotte ist bei {coords} auf deinem eigenen Planeten gelandet — die Schiffe "
              f"stehen dort wieder zur Verfuegung. Gutgeschrieben: {parts}."),
        ttype="system",
    )
    log.info("Deploy(park@own): player=%s landet %s @ %s, cargo=%s", fleet.player_id, ships, coords, cargo)


async def resolve_deploy(session: AsyncSession, fleet: Fleet, mode: str = "park") -> bool:
    """Stationiert die Flotten-Schiffe am Ziel als StationedFleet. True = stationiert
    (Flotte ``done``, kehrt nicht zurueck).

    Genau EIN exklusiver Modus je Station (2026-06-13):
    - ``park``      (Mission 'Stationierung'): rein passiv geparkt. Faengt NICHT ab, bietet
      keine Eskorte. Auf eigenem Gebiet kein Unterhalt.
    - ``intercept`` (Mission 'Abfangen'): aktive Abfang-Patrouille (intercept_enabled, Radius
      aus mission_data, auf Forschungs-Cap geklemmt). Erfasst bereits fliegende Feindflotten.
    - ``escort``    (Mission 'Eskorte'): bietet Geleitschutz fuer Trader an (escort_enabled,
      Radius + Gebuehr aus mission_data). Faengt NICHT ab."""
    intercept = mode == "intercept"
    escort = mode == "escort"
    rows = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet.id)
    )).scalars().all()
    ships = {r.type: r.count for r in rows if r.count > 0}
    if not ships:
        return False
    coords = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"
    md = fleet.mission_data or {}
    cargo = {k: float(v) for k, v in (fleet.cargo or {}).items() if float(v) > 0}

    # Eigener Himmelskoerper am Ziel? Planet vs. Mond anhand mission_data.target_type aufloesen
    # (beide koennen dieselbe Koordinate teilen — wie beim Transport).
    target_moon = md.get("target_type") == "moon"
    own_rows = (await session.execute(
        select(Planet).where(
            Planet.player_id == fleet.player_id,
            Planet.galaxy == fleet.target_galaxy,
            Planet.system == fleet.target_system,
            Planet.position == fleet.target_position,
        )
    )).scalars().all()
    own_here: Planet | None = None
    for pl in own_rows:
        is_moon = (pl.planet_type == "moon")
        if (target_moon and is_moon) or (not target_moon and not is_moon):
            own_here = pl
            break
    if own_here is None and len(own_rows) == 1:
        own_here = own_rows[0]  # nur ein eigener Koerper an der Koordinate -> eindeutig

    # --- Reines Parken auf EIGENEM Planeten/Mond = "buendeln" ------------------
    # Schiffe landen dort (werden wieder Teil der Planeten-Flotte) und die KOMPLETTE Fracht wird
    # gutgeschrieben — kein gesperrter Garnisons-Zustand, kein Frachtverlust. Abfangen/Eskorte
    # bleiben auch im eigenen System aktive Stationen, daher nur fuer ``mode == 'park'``.
    if mode == "park" and own_here is not None:
        await _land_at_own_planet(session, fleet, own_here, rows, ships, cargo, coords)
        return True

    # Treibstoff-Tank = mitgefuehrtes Deuterium (Fracht). Wird als Vorrat BEHALTEN. Gezehrt wird
    # erst im station_fuel_tick. Laenger patrouillieren -> mehr Deuterium mitladen. Restliche
    # Nicht-Treibstoff-Fracht (Metall/Kristall/Exoten) bleibt an Bord und kommt beim Rueckruf zurueck.
    fuel_reserve = float(cargo.get("deuterium", 0) or 0)
    held_cargo = {k: v for k, v in cargo.items() if k != "deuterium" and v > 0}

    radius = 0
    esc_radius = 0
    esc_fee = 0.0
    if intercept:
        from app.economy.service import get_research_levels
        research = await get_research_levels(session, fleet.player_id)
        cap = intercept_radius_cap(research)
        radius = max(0, min(cap, int(md.get("radius", 0) or 0)))
        # Patrouille ohne mitgefuehrtes Deuterium bekommt einen Starter-Tank, sonst Sofort-Rueckkehr.
        if fuel_reserve <= 0:
            fuel_reserve = starter_reserve(ships, get_balance())
    elif escort:
        ecfg = get_balance().data.get("escort", {})
        cap_fee = float(ecfg.get("max_fee_pct", 0.10))
        esc_radius = max(0, int(md.get("escort_radius", ecfg.get("region_radius", 5)) or 0))
        esc_fee = max(0.0, min(cap_fee, float(md.get("escort_fee_pct", 0.0) or 0.0)))
        # Vorgeschobene Eskorte ohne Deuterium bekommt einen Starter-Tank (sonst Sofort-Rueckkehr).
        if own_here is None and fuel_reserve <= 0:
            fuel_reserve = starter_reserve(ships, get_balance())

    st = StationedFleet(
        owner_id=fleet.player_id,
        home_planet_id=fleet.origin_planet_id,
        galaxy=fleet.target_galaxy,
        system=fleet.target_system,
        position=fleet.target_position,
        ships=ships,
        fuel=fuel_reserve,
        cargo=held_cargo,
        intercept_enabled=intercept,
        intercept_radius=radius,
        escort_enabled=escort,
        escort_radius=esc_radius,
        escort_fee_pct=esc_fee,
    )
    session.add(st)
    for r in rows:
        await session.delete(r)
    fleet.status = "done"
    fleet.cargo = {}

    if intercept:
        await session.flush()
        from app.fleet.interception import scan_inflight_for_station
        try:
            await scan_inflight_for_station(session, st)
        except Exception:  # noqa: BLE001
            pass
        scope = "im Stationssystem" if radius <= 0 else f"+/- {radius} Systeme"
        body = (f"Deine Abfang-Patrouille ist bei {coords} aktiv ({scope}) mit {int(fuel_reserve)} "
                f"Deuterium-Vorrat. Sie stellt feindliche Flotten, deren Route sie kreuzt; der Vorrat "
                f"zehrt mit der Zeit (leer -> Rueckkehr). Fuer Ausdauer mehr Deuterium mitladen.")
        subject = f"Abfang-Patrouille aktiv ({coords})"
    elif escort:
        body = (f"Deine Eskorte ist bei {coords} stationiert ({int(esc_fee * 100)} % Gebuehr, "
                f"Radius +/- {esc_radius} Systeme) mit {int(fuel_reserve)} Deuterium-Vorrat. Sie bietet "
                f"Tradern auf gedeckten Routen Geleitschutz; sie faengt selbst keine Flotten ab.")
        subject = f"Eskorte stationiert ({coords})"
    elif own_here is not None:
        body = (f"Deine Flotte ist bei {coords} (eigenes Gebiet) geparkt mit {int(fuel_reserve)} "
                f"Deuterium-Vorrat. Rein passiv: kein Unterhalt, faengt nicht ab, bietet keine Eskorte.")
        subject = f"Flotte stationiert ({coords})"
    else:
        body = (f"Deine Flotte ist VORGESCHOBEN bei {coords} geparkt mit {int(fuel_reserve)} "
                f"Deuterium-Vorrat. Rein passiv (kein Abfangen). Der Vorrat zehrt mit der Zeit; ist er "
                f"leer, kehrt die Flotte automatisch heim. Lade beim Stationieren genug Deuterium als Fracht.")
        subject = f"Flotte stationiert ({coords})"
    await create_system_transmission(
        session, player_id=fleet.player_id, subject=subject, body=body, ttype="system",
    )
    log.info("Deploy(mode=%s): player=%s stationiert %s @ %s", mode, fleet.player_id, ships, coords)
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

def station_mode(st: StationedFleet) -> str:
    """Exklusiver Anzeige-Modus einer Station: 'intercept' | 'escort' | 'park'.
    Bei Altbestand mit beiden Flags gewinnt das aktive Abfangen (Kampf vor Handel)."""
    if getattr(st, "intercept_enabled", False):
        return "intercept"
    if getattr(st, "escort_enabled", False):
        return "escort"
    return "park"


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
        "cargo": {k: v for k, v in (getattr(st, "cargo", None) or {}).items() if v},
        "mode": station_mode(st),
        "escort_enabled": st.escort_enabled,
        "escort_radius": st.escort_radius,
        "escort_fee_pct": st.escort_fee_pct,
        "intercept_enabled": bool(getattr(st, "intercept_enabled", False)),
        "intercept_radius": int(getattr(st, "intercept_radius", 0) or 0),
        "has_interdictor": has_interdictor,
        "interceptors": int(ships.get("interceptor", 0)),
        # Treibstoff: None = eigenes Gebiet (gratis), Zahl = vorgeschobener Vorrat.
        "fuel": (None if getattr(st, "fuel", None) is None else int(round(float(st.fuel)))),
    }


def intercept_radius_cap(research: dict | None = None) -> int:
    """Maximal waehlbarer Abfang-Radius = base_radius + Hyperraum-Interdiktion-Forschung,
    hart gedeckelt bei max_radius. Ohne Forschung also base_radius (1); Forschung dehnt
    +radius_per_interdiction_level/Stufe bis max_radius (6). Default-Radius einer Patrouille ist 0."""
    icfg = get_balance().data.get("combat", {}).get("interception", {})
    base = int(icfg.get("base_radius", 1))
    hard_cap = int(icfg.get("max_radius", 6))
    lvl = int((research or {}).get("hyperspace_interdiction", 0))
    return min(hard_cap, base + int(icfg.get("radius_per_interdiction_level", 0)) * lvl)


def set_intercept_mode(st: StationedFleet, enabled: bool, radius: int, max_radius: int | None = None) -> None:
    """Setzt/aktualisiert den Abfang-Modus einer Patrouille (Radius-Cap aus balance + Forschung).
    Exklusiv: Abfangen scharf -> Eskort-Angebot wird abgeschaltet (genau ein Modus je Station).
    Schaltet man eine Patrouille OHNE Treibstoff-Tank scharf (fuel None, z.B. Alt-Stationierung
    auf eigenem Gebiet), bekommt sie einen Starter-Tank, damit der Unterhalt greift."""
    cap = max_radius if max_radius is not None else intercept_radius_cap()
    st.intercept_enabled = bool(enabled)
    st.intercept_radius = max(0, min(int(cap), int(radius or 0)))
    if st.intercept_enabled:
        # Exklusiv zur Eskorte.
        st.escort_enabled = False
        if getattr(st, "fuel", None) is None:
            st.fuel = starter_reserve(st.ships or {}, get_balance())


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
        fuel=starter_reserve(moved, get_balance()),
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


async def _send_station_home(session: AsyncSession, st: StationedFleet) -> Fleet | None:
    """Schickt eine stationierte Flotte zum Heimatplaneten zurueck (Rueckflug) und loescht die
    Station. Liefert das Rueckflug-Fleet oder None (leer / kein Heimatplanet). Geteilt von
    Rueckruf (manuell) und Treibstoff-Tick (Zwangs-Rueckkehr)."""
    from app.economy.service import fleet_crew, get_research_levels
    from app.fleet.service import compute_distance, fleet_return, flight_seconds, slowest_ship_speed
    from app.platform.scheduler import schedule_at

    ships = {t: c for t, c in (st.ships or {}).items() if c > 0}
    if not ships:
        await session.delete(st)
        return None
    home = await session.get(Planet, st.home_planet_id) if st.home_planet_id else None
    if home is None:
        home = (await session.execute(
            select(Planet).where(Planet.player_id == st.owner_id)
            .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc())
        )).scalars().first()
    if home is None:
        return None
    dist = compute_distance((st.galaxy, st.system, st.position), (home.galaxy, home.system, home.position))
    research = await get_research_levels(session, st.owner_id)
    secs = flight_seconds(dist, slowest_ship_speed(ships, research), 100)
    now = _now()
    # Mitgefuehrte Nicht-Treibstoff-Fracht der Station kehrt mit zurueck (sonst Frachtverlust).
    return_cargo = {k: float(v) for k, v in (st.cargo or {}).items() if float(v) > 0}
    fleet = Fleet(
        player_id=st.owner_id, origin_planet_id=home.id,
        target_galaxy=st.galaxy, target_system=st.system, target_position=st.position,
        mission="deploy", status="returning",
        depart_at=now, arrive_at=now, return_at=now + dt.timedelta(seconds=int(secs)),
        cargo=return_cargo,
        # Phase 2: die Crew der zurueckkehrenden Station-Schiffe wird bei der Heimkehr (fleet_return)
        # der Heimat-Bevoelkerung gutgeschrieben (Station kann nicht kapern -> Deckel = eigene Crew).
        mission_data={"embarked_crew": fleet_crew(ships)},
    )
    session.add(fleet)
    await session.flush()
    for typ, count in ships.items():
        session.add(Ship(planet_id=None, fleet_id=fleet.id, type=typ, count=int(count)))
    await session.delete(st)
    schedule_at(fleet.return_at, fleet_return, str(fleet.id), job_id=f"fleet-return:{fleet.id}")
    return fleet


async def recall_station(session: AsyncSession, player: Player, station_id) -> Fleet:
    """Ruft eine stationierte Patrouille zum Heimatplaneten zurueck (Rueckflug)."""
    st = await session.get(StationedFleet, station_id)
    if st is None or st.owner_id != player.id:
        raise ValueError("Patrouille nicht gefunden")
    if not {t: c for t, c in (st.ships or {}).items() if c > 0}:
        await session.delete(st)
        raise ValueError("Patrouille ist leer")
    fleet = await _send_station_home(session, st)
    if fleet is None:
        raise RuntimeError("Kein Heimatplanet fuer den Rueckruf")
    log.info("Rueckruf: player=%s station %s -> heim", player.id, station_id)
    return fleet


async def station_fuel_tick() -> None:
    """Periodischer Job (balance.fleet.station_fuel.tick_interval_seconds): zehrt den Treibstoff-
    Vorrat (fuel IS NOT NULL). Ist er leer -> Zwangs-Rueckkehr heim.

    Zwei Saetze (getrennt von der Patrouillen-Slot-Logik): VORGESCHOBEN (Stationssystem ist KEIN
    eigener Planet) zehrt IMMER mit upkeep_ratio_per_tick (Modell C, auch geparkt). EIGENES Gebiet
    zehrt NUR als Patrouille (intercept_enabled) und langsamer (own_upkeep_ratio_per_tick) — geparkte
    Eigen-Flotten/Eskorten bleiben gratis."""
    from app.platform.db import session_scope

    bal = get_balance()
    cfg = bal.fleet.get("station_fuel", {})
    fwd_ratio = float(cfg.get("upkeep_ratio_per_tick", 0.0))
    own_ratio = float(cfg.get("own_upkeep_ratio_per_tick", 0.0))
    if fwd_ratio <= 0 and own_ratio <= 0:
        return
    async with session_scope() as session:
        stations = (await session.execute(
            select(StationedFleet).where(StationedFleet.fuel.isnot(None))
        )).scalars().all()
        owned_cache: dict = {}  # owner_id -> set[(galaxy, system, position)]
        recalled = 0
        for st in stations:
            owned = owned_cache.get(st.owner_id)
            if owned is None:
                planets = (await session.execute(
                    select(Planet.galaxy, Planet.system, Planet.position)
                    .where(Planet.player_id == st.owner_id)
                )).all()
                owned = {(p.galaxy, p.system, p.position) for p in planets}
                owned_cache[st.owner_id] = owned
            is_own = (st.galaxy, st.system, st.position) in owned
            if is_own:
                if not st.intercept_enabled:
                    continue  # eigenes Gebiet, geparkt -> gratis
                ratio = own_ratio
            else:
                ratio = fwd_ratio  # vorgeschoben -> immer
            if ratio <= 0:
                continue
            st.fuel = float(st.fuel or 0) - station_upkeep(st.ships or {}, bal) * ratio
            if st.fuel <= 0:
                coords = f"{st.galaxy}:{st.system}:{st.position}"
                owner_id = st.owner_id
                where = "Patrouille" if is_own else "vorgeschobenen Flotte"
                fleet = await _send_station_home(session, st)
                if fleet is not None:
                    recalled += 1
                    await create_system_transmission(
                        session, player_id=owner_id,
                        subject=f"⛽ Treibstoff leer — Flotte kehrt heim ({coords})",
                        body=(f"Der Deuterium-Vorrat deiner {where} bei {coords} ist erschoepft. "
                              f"Sie tritt automatisch den Rueckflug an."),
                        ttype="system",
                    )
        if recalled:
            log.info("Treibstoff-Tick: %d Flotte(n) heimgeschickt (leer)", recalled)


def set_escort_offer(st: StationedFleet, enabled: bool, radius: int, fee_pct: float) -> None:
    """Setzt/aktualisiert das Eskort-Angebot einer Patrouille (mit Validierung gegen Cap).
    Exklusiv: Eskorte an -> Abfangen wird abgeschaltet (genau ein Modus je Station)."""
    cap = float(get_balance().data.get("escort", {}).get("max_fee_pct", 0.10))
    st.escort_enabled = bool(enabled)
    st.escort_radius = max(0, int(radius or 0))
    st.escort_fee_pct = max(0.0, min(cap, float(fee_pct or 0.0)))
    if st.escort_enabled:
        # Exklusiv zum Abfangen.
        st.intercept_enabled = False


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

