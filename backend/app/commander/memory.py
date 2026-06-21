"""Kommandeure mit Gedaechtnis & Eigenleben (Welle 2, 2026-06-20).

Kommandeure ERINNERN sich an Schlachten/Erlebnisse (``commander_memories``), entwickeln
MEINUNGEN ueber Gegner (``commander_opinions``: Respekt/Verachtung/Furcht), haben
BEZIEHUNGEN untereinander (``commander_relationships``: Rivalitaet/Respekt/Bond) und stauen
KRAENKUNGEN auf (``commander_grievances``), die bei dauerhafter Misshandlung zur MEUTEREI
fuehren.

Architektur wie ``npc/diplomacy.py``: die *reinen* Funktionen (``derive_sentiment``,
``evaluate_opinion``, ``merge_opinion``, ``relationship_delta``, ``grievance_severity``,
``accumulate_grievance``, ``open_grievance_sum``, ``mutiny_decision``) sind DB-/LLM-frei und
direkt testbar — sie ziehen nur die LEITPLANKEN/Schwellen aus ``balance.commander``. Die KI
(ai-worker ``memory_digest`` + kontext-bewusste Funksprueche) formuliert/bewertet emergent.

Alle DB-Hooks sind BEST-EFFORT (try/except) — sie duerfen den Hauptpfad (Kampf, Expedition,
Forderungs-Decide, Moral-Tick) NIE stoeren (Vorbild: ``reward_commander_activity``).
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import (
    Commander,
    CommanderGrievance,
    CommanderMemory,
    CommanderOpinion,
    CommanderRelationship,
)

log = logging.getLogger("universe.commander.memory")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=dt.timezone.utc)


# ============================================================================
# Reine Leitplanken-Logik (DB-/LLM-frei, testbar).
# ============================================================================

def derive_sentiment(event_type: str, mem_cfg: dict | None = None) -> str:
    """Leitet das Gefuehl einer Erinnerung aus dem event_type ab (Fallback 'neutral').

    Die Zuordnung steht in ``balance.commander.memory.sentiment`` (Single Source of Truth)."""
    cfg = mem_cfg if mem_cfg is not None else get_balance().commander["memory"]
    table = cfg.get("sentiment", {})
    val = table.get(event_type)
    return val if val in ("positive", "negative", "neutral") else "neutral"


def evaluate_opinion(
    outcome: str, strength_ratio: float, prior_losses: int, op_cfg: dict
) -> dict | None:
    """Reine Meinungs-Regel: leitet aus EINEM Kampfausgang die Meinungs-Aenderung ab.

    - Sieg ueber einen STARKEN Gegner (strength_ratio >= respect_strength_ratio) -> Respekt.
    - Sieg ueber einen klar SCHWAECHEREN (<= despise_strength_ratio) -> Verachtung.
    - Sieg gegen Ebenbuertige -> keine ausgepraegte Meinung (None).
    - Niederlage: ab ``fear_after_losses`` frueheren Niederlagen gegen DENSELBEN -> echte Furcht
      (groesseres Delta), sonst aufkeimende Furcht/Groll (kleineres Delta).

    ``strength_ratio`` = Gegnerstaerke / eigene Staerke (>1 = Gegner staerker).
    Liefert {opinion_type, delta} oder None."""
    if outcome == "win":
        if strength_ratio >= float(op_cfg["respect_strength_ratio"]):
            return {"opinion_type": "respects", "delta": float(op_cfg["respect_delta"])}
        if strength_ratio <= float(op_cfg["despise_strength_ratio"]):
            return {"opinion_type": "despises", "delta": float(op_cfg["despise_delta"])}
        return None
    if outcome == "loss":
        if prior_losses >= int(op_cfg["fear_after_losses"]):
            return {"opinion_type": "fears", "delta": float(op_cfg["fear_delta"])}
        return {"opinion_type": "fears", "delta": float(op_cfg["grudge_delta"])}
    return None


def merge_opinion(
    cur_type: str | None, cur_strength: float, new_type: str, delta: float, max_strength: float
) -> tuple[str, float]:
    """Verschmilzt eine neue Meinungs-Regung mit der bestehenden Meinung.

    - Gleicher Typ -> Staerke akkumuliert (gedeckelt auf ``max_strength``).
    - Anderer Typ -> die alte Meinung wird um ``delta`` geschwaecht; faellt sie auf <=0,
      KIPPT die Meinung in den neuen Typ (mit ``delta`` als Start-Staerke). So koennen sich
      Meinungen ueber Zeit drehen (Furcht -> Respekt etc.)."""
    if not cur_type or cur_strength <= 0:
        return new_type, min(max_strength, max(0.0, delta))
    if cur_type == new_type:
        return cur_type, min(max_strength, cur_strength + delta)
    remaining = cur_strength - delta
    if remaining <= 0:
        return new_type, min(max_strength, abs(remaining) if remaining < 0 else delta)
    return cur_type, remaining


def is_hated(opinion_type: str | None, strength: float, op_cfg: dict) -> bool:
    """True, wenn eine negative Meinung (Verachtung/Furcht) eine Schwelle ueberschreitet —
    dann gilt der Gegner als 'verhasster Gegner' und faerbt den Funkspruch spuerbar."""
    if opinion_type not in ("despises", "fears"):
        return False
    return strength >= float(op_cfg.get("hated_threshold", 0.5))


def relationship_delta(event: str, rel_cfg: dict) -> tuple[str, float] | None:
    """Reine Beziehungs-Regel: leitet aus einem Beziehungs-Ereignis (rel_type, delta) ab.

    - ``co_battle``        -> Bond (kaempften in derselben Schlacht Seite an Seite).
    - ``shared_enemy``     -> Respekt (schlugen nacheinander denselben Gegner).
    - ``promotion_rivalry``-> Rivalitaet (Konkurrenz um eine Befoerderung)."""
    table = {
        "co_battle": ("bond", float(rel_cfg["co_battle_bond_delta"])),
        "shared_enemy": ("respect", float(rel_cfg["shared_enemy_respect_delta"])),
        "promotion_rivalry": ("rivalry", float(rel_cfg["promotion_rivalry_delta"])),
    }
    return table.get(event)


def grievance_severity(grievance_type: str, gr_cfg: dict) -> int:
    """Severity eines Kraenkungs-Vorfalls aus balance (Fallback 1)."""
    return int(gr_cfg.get("severity", {}).get(grievance_type, 1))


def accumulate_grievance(
    cur_severity: int, cur_count: int, add_severity: int, max_severity: int
) -> tuple[int, int]:
    """Akkumuliert einen weiteren Vorfall derselben Kraenkung (Severity gedeckelt, Count++)."""
    return min(max_severity, cur_severity + add_severity), cur_count + 1


def open_grievance_sum(
    grievances: list[tuple[int, dt.datetime, dt.datetime | None]],
    now: dt.datetime,
    decay_days: int,
) -> int:
    """Summe der Severities OFFENER (resolved_at IS NULL) und NICHT verjaehrter Kraenkungen.

    ``grievances`` = Liste von (severity, created_at, resolved_at). Aeltere als ``decay_days``
    zaehlen nicht mehr (Gelegenheits-Spieler werden nicht ewig bestraft)."""
    cutoff = now - dt.timedelta(days=decay_days)
    total = 0
    for severity, created_at, resolved_at in grievances:
        if resolved_at is not None:
            continue
        created = _aware(created_at)
        if created is not None and created < cutoff:
            continue
        total += int(severity)
    return total


def mutiny_decision(
    *,
    loyalty: float,
    unrest: float,
    grievance_sum: int,
    traits: list[str],
    last_check_at: dt.datetime | None,
    now: dt.datetime,
    rng_value: float,
    mut_cfg: dict,
) -> dict:
    """Reine Meuterei-Entscheidung (Schwellen + Cooldown + trait-gefaerbte Wahrscheinlichkeit).

    Liefert ``{"action": "none"|"warn"|"mutiny", "outcome": None|"defect"|"refuse"}``.

    Eskalations-Logik (GROSSZUEGIG, mit klarer Vorwarnung):
    - Voll meuterei-faehig = loyalty < loyalty_threshold UND unrest >= unrest_threshold UND
      grievance_sum >= grievance_sum_threshold.
    - Nicht voll faehig, aber loyalty < loyalty_threshold UND grievance_sum >= warning_grievance_sum
      -> ``warn`` (telegrafierte Vorwarnung, noch keine Folge).
    - Voll faehig + Cooldown abgelaufen + Wuerfel (``rng_value`` < trait-gefaerbte Chance)
      -> ``mutiny``. Folge = ``defect`` (Desertion) bei loyalty < defect_threshold, sonst
      ``refuse`` (verweigert den naechsten Befehl). Faellt der Wuerfel nicht -> ``warn``."""
    loy_t = float(mut_cfg["loyalty_threshold"])
    unr_t = float(mut_cfg["unrest_threshold"])
    grv_t = int(mut_cfg["grievance_sum_threshold"])
    warn_t = int(mut_cfg["warning_grievance_sum"])

    eligible = loyalty < loy_t and unrest >= unr_t and grievance_sum >= grv_t
    if not eligible:
        if loyalty < loy_t and grievance_sum >= warn_t:
            return {"action": "warn", "outcome": None}
        return {"action": "none", "outcome": None}

    # Cooldown: nach einer Pruefung/Folge erst nach mutiny_cooldown_hours wieder wuerfeln.
    last = _aware(last_check_at)
    cooldown = dt.timedelta(hours=float(mut_cfg["mutiny_cooldown_hours"]))
    if last is not None and (now - last) < cooldown:
        return {"action": "none", "outcome": None}

    chance = float(mut_cfg["mutiny_chance_per_day"]) / 24.0
    trait_mult = 1.0
    for tr in traits or []:
        trait_mult *= float(mut_cfg.get("trait_mult", {}).get(tr, 1.0))
    chance *= trait_mult

    if rng_value < chance:
        outcome = "defect" if loyalty < float(mut_cfg["defect_threshold"]) else "refuse"
        return {"action": "mutiny", "outcome": outcome}
    return {"action": "warn", "outcome": None}


# ============================================================================
# DB-Helfer (best-effort) — schreiben Erinnerungen/Meinungen/Beziehungen/Kraenkungen.
# ============================================================================

async def record_memory(
    session: AsyncSession,
    commander_id: uuid.UUID,
    event_type: str,
    context: dict,
    *,
    sentiment: str | None = None,
) -> None:
    """Schreibt EINE Erinnerung (sentiment wird abgeleitet, wenn nicht gegeben)."""
    sent = sentiment or derive_sentiment(event_type)
    session.add(CommanderMemory(
        commander_id=commander_id,
        event_type=event_type,
        context=context or {},
        sentiment=sent,
    ))


async def _prior_losses(session: AsyncSession, commander_id: uuid.UUID, target_key: str, target_id) -> int:
    """Zaehlt fruehere Kampf-Niederlagen DIESES Kommandeurs gegen DENSELBEN Gegner."""
    rows = (await session.execute(
        select(CommanderMemory.context).where(
            CommanderMemory.commander_id == commander_id,
            CommanderMemory.event_type == "combat_defeat",
        )
    )).scalars().all()
    tid = str(target_id)
    return sum(1 for ctx in rows if str((ctx or {}).get(target_key)) == tid)


async def reinforce_opinion(
    session: AsyncSession,
    commander_id: uuid.UUID,
    *,
    about_player_id: uuid.UUID | None,
    about_npc_id: uuid.UUID | None,
    outcome: str,
    strength_ratio: float,
) -> None:
    """Aktualisiert die Meinung des Kommandeurs ueber einen Gegner anhand eines Kampfausgangs."""
    if about_player_id is None and about_npc_id is None:
        return
    bal = get_balance()
    op_cfg = bal.commander["opinions"]
    target_key = "about_player_id" if about_player_id is not None else "about_npc_id"
    target_id = about_player_id if about_player_id is not None else about_npc_id
    prior = await _prior_losses(session, commander_id, target_key, target_id) if outcome == "loss" else 0
    ev = evaluate_opinion(outcome, strength_ratio, prior, op_cfg)
    if ev is None:
        return

    clause = (
        CommanderOpinion.about_player_id == about_player_id
        if about_player_id is not None
        else CommanderOpinion.about_npc_id == about_npc_id
    )
    op = (await session.execute(
        select(CommanderOpinion).where(CommanderOpinion.commander_id == commander_id, clause)
    )).scalar_one_or_none()
    max_s = float(op_cfg["max_strength"])
    if op is None:
        new_type, new_strength = merge_opinion(None, 0.0, ev["opinion_type"], ev["delta"], max_s)
        session.add(CommanderOpinion(
            commander_id=commander_id,
            about_player_id=about_player_id,
            about_npc_id=about_npc_id,
            opinion_type=new_type,
            strength=new_strength,
            last_reinforced_at=_now(),
        ))
    else:
        new_type, new_strength = merge_opinion(
            op.opinion_type, float(op.strength or 0.0), ev["opinion_type"], ev["delta"], max_s
        )
        op.opinion_type = new_type
        op.strength = new_strength
        op.last_reinforced_at = _now()


async def opinion_about(
    session: AsyncSession,
    commander_id: uuid.UUID,
    *,
    about_player_id: uuid.UUID | None = None,
    about_npc_id: uuid.UUID | None = None,
) -> dict | None:
    """Liefert die Meinung eines Kommandeurs ueber einen Gegner als kontext-fertiges Dict
    ({opinion_type, strength, hated}) oder None — fuer kontext-bewusste Funksprueche."""
    if about_player_id is None and about_npc_id is None:
        return None
    clause = (
        CommanderOpinion.about_player_id == about_player_id
        if about_player_id is not None
        else CommanderOpinion.about_npc_id == about_npc_id
    )
    op = (await session.execute(
        select(CommanderOpinion).where(CommanderOpinion.commander_id == commander_id, clause)
    )).scalar_one_or_none()
    if op is None:
        return None
    op_cfg = get_balance().commander["opinions"]
    return {
        "opinion_type": op.opinion_type,
        "strength": round(float(op.strength or 0.0), 3),
        "hated": is_hated(op.opinion_type, float(op.strength or 0.0), op_cfg),
    }


async def bump_relationship(
    session: AsyncSession, commander_a: uuid.UUID, commander_b: uuid.UUID, event: str
) -> None:
    """Verstaerkt/erzeugt eine Beziehung zwischen zwei Kommandeuren (a<b-Konvention)."""
    if commander_a == commander_b:
        return
    rel_cfg = get_balance().commander["relationships"]
    spec = relationship_delta(event, rel_cfg)
    if spec is None:
        return
    new_type, delta = spec
    a, b = sorted((commander_a, commander_b), key=str)
    max_s = float(rel_cfg["max_strength"])
    rel = await session.get(CommanderRelationship, (a, b))
    if rel is None:
        session.add(CommanderRelationship(
            commander_a_id=a, commander_b_id=b, rel_type=new_type,
            strength=min(max_s, delta), last_interaction=_now(), context={"last_event": event},
        ))
        return
    if rel.rel_type == new_type:
        rel.strength = min(max_s, float(rel.strength or 0.0) + delta)
    elif delta > float(rel.strength or 0.0):
        rel.rel_type = new_type
        rel.strength = min(max_s, delta)
    rel.last_interaction = _now()
    rel.context = {"last_event": event}


async def add_grievance(session: AsyncSession, commander_id: uuid.UUID, grievance_type: str) -> None:
    """Stapelt eine Kraenkung (akkumuliert auf der offenen Zeile gleichen Typs, sonst neu)."""
    gr_cfg = get_balance().commander["grievances"]
    add = grievance_severity(grievance_type, gr_cfg)
    max_sev = int(gr_cfg.get("max_severity_per_grievance", 12))
    gr = (await session.execute(
        select(CommanderGrievance).where(
            CommanderGrievance.commander_id == commander_id,
            CommanderGrievance.grievance_type == grievance_type,
            CommanderGrievance.resolved_at.is_(None),
        ).limit(1)
    )).scalar_one_or_none()
    if gr is None:
        session.add(CommanderGrievance(
            commander_id=commander_id, grievance_type=grievance_type,
            severity=min(max_sev, add), accumulated_count=1,
        ))
    else:
        gr.severity, gr.accumulated_count = accumulate_grievance(
            int(gr.severity or 0), int(gr.accumulated_count or 0), add, max_sev
        )


async def resolve_grievances(
    session: AsyncSession, commander_id: uuid.UUID, grievance_type: str | None = None
) -> None:
    """Legt offene Kraenkungen bei (z.B. Forderung doch erfuellt / Befoerderung gewaehrt)."""
    q = select(CommanderGrievance).where(
        CommanderGrievance.commander_id == commander_id,
        CommanderGrievance.resolved_at.is_(None),
    )
    if grievance_type is not None:
        q = q.where(CommanderGrievance.grievance_type == grievance_type)
    for gr in (await session.execute(q)).scalars().all():
        gr.resolved_at = _now()


async def open_grievance_severity_sum(session: AsyncSession, commander_id: uuid.UUID) -> int:
    """Summe der Severities offener, nicht verjaehrter Kraenkungen (Meuterei-Treiber)."""
    gr_cfg = get_balance().commander["grievances"]
    decay_days = int(gr_cfg.get("decay_days", 21))
    rows = (await session.execute(
        select(CommanderGrievance.severity, CommanderGrievance.created_at, CommanderGrievance.resolved_at)
        .where(CommanderGrievance.commander_id == commander_id)
    )).all()
    return open_grievance_sum([(s, c, r) for s, c, r in rows], _now(), decay_days)


# ============================================================================
# High-Level-Hooks (best-effort) — aus Kampf/Expedition/Decide/Tick aufgerufen.
# ============================================================================

_COMBAT_EVENT = {
    "victory": "combat_victory",
    "crushing_victory": "combat_crushing_victory",
    "close_win": "combat_close_win",
    "defeat": "combat_defeat",
}


async def on_combat_memory(
    session: AsyncSession,
    commander: Commander | None,
    *,
    situation: str,
    winner_is_attacker: bool,
    enemy_name: str,
    enemy_player_id: uuid.UUID | None,
    enemy_npc_id: uuid.UUID | None,
    planet: str,
    loot: dict | None,
    strength_ratio: float,
    heavy_losses: bool,
) -> None:
    """Erinnerung + Meinungs-Update nach einer Schlacht. Best-effort."""
    if commander is None:
        return
    try:
        outcome = "win" if winner_is_attacker else "loss"
        event_type = _COMBAT_EVENT.get(situation, "combat_victory" if winner_is_attacker else "combat_defeat")
        ctx = {
            "enemy_name": enemy_name,
            "planet": planet,
            "outcome": outcome,
            "loot": {k: int(v) for k, v in (loot or {}).items() if v},
        }
        if enemy_player_id is not None:
            ctx["about_player_id"] = str(enemy_player_id)
        if enemy_npc_id is not None:
            ctx["about_npc_id"] = str(enemy_npc_id)
        await record_memory(session, commander.id, event_type, ctx)
        if heavy_losses:
            await record_memory(session, commander.id, "heavy_losses",
                                {"enemy_name": enemy_name, "planet": planet})
            # Schwere Verluste = riskante Dauereinsaetze -> staut Groll auf (Meuterei-Treiber).
            await add_grievance(session, commander.id, "risky_missions")
        await reinforce_opinion(
            session, commander.id,
            about_player_id=enemy_player_id, about_npc_id=enemy_npc_id,
            outcome=outcome, strength_ratio=strength_ratio,
        )
    except Exception:  # noqa: BLE001 — Gedaechtnis darf den Kampf-Auflöser nie stoeren
        log.debug("on_combat_memory fehlgeschlagen", exc_info=True)


async def on_expedition_memory(
    session: AsyncSession, commander_id: uuid.UUID | None, planet: str
) -> None:
    """Erinnerung an einen Expeditions-Erfolg. Best-effort."""
    if not commander_id:
        return
    try:
        await record_memory(session, commander_id, "expedition_success", {"planet": planet})
    except Exception:  # noqa: BLE001
        log.debug("on_expedition_memory fehlgeschlagen", exc_info=True)


async def on_demand_memory(
    session: AsyncSession, commander: Commander | None, choice: str, kind: str | None
) -> None:
    """Erinnerung + Kraenkung/Beilegung nach einer Forderungs-Entscheidung. Best-effort.

    - ``accept``/``negotiate`` -> positive Erinnerung, offene Kraenkungen (ignored_demand /
      ggf. denied_promotion) werden beigelegt; eine 'mutinous'-Verweigerung wird aufgehoben.
    - ``reject`` -> negative Erinnerung + Kraenkung (denied_promotion bei Befoerderung, sonst
      ignored_demand)."""
    if commander is None:
        return
    try:
        if choice in ("accept", "negotiate"):
            await record_memory(session, commander.id, "demand_fulfilled", {"kind": kind})
            await resolve_grievances(session, commander.id, "ignored_demand")
            if kind == "promotion":
                await resolve_grievances(session, commander.id, "denied_promotion")
            # Eine erfuellte Forderung beendet eine telegrafierte Befehlsverweigerung.
            if commander.status == "mutinous":
                commander.status = "active"
        else:  # reject
            await record_memory(session, commander.id, "demand_ignored", {"kind": kind})
            gtype = "denied_promotion" if kind == "promotion" else "ignored_demand"
            await add_grievance(session, commander.id, gtype)
    except Exception:  # noqa: BLE001
        log.debug("on_demand_memory fehlgeschlagen", exc_info=True)


async def on_promotion_memory(session: AsyncSession, commander: Commander, new_rank: str) -> None:
    """Erinnerung an eine Befoerderung + Beilegung etwaiger Befoerderungs-Kraenkungen. Best-effort."""
    try:
        await record_memory(session, commander.id, "promotion", {"rank": new_rank},
                            sentiment="positive")
        await resolve_grievances(session, commander.id, "denied_promotion")
    except Exception:  # noqa: BLE001
        log.debug("on_promotion_memory fehlgeschlagen", exc_info=True)


async def mutiny_check(session: AsyncSession, commander: Commander, *, rng_value: float) -> bool:
    """Prueft DREISTUFIG auf Meuterei (Vorwarnung -> akute Meuterei) und wendet die Folge an.

    Aufgerufen je Kommandeur aus ``morale_drift_tick`` (additiv, best-effort). Liefert True, wenn
    eine echte Meuterei (defect/refuse) ausgeloest wurde (der Tick ueberspringt dann weitere
    Schritte). Schwellen GROSSZUEGIG + klare Vorwarnung -> Gelegenheits-Spieler werden nicht
    unfair bestraft. ``rng_value`` (0..1) ist der Wuerfel (im Tick: ``random.random()``)."""
    from app.messaging.service import create_system_transmission

    try:
        bal = get_balance()
        mut_cfg = bal.commander["mutiny"]
        now = _now()
        grievance_sum = await open_grievance_severity_sum(session, commander.id)
        decision = mutiny_decision(
            loyalty=float(commander.loyalty or 0),
            unrest=float(commander.unrest or 0.0),
            grievance_sum=grievance_sum,
            traits=commander.traits or [],
            last_check_at=commander.last_mutiny_check_at,
            now=now,
            rng_value=rng_value,
            mut_cfg=mut_cfg,
        )
        action = decision["action"]
        if action == "none":
            return False
        if action == "warn":
            # Telegrafierte Vorwarnung — nur EINMAL je Cooldown, damit das Postfach nicht zuspamt.
            last = _aware(commander.last_mutiny_check_at)
            cooldown = dt.timedelta(hours=float(mut_cfg["mutiny_cooldown_hours"]))
            if last is not None and (now - last) < cooldown:
                return False
            commander.last_mutiny_check_at = now
            await create_system_transmission(
                session, player_id=commander.player_id,
                subject=f"⚠ {commander.name} steht kurz vor der Meuterei",
                body=(f"Kommandeur {commander.name} ist erbittert: niedrige Treue, hoher Unmut und "
                      f"aufgestaute Kraenkungen. Erfuelle seine Forderungen oder beruhige die Lage — "
                      f"sonst verweigert er bald den Befehl oder desertiert."),
                ttype="system",
            )
            await record_memory(session, commander.id, "mutiny_warning", {}, sentiment="negative")
            return False

        # action == "mutiny": echte Folge anwenden.
        commander.last_mutiny_check_at = now
        outcome = decision["outcome"]
        if outcome == "defect":
            commander.status = "defected"
            subject = f"🏴 {commander.name} ist gemeutert und desertiert"
            body = (f"Kommandeur {commander.name} hat offen gemeutert und mit seiner Flotte deinen "
                    f"Dienst verlassen. Anhaltende Misshandlung hat ihn endgueltig vertrieben.")
        else:  # refuse
            commander.status = "mutinous"
            subject = f"✊ {commander.name} meutert und verweigert den Befehl"
            body = (f"Kommandeur {commander.name} meutert: er verweigert den naechsten Befehl, bis du "
                    f"seine Forderungen erfuellst und die Lage beruhigst.")
        await create_system_transmission(
            session, player_id=commander.player_id, subject=subject, body=body, ttype="system",
        )
        await record_memory(session, commander.id, "mutiny", {"outcome": outcome}, sentiment="negative")
        log.info("Meuterei: commander=%s outcome=%s", commander.id, outcome)
        return True
    except Exception:  # noqa: BLE001 — Meuterei-Pruefung darf den Moral-Tick nie stoeren
        log.debug("mutiny_check fehlgeschlagen", exc_info=True)
        return False
