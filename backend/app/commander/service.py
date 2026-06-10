"""Commander-Logik: Erzeugung, Serialisierung, Span-Berechnung, Training, Moral-Drift.

Konkrete Zahlen stammen aus balance.json (Moral-Baender, Drift, Neglect, Span, Akademie)."""
from __future__ import annotations

import datetime as dt
import logging
import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commander.bonuses import base_bonuses
from app.economy.service import get_building_levels, get_research_levels, spend_resources
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Commander, Fleet, Planet, Transmission

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


def roll_grade(weights: dict[str, float], rng: random.Random) -> str:
    """Wuerfelt eine Gueteklasse gewichtet (Gewichte werden normalisiert, Summe egal).

    ``rng`` ist ein geseedeter random.Random — so ist der Wurf reproduzierbar."""
    items = [(g, float(w)) for g, w in weights.items() if float(w) > 0]
    if not items:
        return "C"
    total = sum(w for _, w in items)
    r = rng.random() * total
    acc = 0.0
    for grade, w in items:
        acc += w
        if r <= acc:
            return grade
    return items[-1][0]


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
    focus: str | None = None,
    grade: str = "C",
    status: str = "active",
    training_finishes_at: dt.datetime | None = None,
    rng: random.Random | None = None,
) -> Commander:
    """Legt einen Commander an und enqueued einen persona_init-Job (Banken-Aufbau).

    ``focus`` (Schiffsklasse) kann explizit gewaehlt werden; sonst wird sie
    spezialisierungstypisch (mit etwas Varianz) gezogen. ``grade`` (Gueteklasse
    F..SSS) ist das angeborene Potenzial (Default C = Baseline)."""
    bal = get_balance()
    rng = rng or random.Random()
    name, persona, traits = generate_persona(rng)
    # Fokus-Schiffsklasse: explizit gewaehlt, sonst meist die Spezialisierungs-Favoritin
    # (mit etwas Varianz), damit Commander unterschiedliche Profile haben.
    cb = bal.commander["combat_bonuses"]
    classes = [k for k in bal.commander["ship_classes"].keys() if not k.startswith("_")]
    favored = cb["profiles"].get(specialization, cb["profiles"]["combat"])["favored_class"]
    if focus in classes:
        persona["focus"] = focus
    else:
        persona["focus"] = favored if rng.random() < 0.6 else rng.choice(classes)
    rank = bal.rank_by_key(rank_key)
    morale_start = bal.commander["morale"]["start"]
    # Grad-Potenz skaliert auch die Span-of-Control-Decke (Doku 05a): hoeherer Grad
    # fuehrt mehr (C = 1.0 Baseline bleibt unveraendert).
    grade_key = grade if grade in bal.grades["potency"] else "C"
    span = max(1, round(rank["span_contrib"] * bal.grade_potency(grade_key)))

    commander = Commander(
        player_id=player_id,
        name=name,
        persona=persona,
        traits=traits,
        specialization=specialization,
        rank=rank_key,
        grade=grade_key,
        xp=rank["xp_threshold"],
        morale=morale_start,
        loyalty=100,
        span_capacity=span,
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
    focus = (c.persona or {}).get("focus")
    grade = c.grade or "C"
    bonuses = base_bonuses(c.specialization, c.rank, c.traits or [], focus, grade)
    return {
        "id": c.id,
        "name": c.name,
        "persona": c.persona or {},
        "traits": c.traits or [],
        "specialization": c.specialization,
        "rank": c.rank,
        "grade": grade,
        "xp": c.xp,
        "morale": c.morale,
        "loyalty": c.loyalty,
        "unrest": round(float(c.unrest or 0.0)),
        "skill_points": int(c.skill_points or 0),
        "abilities": c.abilities or [],
        "arm_slots": arm_slots(c.rank, get_balance()),
        "span_capacity": c.span_capacity,
        "status": c.status,
        "morale_band": {"label": band["label"], "combat_mod": band["combat_mod"]},
        "focus": focus,
        "bonuses": bonuses,
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


async def start_training(
    session: AsyncSession,
    planet: Planet,
    specialization: str | None = None,
    focus: str | None = None,
    tier: str | None = None,
) -> Commander:
    """Bildet einen neuen Commander an der Kommando-Akademie aus.

    ``specialization`` und ``focus`` (Schiffsklasse) sind optional waehlbar — so kann
    der Spieler gezielt z. B. Defensive- oder Tempo-Commander ausbilden. ``tier``
    (Investitions-Stufe) bestimmt Kosten und Grad-Wahrscheinlichkeiten (Doku 05a)."""
    bal = get_balance()
    # Eingaben validieren (sonst Default).
    valid_specs = bal.commander["specializations"]
    spec = specialization if specialization in valid_specs else "combat"
    valid_classes = [k for k in bal.commander["ship_classes"].keys() if not k.startswith("_")]
    focus_class = focus if focus in valid_classes else None  # None -> auto in create_commander
    tier_cfg = bal.training_tier(tier or "standard")

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

    # Investitions-Kosten (Basis x Tier-Multiplikator) vom Heimatplaneten abziehen.
    grades_cfg = bal.grades
    base_cost = grades_cfg["training_base_cost"]
    mult = float(tier_cfg.get("cost_mult", 1))
    cost = {k: float(v) * mult for k, v in base_cost.items()}
    if not await spend_resources(session, planet, cost):
        raise RuntimeError("Nicht genug Ressourcen")

    # Grad gewichtet + geseedet wuerfeln (reproduzierbar, kein ungeseedetes random).
    seed_src = f"{planet.player_id}:{_now().timestamp()}:{len(in_training)}:{tier_cfg['key']}"
    rng = random.Random(seed_src)
    grade = roll_grade(tier_cfg["weights"], rng)

    base_secs = bal.commander["academy"]["base_training_seconds"]
    secs = max(1, int(base_secs / academy))
    finish = _now() + dt.timedelta(seconds=secs)
    # Hoehere Akademie -> hoeherer Start-Rang (Slice: ab Stufe 3 Offizier).
    rank_key = "officer" if academy >= 3 else "cadet"

    commander = await create_commander(
        session, planet.player_id,
        rank_key=rank_key, specialization=spec, focus=focus_class, grade=grade,
        status="training", training_finishes_at=finish, rng=rng,
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


def _rank_index(rank: str, bal) -> int:
    order = [r["key"] for r in bal.commander["ranks"]]
    return order.index(rank) if rank in order else 0


def ability_def(key: str, bal) -> dict | None:
    return bal.commander.get("ability_catalog", {}).get(key)


def arm_slots(rank: str, bal) -> int:
    return int(bal.commander["ability_progression"]["arm_slots"].get(rank, 1))


def commander_ability_level(commander, key: str) -> int:
    for a in (commander.abilities or []):
        if a.get("key") == key:
            return int(a.get("level", 0))
    return 0


def effective_ability(commander, key: str, bal, now: dt.datetime) -> dict | None:
    """Liefert {kind, magnitude} einer erlernten, einsatzbereiten Faehigkeit (Cooldown frei),
    sonst None. magnitude = per_level * Stufe."""
    ab = ability_def(key, bal)
    lvl = commander_ability_level(commander, key)
    if not ab or lvl <= 0:
        return None
    cd = (commander.ability_cooldowns or {}).get(key)
    if cd:
        try:
            t = dt.datetime.fromisoformat(cd)
        except ValueError:
            t = None
        if t is not None:
            if t.tzinfo is None:
                t = t.replace(tzinfo=dt.timezone.utc)
            if (now - t).total_seconds() < float(ab["cooldown_seconds"]):
                return None
    return {"key": key, "kind": ab["kind"], "magnitude": float(ab["per_level"]) * lvl, "label": ab["label"]}


def mark_ability_used(commander, key: str, now: dt.datetime) -> None:
    cds = dict(commander.ability_cooldowns or {})
    cds[key] = now.isoformat()
    commander.ability_cooldowns = cds  # neues dict -> JSONB-Change-Tracking


def governor_production_mult(commander, bal) -> float:
    """Produktions-Multiplikator eines Planeten-Gouverneurs (>=1.0).
    = 1 + peak_pct[rank] * (morale/100) * spec_mult. Nur fuer aktive Kommandeure."""
    if commander is None or commander.status != "active":
        return 1.0
    peak = float(bal.commander["economy_bonus"]["peak_pct_by_rank"].get(commander.rank, 0.0))
    smult = float(bal.commander.get("governor", {}).get("spec_mult", {}).get(commander.specialization, 1.0))
    return 1.0 + peak * (float(commander.morale) / 100.0) * smult


def _pick_demand(traits: list, morale: int) -> tuple[str, str, str]:
    """Waehlt eine trait-gefaerbte Forderung -> (kind, subject_suffix, body)."""
    t = set(traits or [])
    if "ambitious" in t:
        return ("promotion", "fordert Beförderung",
                "verlangt ein eigenes Kommando bzw. eine Beförderung — sonst schwindet seine Treue.")
    if "greedy" in t:
        return ("loot_share", "fordert größeren Beuteanteil",
                "verlangt einen größeren Anteil an der Beute künftiger Feldzüge.")
    if "aggressive" in t or "hot_tempered" in t:
        return ("action", "drängt auf einen Einsatz",
                "will endlich in den Kampf geführt werden — Untätigkeit zehrt an ihm.")
    if morale < 50:
        return ("shore_leave", "fordert Landgang",
                "ist erschöpft und verlangt Landurlaub im Heimathafen.")
    return ("recognition", "fordert Anerkennung",
            "fühlt sich übergangen und verlangt ein Zeichen der Anerkennung.")


def commander_unrest_gain_per_hour(c: Commander, sat: dict, potency: dict) -> float:
    """Reiner Unmut-Stundenzuwachs (ohne Idle) = base/24 * rank_mult * grade_potency * trait_mult."""
    gain = float(sat["base_gain_per_day"]) / 24.0
    gain *= float(sat["rank_mult"].get(c.rank, 1.0))
    gain *= float(potency.get(c.grade, 1.0))
    tmult = 1.0
    for tr in (c.traits or []):
        tmult *= float(sat["trait_mult"].get(tr, 1.0))
    return gain * tmult


async def morale_drift_tick() -> None:
    """Stuendlicher Job: Moral driftet zum Basis-Ziel; Neglect-Decay bei Untaetigkeit;
    Unmut waechst (staerker je staerker der Kommandeur) und erzeugt bei Schwelle eine
    trait-gefaerbte Forderung (Zufriedenheits-Oekonomie / natuerlicher Overkill)."""
    bal = get_balance()
    m = bal.commander["morale"]
    target = m["base_target"]
    drift_rate = m["drift_rate_per_tick"]
    neglect = m["neglect"]
    idle_seconds = neglect["idle_days_before_decay"] * 86400
    decay_per_hour = neglect["decay_per_day"] / 24.0
    traits_cfg = bal.commander["personality_traits"]
    sat = bal.commander["satisfaction"]
    potency = bal.commander["grades"]["potency"]
    threshold = float(sat["demand_threshold"])
    cooldown = dt.timedelta(hours=float(sat["post_demand_cooldown_hours"]))
    defect_threshold = float(sat.get("defect_threshold", 15))
    defect_per_hour = float(sat.get("defect_chance_per_day", 0.25)) / 24.0
    # Forschungs-Skalare (Kommando/Crew-Zweig): Moral-Ziel/Neglect (crew_psychology),
    # Moral-Erholung (logistics_tech), Unmut-Daempfung (leadership_doctrine).
    reff = bal.data["research"].get("effects", {})
    cp_target = float(reff.get("crew_psychology_target_per_level", 0))
    cp_decay_red = float(reff.get("crew_psychology_decay_reduction_per_level", 0))
    lg_regen = float(reff.get("logistics_morale_regen_per_level", 0))
    ld_unrest_red = float(reff.get("leadership_unrest_reduction_per_level", 0))
    now = _now()

    async with session_scope() as session:
        commanders = (await session.execute(
            select(Commander).where(Commander.status.in_(("active", "wounded")))
        )).scalars().all()
        # Forschung je Spieler (einmal pro Spieler) fuer die Kommando/Crew-Techs.
        from app.economy.service import get_research_levels
        research_by_player: dict = {}
        for pid in {c.player_id for c in commanders}:
            research_by_player[pid] = await get_research_levels(session, pid)
        # Kommandeure mit bereits offener Forderung (eine zur Zeit).
        open_demand = set((await session.execute(
            select(Transmission.commander_id).where(
                Transmission.type == "demand", Transmission.requires_decision.is_(True)
            )
        )).scalars().all())
        # Aktuell einer Flotte zugewiesene Kommandeure (im Einsatz -> kein Ueberlauf).
        assigned = set((await session.execute(
            select(Fleet.commander_id).where(
                Fleet.commander_id.isnot(None),
                Fleet.status.in_(("flying", "arrived", "returning")),
            )
        )).scalars().all())
        # Gouverneure sind im Dienst (kein Ueberlauf) — aber sie sammeln weiter Unmut.
        assigned |= set((await session.execute(
            select(Planet.governor_commander_id).where(Planet.governor_commander_id.isnot(None))
        )).scalars().all())

        # Charisma: charismatische Kommandeure heben das Moral-Ziel ihres Imperiums.
        charisma_bonus: dict = {}
        for c in commanders:
            for tr in (c.traits or []):
                b = traits_cfg.get(tr, {}).get("adjacent_morale_boost", 0.0)
                if b:
                    charisma_bonus[c.player_id] = charisma_bonus.get(c.player_id, 0.0) + b * 100.0

        demands = 0
        defections = 0
        for c in commanders:
            decay_mult = 1.0
            for trait in (c.traits or []):
                decay_mult *= traits_cfg.get(trait, {}).get("morale_decay_mult", 1.0)

            res = research_by_player.get(c.player_id, {})
            cp_lvl = int(res.get("crew_psychology", 0))
            lg_lvl = int(res.get("logistics_tech", 0))
            ld_lvl = int(res.get("leadership_doctrine", 0))

            morale = float(c.morale)
            # crew_psychology hebt das (sustained) Moral-Ziel; logistics_tech beschleunigt die Erholung.
            eff_target = min(100.0, target + charisma_bonus.get(c.player_id, 0.0) + cp_target * cp_lvl)
            eff_drift = drift_rate * (1.0 + lg_regen * lg_lvl)
            morale += eff_drift * (eff_target - morale)
            last = c.last_active_at or now
            if last.tzinfo is None:
                last = last.replace(tzinfo=dt.timezone.utc)
            idle = (now - last).total_seconds() > idle_seconds
            if idle:
                # crew_psychology daempft den Neglect-Verfall (gut betreute Crews halten durch).
                morale -= decay_per_hour * decay_mult * max(0.0, 1.0 - cp_decay_red * cp_lvl)
            c.morale = max(0, min(100, int(round(morale))))

            # -- Unmut akkumulieren (leadership_doctrine daempft den Aufbau) --
            gain = commander_unrest_gain_per_hour(c, sat, potency)
            if idle:
                gain += float(sat["idle_unrest_per_hour"])
            gain *= max(0.0, 1.0 - ld_unrest_red * ld_lvl)
            c.unrest = min(100.0, float(c.unrest or 0.0) + gain)

            # -- Ueberlauf: anhaltend niedrige Treue + untaetig --
            if c.loyalty < defect_threshold and c.id not in assigned and random.random() < defect_per_hour:
                c.status = "defected"
                await create_system_transmission(
                    session,
                    player_id=c.player_id,
                    subject=f"🏴 {c.name} ist übergelaufen",
                    body=f"Kommandeur {c.name} hat aus Illoyalität deinen Dienst verlassen. "
                         f"Pflege die Treue deiner Kommandeure, sonst verlierst du sie.",
                    ttype="system",
                )
                defections += 1
                continue

            # -- Forderung erzeugen (Schwelle + Cooldown + keine offene) --
            if c.unrest < threshold or c.id in open_demand:
                continue
            ld = c.last_demand_at
            if ld is not None:
                if ld.tzinfo is None:
                    ld = ld.replace(tzinfo=dt.timezone.utc)
                if now - ld < cooldown:
                    continue
            kind, suffix, body = _pick_demand(c.traits, c.morale)
            await create_system_transmission(
                session,
                player_id=c.player_id,
                subject=f"⚑ {c.name} {suffix}",
                body=f"Kommandeur {c.name} {body}\n\nErfüllst du die Forderung, steigt seine Treue; "
                     f"ignorierst du sie, sinkt sie — anhaltend niedrige Treue führt zu Meuterei oder Überlauf.",
                ttype="demand",
                commander_id=c.id,
                requires_decision=True,
                decision_payload={"kind": kind, "commander_id": str(c.id)},
            )
            c.last_demand_at = now
            open_demand.add(c.id)
            demands += 1

        await session.commit()
    log.info("Moral/Unmut-Tick: %d Commander, %d neue Forderung(en), %d Ueberlaeufer",
             len(commanders), demands, defections)
