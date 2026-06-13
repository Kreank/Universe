"""Galaxie-Nachrichten-Ticker (Phase 4).

Aggregiert bemerkenswerte Ereignisse aus BESTEHENDEN Daten (keine neuen Schreibstellen) — aktuell
die groesste Schlacht der letzten Stunden aus ``combat_reports`` (Truemmerfeld = Schlacht-Groesse) —
und laesst den ai-worker daraus EIN narratives Bulletin generieren (Erzaehler 'news_anchor'), das per
Broadcast-flavor-Job an ALLE Spieler verteilt wird. Periodisch via Scheduler (main.py).
"""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select

from app.platform.db import session_scope
from app.platform.models import CombatReport, Player

log = logging.getLogger("universe.news")

NEWS_WINDOW_HOURS = 6          # Betrachtungsfenster (groesste Schlacht der letzten Stunden).
NEWS_MIN_DEBRIS = 1.0         # Mindest-Truemmer (M+K), damit eine Schlacht "newswuerdig" ist.

# Letzte gemeldete Schlacht (Befund M-1): Fenster (6h) == Tick-Kadenz (6h), daher kann dieselbe
# groesste Schlacht in zwei Folge-Ticks fallen. Dieser prozess-lokale Guard verhindert die
# Doppelmeldung im Normalbetrieb (ueberlebt keinen Neustart -> nach Restart max. eine einzige
# Wiederholung, bewusst akzeptiert ohne Schema-Aenderung).
_last_broadcast_id = None


def _scale(report: CombatReport) -> float:
    d = report.debris or {}
    return float(d.get("metal", 0)) + float(d.get("crystal", 0))


async def news_tick() -> None:
    """Periodischer Job: meldet die groesste Schlacht im Fenster als Galaxie-Nachricht (Broadcast)."""
    from app.platform.ai_jobs import enqueue_flavor

    global _last_broadcast_id
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=NEWS_WINDOW_HOURS)
    async with session_scope() as session:
        reports = (await session.execute(
            select(CombatReport).where(CombatReport.created_at >= cutoff)
        )).scalars().all()
        if not reports:
            return
        top = max(reports, key=_scale)
        if _scale(top) < NEWS_MIN_DEBRIS:
            return
        if top.id == _last_broadcast_id:
            return  # dieselbe Schlacht wurde schon gemeldet (Idempotenz, Befund M-1)
        _last_broadcast_id = top.id
        out = top.outcome or {}
        attacker = await session.get(Player, top.attacker_id) if top.attacker_id else None
        atk_name = attacker.display_name if attacker else "Eine unbekannte Streitmacht"
        def_name = out.get("defender_name") or "ein fremdes Imperium"
        win_de = "der Angreifer setzte sich durch" if out.get("winner") == "attacker" else "die Verteidigung hielt stand"
        location = top.location
        scale_val = int(_scale(top))

    await enqueue_flavor(
        narrator="news_anchor",
        broadcast=True,
        situation="Bemerkenswerte Schlacht im Universum",
        planet=location,
        outcome=win_de,
        detail={
            "Angreifer": atk_name,
            "Verteidiger": def_name,
            "Schauplatz": location,
            "zurueckgelassenes Truemmerfeld (Metall+Kristall)": scale_val,
        },
    )
    log.info("News-Tick: Schlacht bei %s gemeldet (Truemmer=%d)", location, scale_val)
