"""Commander-Logik: Erzeugung, Serialisierung, Span-Berechnung, Training, Moral-Drift.

Konkrete Zahlen stammen aus balance.json (Moral-Baender, Drift, Neglect, Span, Akademie)."""
from __future__ import annotations

import datetime as dt
import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import get_building_levels, get_research_levels
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Commander, Fleet, Planet

log = logging.getLogger("universe.commander")

# Kleine Pools fuer prozedurale Persona-Erzeugung (LLM verfeinert spaeter via persona_init).
_FIRST = ["Mara", "Kellan", "Sora", "Idris", "Vesna", "Tariq", "Lena", "Orin", "Juno", "Cassius"]
_LAST = ["Voss", "Reyes", "Okonkwo", "Halberd", "Nakamura", "Stride", "Vance", "Calder", "Mireles", "Dorne"]
_BACKGROUNDS = [
    "Aus den Asteroidenguerteln aufgestiegen, haerter als das Erz das sie schuerften.",
    "Akademie-Jahrgangsbeste/r, ungeduldig mit Buerokratie.",
    "Ehemalige/r Schmuggler/in mit losem Verhaeltnis zu Vorschriften.",
    "Veteran/in dreier Grenzkonflikte, wortkarg und praezise.",
]
_VOICES = ["nuechtern-militaerisch", "trocken-sarkastisch", "feurig-pathetisch", "ruhig-vaeterlich"]


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def generate_persona(rng: random.Random) -> tuple[str, dict, list[str]]:
    """Erzeugt (name, persona, traits)."""
    bal = get_balance()
    trait_keys = list(bal.commander["personality_traits"].keys())
    name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
    persona = {
        "background": rng.choice(_BACKGROUNDS),
        "voice": rng.choice(_VOICES),
    }
    traits = rng.sample(trait_keys, k=rng.randint(1, 2))
    return name, persona, traits


async def create_commander(
    session: AsyncSession,
    player_id: uuid.UUID,
    *,
    rank_key: str = "cadet",
    specialization: str = "combat",
    status: str = "active",
    training_finishes_at: dt.datetime | None = None,
    rng: random.Random | None = None,
) -> Commander:
    """Legt einen Commander an und enqueued einen persona_init-Job (Banken-Aufbau)."""
    bal = get_balance()
    rng = rng or random.Random()
    name, persona, traits = generate_persona(rng)
    rank = bal.rank_by_key(rank_key)
    morale_start = bal.commander["morale"]["start"]

    commander = Commander(
        player_id=player_id,
        name=name,
        persona=persona,
        traits=traits,
        specialization=specialization,
        rank=rank_key,
        xp=rank["xp_threshold"],
        morale=morale_start,
        loyalty=100,
        span_capacity=rank["span_contrib"],
        status=status,
        training_finishes_at=training_finishes_at,
        last_active_at=_now(),
    )
    session.add(commander)
    await session.flush()

    # persona_init-Job: ai-worker erzeugt Persona-Profil + Erst-Banken (events.md).
    await event_bus.enqueue_job({
        "job_type": "persona_init",
        "commander_id": str(commander.id),
        "player_id": str(player_id),
        "context": {"name": name, "traits": traits, "voice": persona["voice"]},
    })
    return commander


async def assigned_fleet_id(session: AsyncSession, commander_id: uuid.UUID) -> uuid.UUID | None:
    fleet = (await session.execute(
        select(Fleet).where(
            Fleet.commander_id == commander_id,
            Fleet.status.in_(("flying", "arrived", "returning")),
        )
    )).scalars().first()
    return fleet.id if fleet else None


async def commander_to_dict(session: AsyncSession, c: Commander) -> dict:
    bal = get_balance()
    band = bal.morale_band(c.morale)
    return {
        "id": c.id,
        "name": c.name,
        "persona": c.persona or {},
        "traits": c.traits or [],
        "specialization": c.specialization,
        "rank": c.rank,
        "xp": c.xp,
        "morale": c.morale,
        "loyalty": c.loyalty,
        "span_capacity": c.span_capacity,
        "status": c.status,
        "morale_band": {"label": band["label"], "combat_mod": band["combat_mod"]},
        "assigned_fleet_id": await assigned_fleet_id(session, c.id),
        "training_finishes_at": c.training_finishes_at,
    }


async def compute_span(session: AsyncSession, player_id: uuid.UUID) -> dict:
    """Span-of-Control: Basis + Kommandozentrale (abnehmend) + Kommandodoktrin."""
    bal = get_balance()
    span_cfg = bal.commander["span"]
    base = span_cfg["player_base"]

    # Kommandozentrale: Bonus-Array ueber alle Planeten (hoechste Stufe zaehlt).
    cc_level = 0
    planets = (await session.execute(
        select(Planet).where(Planet.player_id == player_id)
    )).scalars().all()
    for p in planets:
        levels = await get_building_levels(session, p.id)
        cc_level = max(cc_level, levels.get("command_center", 0))
    cc_bonus_arr = span_cfg["command_center_bonus"]
    from_cc = sum(cc_bonus_arr[:cc_level]) if cc_level > 0 else 0

    # Kommandodoktrin (Tech).
    research = await get_research_levels(session, player_id)
    from_doctrine = span_cfg["command_doctrine_bonus_per_level"] * research.get("command_doctrine", 0)

    total = base + from_cc + from_doctrine

    # In Benutzung: aktive Commander, die eine Flotte fuehren.
    in_use_rows = (await session.execute(
        select(Fleet.commander_id).where(
            Fleet.player_id == player_id,
            Fleet.commander_id.is_not(None),
            Fleet.status.in_(("flying", "arrived", "returning")),
        ).distinct()
    )).scalars().all()
    in_use = len([x for x in in_use_rows if x is not None])

    return {
        "base": base,
        "from_command_center": from_cc,
        "from_doctrine": from_doctrine,
        "total": total,
        "in_use": in_use,
    }


async def start_training(session: AsyncSession, planet: Planet) -> Commander:
    """Bildet einen neuen Commander an der Kommando-Akademie aus."""
    bal = get_balance()
    levels = await get_building_levels(session, planet.id)
    academy = levels.get("command_academy", 0)
    if academy < 1:
        raise RuntimeError("Kommando-Akademie erforderlich")

    # Gleichzeitige Ausbildungsplaetze = academy_lvl (concurrent_slots_per_level).
    slots = academy * bal.commander["academy"]["concurrent_slots_per_level"]
    in_training = (await session.execute(
        select(Commander).where(
            Commander.player_id == planet.player_id, Commander.status == "training"
        )
    )).scalars().all()
    if len(in_training) >= slots:
        raise RuntimeError("Keine freien Ausbildungsplaetze")

    base_secs = bal.commander["academy"]["base_training_seconds"]
    secs = max(1, int(base_secs / academy))
    finish = _now() + dt.timedelta(seconds=secs)
    # Hoehere Akademie -> hoeherer Start-Rang (Slice: ab Stufe 3 Offizier).
    rank_key = "officer" if academy >= 3 else "cadet"

    commander = await create_commander(
        session, planet.player_id,
        rank_key=rank_key, specialization="combat",
        status="training", training_finishes_at=finish,
    )
    from app.platform.scheduler import schedule_at
    schedule_at(finish, complete_training, str(commander.id), job_id=f"train:{commander.id}")
    return commander


async def complete_training(commander_id: str) -> None:
    async with session_scope() as session:
        c = await session.get(Commander, uuid.UUID(commander_id))
        if c is None or c.status != "training":
            return
        c.status = "active"
        c.training_finishes_at = None
        player_id = c.player_id
        name = c.name
        await session.commit()
    await event_bus.publish_ws(player_id, {
        "type": "transmission",
        "transmission": {
            "type": "system",
            "subject": "Ausbildung abgeschlossen",
            "body": f"{name} hat die Akademie abgeschlossen und steht bereit.",
        },
    })
    log.info("Commander %s ausgebildet", commander_id)


async def morale_drift_tick() -> None:
    """Stuendlicher Job: Moral driftet zum Basis-Ziel; Neglect-Decay bei Untaetigkeit."""
    bal = get_balance()
    m = bal.commander["morale"]
    target = m["base_target"]
    drift_rate = m["drift_rate_per_tick"]
    neglect = m["neglect"]
    idle_seconds = neglect["idle_days_before_decay"] * 86400
    decay_per_hour = neglect["decay_per_day"] / 24.0
    traits_cfg = bal.commander["personality_traits"]
    now = _now()

    async with session_scope() as session:
        commanders = (await session.execute(
            select(Commander).where(Commander.status.in_(("active", "wounded")))
        )).scalars().all()
        for c in commanders:
            decay_mult = 1.0
            for trait in (c.traits or []):
                decay_mult *= traits_cfg.get(trait, {}).get("morale_decay_mult", 1.0)

            morale = float(c.morale)
            # Drift zum Zielwert.
            morale += drift_rate * (target - morale)
            # Neglect-Decay.
            last = c.last_active_at or now
            if last.tzinfo is None:
                last = last.replace(tzinfo=dt.timezone.utc)
            if (now - last).total_seconds() > idle_seconds:
                morale -= decay_per_hour * decay_mult
            c.morale = max(0, min(100, int(round(morale))))
        await session.commit()
    log.debug("Moral-Drift-Tick fertig (%d Commander)", len(commanders))
