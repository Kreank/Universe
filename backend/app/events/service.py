"""Game-Event-Kern: Spawner-Tick für Welt-/Karten-Events + Lebenszyklus (Spawn/Ablauf).

Karten-Events liegen als Overlay auf einer Galaxie-Koordinate. Jeder Event-Typ hat eine
Spawn-Funktion (legt CosmicEvent + ggf. AsteroidField/NPC/Buff an) und wird beim Ablauf
(``resolve_event``) wieder aufgeräumt. Alles offline-sicher (kein Spieler-Input nötig zum Spawn).
"""
from __future__ import annotations

import datetime as dt
import logging
import random
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.buffs import apply_buff
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import (
    AsteroidField,
    CosmicEvent,
    NpcEmpire,
    Planet,
    UniverseCell,
)
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.events")

MAP_EVENT_TYPES = (
    "wandering_comet",
    "cosmic_anomaly",
    "solar_storm",
    "black_market",
    "refugee_flotilla",
    "utopia_shipyard",
)


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _rng_range(lo_hi, default=0) -> float:
    if not isinstance(lo_hi, (list, tuple)) or len(lo_hi) != 2:
        return float(default)
    return random.uniform(float(lo_hi[0]), float(lo_hi[1]))


async def _free_coords(session: AsyncSession, bal) -> tuple[int, int, int] | None:
    """Sucht eine möglichst freie Koordinate (kein Planet/NPC, kein anderes aktives Event)."""
    galaxies = bal.galaxies
    systems = bal.systems_per_galaxy
    positions = bal.positions_per_system
    for _ in range(40):
        g = random.randint(1, galaxies)
        s = random.randint(1, systems)
        p = random.randint(1, positions)
        cell = (await session.execute(
            select(UniverseCell).where(
                UniverseCell.galaxy == g, UniverseCell.system == s, UniverseCell.position == p
            )
        )).scalar_one_or_none()
        if cell is not None and cell.occupant_type in ("player", "npc"):
            continue
        ev = (await session.execute(
            select(CosmicEvent).where(
                CosmicEvent.galaxy == g, CosmicEvent.system == s, CosmicEvent.position == p,
                CosmicEvent.status == "active",
            )
        )).first()
        if ev is not None:
            continue
        return (g, s, p)
    return None


async def _announce(session: AsyncSession, subject: str, body: str) -> None:
    """Universumsweites Bulletin an alle Spieler (ein Funkspruch je Spieler)."""
    from app.messaging.service import create_system_transmission
    player_ids = (await session.execute(select(Planet.player_id).distinct())).scalars().all()
    for pid in player_ids:
        await create_system_transmission(
            session, player_id=pid, subject=subject, body=body, ttype="system", publish=False,
        )


# -- Spawn-Funktionen je Event-Typ -------------------------------------------

async def _spawn_wandering_comet(session: AsyncSession, bal, cfg: dict) -> CosmicEvent | None:
    coords = await _free_coords(session, bal)
    if coords is None:
        return None
    g, s, p = coords
    lifetime = float(cfg.get("lifetime_hours", 48))
    metal = _rng_range(cfg.get("metal", [0, 0]))
    crystal = _rng_range(cfg.get("crystal", [400000, 900000]))
    deuterium = _rng_range(cfg.get("deuterium", [600000, 1400000]))
    # Komet = abbaubares Feld (reused Mining). AsteroidField hält Metall+Kristall; Deuterium
    # legen wir als Crystal-Aequivalent obendrauf (Mining erntet Metall/Kristall).
    field = AsteroidField(
        galaxy=g, system=s, position=p, richness="comet",
        mult=float(cfg.get("richness_mult", 2.5)),
        metal_remaining=metal, crystal_remaining=crystal + deuterium,
        metal_max=metal, crystal_max=crystal + deuterium,
    )
    session.add(field)
    ev = CosmicEvent(
        event_type="wandering_comet", scope="global", galaxy=g, system=s, position=p,
        data={"crystal": int(crystal), "deuterium": int(deuterium), "asteroid_field": True},
        expires_at=_now() + dt.timedelta(hours=lifetime),
    )
    session.add(ev)
    await session.flush()
    await _announce(
        session, "☄️ Wandernder Komet gesichtet",
        f"Ein riesiger eisiger Komet zieht durch {g}:{s}:{p} — randvoll mit Kristall und "
        f"Deuterium. Schick Schürf-/Recycler-Flotten hin, bevor er in {int(lifetime)} h "
        f"weiterzieht! (Mining-Mission auf die Koordinate)",
    )
    return ev


async def _spawn_cosmic_anomaly(session: AsyncSession, bal, cfg: dict) -> CosmicEvent | None:
    coords = await _free_coords(session, bal)
    if coords is None:
        return None
    g, s, p = coords
    lifetime = float(cfg.get("lifetime_hours", 24))
    ev = CosmicEvent(
        event_type="cosmic_anomaly", scope="global", galaxy=g, system=s, position=p,
        data={
            "research_speed_buff": float(cfg.get("research_speed_buff", 1.25)),
            "buff_hours": float(cfg.get("buff_hours", 12)),
            "damage_chance": float(cfg.get("damage_chance", 0.15)),
        },
        expires_at=_now() + dt.timedelta(hours=lifetime),
    )
    session.add(ev)
    await session.flush()
    pct = int((float(cfg.get("research_speed_buff", 1.25)) - 1.0) * 100)
    await _announce(
        session, "🌀 Kosmische Anomalie",
        f"Bei {g}:{s}:{p} ist ein Quanten-Riss aufgetaucht. Schick eine Spionagesonde hin "
        f"(Spionage-Mission) und sichere dir +{pct}% Forschungstempo für "
        f"{int(cfg.get('buff_hours', 12))} h. Achtung: kleines Risiko, dass die Sonde beschädigt wird.",
    )
    return ev


async def _spawn_solar_storm(session: AsyncSession, bal, cfg: dict) -> CosmicEvent | None:
    # Ganzes System blenden — wähle ein System (bevorzugt mit Spielern, sonst beliebig).
    coords = await _free_coords(session, bal)
    if coords is None:
        return None
    g, s, _p = coords
    warning = float(cfg.get("warning_hours", 12))
    lifetime = float(cfg.get("lifetime_hours", 24))
    starts_at = _now() + dt.timedelta(hours=warning)
    ev = CosmicEvent(
        event_type="solar_storm", scope="system", galaxy=g, system=s, position=None,
        data={"starts_at": starts_at.isoformat(), "lifetime_hours": lifetime},
        expires_at=starts_at + dt.timedelta(hours=lifetime),
    )
    session.add(ev)
    await session.flush()
    # Blende-Buffs erst beim Sturm-Beginn aktiv -> per Job einschalten.
    schedule_at(starts_at, activate_solar_storm, str(ev.id), job_id=f"event-storm:{ev.id}")
    await _announce(
        session, "⚡ Sonnensturm-Warnung",
        f"Ein instabiler Stern wird in {int(warning)} h einen Sonnensturm durch System {g}:{s} "
        f"schleudern. Für {int(lifetime)} h fallen dort Phalanx & Spionage komplett aus — "
        f"niemand sieht Flottenbewegungen. Miner: rechtzeitig evakuieren oder im Blindflug agieren.",
    )
    return ev


async def activate_solar_storm(event_id: str) -> None:
    """Job: schaltet die Blende-Buffs (scan/spionage) zum Sturm-Beginn ein."""
    async with session_scope() as session:
        ev = await session.get(CosmicEvent, uuid.UUID(event_id))
        if ev is None or ev.status != "active":
            return
        hours = float((ev.data or {}).get("lifetime_hours", 24))
        for bt in ("scan_block", "spionage_block"):
            await apply_buff(
                session, buff_type=bt, magnitude=1.0, duration_hours=hours,
                scope="system", galaxy=ev.galaxy, system=ev.system, source_event_id=ev.id,
            )
        await session.commit()
    log.info("Sonnensturm aktiv: System %s:%s geblendet (%sh)", ev.galaxy, ev.system, hours)


async def _spawn_black_market(session: AsyncSession, bal, cfg: dict) -> CosmicEvent | None:
    coords = await _free_coords(session, bal)
    if coords is None:
        return None
    g, s, p = coords
    lifetime = float(cfg.get("lifetime_hours", 24))
    rate_bonus = float(cfg.get("rate_bonus", 1.5))
    # Temporäres, unangreifbares Schwarzmarkt-NPC (Vorbild: ensure_trade_centers).
    npc = NpcEmpire(
        name="Schwarzmarkt-Karawane",
        behavior_profile="trade_center",
        galaxy=g, system=s, position=p,
        market={"spec": "black_market", "rate_bonus": rate_bonus, "stock": {}},
    )
    session.add(npc)
    await session.flush()
    from app.universe.service import occupy_cell
    await occupy_cell(session, g, s, p, "npc", npc.id)
    ev = CosmicEvent(
        event_type="black_market", scope="global", galaxy=g, system=s, position=p,
        data={"npc_id": str(npc.id), "rate_bonus": rate_bonus},
        expires_at=_now() + dt.timedelta(hours=lifetime),
    )
    session.add(ev)
    await session.flush()
    await _announce(
        session, "🏴 Intergalaktischer Schwarzmarkt",
        f"Ein schwer bewaffnetes Händlerschiff einer fremden Fraktion ankert bei {g}:{s}:{p}. "
        f"Für {int(lifetime)} h gibt es dort Sonderkurse (+{int((rate_bonus-1)*100)}% besser als "
        f"normal). Handeln per Transport-/Handelsmission.",
    )
    return ev


async def _spawn_refugee_flotilla(session: AsyncSession, bal, cfg: dict) -> CosmicEvent | None:
    # Flüchtlinge springen in ein bewohntes System (es muss Spieler geben, denen sie andocken).
    planet = (await session.execute(
        select(Planet).where(Planet.planet_type != "moon").order_by(func.random()).limit(1)
    )).scalars().first()
    if planet is None:
        return None
    g, s = planet.galaxy, planet.system
    lifetime = float(cfg.get("lifetime_hours", 12))
    ev = CosmicEvent(
        event_type="refugee_flotilla", scope="system", galaxy=g, system=s, position=None,
        data={
            "deuterium_cost": int(cfg.get("deuterium_cost", 50000)),
            "morale_bonus": int(cfg.get("morale_bonus", 12)),
            "build_speed_buff": float(cfg.get("build_speed_buff", 1.5)),
            "buff_hours": float(cfg.get("buff_hours", 24)),
            "pursuer_power_vs_player": float(cfg.get("pursuer_power_vs_player", 0.5)),
            "keep_ships": cfg.get("keep_ships", {"large_cargo": 5}),
            "helpers": [],  # player_ids, die geholfen haben -> Verfolger-Welle bei Ablauf
        },
        expires_at=_now() + dt.timedelta(hours=lifetime),
    )
    session.add(ev)
    await session.flush()
    # Jedem Spieler mit Planet im System eine Hilfe-Entscheidung schicken (offline-sicher).
    from app.events.decisions import create_event_decision
    sys_players = (await session.execute(
        select(Planet.player_id).where(
            Planet.galaxy == g, Planet.system == s, Planet.planet_type != "moon"
        ).distinct()
    )).scalars().all()
    cost = int(cfg.get("deuterium_cost", 50000))
    for pid in sys_players:
        await create_event_decision(
            session, player_id=pid, event=ev,
            subject=f"🚢 Flüchtlings-Flottille ({g}:{s})",
            body=f"Ein Konvoi ziviler Schiffe ist erschöpft in System {g}:{s} gesprungen — auf der "
                 f"Flucht vor einer Alien-Invasion. Sie brauchen {cost} Deuterium und Schutz. Hilfst "
                 f"du, bekommst du einen Moral- + Baugeschwindigkeits-Boost und einige Zivilschiffe — "
                 f"ABER nach {int(lifetime)} h holen ihre Verfolger dich ein und greifen an. (Hilfst du "
                 f"nicht, ziehen sie weiter.)",
            choices=["help", "wait"],
            default_choice="wait",
            timeout_hours=lifetime,
        )
    log.info("Flüchtlings-Flottille @ %s:%s, %d Spieler im System", g, s, len(sys_players))
    return ev


async def _spawn_utopia_shipyard(session: AsyncSession, bal, cfg: dict) -> CosmicEvent | None:
    coords = await _free_coords(session, bal)
    if coords is None:
        return None
    g, s, p = coords
    lifetime = float(cfg.get("lifetime_hours", 48))
    ev = CosmicEvent(
        event_type="utopia_shipyard", scope="global", galaxy=g, system=s, position=p,
        data={
            "reward_ship": cfg.get("reward_ship", "battleship"),
            "reward_count": int(cfg.get("reward_count", 5)),
            "top_n": int(cfg.get("top_n", 3)),
            "contributions": {},  # player_id -> gelieferter Wert (Metall+Kristall+Deuterium)
        },
        expires_at=_now() + dt.timedelta(hours=lifetime),
    )
    session.add(ev)
    await session.flush()
    await _announce(
        session, "⚙️ Utopia-Werft erwacht",
        f"Eine verlassene Orbital-Werft bei {g}:{s}:{p} hat noch Energie für eine Handvoll legendärer "
        f"Prototyp-Schiffe. Liefer Ressourcen per TRANSPORT dorthin — die {int(cfg.get('top_n',3))} "
        f"größten Spender in {int(lifetime)} h bekommen je {int(cfg.get('reward_count',5))}× ein "
        f"einzigartiges Flaggschiff. Ein Wettrennen — bevor der Reaktor kollabiert!",
    )
    return ev


async def record_utopia_contribution(session: AsyncSession, g: int, s: int, p: int, player_id, amount: float) -> bool:
    """Verbucht eine Transport-Lieferung an eine aktive Utopia-Werft. True = verbucht (kein Planet
    am Ort noetig). Aufgerufen aus resolve_transport."""
    ev = (await session.execute(
        select(CosmicEvent).where(
            CosmicEvent.event_type == "utopia_shipyard", CosmicEvent.status == "active",
            CosmicEvent.galaxy == g, CosmicEvent.system == s, CosmicEvent.position == p,
            CosmicEvent.expires_at > _now(),
        )
    )).scalar_one_or_none()
    if ev is None:
        return False
    data = dict(ev.data or {})
    contrib = dict(data.get("contributions", {}))
    contrib[str(player_id)] = float(contrib.get(str(player_id), 0)) + float(amount)
    data["contributions"] = contrib
    ev.data = data
    await session.flush()
    return True


_SPAWNERS = {
    "wandering_comet": _spawn_wandering_comet,
    "cosmic_anomaly": _spawn_cosmic_anomaly,
    "solar_storm": _spawn_solar_storm,
    "black_market": _spawn_black_market,
    "refugee_flotilla": _spawn_refugee_flotilla,
    "utopia_shipyard": _spawn_utopia_shipyard,
}


# -- Ablauf / Aufräumen ------------------------------------------------------

async def resolve_event(event_id: str) -> None:
    """Job bei ``expires_at``: räumt das Event-Objekt auf (Feld/NPC entfernen) + markiert expired."""
    async with session_scope() as session:
        ev = await session.get(CosmicEvent, uuid.UUID(event_id))
        if ev is None or ev.status != "active":
            return
        data = ev.data or {}
        # Komet: zugehöriges Asteroidenfeld entfernen.
        if ev.event_type == "wandering_comet" and ev.galaxy is not None:
            field = (await session.execute(
                select(AsteroidField).where(
                    AsteroidField.galaxy == ev.galaxy, AsteroidField.system == ev.system,
                    AsteroidField.position == ev.position, AsteroidField.richness == "comet",
                )
            )).scalar_one_or_none()
            if field is not None:
                await session.delete(field)
        # Utopia-Werft: bei Ablauf bekommen die Top-N Spender je reward_count Belohnungs-Schiffe.
        if ev.event_type == "utopia_shipyard":
            contrib = (data.get("contributions") or {})
            ranked = sorted(contrib.items(), key=lambda kv: -float(kv[1]))[: int(data.get("top_n", 3))]
            reward_ship = data.get("reward_ship", "battleship")
            reward_count = int(data.get("reward_count", 5))
            from app.messaging.service import create_system_transmission
            from app.platform.models import Ship as _Ship
            for rank, (pid_str, amount) in enumerate(ranked, start=1):
                if float(amount) <= 0:
                    continue
                home = (await session.execute(
                    select(Planet).where(Planet.player_id == uuid.UUID(pid_str))
                    .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc())
                )).scalars().first()
                if home is None:
                    continue
                existing = (await session.execute(
                    select(_Ship).where(_Ship.planet_id == home.id, _Ship.fleet_id.is_(None), _Ship.type == reward_ship)
                )).scalars().first()
                if existing:
                    existing.count += reward_count
                else:
                    session.add(_Ship(planet_id=home.id, fleet_id=None, type=reward_ship, count=reward_count))
                await create_system_transmission(
                    session, player_id=uuid.UUID(pid_str),
                    subject="⚙️ Utopia-Werft: Prototyp erhalten!",
                    body=f"Du bist Platz {rank} im Wettrennen um die Utopia-Werft! Als Belohnung wurden "
                         f"{reward_count}× {reward_ship} in deiner Werft gebaut. Ein legendärer Prototyp.",
                    ttype="big_moment", publish=False,
                )
        # Flüchtlinge: bei Ablauf greifen die Verfolger jeden Helfer an.
        if ev.event_type == "refugee_flotilla":
            from app.events.personal import spawn_pursuer_attack
            ratio = float(data.get("pursuer_power_vs_player", 0.5))
            for pid_str in (data.get("helpers") or []):
                try:
                    await spawn_pursuer_attack(session, uuid.UUID(pid_str), ev.galaxy, ev.system, ratio)
                except Exception:  # noqa: BLE001
                    log.exception("Verfolger-Welle fehlgeschlagen für %s", pid_str)
        # Schwarzmarkt: NPC + Zelle freigeben.
        if ev.event_type == "black_market" and data.get("npc_id"):
            from app.universe.service import vacate_cell
            npc = await session.get(NpcEmpire, uuid.UUID(data["npc_id"]))
            if npc is not None:
                if ev.galaxy is not None:
                    await vacate_cell(session, ev.galaxy, ev.system, ev.position)
                await session.delete(npc)
        ev.status = "expired"
        await session.commit()
    log.info("Event abgelaufen + aufgeräumt: %s (%s)", ev.event_type, event_id)


async def try_anomaly_probe(session: AsyncSession, player_id, g: int, s: int, p: int) -> str | None:
    """Wird beim Spionage-Resolve aufgerufen: liegt am Ziel eine aktive Anomalie, gewährt die
    Sonde dem Spieler einen temporären Forschungstempo-Buff (mit kleinem Beschädigungs-Risiko).
    Liefert die Ergebnis-Meldung oder None (keine Anomalie hier)."""
    ev = (await session.execute(
        select(CosmicEvent).where(
            CosmicEvent.event_type == "cosmic_anomaly", CosmicEvent.status == "active",
            CosmicEvent.galaxy == g, CosmicEvent.system == s, CosmicEvent.position == p,
            CosmicEvent.expires_at > _now(),
        )
    )).scalar_one_or_none()
    if ev is None:
        return None
    data = ev.data or {}
    buff = float(data.get("research_speed_buff", 1.25))
    hours = float(data.get("buff_hours", 12))
    damaged = random.random() < float(data.get("damage_chance", 0.15))
    await apply_buff(
        session, buff_type="research_speed", magnitude=buff, duration_hours=hours,
        scope="player", player_id=player_id, source_event_id=ev.id,
    )
    pct = int((buff - 1.0) * 100)
    if damaged:
        return (f"Deine Sonde durchquerte die Anomalie bei {g}:{s}:{p}, wurde dabei leicht "
                f"beschädigt, lieferte aber seltene Daten: +{pct}% Forschungstempo für {int(hours)} h!")
    return (f"Deine Sonde hat die kosmische Anomalie bei {g}:{s}:{p} vermessen: "
            f"+{pct}% Forschungstempo für {int(hours)} h!")


async def active_map_events(session: AsyncSession) -> list[CosmicEvent]:
    return list((await session.execute(
        select(CosmicEvent).where(
            CosmicEvent.status == "active", CosmicEvent.expires_at > _now(),
            CosmicEvent.galaxy.is_not(None),
        )
    )).scalars().all())


# -- Spawner-Tick ------------------------------------------------------------

_EVENT_LABELS = {
    "wandering_comet": "Wandernder Komet",
    "cosmic_anomaly": "Kosmische Anomalie",
    "solar_storm": "Sonnensturm",
    "black_market": "Schwarzmarkt",
    "utopia_shipyard": "Utopia-Werft",
}


async def _notify_world_event(session: AsyncSession, ev) -> None:
    """Benachrichtigt Spieler mit einem Planeten in der Galaxie des Welt-Events (Toast + Postfach),
    damit globale Events wahrgenommen werden — vorher nur stilles Galaxie-Karten-Overlay."""
    from app.messaging.service import create_system_transmission
    label = _EVENT_LABELS.get(ev.event_type, ev.event_type)
    coords = f"{ev.galaxy}:{ev.system}" + (f":{ev.position}" if ev.position else "")
    pids = set((await session.execute(
        select(Planet.player_id).where(Planet.galaxy == ev.galaxy)
    )).scalars().all())
    for pid in pids:
        await create_system_transmission(
            session, player_id=pid,
            subject=f"🌌 Globales Event: {label}",
            body=(f"In deiner Galaxie ist ein Ereignis aufgetaucht: {label} bei {coords}. "
                  f"Es ist zeitlich begrenzt — hinfliegen kann sich lohnen."),
            ttype="system",
        )


async def events_tick() -> None:
    """Periodischer Tick: würfelt neue Welt-Events (selten) + persönliche Events."""
    bal = get_balance()
    ecfg = bal.events
    if not ecfg:
        return
    async with session_scope() as session:
        active = await active_map_events(session)
        max_map = int(ecfg.get("max_active_map_events", 6))
        gcfg = ecfg.get("global", {})
        for etype in MAP_EVENT_TYPES:
            if len(active) >= max_map:
                break
            cfg = gcfg.get(etype, {})
            if not cfg.get("enabled", False):
                continue
            if random.random() < float(cfg.get("spawn_chance", 0.0)):
                spawner = _SPAWNERS.get(etype)
                if spawner is None:
                    continue
                ev = await spawner(session, bal, cfg)
                if ev is not None:
                    schedule_at(ev.expires_at, resolve_event, str(ev.id), job_id=f"event:{ev.id}")
                    active.append(ev)
                    log.info("Event gespawnt: %s @ %s:%s:%s", etype, ev.galaxy, ev.system, ev.position)
                    await _notify_world_event(session, ev)
        await session.commit()

    # Persönliche Events getrennt (eigener Session-Scope je Spieler).
    from app.events.personal import roll_personal_events
    await roll_personal_events()
