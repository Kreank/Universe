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
from app.messaging.router import router as messaging_router
from app.platform.eventbus import event_bus
from app.platform.migrations import ensure_schema
from app.platform.recovery import recover_pending_jobs
from app.platform.scheduler import schedule_interval, shutdown_scheduler, start_scheduler
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
    # Offene Timer nach Neustart wiederherstellen (MemoryJobStore ist fluechtig).
    await recover_pending_jobs()
    # Stuendlicher Moral-Drift / Neglect-Decay (balance.commander.morale).
    schedule_interval(morale_drift_tick, hours=1, job_id="morale-drift")
    log.info("game-server bereit")
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
):
    app.include_router(r, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_route(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    await websocket_endpoint(websocket, token)
