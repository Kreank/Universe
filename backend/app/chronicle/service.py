"""Lebende Galaxie-Chronik (Welle 3) — Sammel-Logik + Tick.

Eine KI (Erzaehler ``historian``) schreibt fortlaufend die ECHTE Geschichte des Servers:
Aufstiege, Verrat, legendaere Schlachten werden zu erzaehlter Legende. Dieser Modul-Teil
ist der FAKTEN-Sammler — er waehlt aus einem Zeitfenster die erzaehlwuerdigen Tatsachen
(groesste Schlachten, Auf-/Abstiege ggü. der Vorchronik, neuer Verrat, geschlossene Pakte,
grosse Welt-Events) und reicht sie (zusammen mit dem Score-/Ruf-Snapshot des Fensters) an
den ai-worker weiter. Der erzaehlt daraus episch, aber STRIKT faktentreu (keine erfundenen
Namen/Zahlen).

Aufbau analog ``messaging/news.py`` (liest combat_reports, enqueued den Erzaehler-Job). Die
reine Auswahl-Logik (``build_key_events``) ist DB-/LLM-frei und direkt testbar; ``gather_key_events``
holt die Daten, ``run_chronicle_tick`` legt die Chronik-Zeile an und reiht den Job ein.
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import (
    CombatReport,
    CosmicEvent,
    GameChronicle,
    NpcDecision,
    NpcEmpire,
    Player,
    PlayerReputation,
)

log = logging.getLogger("universe.chronicle")

# Welt-Event-Typ -> erzaehl-taugliches deutsches Label (lokal gehalten -> kein Import-Zyklus
# mit events.service). Personliche/Tracking-Events bleiben aussen vor (nur scope global/system).
_EVENT_LABELS: dict[str, str] = {
    "wandering_comet": "ein wandernder Komet",
    "cosmic_anomaly": "eine kosmische Anomalie",
    "solar_storm": "ein Sonnensturm",
    "black_market": "ein intergalaktischer Schwarzmarkt",
    "refugee_flotilla": "eine Flüchtlings-Flottille",
    "utopia_shipyard": "eine erwachte Utopia-Werft",
    "black_hole": "ein Schwarzes Loch",
}

_OFFER_DE: dict[str, str] = {
    "alliance": "ein Bündnis",
    "ceasefire": "einen Waffenstillstand",
    "tribute": "ein Tribut-Abkommen",
}


def _scale(report: CombatReport) -> int:
    d = report.debris or {}
    return int(float(d.get("metal", 0)) + float(d.get("crystal", 0)))


def _winner_de(winner: str | None) -> str:
    if winner == "attacker":
        return "der Angreifer setzte sich durch"
    if winner == "defender":
        return "die Verteidigung hielt stand"
    return "der Ausgang blieb unentschieden"


# ============================================================================
# Reine Auswahl-Logik (DB-/LLM-frei, testbar).
# ============================================================================

def build_key_events(
    *,
    battles: list[dict],
    standings: list[dict],
    prev_snapshot: dict | None,
    reputations: list[dict],
    diplomacy: list[dict],
    cosmic_events: list[dict],
    cfg: dict,
) -> tuple[list[dict], dict]:
    """Waehlt aus den (bereits geholten) Roh-Fakten die erzaehlwuerdigen Eintraege + baut den
    Snapshot fuers naechste Mal.

    Eingaben (alle JSON-freundlich):
      - ``battles``     : [{scale, attacker, defender, location, winner}] (Roh, ungefiltert)
      - ``standings``   : [{player_id, name, score}] (aktueller Stand ALLER Spieler)
      - ``prev_snapshot``: {"scores": {pid: int}, "betrayals": {pid: int}} der Vorchronik (oder None)
      - ``reputations`` : [{player_id, name, betrayals}] (aktueller Verrats-Ruf)
      - ``diplomacy``   : [{npc_name, player_name, offer_type, choice}] (auffaellige NPC-Entscheidungen)
      - ``cosmic_events``: [{event_type, label, coords}]
      - ``cfg``         : balance.chronicle (min_events, max_battles, max_movers, min_battle_debris)

    Rueckgabe: ``(events, snapshot)`` — ``events`` ist die Fakten-Liste fuer den Erzaehler,
    ``snapshot`` wird in der Chronik abgelegt, damit die NAECHSTE Chronik die Veraenderung sieht.
    """
    max_battles = int(cfg.get("max_battles", 5))
    max_movers = int(cfg.get("max_movers", 5))
    min_debris = float(cfg.get("min_battle_debris", 0))
    min_events = int(cfg.get("min_events", 1))

    events: list[dict] = []

    # -- 1) Groesste Schlachten (nach Truemmerfeld Metall+Kristall) ------------
    worthy = [b for b in battles if float(b.get("scale", 0)) >= min_debris]
    worthy.sort(key=lambda b: float(b.get("scale", 0)), reverse=True)
    for b in worthy[:max_battles]:
        events.append({
            "type": "battle",
            "attacker": b.get("attacker"),
            "defender": b.get("defender"),
            "location": b.get("location"),
            "debris": int(float(b.get("scale", 0))),
            "outcome": _winner_de(b.get("winner")),
        })

    # -- 2) Aktuelle Mächte + Auf-/Abstieg ggü. dem Vorsnapshot ---------------
    ranked = sorted(
        (s for s in standings if int(s.get("score", 0)) > 0),
        key=lambda s: int(s.get("score", 0)), reverse=True,
    )
    for rank, s in enumerate(ranked[:max_movers], start=1):
        events.append({
            "type": "power", "rank": rank,
            "name": s.get("name"), "score": int(s.get("score", 0)),
        })

    prev_scores = (prev_snapshot or {}).get("scores") or {}
    if prev_scores:
        movers: list[tuple[int, dict]] = []
        for s in standings:
            pid = str(s.get("player_id"))
            if pid not in prev_scores:
                continue
            delta = int(s.get("score", 0)) - int(prev_scores.get(pid, 0))
            if delta != 0:
                movers.append((delta, s))
        risers = sorted((m for m in movers if m[0] > 0), key=lambda m: m[0], reverse=True)
        fallers = sorted((m for m in movers if m[0] < 0), key=lambda m: m[0])
        for delta, s in risers[:max_movers]:
            events.append({
                "type": "rise", "name": s.get("name"),
                "score": int(s.get("score", 0)), "delta": delta,
            })
        for delta, s in fallers[:max_movers]:
            events.append({
                "type": "fall", "name": s.get("name"),
                "score": int(s.get("score", 0)), "delta": delta,
            })

    # -- 3) Verrat (neuer Pakt-Bruch ggü. Vorsnapshot; erster Lauf = bekannte Verraeter) --
    prev_betrayals = (prev_snapshot or {}).get("betrayals") or {}
    first_run = prev_snapshot is None
    for r in reputations:
        total = int(r.get("betrayals", 0))
        if total <= 0:
            continue
        pid = str(r.get("player_id"))
        prev_b = int(prev_betrayals.get(pid, 0))
        new = total if first_run else max(0, total - prev_b)
        if new <= 0:
            continue
        events.append({
            "type": "betrayal", "name": r.get("name"),
            "new_betrayals": new, "total_betrayals": total,
        })

    # -- 4) Diplomatie (auffaellige NPC-Entscheidungen, z.B. neue Buendnisse) --
    for d in diplomacy[:max_movers]:
        events.append({
            "type": "diplomacy",
            "npc": d.get("npc_name"),
            "player": d.get("player_name"),
            "offer": _OFFER_DE.get(str(d.get("offer_type")), str(d.get("offer_type"))),
            "choice": d.get("choice"),
        })

    # -- 5) Grosse Welt-Events ------------------------------------------------
    for c in cosmic_events:
        events.append({
            "type": "cosmic_event",
            "label": c.get("label") or _EVENT_LABELS.get(str(c.get("event_type")), str(c.get("event_type"))),
            "coords": c.get("coords"),
        })

    # -- Mindest-Schwelle: zu wenig passiert -> "ruhige Zeiten"-Eintrag --------
    if len(events) < min_events:
        events.append({"type": "quiet"})

    snapshot = {
        "scores": {str(s.get("player_id")): int(s.get("score", 0)) for s in standings},
        "betrayals": {str(r.get("player_id")): int(r.get("betrayals", 0)) for r in reputations},
    }
    return events, snapshot


# ============================================================================
# DB-Sammler + Tick.
# ============================================================================

async def gather_key_events(
    session: AsyncSession,
    span_start: dt.datetime,
    span_end: dt.datetime,
    prev_snapshot: dict | None,
) -> tuple[list[dict], dict]:
    """Holt die Roh-Fakten des Zeitfensters aus der DB und ruft ``build_key_events``."""
    cfg = get_balance().data.get("chronicle", {})

    # Spielernamen einmal cachen (fuer Schlacht-Angreifer + Auf-/Abstieg + Verrat).
    name_by_id = dict((await session.execute(select(Player.id, Player.display_name))).all())

    # -- Schlachten im Fenster --
    reports = (await session.execute(
        select(CombatReport).where(
            CombatReport.created_at >= span_start, CombatReport.created_at < span_end
        )
    )).scalars().all()
    battles: list[dict] = []
    for rep in reports:
        out = rep.outcome or {}
        atk = name_by_id.get(rep.attacker_id) if rep.attacker_id else None
        battles.append({
            "scale": _scale(rep),
            "attacker": atk or "Eine unbekannte Streitmacht",
            "defender": out.get("defender_name") or "ein fremdes Imperium",
            "location": rep.location,
            "winner": out.get("winner"),
        })

    # -- Aktueller Punktestand (alle Spieler) --
    standings = [
        {"player_id": str(pid), "name": name, "score": int(score or 0)}
        for pid, name, score in (
            await session.execute(select(Player.id, Player.display_name, Player.score))
        ).all()
    ]

    # -- Verrats-Ruf --
    reputations = [
        {"player_id": str(pid), "name": name_by_id.get(pid, "Unbekannt"), "betrayals": int(b or 0)}
        for pid, b in (
            await session.execute(
                select(PlayerReputation.player_id, PlayerReputation.betrayals)
            )
        ).all()
    ]

    # -- Auffaellige NPC-Entscheidungen im Fenster: geschlossene Buendnisse --
    decisions = (await session.execute(
        select(NpcDecision).where(
            NpcDecision.created_at >= span_start, NpcDecision.created_at < span_end,
            NpcDecision.offer_type == "alliance", NpcDecision.npc_choice == "accept",
        )
    )).scalars().all()
    npc_names = dict((await session.execute(select(NpcEmpire.id, NpcEmpire.name))).all())
    diplomacy = [
        {
            "npc_name": npc_names.get(d.npc_id, "ein fremdes Imperium"),
            "player_name": name_by_id.get(d.player_id, "ein Admiral"),
            "offer_type": d.offer_type, "choice": d.npc_choice,
        }
        for d in decisions
    ]

    # -- Grosse Welt-Events im Fenster (kein persoenliches Tracking) --
    cevents = (await session.execute(
        select(CosmicEvent).where(
            CosmicEvent.spawned_at >= span_start, CosmicEvent.spawned_at < span_end,
            CosmicEvent.scope.in_(("global", "system")),
        )
    )).scalars().all()
    cosmic = [
        {
            "event_type": ev.event_type,
            "label": _EVENT_LABELS.get(ev.event_type, ev.event_type),
            "coords": (
                f"{ev.galaxy}:{ev.system}:{ev.position}" if ev.position is not None
                else (f"{ev.galaxy}:{ev.system}" if ev.system is not None else None)
            ),
        }
        for ev in cevents
        if ev.event_type in _EVENT_LABELS
    ]

    return build_key_events(
        battles=battles, standings=standings, prev_snapshot=prev_snapshot,
        reputations=reputations, diplomacy=diplomacy, cosmic_events=cosmic, cfg=cfg,
    )


async def run_chronicle_tick(session: AsyncSession) -> GameChronicle | None:
    """Legt eine Chronik-Zeile (status pending) mit Fakten+Snapshot an und reiht den
    ai-worker-Job (chronicle) ein. Gibt die Zeile zurueck (oder None, wenn deaktiviert)."""
    cfg = get_balance().data.get("chronicle", {})
    if not cfg.get("enabled", True):
        return None

    now = dt.datetime.now(dt.timezone.utc)
    span_start = now - dt.timedelta(hours=float(cfg.get("lookback_hours", 24)))

    # Vorsnapshot aus der jüngsten Chronik (egal ob schon veroeffentlicht — der Snapshot
    # wird beim Anlegen geschrieben). Erster Lauf -> None (nur aktueller Stand, kein Delta).
    prev = (await session.execute(
        select(GameChronicle).order_by(GameChronicle.created_at.desc()).limit(1)
    )).scalars().first()
    prev_snapshot = None
    if prev is not None and isinstance(prev.key_events, dict):
        prev_snapshot = prev.key_events.get("snapshot")

    events, snapshot = await gather_key_events(session, span_start, now, prev_snapshot)

    narrator = str(cfg.get("narrator", "historian"))
    row = GameChronicle(
        narrator=narrator, span_start=span_start, span_end=now, status="pending",
        key_events={"events": events, "snapshot": snapshot},
    )
    session.add(row)
    await session.flush()

    await event_bus.enqueue_job({
        "job_type": "chronicle",
        "chronicle_id": str(row.id),
        "context": {
            "narrator": narrator,
            "broadcast": bool(cfg.get("broadcast", True)),
            "model": str(cfg.get("model", "qwen3.5:9b")),
            "key_events": events,
            "span_start": span_start.isoformat(),
            "span_end": now.isoformat(),
        },
    })
    log.info("Chronik-Tick: Zeile %s angelegt (%d Schluessel-Ereignisse), Job eingereiht",
             row.id, len(events))
    return row


async def chronicle_tick() -> None:
    """Periodischer Scheduler-Job (eigener Session-Scope, Vorbild news_tick/score_tick)."""
    async with session_scope() as session:
        await run_chronicle_tick(session)
