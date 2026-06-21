"""Eskort-Gesuche-Board (Nachfrage-Seite des Geleitschutz-Marktes).

Ein Trader POSTET aktiv einen Eskort-Auftrag (``EscortJob``: Route + geschaetzter Frachtwert +
max. Gebuehr + optionale Mindest-Kampfkraft); Eskort-Anbieter nehmen ihn mit einer ihrer
Eskort-Stationen (``StationedFleet``, escort_enabled) an. Spiegelt das bestehende Angebots-Modell:
die Route ist galaxie-intern (origin_system -> target_system), eine Station deckt sie ueber
``escort_covers`` (System im Intervall +/- escort_radius).

INTEGRATION mit dem Handel (bewusst minimal, kein doppeltes Abrechnen): die angenommene Station
ist eine ganz normale escort_enabled-``StationedFleet`` auf der Route. Startet der Trader spaeter
seine Handels-/Transport-Flotte, taucht sie ueber die bestehende coveringEscorts-/``escort_ids``-
Logik (GET /escort/offers) als deckende Eskorte auf und wird via ``charge_trade_escorts`` regulaer
gebucht (Gebuehr -> Anbieter, Kampfkraft -> Routenrisiko). Das Board liefert dafuer im
„mine"-Listing die ``accepted_station_id`` zum Vorauswaehlen.

Abgelaufene Gesuche (``expires_at``) werden beim Listen LAZY auf 'expired' gesetzt (kein
Scheduler-Tick noetig). Reine, DB-freie Regel-Helfer (``is_self``, ``fee_ok``, ``power_ok``,
``job_coverable``, ``is_expired``, ``job_route``) sind separat testbar.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import EscortJob, Planet, Player, StationedFleet

log = logging.getLogger("universe.escort_jobs")

UTC = dt.timezone.utc

# Erlaubte Status-Werte (Lebenszyklus): open -> accepted -> done; open/accepted -> cancelled;
# open -> expired (lazy beim Listen).
OPEN = "open"
ACCEPTED = "accepted"
CANCELLED = "cancelled"
EXPIRED = "expired"
DONE = "done"


def _now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


# -- Reine Helfer (DB-frei, testbar) -----------------------------------------

def job_route(job: EscortJob) -> tuple[int, int, int, int]:
    """Routen-Tupel des Auftrags fuer ``escort_covers`` = (galaxy, sys_a, sys_b, _ignored).

    Identisch zum Handels-Pfad (``charge_trade_escorts``): galaxie-intern, das Origin-System
    und das Ziel-System spannen das Deckungsintervall auf."""
    return (job.origin_galaxy, job.origin_system, job.target_system, 0)


def is_self(job: EscortJob, player_id: uuid.UUID) -> bool:
    """Ist der Auftrag der eigene? (Eigene Auftraege darf man nicht annehmen / sieht man nur
    unter 'mine')."""
    return job.requester_id == player_id


def fee_ok(station_fee_pct: float, max_fee_pct: float) -> bool:
    """Liegt die Stations-Gebuehr im vom Trader gesetzten Rahmen (<= max_fee_pct)?"""
    return float(station_fee_pct or 0.0) <= float(max_fee_pct or 0.0) + 1e-9


def power_ok(station_power: float, min_power: float) -> bool:
    """Erfuellt die Stations-Kampfkraft die vom Trader verlangte Mindeststaerke?"""
    return float(station_power or 0.0) + 1e-9 >= float(min_power or 0.0)


def job_coverable(
    station: StationedFleet, covers: bool, station_power: float,
    min_power: float, max_fee_pct: float,
) -> bool:
    """Kann diese Eskort-Station den Auftrag bedienen? Buendelt alle Annahme-Regeln an einer
    Stelle: Station bietet Eskorte an, deckt die Route (``covers`` = Ergebnis von ``escort_covers``),
    Gebuehr <= max_fee_pct UND Kampfkraft >= min_power."""
    if not getattr(station, "escort_enabled", False):
        return False
    if not covers:
        return False
    if not fee_ok(getattr(station, "escort_fee_pct", 0.0), max_fee_pct):
        return False
    return power_ok(station_power, min_power)


def is_expired(job: EscortJob, now: dt.datetime | None = None) -> bool:
    """Ist der Auftrag abgelaufen (expires_at <= now)? (zeit-rein, testbar)."""
    exp = _aware(job.expires_at)
    if exp is None:
        return False
    return exp <= (now or _now())


def job_max_hours() -> float:
    return float(get_balance().data.get("escort", {}).get("job_max_hours", 24))


# -- Ausgabe-Serialisierung ---------------------------------------------------

def _job_base(job: EscortJob) -> dict:
    return {
        "id": str(job.id),
        "origin": f"{job.origin_galaxy}:{job.origin_system}:{job.origin_position}",
        "target": f"{job.target_galaxy}:{job.target_system}:{job.target_position}",
        "origin_coords": {"galaxy": job.origin_galaxy, "system": job.origin_system, "position": job.origin_position},
        "target_coords": {"galaxy": job.target_galaxy, "system": job.target_system, "position": job.target_position},
        "cargo_value": float(job.cargo_value or 0.0),
        "max_fee_pct": float(job.max_fee_pct or 0.0),
        "min_power": float(job.min_power or 0.0),
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "expires_at": job.expires_at.isoformat() if job.expires_at else None,
    }


def _station_offer(st: StationedFleet, cargo_value: float, bal) -> dict:
    from app.fleet.stationing import escort_fee, station_power
    return {
        "station_id": str(st.id),
        "coords": f"{st.galaxy}:{st.system}:{st.position}",
        "fee_pct": float(st.escort_fee_pct or 0.0),
        "fee": escort_fee(st.escort_fee_pct, cargo_value),
        "power": round(station_power(st.ships or {}, bal)),
        "ships_total": sum((st.ships or {}).values()),
    }


# -- Lazy-Ablauf --------------------------------------------------------------

async def expire_due_jobs(session: AsyncSession, now: dt.datetime | None = None) -> int:
    """Setzt offene, abgelaufene Gesuche auf 'expired' (lazy, beim Listen aufgerufen). Liefert die
    Anzahl. Schlank — kein Scheduler-Tick noetig."""
    now = now or _now()
    rows = (await session.execute(
        select(EscortJob).where(EscortJob.status == OPEN, EscortJob.expires_at <= now)
    )).scalars().all()
    for job in rows:
        job.status = EXPIRED
    if rows:
        log.info("Eskort-Board: %d Gesuch(e) abgelaufen", len(rows))
    return len(rows)


# -- Service ------------------------------------------------------------------

async def _home_planet(session: AsyncSession, player_id: uuid.UUID) -> Planet | None:
    return (await session.execute(
        select(Planet).where(Planet.player_id == player_id)
        .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc())
    )).scalars().first()


async def create_escort_job(
    session: AsyncSession,
    player: Player,
    *,
    target: tuple[int, int, int],
    cargo_value: float,
    max_fee_pct: float,
    origin: tuple[int, int, int] | None = None,
    min_power: float = 0.0,
) -> EscortJob:
    """Legt ein Eskort-Gesuch an. Origin default = Heimat-/erster Planet des Spielers.
    Validiert Frachtwert/Gebuehr; ``expires_at`` aus balance (escort.job_max_hours)."""
    if origin is None:
        home = await _home_planet(session, player.id)
        if home is None:
            raise ValueError("Kein Heimatplanet als Startpunkt gefunden")
        origin = (home.galaxy, home.system, home.position)

    cargo_value = float(cargo_value or 0.0)
    if cargo_value <= 0:
        raise ValueError("Frachtwert muss positiv sein")
    max_fee_pct = float(max_fee_pct or 0.0)
    if max_fee_pct <= 0:
        raise ValueError("Maximale Gebuehr (max_fee_pct) muss positiv sein")
    min_power = max(0.0, float(min_power or 0.0))

    now = _now()
    job = EscortJob(
        requester_id=player.id,
        origin_galaxy=origin[0], origin_system=origin[1], origin_position=origin[2],
        target_galaxy=target[0], target_system=target[1], target_position=target[2],
        cargo_value=cargo_value,
        max_fee_pct=max_fee_pct,
        min_power=min_power,
        status=OPEN,
        created_at=now,
        expires_at=now + dt.timedelta(hours=job_max_hours()),
    )
    session.add(job)
    await session.flush()
    log.info("Eskort-Gesuch %s erstellt: player=%s route=%s->%s", job.id, player.id,
             f"{origin[0]}:{origin[1]}:{origin[2]}", f"{target[0]}:{target[1]}:{target[2]}")
    return job


async def list_coverable_jobs(session: AsyncSession, player: Player) -> list[dict]:
    """Offene Auftraege ANDERER, die der Spieler mit MINDESTENS einer eigenen Eskort-Station decken
    kann (Route + min_power + Gebuehr <= max_fee_pct). Liefert je Auftrag die deckenden Stationen
    (zum Annehmen). Eigene Auftraege ausgeschlossen. Abgelaufene werden vorher lazy weggeraeumt."""
    await expire_due_jobs(session)
    bal = get_balance()
    from app.fleet.stationing import escort_covers, station_power

    my_stations = (await session.execute(
        select(StationedFleet).where(
            StationedFleet.owner_id == player.id,
            StationedFleet.escort_enabled.is_(True),
        )
    )).scalars().all()

    jobs = (await session.execute(
        select(EscortJob).where(
            EscortJob.status == OPEN,
            EscortJob.requester_id != player.id,
        ).order_by(EscortJob.created_at.desc())
    )).scalars().all()

    out: list[dict] = []
    for job in jobs:
        route = job_route(job)
        covering: list[dict] = []
        for st in my_stations:
            covers = escort_covers(st, route)
            if job_coverable(st, covers, station_power(st.ships or {}, bal), job.min_power, job.max_fee_pct):
                covering.append(_station_offer(st, job.cargo_value, bal))
        if not covering:
            continue
        requester = await session.get(Player, job.requester_id)
        entry = _job_base(job)
        entry["requester"] = requester.display_name if requester else "Unbekannt"
        entry["covering_stations"] = covering
        out.append(entry)
    return out


async def list_my_jobs(session: AsyncSession, player: Player) -> list[dict]:
    """Eigene Auftraege (alle Status), neueste zuerst — mit angenommener Eskorte/Anbieter."""
    await expire_due_jobs(session)
    jobs = (await session.execute(
        select(EscortJob).where(EscortJob.requester_id == player.id)
        .order_by(EscortJob.created_at.desc())
    )).scalars().all()
    out: list[dict] = []
    for job in jobs:
        entry = _job_base(job)
        entry["accepted_fee_pct"] = float(job.accepted_fee_pct) if job.accepted_fee_pct is not None else None
        entry["accepted_station_id"] = str(job.accepted_station_id) if job.accepted_station_id else None
        entry["accepted_by"] = None
        entry["accepted_station_coords"] = None
        if job.accepted_by:
            provider = await session.get(Player, job.accepted_by)
            entry["accepted_by"] = provider.display_name if provider else "Unbekannt"
        if job.accepted_station_id:
            st = await session.get(StationedFleet, job.accepted_station_id)
            if st is not None:
                entry["accepted_station_coords"] = f"{st.galaxy}:{st.system}:{st.position}"
        out.append(entry)
    return out


async def accept_escort_job(
    session: AsyncSession, player: Player, job_id: uuid.UUID, station_id: uuid.UUID,
) -> EscortJob:
    """Eskort-Anbieter nimmt einen offenen Auftrag mit einer eigenen Eskort-Station an.

    Prueft Deckung (escort_covers) + min_power + Gebuehr <= max_fee_pct. Erste Annahme gewinnt:
    danach ist der Auftrag 'accepted' und nicht mehr offen. Wirft ValueError (nicht gefunden) /
    RuntimeError (Regelverletzung)."""
    from app.fleet.stationing import escort_covers, station_power

    job = await session.get(EscortJob, job_id)
    if job is None:
        raise ValueError("Auftrag nicht gefunden")
    if is_self(job, player.id):
        raise RuntimeError("Eigene Auftraege koennen nicht angenommen werden")
    if job.status != OPEN:
        raise RuntimeError("Auftrag ist nicht mehr offen")
    if is_expired(job):
        job.status = EXPIRED
        raise RuntimeError("Auftrag ist abgelaufen")

    st = await session.get(StationedFleet, station_id)
    if st is None or st.owner_id != player.id:
        raise ValueError("Eskort-Station nicht gefunden")

    bal = get_balance()
    covers = escort_covers(st, job_route(job))
    power = station_power(st.ships or {}, bal)
    if not getattr(st, "escort_enabled", False):
        raise RuntimeError("Station bietet keine Eskorte an")
    if not covers:
        raise RuntimeError("Station deckt die Auftrags-Route nicht ab")
    if not fee_ok(st.escort_fee_pct, job.max_fee_pct):
        raise RuntimeError("Stations-Gebuehr uebersteigt die maximale Gebuehr des Auftrags")
    if not power_ok(power, job.min_power):
        raise RuntimeError("Stations-Kampfkraft erfuellt die geforderte Mindeststaerke nicht")

    job.status = ACCEPTED
    job.accepted_station_id = st.id
    job.accepted_by = player.id
    job.accepted_fee_pct = float(st.escort_fee_pct or 0.0)

    route_txt = f"{job.origin_galaxy}:{job.origin_system}:{job.origin_position} -> " \
                f"{job.target_galaxy}:{job.target_system}:{job.target_position}"
    await create_system_transmission(
        session, player_id=job.requester_id,
        subject="Eskort-Gesuch angenommen",
        body=(f"{player.display_name} bietet Geleitschutz fuer deine Route {route_txt} an "
              f"({int(float(st.escort_fee_pct or 0.0) * 100)} % Gebuehr). Beim naechsten Handel auf "
              f"dieser Route kannst du die Eskorte als deckendes Angebot mitbuchen."),
        ttype="system",
    )
    log.info("Eskort-Gesuch %s angenommen: provider=%s station=%s", job.id, player.id, st.id)
    return job


async def cancel_escort_job(session: AsyncSession, player: Player, job_id: uuid.UUID) -> EscortJob:
    """Der Ersteller storniert sein Gesuch (nur wenn open oder accepted)."""
    job = await session.get(EscortJob, job_id)
    if job is None or job.requester_id != player.id:
        raise ValueError("Auftrag nicht gefunden")
    if job.status not in (OPEN, ACCEPTED):
        raise RuntimeError("Auftrag kann nicht mehr storniert werden")
    job.status = CANCELLED
    log.info("Eskort-Gesuch %s storniert: player=%s", job.id, player.id)
    return job
