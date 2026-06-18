"""Startup-Recovery offener Timer.

Der APScheduler nutzt einen MemoryJobStore — geplante Abschluss-Jobs (Gebaeude-/
Forschungs-Bau, Flottenankunft/-rueckkehr, Commander-Ausbildung) ueberleben einen
Neustart des game-servers NICHT. Diese Funktion liest beim Startup die DB und plant
alle noch offenen ``*_finishes_at`` / ``arrive_at`` / ``return_at`` neu ein.

Liegt der Zeitpunkt in der Vergangenheit (Server war laenger offline), feuert der
Date-Trigger sofort (misfire_grace_time=None) — der Abschluss wird nachgeholt.
Schliesst die vom Backend-Review markierte Robustheits-Luecke (ADR-002/§6 Zeit-Modell)."""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select

from app.platform.db import session_scope
from app.platform.models import Building, Commander, Fleet, NpcAttack, Research, ShipyardQueueItem
from app.platform.scheduler import schedule_at

log = logging.getLogger("universe.recovery")


async def recover_pending_jobs() -> None:
    """Plant alle in der DB offenen Abschluss-Jobs nach einem Neustart neu ein."""
    # Lazy-Import der Callbacks (vermeidet Import-Zyklen mit den Service-Modulen).
    from app.buildings.service import complete_building
    from app.buildings.shipyard import complete_shipyard_build
    from app.commander.service import complete_training
    from app.fleet.service import fleet_arrive, fleet_return
    from app.npc.attack import resolve_npc_attack
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

        # -- Megastrukturen (stufenweiser Bau) ------------------------------
        from app.megastructure.service import complete_megastructure
        from app.platform.models import Megastructure
        rows = (await session.execute(
            select(Megastructure).where(Megastructure.building_until.is_not(None))
        )).scalars().all()
        for m in rows:
            schedule_at(
                m.building_until, complete_megastructure, str(m.player_id), m.type,
                job_id=f"megastructure:{m.player_id}",
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

        # -- Werft-Bau-Warteschlange ---------------------------------------
        rows = (await session.execute(select(ShipyardQueueItem))).scalars().all()
        for q in rows:
            schedule_at(
                q.finishes_at, complete_shipyard_build, str(q.id),
                job_id=f"shipyard:{q.id}",
            )
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

        # -- Eingehende NPC-Angriffe (status 'incoming') -------------------
        rows = (await session.execute(
            select(NpcAttack).where(NpcAttack.status == "incoming")
        )).scalars().all()
        for atk in rows:
            schedule_at(
                atk.arrive_at, resolve_npc_attack, str(atk.id),
                job_id=f"npc-attack:{atk.id}",
            )
            recovered += 1

        # -- Game-Events: Ablauf-Jobs + Sonnensturm-Aktivierung -------------
        from app.events.service import activate_solar_storm, resolve_event
        from app.platform.models import CosmicEvent, Transmission
        now = dt.datetime.now(dt.timezone.utc)
        ev_rows = (await session.execute(
            select(CosmicEvent).where(CosmicEvent.status == "active")
        )).scalars().all()
        for ev in ev_rows:
            schedule_at(ev.expires_at, resolve_event, str(ev.id), job_id=f"event:{ev.id}")
            recovered += 1
            if ev.event_type == "solar_storm":
                starts = (ev.data or {}).get("starts_at")
                if starts:
                    try:
                        starts_at = dt.datetime.fromisoformat(starts)
                    except ValueError:
                        starts_at = now
                    schedule_at(starts_at, activate_solar_storm, str(ev.id), job_id=f"event-storm:{ev.id}")
                    recovered += 1

        # -- Offene Event-Entscheidungen: Timeout-Default neu planen --------
        from app.events.decisions import apply_event_default
        dec_rows = (await session.execute(
            select(Transmission).where(Transmission.requires_decision.is_(True))
        )).scalars().all()
        for t in dec_rows:
            payload = t.decision_payload or {}
            if payload.get("kind") != "event":
                continue
            ts = payload.get("timeout_at")
            if not ts:
                continue
            try:
                timeout_at = dt.datetime.fromisoformat(ts)
            except ValueError:
                continue
            schedule_at(timeout_at, apply_event_default, str(t.id), job_id=f"event-decide:{t.id}")
            recovered += 1

        # -- Allianz-Stationen: Upkeep-Tick (zehrt Deuterium) + Transit-Ankunft -------
        # Der Upkeep-Tick perpetuiert sich selbst, geht aber beim Neustart verloren -> ohne
        # Recovery friert der Treibstoff ein. Transit-Stationen brauchen ihren Ankunfts-Job.
        from app.alliance.station import _scfg, schedule_upkeep, station_arrive
        from app.platform.models import AllianceStation
        interval = int(_scfg().get("tick_interval_seconds", 3600))
        st_rows = (await session.execute(
            select(AllianceStation).where(AllianceStation.status != "destroyed")
        )).scalars().all()
        for st in st_rows:
            schedule_upkeep(st.id, interval)
            recovered += 1
            if st.status == "transit":
                arr = (st.transit or {}).get("arrive_at")
                if arr:
                    try:
                        arr_at = dt.datetime.fromisoformat(arr)
                    except ValueError:
                        arr_at = now
                    schedule_at(arr_at, station_arrive, str(st.id), job_id=f"station-arrive:{st.id}")
                    recovered += 1

    log.info("Startup-Recovery: %d offene Timer neu eingeplant", recovered)
