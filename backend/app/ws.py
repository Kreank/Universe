"""WebSocket-Gateway (api-contract §9).

`WS /ws?token=<jwt>`:
- authentifiziert per JWT,
- subscribed den Redis-Channel ``ws:player:{id}`` und leitet Nachrichten an den Client,
- sendet periodische ``resource_tick``-Nachrichten,
- verarbeitet Client->Server (``subscribe``, ``ping``).

Der game-server ist damit der Redis-Subscriber pro verbundenem Spieler (events.md)."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.platform.config import settings
from app.economy.service import refresh_resources
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import Planet
from app.platform.security import decode_token

log = logging.getLogger("universe.ws")


async def _forward_pubsub(websocket: WebSocket, pubsub) -> None:
    """Leitet eingehende Redis-PubSub-Nachrichten an den WS-Client weiter."""
    async for message in pubsub.listen():
        if message is None:
            continue
        if message.get("type") == "message":
            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await websocket.send_text(data)


async def _resource_ticker(websocket: WebSocket, player_id: uuid.UUID) -> None:
    """Sendet periodisch den aktuellen Ressourcenstand aller Planeten."""
    while True:
        await asyncio.sleep(settings.WS_TICK_SECONDS)
        async with session_scope() as session:
            planets = (await session.execute(
                select(Planet).where(Planet.player_id == player_id)
            )).scalars().all()
            for planet in planets:
                resources = await refresh_resources(session, planet)
                await websocket.send_json({
                    "type": "resource_tick",
                    "planet_id": str(planet.id),
                    "resources": resources,
                })


async def _receiver(websocket: WebSocket) -> None:
    """Verarbeitet Client->Server-Nachrichten (subscribe, ping)."""
    while True:
        raw = await websocket.receive_text()
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if msg.get("type") == "ping":
            await websocket.send_json({"type": "pong"})
        # "subscribe" wird angenommen; der Server pusht ohnehin alle Player-Events.


async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    """Haupt-Handler fuer ``/ws``."""
    if not token:
        await websocket.close(code=1008)
        return
    try:
        player_id = decode_token(token)
    except Exception:  # noqa: BLE001 - ungueltiges Token
        await websocket.close(code=1008)
        return

    await websocket.accept()
    pubsub = event_bus.redis.pubsub()
    channel = event_bus.channel_name(player_id)
    try:
        await pubsub.subscribe(channel)
    except Exception as exc:  # noqa: BLE001 - Redis evtl. nicht verfuegbar
        log.warning("WS-Subscribe fehlgeschlagen: %s", exc)

    tasks = [
        asyncio.create_task(_forward_pubsub(websocket, pubsub)),
        asyncio.create_task(_resource_ticker(websocket, player_id)),
        asyncio.create_task(_receiver(websocket)),
    ]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        log.info("WS-Verbindung beendet: %s", exc)
    finally:
        for task in tasks:
            task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass
        log.debug("WS geschlossen fuer player %s", player_id)
