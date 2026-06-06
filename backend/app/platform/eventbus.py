"""Eventbus ueber Redis (zweite harte Grenze, events.md).

- ``publish_ws``: published JSON an den Pub/Sub-Channel ``ws:player:{id}`` (WS-Fan-out).
- ``enqueue_job``: legt einen Job in die Liste ``ai:jobs`` (LPUSH; ai-worker BRPOPt).
- ``subscribe_player``: liefert ein PubSub-Objekt fuer den WS-Gateway.

Der Eventbus ist absichtlich duenn: game-server und ai-worker reden ausschliesslich
ueber Redis (Jobs) und Postgres (Ergebnisse) — nie direkt."""
from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.platform.config import settings

log = logging.getLogger("universe.eventbus")

AI_JOBS_KEY = "ai:jobs"


def _player_channel(player_id: uuid.UUID | str) -> str:
    return f"ws:player:{player_id}"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Nicht serialisierbar: {type(obj)!r}")


class EventBus:
    """Kapselt den Redis-Client. Ein Singleton pro Prozess (siehe ``event_bus``)."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._redis: aioredis.Redis | None = None

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            # decode_responses=True -> wir arbeiten mit str statt bytes
            self._redis = aioredis.from_url(self._url, decode_responses=True)
        return self._redis

    async def publish_ws(self, player_id: uuid.UUID | str, message: dict[str, Any]) -> None:
        """Sendet eine WS-Nachricht an alle Verbindungen eines Spielers.

        Faellt Redis aus, wird der Fehler geloggt aber nicht propagiert (Degradation,
        ADR-003: das Spiel bleibt spielbar, KI/Live-Updates sind Veredelung)."""
        payload = json.dumps(message, default=_json_default)
        try:
            await self.redis.publish(_player_channel(player_id), payload)
        except Exception as exc:  # noqa: BLE001 - Degradation gewollt
            log.warning("publish_ws fehlgeschlagen (Redis?): %s", exc)

    async def enqueue_job(self, job: dict[str, Any]) -> None:
        """Reiht einen ai-worker-Job ein (Format siehe events.md). Nicht-kritisch."""
        job.setdefault("enqueued_at", dt.datetime.now(dt.timezone.utc).isoformat())
        try:
            await self.redis.lpush(AI_JOBS_KEY, json.dumps(job, default=_json_default))
        except Exception as exc:  # noqa: BLE001 - Degradation gewollt
            log.warning("enqueue_job fehlgeschlagen (Redis?): %s", exc)

    def subscribe_player(self, player_id: uuid.UUID | str) -> aioredis.client.PubSub:
        """PubSub-Objekt fuer den WS-Gateway (Aufrufer muss subscribe()/close() steuern)."""
        pubsub = self.redis.pubsub()
        return pubsub

    def channel_name(self, player_id: uuid.UUID | str) -> str:
        return _player_channel(player_id)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None


# Prozessweiter Singleton-Eventbus.
event_bus = EventBus(settings.REDIS_URL)
