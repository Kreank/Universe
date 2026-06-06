"""Startup-Recovery offener Timer.

Der APScheduler nutzt einen MemoryJobStore — geplante Abschluss-Jobs (Gebaeude-/
Forschungs-Bau, Flottenankunft/-rueckkehr, Commander-Ausbildung) ueberleben einen
Neustart des game-servers NICHT. Diese Funktion liest beim Startup die DB und plant
alle noch offenen ``*_finishes_at`` / ``arrive_at`` / ``return_at`` neu ein.

Liegt der Zeitpunkt in der Vergangenheit (Server war laenger offline), feuert der
Date-Trigger sofort (misfire_grace_time=None) — der Abschluss wird nachgeholt.
Schliesst die vom Backend-Review markierte Robustheits-Luecke (ADR-002/§6 Zeit-Modell)."""
from __future__ import annotations

import logging

from sqlalchemy import select

from app.platform.db import session_scope
from app.platform.models import Building, Commander, Fleet, Research
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.recovery")


async def recover_pending_jobs() -> None:
    """Plant alle in der DB offenen Abschluss-Jobs nach einem Neustart neu ein."""
    # Lazy-Import der Callbacks (vermeidet Import-Zyklen mit den Service-Modulen).
    from app.buildings.service import complete_building
    from app.commander.service import complete_training
    from app.fleet.service import fleet_arrive, fleet_return
    from app.research.service import complete_research

    recovered = 0
    async with session_scope() as session:
        # -- Gebaeude-Bau ---------------------------------------------------
        rows = (await session.execute(
            select(Building).where(Building.upgrade_finishes_at.is_not(None))
        )).scalars().all()
        for b in rows:
            schedule_at(
                b.upgrade_finishes_at, complete_building, str(b.planet_id), b.type,
                job_id=f"build:{b.planet_id}:{b.type}",
            )
            recovered += 1

        # -- Forschung ------------------------------------------------------
        rows = (await session.execute(
            select(Research).where(Research.finishes_at.is_not(None))
        )).scalars().all()
        for r in rows:
            # Job-ID exakt wie im research-Service (nur eine Forschung gleichzeitig).
            schedule_at(
                r.finishes_at, complete_research, str(r.player_id), r.type,
                job_id=f"research:{r.player_id}",
            )
            recovered += 1

        # -- Flotten (Ankunft + Rueckkehr) ----------------------------------
        rows = (await session.execute(
            select(Fleet).where(Fleet.status.in_(("flying", "returning")))
        )).scalars().all()
        for f in rows:
            if f.status == "flying":
                schedule_at(f.arrive_at, fleet_arrive, str(f.id), job_id=f"fleet-arrive:{f.id}")
                recovered += 1
            if f.return_at is not None:
                schedule_at(f.return_at, fleet_return, str(f.id), job_id=f"fleet-return:{f.id}")
                recovered += 1

        # -- Commander-Ausbildung ------------------------------------------
        rows = (await session.execute(
            select(Commander).where(
                Commander.status == "training",
                Commander.training_finishes_at.is_not(None),
            )
        )).scalars().all()
        for c in rows:
            schedule_at(
                c.training_finishes_at, complete_training, str(c.id),
                job_id=f"train:{c.id}",
            )
            recovered += 1

    log.info("Startup-Recovery: %d offene Timer neu eingeplant", recovered)
