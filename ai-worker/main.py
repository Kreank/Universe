"""ai-worker — Entry-Point.

Async-Loop: BRPOP auf der Redis-Queue `ai:jobs`, Dispatch nach job_type an die
Handler unter jobs/. Vom Game-Tick entkoppelt (GDD §10.5, ADR-003): faellt Ollama
aus, wird der Job zurueckgestellt statt verloren, der Worker crasht nie.
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal

import redis.asyncio as aioredis

from config import settings
from db import Database
from jobs import big_moment, flavor, nightly_batch, persona_init
from logging_setup import setup_logging
from models import Job
from ollama_client import OllamaClient, OllamaUnavailable

log = logging.getLogger("worker")


class Worker:
    def __init__(self) -> None:
        self.redis: aioredis.Redis = aioredis.from_url(
            settings.redis_url, decode_responses=True
        )
        self.db = Database()
        self.ollama = OllamaClient()
        self._stop = asyncio.Event()

    # ----------------------------------------------------------------- Lifecycle
    async def start(self) -> None:
        await self.db.connect()
        log.info(
            "ai-worker bereit. queue=%s model=%s embed=%s ollama=%s",
            settings.job_queue, settings.ollama_model,
            settings.ollama_embed_model, settings.ollama_url,
        )
        await self._loop()

    def request_stop(self) -> None:
        if not self._stop.is_set():
            log.info("Shutdown angefordert — beende nach aktuellem Job")
        self._stop.set()

    async def aclose(self) -> None:
        await self.ollama.aclose()
        await self.db.close()
        await self.redis.aclose()

    # ---------------------------------------------------------------------- Loop
    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = await self.redis.brpop(settings.job_queue, timeout=settings.brpop_timeout)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # Redis-Aussetzer: nicht crashen, backoff.
                log.error("Redis BRPOP-Fehler: %s — backoff", exc)
                await self._interruptible_sleep(settings.ollama_outage_backoff_seconds)
                continue

            if item is None:
                continue  # Timeout ohne Job -> Stop-Flag pruefen, weiter warten.

            _key, raw = item
            await self._handle(raw)

    async def _handle(self, raw: str) -> None:
        try:
            job = Job.model_validate(json.loads(raw))
        except Exception as exc:
            log.error("Ungueltiger Job verworfen: %s | payload=%.300s", exc, raw)
            return

        log.info("Job empfangen: type=%s commander=%s player=%s",
                 job.job_type, job.commander_id, job.player_id)
        try:
            if job.job_type == "persona_init":
                await persona_init.run(job, self.db, self.ollama)
            elif job.job_type == "nightly_batch":
                await nightly_batch.run(job, self.db, self.ollama)
            elif job.job_type == "big_moment":
                await big_moment.run(job, self.db, self.ollama, self.redis)
            elif job.job_type == "flavor":
                await flavor.run(job, self.db, self.ollama, self.redis)
            else:  # pragma: no cover — Literal verhindert das eigentlich.
                log.warning("Unbekannter job_type: %s — verworfen", job.job_type)
        except OllamaUnavailable as exc:
            log.warning("Ollama nicht erreichbar (%s) — Job '%s' zurueckgestellt",
                        exc, job.job_type)
            await self._requeue(raw)
            await self._interruptible_sleep(settings.ollama_outage_backoff_seconds)
        except asyncio.CancelledError:
            # Shutdown mitten im Job: Job zurueckstellen, sauber abbrechen.
            await self._requeue(raw)
            raise
        except Exception:
            # Anderer, nicht-transienter Fehler: Job NICHT endlos requeuen
            # (sonst Poison-Loop). Loggen, verwerfen, weiterlaufen.
            log.exception("Job '%s' fehlgeschlagen — verworfen, Worker laeuft weiter",
                          job.job_type)

    async def _requeue(self, raw: str) -> None:
        """Job an den Kopf der Queue zuruecklegen (BRPOP zieht vom Ende ->
        landet hinter bereits wartenden Jobs, kein Hot-Loop)."""
        try:
            await self.redis.lpush(settings.job_queue, raw)
        except Exception:
            log.exception("Requeue fehlgeschlagen — Job verloren: %.200s", raw)

    async def _interruptible_sleep(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    setup_logging()
    worker = Worker()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except NotImplementedError:
            # Windows unterstuetzt add_signal_handler nicht — KeyboardInterrupt faengt SIGINT.
            pass

    try:
        await worker.start()
    finally:
        await worker.aclose()
        log.info("ai-worker beendet")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
