"""FastAPI-App des game-servers.

- registriert alle Domaenen-Router unter ``/api``,
- mountet den WebSocket ``/ws``,
- startet beim Startup den APScheduler und den stuendlichen Moral-Drift-Job.
Modularer Monolith, autoritativ (ARCHITECTURE §4)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.buildings.router import router as buildings_router
from app.combat.router import router as combat_router
from app.commander.router import router as commander_router
from app.commander.service import morale_drift_tick
from app.economy.router import router as economy_router
from app.fleet.router import router as fleet_router
from app.fleet.stationing import station_fuel_tick
from app.fleet.trade import market_regen_tick
from app.fleet.trade_index import index_tick
from app.messaging.router import router as messaging_router
from app.npc.population import ensure_trade_centers, npc_population_tick
from app.npc.service import npc_behavior_tick
from app.platform.balance import get_balance
from app.platform.eventbus import event_bus
from app.planets.derive import backfill_planets
from app.platform.migrations import ensure_schema
from app.platform.recovery import recover_pending_jobs
from app.platform.scheduler import schedule_interval, shutdown_scheduler, start_scheduler
from app.ranking.router import router as ranking_router
from app.ranking.service import score_tick
from app.research.router import router as research_router
from app.universe.router import router as universe_router
from app.ws import websocket_endpoint

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("universe.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown: Scheduler + periodische Jobs."""
    start_scheduler()
    # Idempotente Schema-Migrationen (neue Tabellen/ENUMs in bestehende DBs bringen).
    await ensure_schema()
    # Bestehende Planeten auf positionsabhaengigen Typ/Temp/Felder bringen (idempotent).
    await backfill_planets()
    # Offene Timer nach Neustart wiederherstellen (MemoryJobStore ist fluechtig).
    await recover_pending_jobs()
    # Stuendlicher Moral-Drift / Neglect-Decay (balance.commander.morale).
    schedule_interval(morale_drift_tick, hours=1, job_id="morale-drift")
    # NPC-Behavior-Tick: Garnison-Wiederaufbau/Wachstum je Profil (balance.npc).
    schedule_interval(
        npc_behavior_tick,
        seconds=get_balance().npc["tick_interval_seconds"],
        job_id="npc-behavior",
    )
    # NPC-Populations-Tick: haelt nahe bei Spielern eine Ziel-NPC-Dichte (balance.npc.population).
    schedule_interval(
        npc_population_tick,
        seconds=get_balance().npc["population"]["tick_interval_seconds"],
        job_id="npc-population",
    )
    # Markt-Regen-Tick: Haendler-Bestaende driften langsam zum Sollwert (balance.trade).
    schedule_interval(
        market_regen_tick,
        seconds=get_balance().trade["market_tick_interval_seconds"],
        job_id="market-regen",
    )
    # Unangreifbare Handelszentren seeden (idempotent) + globalen Handelsindex aktualisieren.
    await ensure_trade_centers()
    schedule_interval(
        index_tick,
        seconds=get_balance().trade["index"]["tick_interval_seconds"],
        job_id="trade-index",
    )
    # Ranglisten-Score (Imperiumswert) periodisch neu berechnen. Wird zusaetzlich
    # bei jedem /api/ranking-Abruf frisch gerechnet; der Tick haelt Player.score
    # (Auth-Response/Topbar) auch ohne Ranglisten-Besuch aktuell.
    schedule_interval(score_tick, minutes=5, job_id="ranking-score")
    # Treibstoff-Tick: vorgeschobene Stationierungen zehren ihren Deuterium-Vorrat; leer -> heim.
    schedule_interval(
        station_fuel_tick,
        seconds=get_balance().fleet["station_fuel"]["tick_interval_seconds"],
        job_id="station-fuel",
    )
    try:
        yield
    finally:
        shutdown_scheduler()
        await event_bus.close()
        log.info("game-server heruntergefahren")


app = FastAPI(title="Universe game-server", version="0.1.0", lifespan=lifespan)

# CORS offen fuer das lokale Angular-Frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Alle Domaenen-Router unter /api ------------------------------------------
for r in (
    auth_router,
    economy_router,
    buildings_router,
    research_router,
    fleet_router,
    combat_router,
    commander_router,
    messaging_router,
    universe_router,
    ranking_router,
):
    app.include_router(r, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_route(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    await websocket_endpoint(websocket, token)
