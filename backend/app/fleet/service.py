"""Flotten-Logik: Distanz/Tempo/Sprit, Versand, Rueckruf, Anflug- & Rueckkehr-Jobs.

Flottenslots = 1 + Computertechnik-Stufe. Alle Zeiten/Kosten serverseitig (autoritativ)."""
from __future__ import annotations

import datetime as dt
import logging
import math
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import add_resources, get_research_levels, spend_resources
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Commander, Fleet, NpcAttack, NpcEmpire, Planet, Player, Ship, UniverseCell
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.fleet")

ACTIVE_STATUSES = ("flying", "arrived", "returning")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def compute_distance(o: tuple[int, int, int], t: tuple[int, int, int]) -> int:
    """Distanzklassen (balance.fleet.distance)."""
    dist = get_balance().fleet["distance"]
    if o[0] != t[0]:
        return dist["inter_galaxy"]
    if o[1] != t[1]:
        return abs(o[1] - t[1]) * dist["same_galaxy_per_system"]
    return dist["same_system"]


def flight_seconds(distance: int, slowest_speed: float, speed_pct: int) -> float:
    """flight_seconds = (10 + 3500/speed_pct * sqrt(distance*10/slowest_ship_speed)) / universe_speed."""
    bal = get_balance()
    universe_speed = bal.speed
    speed_pct = max(1, speed_pct)
    slowest_speed = max(1.0, slowest_speed)
    raw = 10 + (3500 / speed_pct) * math.sqrt(distance * 10 / slowest_speed)
    return raw / universe_speed


def fuel_cost(ships: dict[str, int], distance: int) -> int:
    """Sprit (Deuterium): Summe(Schiff-Sprit) * Distanz / speed_factor * fuel_per_distance_unit."""
    bal = get_balance()
    catalog = bal.ships
    factor = bal.fleet["fuel_per_distance_unit"]
    speed_factor = bal.fleet["speed_factor"]
    total = 0.0
    for typ, count in ships.items():
        cfg = catalog.get(typ)
        if cfg:
            total += cfg.get("fuel", 0) * count
    return max(1, int(math.ceil(total * distance / speed_factor * factor)))


def slowest_ship_speed(ships: dict[str, int]) -> float:
    bal = get_balance()
    speeds = [bal.ships[t]["speed"] for t in ships if t in bal.ships and ships[t] > 0]
    return min(speeds) if speeds else 1.0


async def fleet_slots(session: AsyncSession, player_id: uuid.UUID) -> int:
    research = await get_research_levels(session, player_id)
    bal = get_balance()
    return bal.fleet["base_slots"] + bal.fleet["slots_per_computer_tech"] * research.get("computer_tech", 0)


async def active_fleet_count(session: AsyncSession, player_id: uuid.UUID) -> int:
    rows = (await session.execute(
        select(Fleet).where(Fleet.player_id == player_id, Fleet.status.in_(ACTIVE_STATUSES))
    )).scalars().all()
    return len(rows)


async def _fleet_ship_map(session: AsyncSession, fleet_id: uuid.UUID) -> dict[str, int]:
    rows = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet_id)
    )).scalars().all()
    return {r.type: r.count for r in rows if r.count > 0}


async def fleet_to_dict(session: AsyncSession, fleet: Fleet) -> dict:
    origin = None
    if fleet.origin_planet_id:
        p = await session.get(Planet, fleet.origin_planet_id)
        if p:
            origin = f"{p.galaxy}:{p.system}:{p.position}"
    return {
        "id": fleet.id,
        "mission": fleet.mission,
        "status": fleet.status,
        "origin": origin,
        "target": {
            "galaxy": fleet.target_galaxy,
            "system": fleet.target_system,
            "position": fleet.target_position,
        },
        "commander_id": fleet.commander_id,
        "ships": await _fleet_ship_map(session, fleet.id),
        "cargo": fleet.cargo or {},
        "depart_at": fleet.depart_at,
        "arrive_at": fleet.arrive_at,
        "return_at": fleet.return_at,
    }


async def send_fleet(
    session: AsyncSession,
    player: Player,
    *,
    origin_planet_id: uuid.UUID,
    target: tuple[int, int, int],
    mission: str,
    ships: dict[str, int],
    cargo: dict,
    commander_id: uuid.UUID | None,
    speed_pct: int,
) -> Fleet:
    """Sendet eine Flotte. Validiert Schiffe, Slots, Ziel-Schutz, zieht Sprit+Fracht ab."""
    bal = get_balance()
    valid_missions = {"attack", "transport", "spy", "deploy", "recycle", "colonize"}
    if mission not in valid_missions:
        raise ValueError(f"Mission muss eine von {sorted(valid_missions)} sein")

    planet = await session.get(Planet, origin_planet_id)
    if planet is None or planet.player_id != player.id:
        raise ValueError("Startplanet nicht gefunden")

    ships = {t: int(c) for t, c in ships.items() if int(c) > 0}
    if not ships:
        raise ValueError("Keine Schiffe ausgewaehlt")

    # Flottenslots pruefen.
    slots = await fleet_slots(session, player.id)
    if await active_fleet_count(session, player.id) >= slots:
        raise RuntimeError("Keine freien Flottenslots")

    # Schiffsbestand pruefen.
    planet_ships = (await session.execute(
        select(Ship).where(Ship.planet_id == origin_planet_id, Ship.fleet_id.is_(None))
    )).scalars().all()
    by_type = {r.type: r for r in planet_ships}
    for typ, count in ships.items():
        if typ not in bal.ships:
            raise ValueError(f"Unbekannter Schiffstyp: {typ}")
        have = by_type.get(typ)
        if have is None or have.count < count:
            raise RuntimeError(f"Zu wenige Schiffe vom Typ {typ}")

    # Spionage erfordert Spionagesonden in der Flotte (Doku 04 §6).
    if mission == "spy":
        spy_cfg = bal.data["spy"]
        probes = ships.get(spy_cfg["probe_type"], 0)
        if probes < spy_cfg["min_probes"]:
            raise RuntimeError(
                f"Spionage benoetigt mindestens {spy_cfg['min_probes']} {spy_cfg['probe_type']}"
            )

    # Recycler-Mission erfordert Recycler in der Flotte (Truemmer einsammeln).
    if mission == "recycle":
        h_cfg = bal.data.get("harvest", {})
        collector = h_cfg.get("collector_type", "recycler")
        if ships.get(collector, 0) < h_cfg.get("min_collectors", 1):
            raise RuntimeError(
                f"Recycler-Mission benoetigt mindestens {h_cfg.get('min_collectors', 1)} {collector}"
            )

    # Kolonisierung erfordert ein Kolonieschiff in der Flotte.
    if mission == "colonize":
        c_cfg = bal.data.get("colonization", {})
        cs_type = c_cfg.get("ship_type", "colony_ship")
        if ships.get(cs_type, 0) < 1:
            raise RuntimeError(f"Kolonisierung benoetigt ein {cs_type}")

    # Commander pruefen (falls angegeben).
    commander = None
    if commander_id:
        commander = await session.get(Commander, commander_id)
        if commander is None or commander.player_id != player.id:
            raise ValueError("Commander nicht gefunden")
        if commander.status not in ("active", "wounded"):
            raise RuntimeError("Commander ist nicht einsatzbereit")

    # Ziel-Neulingsschutz pruefen (kein Angriff auf geschuetzte Spieler).
    if mission == "attack":
        cell = (await session.execute(
            select(UniverseCell).where(
                UniverseCell.galaxy == target[0],
                UniverseCell.system == target[1],
                UniverseCell.position == target[2],
            )
        )).scalar_one_or_none()
        if cell and cell.occupant_type == "player" and cell.ref_id:
            tgt_planet = await session.get(Planet, cell.ref_id)
            if tgt_planet:
                tgt_player = await session.get(Player, tgt_planet.player_id)
                if tgt_player and tgt_player.is_protected:
                    raise RuntimeError("Ziel steht unter Neulingsschutz")

    # Distanz, Tempo, Sprit.
    origin = (planet.galaxy, planet.system, planet.position)
    distance = compute_distance(origin, target)
    secs = flight_seconds(distance, slowest_ship_speed(ships), speed_pct)
    # Commander-Tempobonus verkuerzt die Flugzeit (moral-skaliert).
    if commander is not None:
        from app.commander.bonuses import base_bonuses, resolve_ship_bonuses
        focus = (commander.persona or {}).get("focus")
        cmd_bonuses = base_bonuses(
            commander.specialization, commander.rank, commander.traits or [], focus,
            commander.grade or "C",
        )
        _sb, speed_bonus = resolve_ship_bonuses(cmd_bonuses, commander.morale, list(ships.keys()))
        if speed_bonus > 0:
            secs = int(round(secs / (1.0 + speed_bonus)))
    fuel = fuel_cost(ships, distance)

    cargo = {
        "metal": float(cargo.get("metal", 0)),
        "crystal": float(cargo.get("crystal", 0)),
        "deuterium": float(cargo.get("deuterium", 0)),
    }
    # Gesamtkosten = Fracht + Sprit (Deuterium).
    total_cost = {
        "metal": cargo["metal"],
        "crystal": cargo["crystal"],
        "deuterium": cargo["deuterium"] + fuel,
    }
    if not await spend_resources(session, planet, total_cost):
        raise RuntimeError("Nicht genug Ressourcen (Fracht/Sprit)")

    depart = _now()
    arrive = depart + dt.timedelta(seconds=secs)
    return_at = arrive + dt.timedelta(seconds=secs)

    fleet = Fleet(
        player_id=player.id,
        commander_id=commander_id,
        origin_planet_id=origin_planet_id,
        target_galaxy=target[0],
        target_system=target[1],
        target_position=target[2],
        mission=mission,
        status="flying",
        depart_at=depart,
        arrive_at=arrive,
        return_at=return_at,
        cargo=cargo,
    )
    session.add(fleet)
    await session.flush()

    # Schiffe vom Planeten in die Flotte verschieben.
    for typ, count in ships.items():
        src = by_type[typ]
        src.count -= count
        if src.count == 0:
            await session.delete(src)
        session.add(Ship(planet_id=None, fleet_id=fleet.id, type=typ, count=count))

    await session.flush()

    schedule_at(arrive, fleet_arrive, str(fleet.id), job_id=f"fleet-arrive:{fleet.id}")
    schedule_at(return_at, fleet_return, str(fleet.id), job_id=f"fleet-return:{fleet.id}")
    log.info("Flotte %s gesendet -> %s (mission=%s)", fleet.id, target, mission)
    return fleet


async def list_incoming_attacks(session: AsyncSession, player_id: uuid.UUID) -> list[dict]:
    """Eingehende NPC-Angriffe auf die Planeten des Spielers (im Anflug), naechste zuerst."""
    rows = (await session.execute(
        select(NpcAttack)
        .where(NpcAttack.target_player_id == player_id, NpcAttack.status == "incoming")
        .order_by(NpcAttack.arrive_at.asc())
    )).scalars().all()
    out: list[dict] = []
    for a in rows:
        npc = await session.get(NpcEmpire, a.npc_id)
        out.append({
            "id": a.id,
            "attacker": npc.name if npc else "Unbekannte Flotte",
            "origin": f"{npc.galaxy}:{npc.system}:{npc.position}" if npc else None,
            "target": {
                "galaxy": a.target_galaxy,
                "system": a.target_system,
                "position": a.target_position,
            },
            "ships_total": sum((a.fleet or {}).values()),
            "arrive_at": a.arrive_at,
        })
    return out


async def recall_fleet(session: AsyncSession, player: Player, fleet_id: uuid.UUID) -> Fleet:
    """Ruft eine fliegende Flotte zurueck (Basis fuer Fleetsave)."""
    fleet = await session.get(Fleet, fleet_id)
    if fleet is None or fleet.player_id != player.id:
        raise ValueError("Flotte nicht gefunden")
    if fleet.status not in ("flying", "arrived"):
        raise RuntimeError("Flotte kann nicht mehr zurueckgerufen werden")

    now = _now()
    depart = fleet.depart_at
    if depart.tzinfo is None:
        depart = depart.replace(tzinfo=dt.timezone.utc)
    arrive = fleet.arrive_at
    if arrive.tzinfo is None:
        arrive = arrive.replace(tzinfo=dt.timezone.utc)

    elapsed = (now - depart).total_seconds()
    full_flight = (arrive - depart).total_seconds()
    # Rueckflug dauert so lange wie der bereits geflogene Teil (max. voller Flug).
    return_duration = min(max(0.0, elapsed), full_flight)
    fleet.status = "returning"
    fleet.return_at = now + dt.timedelta(seconds=return_duration)

    schedule_at(fleet.return_at, fleet_return, str(fleet.id), job_id=f"fleet-return:{fleet.id}")
    log.info("Flotte %s zurueckgerufen", fleet.id)
    return fleet


async def fleet_arrive(fleet_id: str) -> None:
    """Anflug-Job: bei Angriff Kampf, bei Spionage Aufklaerung; danach Rueckflug."""
    from app.combat.service import resolve_attack
    from app.fleet.harvest import resolve_harvest
    from app.planets.colonize import resolve_colonize
    from app.universe.spionage import resolve_spy

    async with session_scope() as session:
        fleet = await session.get(Fleet, uuid.UUID(fleet_id))
        if fleet is None or fleet.status != "flying":
            return  # zurueckgerufen oder bereits verarbeitet
        fleet.status = "arrived"
        player_id = fleet.player_id
        mission = fleet.mission

        if mission == "attack":
            await resolve_attack(session, fleet)
        elif mission == "spy":
            await resolve_spy(session, fleet)
        elif mission == "recycle":
            await resolve_harvest(session, fleet)
        elif mission == "colonize":
            await resolve_colonize(session, fleet)

        # Nach Ankunft kehrt die Flotte zurueck (return_at bleibt wie geplant).
        fleet.status = "returning"
        await session.commit()

    await event_bus.publish_ws(player_id, {
        "type": "fleet_arrived",
        "fleet_id": fleet_id,
        "mission": mission,
    })


async def fleet_return(fleet_id: str) -> None:
    """Rueckkehr-Job: Schiffe + Fracht an den Heimatplaneten zurueckgeben."""
    async with session_scope() as session:
        fleet = await session.get(Fleet, uuid.UUID(fleet_id))
        if fleet is None or fleet.status == "done":
            return
        player_id = fleet.player_id
        origin = await session.get(Planet, fleet.origin_planet_id) if fleet.origin_planet_id else None

        fleet_ships = (await session.execute(
            select(Ship).where(Ship.fleet_id == fleet.id)
        )).scalars().all()

        if origin is not None:
            # Schiffe in den Planetenbestand zurueckfuehren. Es kann mehrere
            # Bestands-Zeilen je Typ geben (kein DB-Unique); robust zusammenfuehren.
            for fs in fleet_ships:
                existing = (await session.execute(
                    select(Ship).where(
                        Ship.planet_id == origin.id, Ship.fleet_id.is_(None), Ship.type == fs.type
                    )
                )).scalars().all()
                if existing:
                    dest = existing[0]
                    dest.count += fs.count
                    # Etwaige Duplikate in die erste Zeile konsolidieren.
                    for extra in existing[1:]:
                        dest.count += extra.count
                        await session.delete(extra)
                else:
                    session.add(Ship(planet_id=origin.id, fleet_id=None, type=fs.type, count=fs.count))
                await session.delete(fs)
            # Fracht gutschreiben.
            await add_resources(session, origin, fleet.cargo or {})

        fleet.status = "done"
        fleet.cargo = {}
        await session.commit()

    await event_bus.publish_ws(player_id, {
        "type": "fleet_returned",
        "fleet_id": fleet_id,
    })
    log.info("Flotte %s zurueckgekehrt", fleet_id)
