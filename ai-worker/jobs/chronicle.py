"""Job: chronicle (Welle 3 — Lebende Galaxie-Chronik).

Der Chronist (Erzaehler 'historian') verdichtet die vom Backend gesammelten ECHTEN
Spieler-Taten eines Zeitfensters (groesste Schlachten, Auf-/Abstiege, Verrat, Bündnisse,
grosse Welt-Events) zu EINEM epischen, FAKTENTREUEN Saga-Eintrag (Titel + Fliesstext).

1. baut den Chronisten-Prompt aus ``context.key_events``,
2. generiert mit dem Entscheidungs-/Qualitaetsmodell (Override, think=false, format=json) —
   robustes JSON-Parsen ({titel, text}) mit Fallback,
3. schreibt title+body in ``game_chronicle`` (status='published', published_at=now),
4. optional: dezente Broadcast-Funkmeldung "📜 Neue Chronik: {Titel}" an alle Spieler (WS-Push).

Faellt Ollama aus -> Job wird zurueckgestellt (die pending-Zeile bleibt, wird beim Retry befuellt).
"""
from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from config import settings
from db import Database
from jobs.big_moment import _transmission_to_dict
from models import Job
from ollama_client import OllamaClient
from personas import build_chronicle_prompt, parse_chronicle_json

log = logging.getLogger("job.chronicle")

_MAX_ATTEMPTS = 3  # 1 Versuch + bis zu 2 Retries bei Parse-Fehler


async def run(job: Job, db: Database, ollama: OllamaClient, redis: aioredis.Redis) -> None:
    chronicle_id = job.chronicle_id
    if not chronicle_id:
        log.warning("chronicle ohne chronicle_id — verworfen")
        return

    ctx = job.context
    key_events = ctx.key_events or []
    model = str(ctx.model or settings.ollama_model)

    system, user = build_chronicle_prompt(
        key_events, span_start=ctx.span_start, span_end=ctx.span_end
    )

    parsed: dict[str, str] | None = None
    raw = ""
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        raw = await ollama.generate(system, user, model=model, format="json", think=False)
        parsed = parse_chronicle_json(raw)
        if parsed is not None:
            break
        log.info("chronicle: ungueltiges JSON (Versuch %d/%d)", attempt, _MAX_ATTEMPTS)

    if parsed is None:
        # Robustheit: kein verwertbares JSON -> Rohtext als Eintrag (besser als leere Chronik).
        parsed = {"titel": "Ein Kapitel der Galaxie", "text": raw.strip()}
        log.warning("chronicle: nach %d Versuchen kein JSON — nehme Rohtext", _MAX_ATTEMPTS)

    title = parsed["titel"] or "Ein Kapitel der Galaxie"
    body = parsed["text"]

    await db.update_chronicle(chronicle_id, title=title, body=body)
    log.info("chronicle %s veroeffentlicht: „%s\"", chronicle_id, title)

    # Optionaler, dezenter Broadcast an alle Spieler.
    if ctx.broadcast:
        targets = await db.active_player_ids()
        for pid in targets:
            row = await db.insert_transmission(
                player_id=pid, commander_id=None, ttype="system",
                subject="📜 Neue Chronik der Galaxie",
                body=f"Der Chronist hat ein neues Kapitel verfasst: „{title}\".",
            )
            message = json.dumps(
                {"type": "transmission", "transmission": _transmission_to_dict(row)},
                ensure_ascii=False,
            )
            await redis.publish(f"ws:player:{pid}", message)
        log.info("chronicle: Broadcast an %d Spieler", len(targets))
