"""Persönliche Events — triggern zufällig pro Spieler (offline-sicher).

- Piraten-Razzia: skalierter NPC-Angriff auf einen Spielerplaneten (Vorwarnzeit, Verteidigung
  kämpft automatisch — kein Online-Zwang). Sieg → Trümmerfeld.
- Minen-Streik: Produktions-Debuff (Buff) + Postfach-Entscheidung (Deuterium zahlen ODER Gewalt).
  Offline → Default = aussitzen (Debuff läuft ab).
- Wissenschaftlicher Durchbruch: sofortiges Geschenk (Forschungsstufe ODER Upgrade-Rabatt).
"""
from __future__ import annotations

import datetime as dt
import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.buffs import apply_buff
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import (
    CosmicEvent,
    Defense,
    NpcAttack,
    NpcEmpire,
    Planet,
    Player,
    Research,
    Ship,
)
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.events.personal")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def _eligible_players(session: AsyncSession, min_score: int) -> list[tuple[Player, Planet]]:
    """Spieler (nicht geschützt, nicht Urlaub, Score >= min) mit einem zufälligen eigenen Planeten."""
    now = _now()
    players = (await session.execute(select(Player))).scalars().all()
    out: list[tuple[Player, Planet]] = []
    for p in players:
        if p.is_protected or int(p.score or 0) < min_score:
            continue
        vac = p.vacation_until
        if vac is not None:
            if vac.tzinfo is None:
                vac = vac.replace(tzinfo=dt.timezone.utc)
            if vac > now:
                continue
        planets = (await session.execute(
            select(Planet).where(Planet.player_id == p.id, Planet.planet_type != "moon")
        )).scalars().all()
        if planets:
            out.append((p, random.choice(planets)))
    return out


# -- Piraten-Razzia ----------------------------------------------------------

def _ship_attack(catalog: dict, t: str) -> float:
    return float(catalog.get(t, {}).get("attack", 0) or 0)


async def _defender_power(session: AsyncSession, planet: Planet, bal) -> float:
    """Grobe Verteidigungs-Stärke (Defensivanlagen + Garnison-Schiffe) zur Skalierung."""
    power = 0.0
    defs = (await session.execute(
        select(Defense).where(Defense.planet_id == planet.id)
    )).scalars().all()
    for d in defs:
        power += _ship_attack(bal.defenses, d.type) * d.count
    ships = (await session.execute(
        select(Ship).where(Ship.planet_id == planet.id, Ship.fleet_id.is_(None))
    )).scalars().all()
    for s in ships:
        power += _ship_attack(bal.ships, s.type) * s.count
    return power


async def trigger_pirate_raid(session: AsyncSession, player: Player, planet: Planet, cfg: dict) -> bool:
    bal = get_balance()
    # Angreifer-Identität: ein beliebiges Nicht-Handelszentrum-NPC (FK-Pflicht).
    npc = (await session.execute(
        select(NpcEmpire).where(NpcEmpire.behavior_profile != "trade_center").limit(1)
    )).scalars().first()
    if npc is None:
        return False
    power_ratio = float(cfg.get("power_vs_player", 0.45))
    budget = power_ratio * max(await _defender_power(session, planet, bal), 50.0)
    roster = ["light_fighter", "heavy_fighter", "cruiser"]
    roster = [t for t in roster if t in bal.ships]
    per = budget / max(1, len(roster))
    fleet: dict[str, int] = {}
    for t in roster:
        n = int(per // max(1.0, _ship_attack(bal.ships, t)))
        if n > 0:
            fleet[t] = n
    if not fleet:
        fleet = {roster[0]: 3} if roster else {"light_fighter": 3}

    warn_min = float(cfg.get("warning_minutes", 150))
    arrive = _now() + dt.timedelta(minutes=warn_min)
    atk = NpcAttack(
        npc_id=npc.id,
        target_player_id=player.id,
        target_planet_id=planet.id,
        target_galaxy=planet.galaxy, target_system=planet.system, target_position=planet.position,
        fleet=fleet,
        status="incoming",
        arrive_at=arrive,
    )
    session.add(atk)
    await session.flush()
    schedule_at(arrive, _resolve_pirate_attack, str(atk.id), job_id=f"npc-attack:{atk.id}")
    total = sum(fleet.values())
    await create_system_transmission(
        session, player_id=player.id,
        subject=f"☠️ Piraten-Razzia im Anflug ({planet.galaxy}:{planet.system}:{planet.position})",
        body=f"Ein Piratenclan hat einen Funkspruch abgefangen und schickt {total} Plünderer-Schiffe "
             f"zu deinem Planeten {planet.name}. Ankunft in ~{int(warn_min)} Minuten. Die Flotte ist "
             f"deinen Verteidigungsanlagen angepasst — wehr sie ab, und ihr Trümmerfeld lohnt sich! "
             f"(Verteidigung kämpft automatisch, auch wenn du offline bist.)",
        ttype="system",
    )
    log.info("Piraten-Razzia: player=%s planet=%s fleet=%s", player.id, planet.id, fleet)
    return True


async def _resolve_pirate_attack(attack_id: str) -> None:
    """Wrapper auf die bestehende NPC-Angriffs-Auflösung (Kampf, Trümmer, Bericht)."""
    from app.npc.attack import resolve_npc_attack
    await resolve_npc_attack(attack_id)


# -- Minen-Streik ------------------------------------------------------------

async def trigger_mine_strike(session: AsyncSession, player: Player, planet: Planet, cfg: dict) -> bool:
    mult = float(cfg.get("production_mult", 0.5))
    hours = float(cfg.get("duration_hours", 12))
    bribe = int(cfg.get("bribe_deuterium", 30000))
    timeout_h = float(cfg.get("decision_timeout_hours", hours))
    ev = CosmicEvent(
        event_type="mine_strike", scope="personal", galaxy=planet.galaxy, system=planet.system,
        position=planet.position, player_id=player.id,
        data={"planet_id": str(planet.id), "production_mult": mult,
              "bribe_deuterium": bribe, "morale_penalty": int(cfg.get("force_morale_penalty", 10))},
        expires_at=_now() + dt.timedelta(hours=hours),
    )
    session.add(ev)
    await session.flush()
    await apply_buff(
        session, buff_type="production", magnitude=mult, duration_hours=hours,
        scope="planet", planet_id=planet.id, source_event_id=ev.id,
    )
    # Offline-sichere Entscheidung übers Postfach (Default: aussitzen).
    from app.events.decisions import create_event_decision
    await create_event_decision(
        session, player_id=player.id, event=ev,
        subject=f"⛏️ Streik in den Minen ({planet.name})",
        body=f"Unruhen in den Minen von {planet.name}: Die Metall-/Kristallproduktion ist für "
             f"{int(hours)} h um {int((1-mult)*100)}% eingebrochen. Du kannst den Streik sofort "
             f"beenden: entweder {bribe:,} Deuterium zahlen (Bestechung), oder ihn gewaltsam "
             f"niederschlagen (Crew-Moral sinkt). Tust du nichts, läuft der Streik aus.".replace(",", "."),
        choices=["bribe", "force", "wait"],
        default_choice="wait",
        timeout_hours=timeout_h,
    )
    log.info("Minen-Streik: player=%s planet=%s", player.id, planet.id)
    return True


# -- Wissenschaftlicher Durchbruch -------------------------------------------

async def trigger_breakthrough(session: AsyncSession, player: Player, planet: Planet, cfg: dict) -> bool:
    techs = list(get_balance().techs.keys())
    owned = (await session.execute(
        select(Research).where(Research.player_id == player.id)
    )).scalars().all()
    by_type = {r.type: r for r in owned}
    # Bevorzugt eine bereits begonnene Forschung, sonst eine zufällige Tech.
    candidates = [t for t in techs if t in by_type and by_type[t].finishes_at is None]
    if not candidates:
        candidates = techs
    if not candidates:
        return False
    tech = random.choice(candidates)
    free_level = random.random() < float(cfg.get("free_level_chance", 0.5))
    if free_level:
        row = by_type.get(tech)
        if row is None:
            row = Research(player_id=player.id, type=tech, level=0)
            session.add(row)
            await session.flush()
        row.level += 1
        gift = f"Stufe {row.level} der Technologie wurde dir GESCHENKT."
    else:
        # Rabatt-Buff: nächste Forschung doppelt so schnell (research_speed-Buff).
        await apply_buff(
            session, buff_type="research_speed", magnitude=2.0, duration_hours=48,
            scope="player", player_id=player.id,
        )
        gift = "Deine nächste Forschung läuft dank des Durchbruchs doppelt so schnell (48 h)."
    await create_system_transmission(
        session, player_id=player.id,
        subject="💡 Wissenschaftlicher Durchbruch!",
        body=f"Deine Forscher hatten im Labor eine unerwartete Entdeckung bei '{tech}'. {gift}",
        ttype="big_moment",
    )
    log.info("Durchbruch: player=%s tech=%s free_level=%s", player.id, tech, free_level)
    return True


# -- Roll-Tick ---------------------------------------------------------------

async def roll_personal_events() -> None:
    bal = get_balance()
    ecfg = bal.events
    pcfg = ecfg.get("personal", {})
    if not pcfg:
        return
    min_score = int(ecfg.get("min_player_score", 50))
    async with session_scope() as session:
        eligible = await _eligible_players(session, min_score)
        for player, planet in eligible:
            # Pro Spieler höchstens EIN persönliches Event je Tick.
            rolls = [
                ("pirate_raid", trigger_pirate_raid),
                ("mine_strike", trigger_mine_strike),
                ("breakthrough", trigger_breakthrough),
            ]
            random.shuffle(rolls)
            for key, fn in rolls:
                c = pcfg.get(key, {})
                if not c.get("enabled", False):
                    continue
                if random.random() < float(c.get("spawn_chance_per_player", 0.0)):
                    try:
                        if await fn(session, player, planet, c):
                            break
                    except Exception:  # noqa: BLE001 — ein Event darf den Tick nicht kippen
                        log.exception("Persönliches Event %s fehlgeschlagen für player=%s", key, player.id)
        await session.commit()
