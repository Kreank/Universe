"""Pydantic-Modelle fuer die Job-Payloads aus der Redis-Queue `ai:jobs`.

Format laut shared/events.md. `extra="allow"`, weil der game-server jederzeit
zusaetzliche Kontextfelder mitschicken darf, ohne den Worker zu brechen.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

JobType = Literal[
    "big_moment", "nightly_batch", "persona_init", "flavor", "npc_decision", "memory_digest",
    "chronicle",
]


class JobContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    situation: Optional[str] = None
    enemy: Optional[str] = None
    planet: Optional[str] = None
    loot: Optional[dict[str, Any]] = None
    outcome: Optional[str] = None
    # Flavor-Jobs (Phase 2): erzaehlerischer Text ohne Entitaet/Bank (Spionage, Expedition, …).
    narrator: Optional[str] = None
    subject: Optional[str] = None
    detail: Optional[dict[str, Any]] = None
    # Ziel-Transmission-Typ der Flavor-Nachricht (spy_report/system/routine/…). Default routine —
    # NIE big_moment, ausser explizit gewollt (sonst landet z.B. ein Spio-Text als "Großmoment").
    ttype: Optional[str] = None
    # Broadcast (Phase 4, Galaxie-News): einmal generieren, an ALLE aktiven Spieler verteilen.
    broadcast: Optional[bool] = None
    # NPC-Diplomatie (Welle 1): Verhandlungs-Entscheidung. offer_type/terms = Spieler-Angebot,
    # caps = vom Backend gelieferte Leitplanken (KI darf nie darueber hinaus), state =
    # strukturierter Spielzustand (Staerkeverhaeltnis, Lage, Historie, Spieler-Ruf).
    offer_type: Optional[str] = None
    terms: Optional[dict[str, Any]] = None
    caps: Optional[dict[str, Any]] = None
    state: Optional[dict[str, Any]] = None
    # Welle 2 (Gedaechtnis & Eigenleben): Gegner-Identitaet eines big_moment -> der Worker laedt
    # die Meinung des Kommandeurs ueber DIESEN Gegner (verhasst/gefuerchtet/geachtet) + sein
    # Erinnerungs-Narrativ und faerbt den Funkspruch.
    about_player_id: Optional[str] = None
    about_npc_id: Optional[str] = None
    # Welle 3 (Lebende Galaxie-Chronik): die vom Backend gesammelten erzaehlwuerdigen Fakten
    # eines Zeitfensters + das Fenster + Modell-Override. Der Job 'chronicle' verdichtet sie
    # zu einem epischen, faktentreuen Saga-Eintrag (Erzaehler 'historian').
    key_events: Optional[list[dict[str, Any]]] = None
    span_start: Optional[str] = None
    span_end: Optional[str] = None
    model: Optional[str] = None
    # Welle 4 (Der Erwachte Waechter): die Flavor-Stimme darf ein Qualitaetsmodell mit
    # abgeschaltetem Thinking nutzen (qwen3.5:9b, think=false). None -> Worker-Default.
    think: Optional[bool] = None


class Job(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_type: JobType
    commander_id: Optional[str] = None
    npc_id: Optional[str] = None
    player_id: Optional[str] = None
    # Welle 3: Ziel-Zeile der Chronik, die der Job mit Titel+Text befuellt.
    chronicle_id: Optional[str] = None
    context: JobContext = Field(default_factory=JobContext)
    enqueued_at: Optional[str] = None
