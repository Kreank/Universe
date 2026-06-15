"""Farm-Routinen: dauerhaft fliegende Sammelschleifen ueber Asteroiden-/Truemmerfelder.

Eine Routine (``FarmRoute``) ist eine persistente Definition + zugeordnete Schiffe. Der
Controller hier startet je ZYKLUS einen ganz normalen ``mine``/``recycle``-Flug zum aktuellen
Waypoint (``cursor``), getaggt mit ``mission_data.farm_route_id``. Dadurch erbt jeder Zyklus
Flugzeit, Treibstoff (Hin+Rueck von der Heim-Station), Frachtdeckel, Abfangbarkeit und das
Ausladen bei Rueckkehr KOMPLETT vom bestehenden Flotten-System (``fleet/service.py``).

Ablauf je Zyklus (per-Feld-Rueckkehr):
  start_cycle -> send_fleet(mine|recycle) zum Feld[cursor] -> (Anflug: resolve_mine/harvest in
  fleet.cargo) -> fleet_return laedt aus -> advance_after_return: Feld leer? -> Cursor++ (modulo,
  endlos); Laderaum war voll -> Cursor bleibt (selbes Feld nochmal) -> naechster Zyklus.

Verlust-Erkennung: ``loss_check`` wird kurz nach der geplanten Rueckkehr eingeplant. Lief die
Erfolgs-Bahn (advance_after_return), zeigt ``active_fleet_id`` schon auf eine neue/keine Flotte
-> Check ist stale, ignoriert. Wurde die Flotte abgefangen/vernichtet (Flotte 'done', aber
Routine zeigt noch auf sie), pausiert die Routine mit ``fleet_lost``.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import get_research_levels
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import AsteroidField, FarmRoute, Fleet, Planet, Player, UniverseCell
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.routines")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _cfg() -> dict:
    return get_balance().data.get("routines", {})


# -- Forschungs-Limits ----------------------------------------------------------

def max_routines(research: dict[str, int]) -> int:
    """Erlaubte gleichzeitige Routinen = base_routines + Stufe der routines_research."""
    cfg = _cfg()
    key = cfg.get("routines_research", "fleet_logistics")
    return int(cfg.get("base_routines", 2)) + int(research.get(key, 0))


def max_fields_per_route(research: dict[str, int]) -> int:
    """Erlaubte Felder je Route = base_fields_per_route + Stufe der fields_research."""
    cfg = _cfg()
    key = cfg.get("fields_research", "route_planning")
    return int(cfg.get("base_fields_per_route", 2)) + int(research.get(key, 0))


def advance_cursor(cursor: int, n: int, emptied: bool) -> int:
    """Reine Cursor-Logik nach einem Zyklus: Feld leer -> naechstes Feld (modulo, endlos);
    Laderaum war voll bevor das Feld leer war -> selbes Feld nochmal (Cursor bleibt)."""
    if n <= 0:
        return 0
    return (cursor + 1) % n if emptied else cursor % n


# -- Feld-/Schiff-Helfer --------------------------------------------------------

async def _asteroid_at(session: AsyncSession, wp: dict) -> AsteroidField | None:
    return (await session.execute(
        select(AsteroidField).where(
            AsteroidField.galaxy == int(wp["galaxy"]),
            AsteroidField.system == int(wp["system"]),
            AsteroidField.position == int(wp["position"]),
        )
    )).scalar_one_or_none()


async def _debris_total(session: AsyncSession, wp: dict) -> float:
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == int(wp["galaxy"]),
            UniverseCell.system == int(wp["system"]),
            UniverseCell.position == int(wp["position"]),
        )
    )).scalar_one_or_none()
    if cell is None or not cell.debris_field:
        return 0.0
    d = cell.debris_field
    return float(d.get("metal", 0)) + float(d.get("crystal", 0))


async def _mission_for(session: AsyncSession, wp: dict) -> str | None:
    """Welche Mission farmt dieses Feld JETZT? Asteroid -> 'mine', Truemmer (>0) -> 'recycle',
    sonst None (nichts zu holen)."""
    if await _asteroid_at(session, wp) is not None:
        return "mine"
    if await _debris_total(session, wp) > 0:
        return "recycle"
    return None


async def _field_emptied(session: AsyncSession, wp: dict, mission: str | None) -> bool:
    """Ist das Feld nach dem letzten Abbau (praktisch) leer? Dann rueckt der Cursor weiter."""
    thr = float(_cfg().get("empty_threshold", 1.0))
    if mission == "mine":
        field = await _asteroid_at(session, wp)
        if field is None:
            return True
        return (field.metal_remaining + field.crystal_remaining) <= thr
    # recycle (oder unbekannt -> Truemmer pruefen)
    return await _debris_total(session, wp) <= thr


def _has_required_ships(ships: dict, mission: str) -> bool:
    bal = get_balance()
    if mission == "mine":
        mt = bal.data.get("mining", {}).get("ship_type", "miner")
        return int(ships.get(mt, 0)) >= int(bal.data.get("mining", {}).get("min_ships", 1))
    ct = bal.data.get("harvest", {}).get("collector_type", "recycler")
    return int(ships.get(ct, 0)) >= int(bal.data.get("harvest", {}).get("min_collectors", 1))


# -- Pause + Benachrichtigung ---------------------------------------------------

_PAUSE_TEXT = {
    "no_fuel": ("Routine pausiert: kein Deuterium",
                "Deine Farm-Routine '{name}' konnte den naechsten Flug nicht starten — die Heim-Station "
                "hat nicht genug Deuterium. Die Routine pausiert. Tanke auf und aktiviere sie erneut."),
    "no_ships": ("Routine pausiert: zu wenige Schiffe",
                 "Deine Farm-Routine '{name}' fand nicht genug der zugeordneten Schiffe an der Heim-Station "
                 "(woanders im Einsatz?). Die Routine pausiert."),
    "no_slot": ("Routine pausiert: kein Flottenslot",
                "Deine Farm-Routine '{name}' bekam keinen freien Flottenslot. Die Routine pausiert — "
                "gib einen Slot frei und aktiviere sie erneut."),
    "no_target": ("Routine pausiert: kein farmbares Feld",
                  "Deine Farm-Routine '{name}' fand an keinem ihrer Felder etwas zu farmen (Asteroid weg / "
                  "Truemmer leer / Ziel ausser Reichweite). Die Routine pausiert."),
    "fleet_lost": ("Routine pausiert: Flotte verloren",
                   "Die Flotte deiner Farm-Routine '{name}' ist nicht zurueckgekehrt (abgefangen/vernichtet). "
                   "Die Routine pausiert."),
}


async def _pause(session: AsyncSession, route: FarmRoute, reason: str) -> None:
    route.status = "paused"
    route.pause_reason = reason
    route.active_fleet_id = None
    subj, body = _PAUSE_TEXT.get(reason, ("Routine pausiert", "Deine Farm-Routine '{name}' pausiert."))
    try:
        await create_system_transmission(
            session, player_id=route.player_id,
            subject=subj, body=body.format(name=route.name),
        )
    except Exception:  # noqa: BLE001
        log.exception("Pausen-Benachrichtigung fuer Routine %s fehlgeschlagen (ignoriert)", route.id)
    log.info("Routine %s pausiert (%s)", route.id, reason)


def _classify_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "slot" in msg:
        return "no_slot"
    if "schiffe" in msg or "wenige" in msg:
        return "no_ships"
    if "ressourcen" in msg or "sprit" in msg or "deuterium" in msg:
        return "no_fuel"
    return "no_target"  # Reichweite/Ziel/unbekannt -> Routine ruht, bis der Spieler eingreift


# -- Zyklus-Steuerung -----------------------------------------------------------

def schedule_start(route_id: uuid.UUID | str, delay_seconds: float = 0.0) -> None:
    """Plant den (Wieder-)Start eines Routinen-Zyklus."""
    rid = str(route_id)
    schedule_at(_now() + dt.timedelta(seconds=max(0.0, delay_seconds)),
                start_cycle, rid, job_id=f"routine-cycle:{rid}")


async def start_cycle(route_id: str) -> None:
    """Startet einen Zyklus: sucht ab dem Cursor das naechste farmbare Feld und entsendet die
    Flotte als getaggten mine/recycle-Flug. Pausiert bei Fehlschlag (kein Sprit/Slot/Schiff/Ziel)."""
    from app.fleet.service import send_fleet

    fleet_id: uuid.UUID | None = None
    return_at: dt.datetime | None = None
    async with session_scope() as session:
        route = await session.get(FarmRoute, uuid.UUID(route_id))
        if route is None or not route.enabled:
            return
        # Laeuft schon eine Flotte fuer diese Routine? (Doppelstart vermeiden.)
        if route.active_fleet_id is not None:
            af = await session.get(Fleet, route.active_fleet_id)
            if af is not None and af.status in ("flying", "arrived", "returning"):
                return
        player = await session.get(Player, route.player_id)
        if player is None:
            return

        wps = list(route.waypoints or [])
        n = len(wps)
        if n == 0:
            await _pause(session, route, "no_target")
            await session.commit()
            return

        # Ab dem Cursor das naechste Feld suchen, das JETZT farmbar ist + zu den Schiffen passt.
        chosen: tuple[int, dict, str] | None = None
        for i in range(n):
            idx = (route.cursor + i) % n
            wp = wps[idx]
            mission = await _mission_for(session, wp)
            if mission is not None and _has_required_ships(route.ships or {}, mission):
                chosen = (idx, wp, mission)
                break
        if chosen is None:
            await _pause(session, route, "no_target")
            await session.commit()
            return

        idx, wp, mission = chosen
        route.cursor = idx
        try:
            fleet = await send_fleet(
                session, player,
                origin_planet_id=route.home_planet_id,
                target=(int(wp["galaxy"]), int(wp["system"]), int(wp["position"])),
                mission=mission,
                ships=dict(route.ships or {}),
                cargo={},
                commander_id=None,
                speed_pct=100,
                mission_data={"farm_route_id": str(route.id)},
            )
        except Exception as exc:  # noqa: BLE001 — alle send_fleet-Fehlschlaege -> Routine pausieren
            await _pause(session, route, _classify_error(exc))
            await session.commit()
            return

        route.status = "flying"
        route.pause_reason = None
        route.active_fleet_id = fleet.id
        fleet_id = fleet.id
        return_at = fleet.return_at
        await session.commit()

    # Sicherheits-Check fuer Flottenverlust kurz nach der geplanten Rueckkehr einplanen.
    if fleet_id is not None:
        buf = int(_cfg().get("loss_check_buffer_seconds", 30))
        check_at = (return_at or _now()) + dt.timedelta(seconds=buf)
        schedule_at(check_at, loss_check, route_id, str(fleet_id),
                    job_id=f"routine-losscheck:{route_id}")


async def advance_after_return(route_id: str, fleet_id: str) -> None:
    """Nach erfolgreicher Rueckkehr eines Routinen-Flugs: Cursor ggf. weiterruecken (Feld leer)
    und den naechsten Zyklus einplanen. Wird aus ``fleet_return`` aufgerufen (Erfolgs-Bahn)."""
    async with session_scope() as session:
        route = await session.get(FarmRoute, uuid.UUID(route_id))
        if route is None:
            return
        # Nur reagieren, wenn DIESE Flotte die aktive der Routine ist (kein Doppel-Advance).
        if route.active_fleet_id is None or str(route.active_fleet_id) != str(fleet_id):
            return
        route.active_fleet_id = None

        wps = list(route.waypoints or [])
        if wps:
            n = len(wps)
            wp = wps[route.cursor % n]
            fleet = await session.get(Fleet, uuid.UUID(fleet_id))
            mission = fleet.mission if fleet is not None else None
            emptied = await _field_emptied(session, wp, mission)
            route.cursor = advance_cursor(route.cursor, n, emptied)

        if route.enabled:
            route.status = "idle"
            route.pause_reason = None
        await session.commit()
        enabled = route.enabled

    if enabled:
        schedule_start(route_id, delay_seconds=float(_cfg().get("dock_seconds", 5)))


async def loss_check(route_id: str, fleet_id: str) -> None:
    """Sicherheits-Check: lief die Erfolgs-Bahn nicht (Flotte abgefangen/vernichtet),
    pausiert die Routine. Verzoegerte (noch fliegende) Flotten -> Check neu einplanen."""
    reschedule = False
    async with session_scope() as session:
        route = await session.get(FarmRoute, uuid.UUID(route_id))
        if route is None:
            return
        # Erfolg lief schon -> Routine zeigt nicht mehr auf diese Flotte -> nichts tun.
        if route.active_fleet_id is None or str(route.active_fleet_id) != str(fleet_id):
            return
        fleet = await session.get(Fleet, uuid.UUID(fleet_id))
        if fleet is not None and fleet.status in ("flying", "arrived", "returning"):
            reschedule = True  # nur verspaetet -> spaeter erneut pruefen
        else:
            # Flotte weg oder 'done', aber Routine hat nicht advanced -> verloren.
            await _pause(session, route, "fleet_lost")
            await session.commit()

    if reschedule:
        buf = int(_cfg().get("loss_check_buffer_seconds", 30))
        schedule_at(_now() + dt.timedelta(seconds=buf), loss_check, route_id, fleet_id,
                    job_id=f"routine-losscheck:{route_id}")


# -- CRUD (vom Router genutzt) --------------------------------------------------

def route_to_dict(route: FarmRoute) -> dict:
    return {
        "id": str(route.id),
        "name": route.name,
        "home_planet_id": str(route.home_planet_id),
        "ships": route.ships or {},
        "waypoints": route.waypoints or [],
        "enabled": route.enabled,
        "status": route.status,
        "pause_reason": route.pause_reason,
        "cursor": route.cursor,
        "active_fleet_id": str(route.active_fleet_id) if route.active_fleet_id else None,
    }


def _norm_waypoints(waypoints: list) -> list[dict]:
    out: list[dict] = []
    for wp in waypoints or []:
        try:
            out.append({
                "galaxy": int(wp["galaxy"]),
                "system": int(wp["system"]),
                "position": int(wp["position"]),
            })
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Waypoint braucht galaxy, system und position (Ganzzahlen).") from exc
    return out


async def _validate_waypoints_and_ships(session: AsyncSession, waypoints: list[dict], ships: dict) -> None:
    """Jeder Waypoint muss aktuell ein Asteroiden- oder Truemmerfeld sein; die Schiffe muessen
    zu den vorkommenden Feldtypen passen (Bergbauschiffe fuer Asteroiden, Recycler fuer Truemmer)."""
    has_asteroid = has_debris = False
    for wp in waypoints:
        mission = await _mission_for(session, wp)
        if mission is None:
            raise ValueError(
                f"{wp['galaxy']}:{wp['system']}:{wp['position']} ist kein farmbares "
                f"Asteroiden-/Truemmerfeld."
            )
        if mission == "mine":
            has_asteroid = True
        else:
            has_debris = True
    if has_asteroid and not _has_required_ships(ships, "mine"):
        bal = get_balance()
        mt = bal.data.get("mining", {}).get("ship_type", "miner")
        raise ValueError(f"Die Route enthaelt Asteroidenfelder — ordne mindestens ein {mt} zu.")
    if has_debris and not _has_required_ships(ships, "recycle"):
        bal = get_balance()
        ct = bal.data.get("harvest", {}).get("collector_type", "recycler")
        raise ValueError(f"Die Route enthaelt Truemmerfelder — ordne mindestens einen {ct} zu.")


async def list_routes(session: AsyncSession, player_id: uuid.UUID) -> list[FarmRoute]:
    return list((await session.execute(
        select(FarmRoute).where(FarmRoute.player_id == player_id).order_by(FarmRoute.created_at)
    )).scalars().all())


async def create_route(
    session: AsyncSession, player: Player, *,
    name: str, home_planet_id: uuid.UUID, ships: dict, waypoints: list,
) -> FarmRoute:
    research = await get_research_levels(session, player.id)
    existing = (await session.execute(
        select(FarmRoute).where(FarmRoute.player_id == player.id)
    )).scalars().all()
    if len(existing) >= max_routines(research):
        raise ValueError(
            f"Routinen-Limit erreicht ({max_routines(research)}). Forsche 'Logistik-Netz' fuer mehr."
        )

    home = await session.get(Planet, home_planet_id)
    if home is None or home.player_id != player.id:
        raise ValueError("Heim-Station nicht gefunden.")

    ships = {t: int(c) for t, c in (ships or {}).items() if int(c) > 0}
    if not ships:
        raise ValueError("Ordne der Routine mindestens ein Schiff zu.")

    wps = _norm_waypoints(waypoints)
    if not wps:
        raise ValueError("Lege mindestens ein Feld fuer die Route fest.")
    cap = max_fields_per_route(research)
    if len(wps) > cap:
        raise ValueError(f"Zu viele Felder ({len(wps)}). Maximum aktuell {cap} — forsche 'Routen-Planung'.")
    await _validate_waypoints_and_ships(session, wps, ships)

    route = FarmRoute(
        player_id=player.id, home_planet_id=home_planet_id, name=(name or "Routine").strip()[:80],
        ships=ships, waypoints=wps, enabled=True, status="idle", cursor=0,
    )
    session.add(route)
    await session.flush()
    return route


async def update_route(
    session: AsyncSession, player: Player, route_id: uuid.UUID, *,
    name: str | None = None, enabled: bool | None = None,
    ships: dict | None = None, waypoints: list | None = None,
) -> tuple[FarmRoute, bool]:
    """Aktualisiert eine Routine. Liefert (route, should_start) — should_start=True, wenn der
    Aufrufer nach dem Commit einen Zyklus anstossen soll (frisch aktiviert)."""
    route = await session.get(FarmRoute, route_id)
    if route is None or route.player_id != player.id:
        raise ValueError("Routine nicht gefunden.")
    research = await get_research_levels(session, player.id)

    if name is not None:
        route.name = name.strip()[:80] or route.name
    if ships is not None:
        route.ships = {t: int(c) for t, c in ships.items() if int(c) > 0}
        if not route.ships:
            raise ValueError("Ordne der Routine mindestens ein Schiff zu.")
    if waypoints is not None:
        wps = _norm_waypoints(waypoints)
        if not wps:
            raise ValueError("Lege mindestens ein Feld fuer die Route fest.")
        cap = max_fields_per_route(research)
        if len(wps) > cap:
            raise ValueError(f"Zu viele Felder ({len(wps)}). Maximum aktuell {cap}.")
        route.waypoints = wps
        route.cursor = 0  # geaenderte Route -> von vorn
    if ships is not None or waypoints is not None:
        await _validate_waypoints_and_ships(session, route.waypoints or [], route.ships or {})

    should_start = False
    if enabled is not None:
        was_enabled = route.enabled
        route.enabled = enabled
        if enabled and not was_enabled:
            route.status = "idle"
            route.pause_reason = None
            should_start = True
        elif not enabled:
            route.status = "paused"
            route.pause_reason = None
    return route, should_start


async def delete_route(session: AsyncSession, player: Player, route_id: uuid.UUID) -> None:
    route = await session.get(FarmRoute, route_id)
    if route is None or route.player_id != player.id:
        raise ValueError("Routine nicht gefunden.")
    await session.delete(route)


async def resume_route(session: AsyncSession, player: Player, route_id: uuid.UUID) -> FarmRoute:
    """Holt eine pausierte (oder steckengebliebene) Routine aus dem Wartezustand: aktiviert sie,
    loescht den Pausen-Grund + eine etwaige Geister-Flotte. Der Aufrufer plant danach einen Zyklus."""
    route = await session.get(FarmRoute, route_id)
    if route is None or route.player_id != player.id:
        raise ValueError("Routine nicht gefunden.")
    route.enabled = True
    route.status = "idle"
    route.pause_reason = None
    route.active_fleet_id = None
    return route
