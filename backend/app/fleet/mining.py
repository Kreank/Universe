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


async def resolve_mine(session: AsyncSession, fleet: Fleet) -> dict | None:
    """Foerdert Erz aus dem Asteroidenfeld am Zielort in die Flotten-Fracht.
    Liefert eine kurze Zusammenfassung (oder None ohne Bergbauschiffe)."""
    bal = get_balance()
    cfg = bal.data.get("mining", {})
    ship_type = cfg.get("ship_type", "miner")
    location = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"

    ships = {
        r.type: r.count
        for r in (await session.execute(select(Ship).where(Ship.fleet_id == fleet.id))).scalars().all()
        if r.count > 0
    }
    # Mining-faehig = Bergbauschiffe ODER ein Ernte-Titan (roster.harvester). Beide sind nur die
    # VORAUSSETZUNG; der Ertrag haengt am Frachtraum (Modell 'fuelle deinen Frachtraum'), NICHT an
    # der Schiffszahl -> kein harvester_yield_mult mehr. Der Ernte-Titan zieht seine Staerke aus
    # seinem riesigen eigenen Laderaum (ships.harvest_titan.cargo).
    roster = bal.combat_roster
    miners = int(ships.get(ship_type, 0)) + sum(
        c for t, c in ships.items() if (roster.get(t) or {}).get("harvester")
    )
    if miners <= 0:
        return None

    field = (await session.execute(
        select(AsteroidField).where(
            AsteroidField.galaxy == fleet.target_galaxy,
            AsteroidField.system == fleet.target_system,
            AsteroidField.position == fleet.target_position,
        )
    )).scalar_one_or_none()

    if field is None:
        log.info("Mining @ %s -> kein Asteroidenfeld (%d Bergbauschiffe leer zurueck)", location, miners)
        await create_system_transmission(
            session, player_id=fleet.player_id,
            subject=f"Bergbau: kein Asteroidenfeld ({location})",
            body=(f"Deine Bergbauflotte erreichte {location}, fand dort aber KEIN Asteroidenfeld. "
                  f"Es wurde nichts gefoerdert; die Flotte kehrt leer zurueck. Pruefe in der Galaxie-Ansicht, "
                  f"ob am Ziel wirklich ein Asteroidenfeld liegt."),
        )
        return {"location": location, "mined": {"metal": 0.0, "crystal": 0.0}, "note": "kein_asteroidenfeld"}

    # Lazy-Regeneration vor der Foerderung anwenden.
    regen_field(field)

    # Modell 'fuelle deinen Frachtraum': die Flotte holt so viel, wie ihr Frachtraum fasst,
    # gedeckelt durch den Feld-Restvorrat. miners/Ernte-Titan sind nur die Voraussetzung (>0 oben).
    gained, new_metal, new_crystal = mine_from_field(
        field.metal_remaining, field.crystal_remaining, _cargo_capacity(ships),
    )
    field.metal_remaining = new_metal
    field.crystal_remaining = new_crystal

    # Allianz-Bonus „Foerderquote" (Zone-Kontext): Effizienz-Extra auf den Ertrag, OHNE das Feld
    # zusaetzlich zu erschoepfen (Doppel-Dip-Schutz: greift nur in der Stations-Einflusszone).
    from app.alliance.bonus import alliance_bonus
    from app.platform.models import Player
    owner = await session.get(Player, fleet.player_id)
    zone_bonus = await alliance_bonus(
        session, owner, "mining_yield_zone",
        galaxy=fleet.target_galaxy, system=fleet.target_system,
    )
    if zone_bonus > 0:
        gained = {
            "metal": round(gained["metal"] * (1 + zone_bonus), 1),
            "crystal": round(gained["crystal"] * (1 + zone_bonus), 1),
        }

    cargo = dict(fleet.cargo or {})
    cargo["metal"] = round(cargo.get("metal", 0) + gained["metal"], 1)
    cargo["crystal"] = round(cargo.get("crystal", 0) + gained["crystal"], 1)
    fleet.cargo = cargo

    log.info("Mining @ %s [%s] -> %s (%d Bergbauschiffe, Rest m=%.0f k=%.0f)",
             location, field.richness, gained, miners, new_metal, new_crystal)

    total = gained["metal"] + gained["crystal"]
    if total > 0:
        subject = f"Bergbau erfolgreich ({location})"
        body = (f"Deine Bergbauschiffe foerderten am Asteroidenfeld {location} ({field.richness}): "
                f"{int(gained['metal'])} Metall + {int(gained['crystal'])} Kristall. Die Flotte kehrt mit der "
                f"Fracht zurueck (wird bei Ankunft dem Heimatplaneten gutgeschrieben). "
                f"Feld-Restvorrat: {int(new_metal)} Metall, {int(new_crystal)} Kristall.")
    else:
        subject = f"Bergbau: Feld erschoepft ({location})"
        body = (f"Das Asteroidenfeld {location} ({field.richness}) ist derzeit erschoepft — es wurde nichts "
                f"gefoerdert. Asteroidenfelder regenerieren mit der Zeit; spaeter erneut versuchen.")
    await create_system_transmission(
        session, player_id=fleet.player_id, subject=subject, body=body,
    )
    return {
        "location": location,
        "richness": field.richness,
        "mined": gained,
        "remaining": {"metal": round(new_metal, 1), "crystal": round(new_crystal, 1)},
    }
