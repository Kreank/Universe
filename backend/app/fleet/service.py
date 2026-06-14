"""Flotten-Logik: Distanz/Tempo/Sprit, Versand, Rueckruf, Anflug- & Rueckkehr-Jobs.

Flottenslots = 1 + Computertechnik-Stufe. Alle Zeiten/Kosten serverseitig (autoritativ)."""
from __future__ import annotations

import datetime as dt
import logging
import math
import uuid

from sqlalchemy import func, select
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
    """OGame-Distanzmodell (balance.fleet.distance). o/t = (Galaxie, System, Position).

    - Andere Galaxie:   per_galaxy * |Galaxie-Diff|.
    - Anderes System:   same_galaxy_base + per_system * |System-Diff|.
    - Andere Position:  same_system_base + per_position * |Positions-Diff| (Position zaehlt jetzt).
    - Gleiche Koords (z.B. Mond<->Planet): same_position (klein)."""
    d = get_balance().fleet["distance"]
    if o[0] != t[0]:
        return d["inter_galaxy_per_galaxy"] * abs(o[0] - t[0])
    if o[1] != t[1]:
        return d["same_galaxy_base"] + d["same_galaxy_per_system"] * abs(o[1] - t[1])
    if o[2] != t[2]:
        return d["same_system_base"] + d["same_system_per_position"] * abs(o[2] - t[2])
    return d["same_position"]


def flight_seconds(distance: int, slowest_speed: float, speed_pct: int) -> float:
    """flight_seconds = (10 + 35000/speed_pct * sqrt(distance*10/slowest_ship_speed)) / fleet_speed.

    35000 = echte OGame-Konstante. fleet_speed (universe.fleet_speed) ist der eigenstaendige
    Flotten-Tempo-Regler, BEWUSST getrennt von speed (=Wirtschaft/Produktion)."""
    bal = get_balance()
    fleet_speed = max(0.01, bal.fleet_speed)
    speed_pct = max(1, speed_pct)
    slowest_speed = max(1.0, slowest_speed)
    raw = 10 + (35000 / speed_pct) * math.sqrt(distance * 10 / slowest_speed)
    return raw / fleet_speed


def fuel_cost(ships: dict[str, int], distance: int, round_trip: bool = False) -> int:
    """Sprit (Deuterium): Summe(Schiff-Sprit) * Distanz / speed_factor * fuel_per_distance_unit.
    ``round_trip`` verdoppelt (Hin + Rueck) — fuer Missionen, die zurueckkehren."""
    bal = get_balance()
    catalog = bal.ships
    factor = bal.fleet["fuel_per_distance_unit"]
    speed_factor = bal.fleet["speed_factor"]
    legs = 2 if round_trip else 1
    total = 0.0
    for typ, count in ships.items():
        cfg = catalog.get(typ)
        if cfg:
            total += cfg.get("fuel", 0) * count
    return max(1, int(math.ceil(total * distance / speed_factor * factor * legs)))


def ship_range(typ: str, round_trip: bool = True) -> float:
    """Maximale EINFACHE Distanz, die dieser Schiffstyp mit vollem Tank schafft.

    Tank (``fuel_tank``) ist ein dedizierter Sprit-Vorrat pro Schiff (getrennt von Fracht).
    Verbrauch je Distanzeinheit = ``fuel * fuel_per_distance_unit / speed_factor``; bei
    ``round_trip`` muss der Tank Hin + Rueck decken -> halbe Reichweite. Schiffe ohne Sprit
    (z. B. Solarsatellit) sind ortsfest -> keine Begrenzung (inf)."""
    bal = get_balance()
    cfg = bal.ships.get(typ)
    if not cfg:
        return float("inf")
    fuel = float(cfg.get("fuel", 0))
    if fuel <= 0:
        return float("inf")
    sf = bal.fleet["speed_factor"]
    fpu = bal.fleet["fuel_per_distance_unit"]
    legs = 2 if round_trip else 1
    tank = float(cfg.get("fuel_tank", 0))
    return tank * sf / (fuel * fpu * legs)


def fleet_max_range(ships: dict[str, int], round_trip: bool = True) -> tuple[float, str | None]:
    """Reichweite der gesamten Flotte = das schwaechste mitfliegende Schiff bestimmt sie.
    Liefert (max_einfache_distanz, limitierender_schiffstyp)."""
    best: float | None = None
    limiting: str | None = None
    for typ, count in ships.items():
        if count <= 0:
            continue
        r = ship_range(typ, round_trip)
        if r == float("inf"):
            continue
        if best is None or r < best:
            best = r
            limiting = typ
    return (float("inf"), None) if best is None else (best, limiting)


# Reise-Antriebe (Forschung) -> Tempobonus. Reihenfolge = Prioritaet (hoechster Antrieb gewinnt),
# falls ein Schiff mehrere Antriebs-Voraussetzungen haette. BEWUSST getrennt vom Kampf-"drive"
# (combat_roster[*].drive / combat.drive_stages = Disengage/Interdiktion, NICHT Reisetempo).
TRAVEL_DRIVES = ("hyperspace_drive", "impulse_drive", "combustion_drive")


def ship_speed(typ: str, research: dict[str, int] | None = None) -> float:
    """Effektive Reisegeschwindigkeit eines Schiffstyps inkl. Antriebsforschung.

    Der Antrieb wird aus den Bau-Voraussetzungen (requires) abgeleitet: ein Schiff fliegt mit dem
    Antrieb, auf dem es gebaut ist. Jede Forschungsstufe erhoeht das Grundtempo um den in
    research.effects hinterlegten Prozentsatz (OGame-Modell: Verbrennung +10%, Impuls +20%,
    Hyperraum +30% je Stufe). Schiffe ohne Antriebs-Voraussetzung (z.B. Solarsatellit) skalieren nicht.
    """
    bal = get_balance()
    cfg = bal.ships.get(typ)
    if not cfg:
        return 1.0
    base = float(cfg.get("speed", 0))
    if research:
        requires = cfg.get("requires", {})
        effects = bal.data["research"].get("effects", {})
        for drive in TRAVEL_DRIVES:
            if drive in requires:
                per_level = effects.get(f"{drive}_speed_per_level", 0.0)
                base *= 1.0 + per_level * research.get(drive, 0)
                break
    return base


def is_sendable(typ: str) -> bool:
    """Ob ein Schiffstyp ueberhaupt entsendet werden kann. Stationaere Einheiten ohne
    Antrieb (Grundtempo 0, z.B. Solarsatellit) bleiben in der Umlaufbahn und sind nicht
    flottenfaehig."""
    cfg = get_balance().ships.get(typ)
    return bool(cfg) and float(cfg.get("speed", 0)) > 0


def slowest_ship_speed(ships: dict[str, int], research: dict[str, int] | None = None) -> float:
    """Tempo der langsamsten Flotteneinheit (bestimmt die Flugzeit) inkl. Antriebsforschung."""
    bal = get_balance()
    speeds = [ship_speed(t, research) for t in ships if t in bal.ships and ships[t] > 0]
    return min(speeds) if speeds else 1.0


def carrier_drone_capacity(ships: dict[str, int], computer_tech: int, carrier_cfg: dict) -> int:
    """Gesamte Drohnen-Kapazitaet einer Flotte (03d): Kapazitaet je Traeger-Typ aus
    carrier_cfg.capacity_by_type (Fallback drone_capacity = nur 'carrier'). Der Todesstern
    skaliert mit computer_tech (Basis -> deathstar_capacity_max)."""
    cap_by_type = dict(carrier_cfg.get("capacity_by_type", {}))
    if not cap_by_type and carrier_cfg.get("drone_capacity"):
        cap_by_type = {"carrier": int(carrier_cfg["drone_capacity"])}
    if "deathstar" in cap_by_type:
        base = int(cap_by_type["deathstar"])
        per = int(carrier_cfg.get("deathstar_capacity_per_computer_level", 0))
        cmax = int(carrier_cfg.get("deathstar_capacity_max", base))
        cap_by_type["deathstar"] = min(cmax, base + per * int(computer_tech))
    return sum(int(cap_by_type.get(t, 0)) * int(ships.get(t, 0)) for t in cap_by_type)


async def fleet_slots(session: AsyncSession, player_id: uuid.UUID) -> int:
    from app.platform.doctrine import fleet_slot_bonus
    research = await get_research_levels(session, player_id)
    bal = get_balance()
    base = bal.fleet["base_slots"] + bal.fleet["slots_per_computer_tech"] * research.get("computer_tech", 0)
    player = await session.get(Player, player_id)
    return base + fleet_slot_bonus(player.doctrine if player else None)


async def active_fleet_count(session: AsyncSession, player_id: uuid.UUID) -> int:
    rows = (await session.execute(
        select(Fleet).where(Fleet.player_id == player_id, Fleet.status.in_(ACTIVE_STATUSES))
    )).scalars().all()
    return len(rows)


async def active_patrol_count(session: AsyncSession, player_id: uuid.UUID) -> int:
    """Aktive Abfang-Patrouillen (intercept_enabled StationedFleets). Jede belegt EINEN Flottenslot
    (Anti-Omnipraesenz, 2026-06-12): Patrouillen sind dadurch hart begrenzt -> nur Chokepoints
    deckbar, nicht die ganze Galaxie. Stationierte Flotten OHNE Abfang zaehlen NICHT."""
    from app.platform.models import StationedFleet
    rows = (await session.execute(
        select(StationedFleet).where(
            StationedFleet.owner_id == player_id,
            StationedFleet.intercept_enabled.is_(True),
        )
    )).scalars().all()
    return len(rows)


async def used_fleet_slots(session: AsyncSession, player_id: uuid.UUID) -> int:
    """Belegte Flottenslots = Flotten im Flug + aktive Abfang-Patrouillen."""
    return await active_fleet_count(session, player_id) + await active_patrol_count(session, player_id)


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
    mission_data: dict | None = None,
) -> Fleet:
    """Sendet eine Flotte. Validiert Schiffe, Slots, Ziel-Schutz, zieht Sprit+Fracht ab.

    ``mission_data`` traegt missionsspezifische Auftragsdaten (z. B. Handel:
    {offer_res, offer_amount, want_res}) und wird auf ``fleet.mission_data`` gesetzt."""
    bal = get_balance()
    mission_data = mission_data or {}
    valid_missions = {"attack", "transport", "spy", "deploy", "recycle", "colonize", "mine", "expedition", "trade", "intercept", "escort"}
    if mission not in valid_missions:
        raise ValueError(f"Mission muss eine von {sorted(valid_missions)} sein")

    planet = await session.get(Planet, origin_planet_id)
    if planet is None or planet.player_id != player.id:
        raise ValueError("Startplanet nicht gefunden")

    # Forschung einmal frueh laden: mehrere missionsspezifische Branches weiter unten
    # (Traeger-Drohnenkapazitaet beim Angriff, Abfang-Radius, Flugzeit) lesen ``research``,
    # bevor die fruehere Stelle der Zuweisung erreicht waere -> sonst UnboundLocalError.
    research = await get_research_levels(session, player.id)

    ships = {t: int(c) for t, c in ships.items() if int(c) > 0}
    if not ships:
        raise ValueError("Keine Schiffe ausgewaehlt")

    # Flottenslots pruefen (Flotten im Flug + aktive Abfang-Patrouillen belegen je einen Slot).
    slots = await fleet_slots(session, player.id)
    if await used_fleet_slots(session, player.id) >= slots:
        raise RuntimeError("Keine freien Flottenslots")

    # Schiffsbestand pruefen.
    planet_ships = (await session.execute(
        select(Ship).where(Ship.planet_id == origin_planet_id, Ship.fleet_id.is_(None))
    )).scalars().all()
    by_type = {r.type: r for r in planet_ships}

    # Option A: Traeger laden beim Angriff automatisch Drohnen aus der Garnison nach
    # (bis zur Traeger-Kapazitaet drone_capacity). Diese fliegen als ECHTE Schiffe mit
    # (echte Verluste). Bereits manuell gewaehlte Drohnen zaehlen auf die Kapazitaet an.
    if mission == "attack":
        capacity = carrier_drone_capacity(ships, int(research.get("computer_tech", 0)), bal.combat.get("carrier", {}))
        if capacity > 0:
            already = int(ships.get("drone", 0))
            need = capacity - already
            garrison_drones = by_type.get("drone")
            avail = (garrison_drones.count - already) if garrison_drones else 0
            take = max(0, min(need, avail))
            if take > 0:
                ships["drone"] = already + take

    for typ, count in ships.items():
        if typ not in bal.ships:
            raise ValueError(f"Unbekannter Schiffstyp: {typ}")
        # Stationaere Einheiten (kein Antrieb, speed 0 -> z.B. Solarsatellit) bleiben in der
        # Umlaufbahn und koennen nicht entsendet werden.
        if count > 0 and not is_sendable(typ):
            raise ValueError(f"{typ} ist stationaer (kein Antrieb) und kann nicht entsendet werden")
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

    # Mining erfordert Bergbauschiffe in der Flotte.
    if mission == "mine":
        m_cfg = bal.data.get("mining", {})
        mtype = m_cfg.get("ship_type", "miner")
        if ships.get(mtype, 0) < m_cfg.get("min_ships", 1):
            raise RuntimeError(
                f"Mining benoetigt mindestens {m_cfg.get('min_ships', 1)} {mtype}"
            )

    # Abfangen: die Flotte fliegt zum Zielsystem und wird dort zur Abfang-Patrouille.
    # Radius (Default 0 = nur das Zielsystem) wird auf den forschungs-abhaengigen Cap geklemmt.
    if mission == "intercept":
        from app.fleet.stationing import intercept_radius_cap
        cap = intercept_radius_cap(research)
        radius = max(0, min(cap, int(mission_data.get("radius", 0) or 0)))
        mission_data = {**mission_data, "radius": radius}

    # Eskorte: die Flotte stationiert am Ziel als Geleitschutz-Angebot (Radius + Gebuehr).
    if mission == "escort":
        ecfg = bal.data.get("escort", {})
        cap_fee = float(ecfg.get("max_fee_pct", 0.10))
        e_radius = max(0, int(mission_data.get("escort_radius", ecfg.get("region_radius", 5)) or 0))
        e_fee = max(0.0, min(cap_fee, float(mission_data.get("escort_fee_pct", 0.0) or 0.0)))
        mission_data = {**mission_data, "escort_radius": e_radius, "escort_fee_pct": e_fee}

    # Expedition erfordert Expeditions-Schiffe in der Flotte.
    if mission == "expedition":
        from app.fleet.expedition import clamp_hours, max_expedition_hours
        e_cfg = bal.data.get("expedition", {})
        etype = e_cfg.get("ship_type", "expedition_ship")
        if ships.get(etype, 0) < e_cfg.get("min_ships", 1):
            raise RuntimeError(
                f"Expedition benoetigt mindestens {e_cfg.get('min_ships', 1)} {etype}"
            )
        # Ziel MUSS der Deep-Space-Slot sein (galaktische Weiten).
        deep = int(e_cfg.get("deep_space_position", 16))
        if target[2] != deep:
            raise ValueError(f"Expeditionen fliegen nur in die galaktischen Weiten (Position {deep}).")
        # Astrophysik schaltet Expeditionen frei + bestimmt die Maximaldauer.
        exp_research = await get_research_levels(session, player.id)
        astro = int(exp_research.get("astrophysics", 0))
        if max_expedition_hours(astro, e_cfg) <= 0:
            raise RuntimeError("Astrophysik Stufe 1 nötig, um Expeditionen zu entsenden.")
        hours = clamp_hours(int(mission_data.get("expedition_hours", 1)), astro, e_cfg)
        mission_data = {**mission_data, "expedition_hours": hours}
    elif target[2] == int(bal.data.get("expedition", {}).get("deep_space_position", 16)):
        # Position 16 ist reiner Expeditions-Slot — andere Missionen haben dort kein Ziel.
        raise ValueError("Position 16 (galaktische Weiten) ist nur per Expedition erreichbar.")

    # Handel erfordert einen Haendler-NPC am Ziel + einen gueltigen Auftrag.
    # Die Angebots-Ressource faehrt als Fracht mit (cargo wird vom Router gesetzt).
    if mission == "trade":
        from app.fleet.trade import validate_trade_order
        cell = (await session.execute(
            select(UniverseCell).where(
                UniverseCell.galaxy == target[0],
                UniverseCell.system == target[1],
                UniverseCell.position == target[2],
            )
        )).scalar_one_or_none()
        merchant: NpcEmpire | None = None
        if cell and cell.occupant_type == "npc" and cell.ref_id:
            merchant = await session.get(NpcEmpire, cell.ref_id)
        if merchant is None:
            merchant = (await session.execute(
                select(NpcEmpire).where(
                    NpcEmpire.galaxy == target[0],
                    NpcEmpire.system == target[1],
                    NpcEmpire.position == target[2],
                )
            )).scalar_one_or_none()
        if merchant is None or merchant.behavior_profile not in ("merchant", "trade_center"):
            raise ValueError("Am Ziel ist kein Haendler")
        order = validate_trade_order(mission_data, bal.trade)
        if order is None:
            raise ValueError("Ungueltiger Handelsauftrag")
        # Angebot darf die Frachtkapazitaet der Flotte nicht uebersteigen.
        from app.combat.service import _cargo_capacity
        capacity = _cargo_capacity(ships)
        _offer_res, offer_amount, _want_res = order
        if offer_amount > capacity:
            raise ValueError(
                f"Angebot ({int(offer_amount)}) uebersteigt die Frachtkapazitaet ({int(capacity)})"
            )
        # Gewaehlte Eskorten buchen: Gebuehr abziehen, Kampfkraft fuer das Routenrisiko merken.
        escort_ids = mission_data.pop("escort_ids", []) if isinstance(mission_data, dict) else []
        if escort_ids:
            from app.fleet.stationing import charge_trade_escorts
            cargo_value = offer_amount * float(bal.trade["base_value"][_offer_res])
            power = await charge_trade_escorts(session, player.id, planet, target, escort_ids, cargo_value)
            if power > 0:
                mission_data["escort_power"] = power

    # Commander pruefen (falls angegeben).
    commander = None
    if commander_id:
        commander = await session.get(Commander, commander_id)
        if commander is None or commander.player_id != player.id:
            raise ValueError("Commander nicht gefunden")
        if commander.status not in ("active", "wounded"):
            raise RuntimeError("Commander ist nicht einsatzbereit")
        # Ein Gouverneur (Planeten-Posten) kann nicht gleichzeitig eine Flotte fuehren.
        is_governor = (await session.execute(
            select(Planet.id).where(Planet.governor_commander_id == commander.id)
        )).first() is not None
        if is_governor:
            raise RuntimeError("Dieser Kommandeur ist als Gouverneur eingesetzt — erst abberufen")
        # Arm-Slots: nicht mehr Faehigkeiten scharfschalten als der Rang erlaubt.
        ak = (mission_data or {}).get("ability_keys") or []
        if ak:
            from app.commander.service import arm_slots
            if len(ak) > arm_slots(commander.rank, get_balance()):
                raise RuntimeError("Mehr Faehigkeiten scharfgeschaltet als Arm-Slots verfuegbar")

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
        # Handelszentren sind unangreifbar (neutrale Infrastruktur).
        if cell and cell.occupant_type == "npc" and cell.ref_id:
            tgt_npc = await session.get(NpcEmpire, cell.ref_id)
            if tgt_npc and tgt_npc.behavior_profile == "trade_center":
                raise RuntimeError("Handelszentren sind neutral und koennen nicht angegriffen werden")

    # Distanz, Tempo, Sprit. Deploy bleibt einfach (Schiff bleibt vor Ort); alles andere kehrt
    # zurueck -> Sprit + Reichweite muessen Hin + Rueck decken.
    origin = (planet.galaxy, planet.system, planet.position)
    distance = compute_distance(origin, target)
    round_trip = mission not in ("deploy", "escort")
    # Reichweiten-Grenze (Treibstoff-Tank pro Schiff): das schwaechste Schiff begrenzt die Flotte.
    max_range, limiting = fleet_max_range(ships, round_trip=round_trip)
    if distance > max_range:
        leg = "Hin + Rück" if round_trip else "einfach"
        raise ValueError(
            f"Reichweite zu kurz: Ziel-Distanz {distance}, Flotte schafft max. {int(max_range)} "
            f"({leg}) — limitierend: {limiting}. Tank reicht nicht für die Strecke."
        )
    secs = flight_seconds(distance, slowest_ship_speed(ships, research), speed_pct)
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
    fuel = fuel_cost(ships, distance, round_trip=round_trip)

    # Scharfgeschaltete Faehigkeiten (RPG): Eilmarsch (Flugzeit) / Sparflug (Sprit).
    if commander is not None and mission_data:
        from app.commander.service import effective_ability, mark_ability_used
        now_a = _now()
        for key in mission_data.get("ability_keys", []):
            eff = effective_ability(commander, key, get_balance(), now_a)
            if not eff:
                continue
            if eff["kind"] == "flight_pct":
                secs = int(round(secs * (1.0 - eff["magnitude"])))
                mark_ability_used(commander, key, now_a)
            elif eff["kind"] == "fuel_pct":
                fuel = fuel * (1.0 - eff["magnitude"])
                mark_ability_used(commander, key, now_a)

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
    # Expedition: Aufenthalt in den galaktischen Weiten vor dem Rueckflug.
    hold_seconds = 0
    if mission == "expedition":
        hold_seconds = int(mission_data.get("expedition_hours", 1)) * 3600
    return_at = arrive + dt.timedelta(seconds=hold_seconds + secs)

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
        mission_data=mission_data,
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

    # Abfangen im Flug (A): feindliche Abfang-Patrouillen auf der galaxie-internen Route
    # planen einen Abfang-Job. Defensiv — ein Fehler darf den Flottenstart nie blockieren.
    try:
        from app.fleet.interception import schedule_interceptions_for_fleet
        await schedule_interceptions_for_fleet(session, fleet)
    except Exception:  # noqa: BLE001
        log.exception("Abfang-Planung fuer Flotte %s fehlgeschlagen (ignoriert)", fleet.id)

    # Verteidiger-Vorwarnung bei Spieler-Angriff (ermoeglicht Fleetsave).
    if mission == "attack":
        tcell = (await session.execute(
            select(UniverseCell).where(
                UniverseCell.galaxy == target[0],
                UniverseCell.system == target[1],
                UniverseCell.position == target[2],
            )
        )).scalar_one_or_none()
        if tcell and tcell.occupant_type == "player" and tcell.ref_id:
            tplanet = await session.get(Planet, tcell.ref_id)
            if tplanet and tplanet.player_id != player.id:
                await event_bus.publish_ws(tplanet.player_id, {
                    "type": "attack_warning",
                    "location": f"{target[0]}:{target[1]}:{target[2]}",
                    "arrive_at": arrive.isoformat(),
                    "ships_total": sum(ships.values()),
                    "attacker_name": player.display_name,
                })

    log.info("Flotte %s gesendet -> %s (mission=%s)", fleet.id, target, mission)
    return fleet


async def jump_fleet(
    session: AsyncSession, player: Player, from_moon_id: uuid.UUID, to_moon_id: uuid.UUID, ships: dict[str, int]
) -> dict:
    """Sprungtor: versetzt Schiffe SOFORT zwischen zwei eigenen Monden (kein Flug/Sprit, Cooldown)."""
    from app.economy.service import get_building_levels

    bal = get_balance()
    if from_moon_id == to_moon_id:
        raise ValueError("Quell- und Zielmond muessen verschieden sein")
    src = await session.get(Planet, from_moon_id)
    dst = await session.get(Planet, to_moon_id)
    for m in (src, dst):
        if m is None or m.player_id != player.id or m.planet_type != "moon":
            raise ValueError("Mond nicht gefunden")
        levels = await get_building_levels(session, m.id)
        if levels.get("jump_gate", 0) < 1:
            raise RuntimeError("Beide Monde benoetigen ein Sprungtor")
    # Forschung: Sprungtor-Kalibrierung senkt Abklingzeit + Sprungkosten.
    research = await get_research_levels(session, player.id)
    eff = bal.data["research"]["effects"]
    jgt = int(research.get("jump_gate_tech", 0))
    cd_mult = max(float(eff.get("jump_cooldown_floor", 0.4)),
                  1.0 - jgt * float(eff.get("jump_cooldown_reduction_per_level", 0.0)))
    cost_mult = max(0.0, 1.0 - jgt * float(eff.get("jump_cost_reduction_per_level", 0.0)))
    cd = float(bal.data["moon"]["jump_gate_cooldown_seconds"]) * cd_mult

    last = src.last_jump_at
    if last is not None:
        if last.tzinfo is None:
            last = last.replace(tzinfo=dt.timezone.utc)
        wait = cd - (_now() - last).total_seconds()
        if wait > 0:
            raise RuntimeError(f"Sprungtor im Cooldown ({int(wait)}s)")

    ships = {t: int(c) for t, c in ships.items() if int(c) > 0}
    if not ships:
        raise ValueError("Keine Schiffe gewaehlt")
    # Sprung-Kosten (Deuterium) am Quellmond abziehen: je Schiff nach Groessenklasse
    # (kleiner Jaeger/Transporter guenstig, Grosskampfschiffe/Traeger ~4x).
    mcfg = bal.data["moon"]
    base = float(mcfg.get("jump_cost_base_deuterium", 0))
    class_mult = mcfg.get("jump_cost_class_mult", {})
    ship_class = {
        typ: cls
        for cls, types in bal.commander["ship_classes"].items()
        if not cls.startswith("_")
        for typ in types
    }
    jump_cost = int(round(cost_mult * base * sum(
        float(class_mult.get(ship_class.get(typ, "fighter"), 1.0)) * count
        for typ, count in ships.items()
    )))
    if jump_cost > 0 and not await spend_resources(session, src, {"deuterium": jump_cost}):
        raise RuntimeError(f"Nicht genug Deuterium fuer den Sprung ({jump_cost})")
    # Schiffe aus der Quell-Garnison nehmen.
    rows = (await session.execute(
        select(Ship).where(Ship.planet_id == src.id, Ship.fleet_id.is_(None))
    )).scalars().all()
    by_type = {r.type: r for r in rows}
    for typ, count in ships.items():
        if by_type.get(typ) is None or by_type[typ].count < count:
            raise RuntimeError(f"Zu wenige Schiffe vom Typ {typ}")
    for typ, count in ships.items():
        src_row = by_type[typ]
        src_row.count -= count
        if src_row.count == 0:
            await session.delete(src_row)
        existing = (await session.execute(
            select(Ship).where(Ship.planet_id == dst.id, Ship.fleet_id.is_(None), Ship.type == typ)
        )).scalars().first()
        if existing:
            existing.count += count
        else:
            session.add(Ship(planet_id=dst.id, fleet_id=None, type=typ, count=count))
    src.last_jump_at = _now()
    log.info("Sprung: player=%s %s -> %s ships=%s", player.id, src.id, dst.id, ships)
    return {"ok": True, "next_jump_at": (src.last_jump_at + dt.timedelta(seconds=cd)).isoformat()}


async def list_incoming_attacks(session: AsyncSession, player_id: uuid.UUID) -> list[dict]:
    """Eingehende Angriffe auf die Planeten des Spielers (NPC + Spieler), naechste zuerst.

    NPC-Angriffe stammen aus ``npc_attacks``; Spieler-Angriffe sind fremde Fleet-Zeilen
    mission='attack' im Anflug (status 'flying') auf einen eigenen Planeten — sie machen
    Fleetsave moeglich (rechtzeitig die eigene Flotte wegschicken)."""
    rows = (await session.execute(
        select(NpcAttack)
        .where(NpcAttack.target_player_id == player_id, NpcAttack.status == "incoming")
        .order_by(NpcAttack.arrive_at.asc())
    )).scalars().all()
    out: list[dict] = []
    for a in rows:
        npc = await session.get(NpcEmpire, a.npc_id)
        out.append({
            "id": str(a.id),
            "attacker": npc.name if npc else "Unbekannte Flotte",
            "kind": "npc",
            "origin": f"{npc.galaxy}:{npc.system}:{npc.position}" if npc else None,
            "target": {
                "galaxy": a.target_galaxy,
                "system": a.target_system,
                "position": a.target_position,
            },
            "ships_total": sum((a.fleet or {}).values()),
            "arrive_at": a.arrive_at,
        })

    # -- Eingehende SPIELER-Angriffsflotten auf eigene Planeten --
    my_planets = (await session.execute(
        select(Planet).where(Planet.player_id == player_id)
    )).scalars().all()
    coords = {(p.galaxy, p.system, p.position) for p in my_planets}
    if coords:
        atk_fleets = (await session.execute(
            select(Fleet).where(
                Fleet.mission == "attack",
                Fleet.status == "flying",
                Fleet.player_id != player_id,
            ).order_by(Fleet.arrive_at.asc())
        )).scalars().all()
        for f in atk_fleets:
            if (f.target_galaxy, f.target_system, f.target_position) not in coords:
                continue
            attacker = await session.get(Player, f.player_id)
            origin = await session.get(Planet, f.origin_planet_id) if f.origin_planet_id else None
            ships_total = int((await session.execute(
                select(func.coalesce(func.sum(Ship.count), 0)).where(Ship.fleet_id == f.id)
            )).scalar_one() or 0)
            out.append({
                "id": str(f.id),
                "attacker": attacker.display_name if attacker else "Feindflotte",
                "kind": "player",
                "origin": f"{origin.galaxy}:{origin.system}:{origin.position}" if origin else None,
                "target": {
                    "galaxy": f.target_galaxy,
                    "system": f.target_system,
                    "position": f.target_position,
                },
                "ships_total": ships_total,
                "arrive_at": f.arrive_at,
            })

    out.sort(key=lambda x: x["arrive_at"])
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
    from app.fleet.expedition import resolve_expedition
    from app.fleet.harvest import resolve_harvest
    from app.fleet.mining import resolve_mine
    from app.fleet.stationing import resolve_deploy
    from app.fleet.trade import resolve_trade
    from app.planets.colonize import resolve_colonize
    from app.universe.spionage import resolve_spy

    async with session_scope() as session:
        fleet = await session.get(Fleet, uuid.UUID(fleet_id))
        if fleet is None or fleet.status != "flying":
            return  # zurueckgerufen oder bereits verarbeitet
        fleet.status = "arrived"
        player_id = fleet.player_id
        mission = fleet.mission

        stationed = False
        exp_result: dict | None = None
        if mission == "attack":
            await resolve_attack(session, fleet)
        elif mission == "spy":
            await resolve_spy(session, fleet)
        elif mission == "recycle":
            await resolve_harvest(session, fleet)
        elif mission == "colonize":
            await resolve_colonize(session, fleet)
        elif mission == "mine":
            await resolve_mine(session, fleet)
        elif mission == "expedition":
            exp_result = await resolve_expedition(session, fleet)
        elif mission == "trade":
            await resolve_trade(session, fleet)
        elif mission == "deploy":
            stationed = await resolve_deploy(session, fleet, mode="park")
        elif mission == "intercept":
            stationed = await resolve_deploy(session, fleet, mode="intercept")
        elif mission == "escort":
            stationed = await resolve_deploy(session, fleet, mode="escort")

        wiped = bool(exp_result and exp_result.get("wiped"))
        if wiped:
            # Totalverlust (Schwarzes Loch / vernichtende Begegnung): keine Rueckkehr.
            # Der bereits geplante fleet_return-Job laeuft ins Leere (Guard: status == 'done').
            fleet.status = "done"
        elif not stationed:
            # Expeditions-Ereignis kann die Rueckkehr verlaengern (return_at + extra_hours).
            extra_h = int(exp_result.get("extra_hours", 0)) if exp_result else 0
            if extra_h > 0 and fleet.return_at is not None:
                ret = fleet.return_at
                if ret.tzinfo is None:
                    ret = ret.replace(tzinfo=dt.timezone.utc)
                fleet.return_at = ret + dt.timedelta(hours=extra_h)
                schedule_at(fleet.return_at, fleet_return, str(fleet.id), job_id=f"fleet-return:{fleet.id}")
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
