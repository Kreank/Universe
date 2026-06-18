"""Mining-Mission: Bergbauschiffe foerdern an einem Asteroidenfeld (Doku 03c).

Eine Flotte mit Mission ``mine`` fliegt zu einem Sektor; liegt dort ein Asteroidenfeld
(occupant 'asteroid_field'), foerdern die Bergbauschiffe Metall/Kristall als Fracht fuer die
Heimreise. Ertrag = Bergbauschiffe x Ertrag/Schiff x Feld-Reichtum, gedeckelt durch den
endlichen Restvorrat des Feldes UND die Frachtkapazitaet der Flotte. Das Feld erschoepft
(zehrt den Vorrat) und regeneriert lazy ueber die Zeit. Kein Feld am Ziel -> kein Ertrag.
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import AsteroidField, Fleet, Ship
from app.universe.asteroids import mine_from_field, regen_field

log = logging.getLogger("universe.mining")

UTC = dt.timezone.utc


def _parse_iso(value) -> dt.datetime | None:
    """Parst einen ISO-Zeitstempel (aus mission_data) zu einem aware UTC-Datum; None bei Fehlern."""
    if not value:
        return None
    try:
        t = dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


def is_parked_mining(fleet, galaxy: int, system: int, position: int, now: dt.datetime) -> bool:
    """True, wenn ``fleet`` GERADE am Feld (galaxy:system:position) schuerft und damit angreifbar ist.

    Regel (Doku 2026-06-15): mission == 'mine', status != 'done', Zielkoordinate == Feld,
    und ``now`` liegt noch im Verweil-Fenster (``mission_data['hold_until']``). Nach hold_until
    fliegt die Flotte heim (das deckt das Abfangen ab, NICHT dieses Feature). Reine, testbare
    Praedikat-Funktion (akzeptiert jedes Flotten-aehnliche Objekt)."""
    if getattr(fleet, "mission", None) != "mine":
        return False
    if getattr(fleet, "status", None) == "done":
        return False
    if (fleet.target_galaxy, fleet.target_system, fleet.target_position) != (galaxy, system, position):
        return False
    hold = _parse_iso((getattr(fleet, "mission_data", None) or {}).get("hold_until"))
    if hold is None:
        return False
    return now <= hold


async def parked_mining_fleets_at(
    session: AsyncSession, galaxy: int, system: int, position: int, now: dt.datetime,
    exclude_player_id=None,
) -> list[dict]:
    """Alle GERADE am Feld schuerfenden (angreifbaren) Bergbauflotten an der Koordinate.

    Liefert Verteidiger-Quellen [{"kind":"mining","obj":Fleet,"rows":[Ship],"ships":{typ:cnt}}],
    kompatibel mit ``distribute_losses``. ``exclude_player_id`` blendet eigene Flotten aus
    (Angreifer kann seine eigene Schuerf-Flotte nicht angreifen)."""
    rows = (await session.execute(
        select(Fleet).where(
            Fleet.target_galaxy == galaxy,
            Fleet.target_system == system,
            Fleet.target_position == position,
            Fleet.mission == "mine",
            Fleet.status != "done",
        )
    )).scalars().all()
    out: list[dict] = []
    for f in rows:
        if exclude_player_id is not None and f.player_id == exclude_player_id:
            continue
        if not is_parked_mining(f, galaxy, system, position, now):
            continue
        ship_rows = (await session.execute(
            select(Ship).where(Ship.fleet_id == f.id)
        )).scalars().all()
        ships = {r.type: r.count for r in ship_rows if r.count > 0}
        if ships:
            out.append({"kind": "mining", "obj": f, "rows": ship_rows, "ships": ships})
    return out


def _cargo_capacity(ships: dict[str, int]) -> float:
    bal = get_balance()
    cap = 0.0
    for typ, count in ships.items():
        cfg = bal.ships.get(typ)
        if cfg:
            cap += cfg.get("cargo", 0) * count
    return cap


def _now() -> dt.datetime:
    return dt.datetime.now(UTC)


async def _field_at(session: AsyncSession, fleet: Fleet) -> AsteroidField | None:
    return (await session.execute(
        select(AsteroidField).where(
            AsteroidField.galaxy == fleet.target_galaxy,
            AsteroidField.system == fleet.target_system,
            AsteroidField.position == fleet.target_position,
        )
    )).scalar_one_or_none()


def _mine_miners(ships: dict[str, int], bal) -> int:
    cfg = bal.data.get("mining", {})
    roster = bal.combat_roster
    return int(ships.get(cfg.get("ship_type", "miner"), 0)) + sum(
        c for t, c in ships.items() if (roster.get(t) or {}).get("harvester")
    )


async def resolve_mine(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Startet eine ZEITBASIERTE Schuerf-Session am Asteroidenfeld (Doku 03c, 2026-06-17).

    Es wird hier NICHTS sofort gefoerdert — der Frachtraum fuellt sich anteilig ueber die
    Verweildauer. Real gefoerdert (Feld abgebaut + Fracht gutgeschrieben) wird erst beim
    VERLASSEN des Feldes via ``settle_mining``: bei Rueckkehr die volle Ausbeute, bei einem
    frueheren Abfang nur der bis dahin geschuerfte Anteil (kein Instant-Voll-Exploit mehr)."""
    bal = get_balance()
    location = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"

    ships = {
        r.type: r.count
        for r in (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        if r.count > 0
    }
    if _mine_miners(ships, bal) <= 0:
        return None

    field = await _field_at(session, fleet)
    if field is None:
        log.info("Mining @ %s -> kein Asteroidenfeld (Flotte leer zurueck)", location)
        await create_system_transmission(
            session, player_id=fleet.player_id,
            subject=f"Bergbau: kein Asteroidenfeld ({location})",
            body=(f"Deine Bergbauflotte erreichte {location}, fand dort aber KEIN Asteroidenfeld. "
                  f"Es wurde nichts gefoerdert; die Flotte kehrt leer zurueck. Pruefe in der Galaxie-Ansicht, "
                  f"ob am Ziel wirklich ein Asteroidenfeld liegt."),
        )
        return {"location": location, "mined": {"metal": 0.0, "crystal": 0.0}, "note": "kein_asteroidenfeld"}

    # Schuerf-Session anlegen: Startzeit + zu fuellende Kapazitaet. Foerderung erfolgt bei settle.
    md = dict(fleet.mission_data or {})
    md["mine_active"] = True
    md["mine_start"] = _now().isoformat()
    md["mine_cap"] = _cargo_capacity(ships)
    fleet.mission_data = md

    hold_until = _parse_iso(md.get("hold_until"))
    hrs = max(0.0, (hold_until - _now()).total_seconds() / 3600.0) if hold_until else 0.0
    await create_system_transmission(
        session, player_id=fleet.player_id,
        subject=f"Bergbau begonnen ({location})",
        body=(f"Deine Bergbauflotte schuerft am Asteroidenfeld {location} ({field.richness}). Der "
              f"Frachtraum fuellt sich ueber ~{hrs:.1f} Std und wird bei der Rueckkehr dem Heimatplaneten "
              f"gutgeschrieben. ACHTUNG: Waehrend des Schuerfens ist die Flotte am Feld angreifbar — bei "
              f"einem Abfang erbeutet der Gegner NUR das bis dahin Gefoerderte; der Rest bleibt im Feld."),
    )
    return {"location": location, "richness": field.richness, "started": True}


async def mining_projection(session: AsyncSession, fleet: Fleet, now: dt.datetime | None = None) -> dict | None:
    """Read-only: was die Flotte BISHER (anteilig zur Verweilzeit) geschuerft haette — fuer den
    Live-Frachtbalken. Mutiert NICHTS. Liefert {metal, crystal, filled, capacity, progress} oder
    None, wenn keine aktive Schuerf-Session laeuft."""
    md = fleet.mission_data or {}
    if not md.get("mine_active"):
        return None
    now = now or _now()
    start = _parse_iso(md.get("mine_start")) or now
    hold_until = _parse_iso(md.get("hold_until"))
    if hold_until and hold_until > start:
        progress = min(1.0, max(0.0, (now - start).total_seconds() / (hold_until - start).total_seconds()))
    else:
        progress = 1.0
    cap_total = float(md.get("mine_cap", 0.0))
    cap = cap_total * progress
    metal = crystal = 0.0
    if cap > 0:
        field = await _field_at(session, fleet)
        if field is not None:
            from app.universe.asteroids import projected_remaining
            pm, pc = projected_remaining(field)  # Regen read-only mitrechnen
            g, _m, _c = mine_from_field(pm, pc, cap)
            from app.alliance.bonus import alliance_bonus
            from app.platform.models import Player
            owner = await session.get(Player, fleet.player_id)
            zb = await alliance_bonus(
                session, owner, "mining_yield_zone",
                galaxy=fleet.target_galaxy, system=fleet.target_system,
            )
            mult = (1 + zb) if zb > 0 else 1.0
            metal, crystal = round(g["metal"] * mult, 1), round(g["crystal"] * mult, 1)
    return {
        "metal": metal, "crystal": crystal,
        "filled": round(cap, 0), "capacity": round(cap_total, 0), "progress": round(progress, 3),
    }


async def settle_mining(session: AsyncSession, fleet: Fleet, now: dt.datetime | None = None) -> dict | None:
    """Beendet die Schuerf-Session: foerdert das bis ``now`` ANTEILIG (verstrichene Verweilzeit)
    Geschuerfte real aus dem Feld in ``fleet.cargo`` und markiert die Session als erledigt.

    Rueckkehr (now >= hold_until) -> voller Frachtraum; Abfang davor -> nur der Zeit-Anteil.
    Liefert das Gefoerderte ``{metal, crystal}`` oder None, wenn keine aktive Session lief."""
    md = dict(fleet.mission_data or {})
    if not md.get("mine_active"):
        return None
    now = now or _now()
    start = _parse_iso(md.get("mine_start")) or now
    hold_until = _parse_iso(md.get("hold_until"))
    if hold_until and hold_until > start:
        span = (hold_until - start).total_seconds()
        progress = min(1.0, max(0.0, (now - start).total_seconds() / span))
    else:
        progress = 1.0
    cap = float(md.get("mine_cap", 0.0)) * progress

    gained = {"metal": 0.0, "crystal": 0.0}
    if cap > 0:
        field = await _field_at(session, fleet)
        if field is not None:
            regen_field(field)  # Lazy-Regen vor der Foerderung
            g, new_metal, new_crystal = mine_from_field(field.metal_remaining, field.crystal_remaining, cap)
            field.metal_remaining = new_metal
            field.crystal_remaining = new_crystal
            # Allianz-Zonen-Bonus (Effizienz, ohne Feld extra zu erschoepfen).
            from app.alliance.bonus import alliance_bonus
            from app.platform.models import Player
            owner = await session.get(Player, fleet.player_id)
            zb = await alliance_bonus(
                session, owner, "mining_yield_zone",
                galaxy=fleet.target_galaxy, system=fleet.target_system,
            )
            gained = {
                "metal": round(g["metal"] * (1 + zb), 1),
                "crystal": round(g["crystal"] * (1 + zb), 1),
            } if zb > 0 else g

    cargo = dict(fleet.cargo or {})
    cargo["metal"] = round(cargo.get("metal", 0) + gained["metal"], 1)
    cargo["crystal"] = round(cargo.get("crystal", 0) + gained["crystal"], 1)
    fleet.cargo = cargo
    md["mine_active"] = False
    fleet.mission_data = md
    log.info("Mining settle @ %d:%d:%d -> progress=%.2f gained=%s",
             fleet.target_galaxy, fleet.target_system, fleet.target_position, progress, gained)
    return gained
