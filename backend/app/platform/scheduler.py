"""APScheduler-Wrapper (AsyncIOScheduler).

Plant einmalige Abschluss-Jobs (Gebaeude-/Forschungs-/Werft-Bau, Flottenankunft/
-rueckkehr) zu absoluten Zeitpunkten und registriert periodische Jobs (Moral-Drift).
Job-Callbacks sind Coroutinen in den Domaenen-Services."""
from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("universe.scheduler")

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        log.info("Scheduler gestartet")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def schedule_at(
    run_date: dt.datetime,
    func: Callable[..., Awaitable[Any]],
    *args: Any,
    job_id: str | None = None,
) -> None:
    """Plant ``func(*args)`` zum Zeitpunkt ``run_date`` (UTC). Liegt der Zeitpunkt in
    der Vergangenheit, fuehrt APScheduler den Job mit minimaler Verzoegerung aus."""
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=dt.timezone.utc)
    scheduler.add_job(
        func,
        trigger="date",
        run_date=run_date,
        args=args,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=None,  # auch verpasste Jobs noch ausfuehren
        coalesce=True,
    )


def schedule_interval(
    func: Callable[..., Awaitable[Any]],
    *,
    hours: float = 0,
    minutes: float = 0,
    seconds: float = 0,
    job_id: str | None = None,
) -> None:
    """Periodischer Job (z. B. stuendliche Moral-Drift)."""
    scheduler.add_job(
        func,
        trigger="interval",
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        id=job_id,
        replace_existing=True,
        coalesce=True,
    )
