"""NPC-Behavior-Tick: periodischer Job, der NPC-Imperien leben laesst (Doku 08).

Pro Tick erhaelt jeder NPC passives Einkommen (gedeckelt) und fuehrt ueber seinen
profilspezifischen Behavior-Tree GENAU EINE Aufbau-Aktion aus (Verteidigung/Flotte
Richtung baseline, sonst horten). Gefarmte NPCs (reduzierte fleet/defenses) bauen so
ueber mehrere Ticks Richtung baseline wieder auf -- begrenzt durch ihre Resschen.

Determinismus: Aktionen leiten sich ausschliesslich aus State + Balance ab (keine
Zufallsquellen). JSONB-Felder werden als NEUE dict-Objekte zurueckgeschrieben, damit
SQLAlchemy die Aenderung erkennt (vgl. combat/service.py)."""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select

from app.npc.behavior import NpcContext
from app.npc.profiles import build_tree
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import NpcEmpire

log = logging.getLogger("universe.npc")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


_RESOURCES = ("metal", "crystal", "deuterium")


def _apply_income(resources: dict, income: dict, cap: dict) -> dict[str, float]:
    """Schreibt passives Einkommen gut, gedeckelt je Resource. Liefert ein NEUES dict."""
    out = dict(resources)
    for res in _RESOURCES:
        gained = out.get(res, 0) + income.get(res, 0)
        out[res] = min(cap.get(res, gained), gained)
    return out


async def npc_behavior_tick() -> None:
    """Periodischer Job (balance.npc.tick_interval_seconds): ein Tick fuer alle NPCs.

    Direkt aufrufbar (Tests) und idempotent pro Tick-Aufruf."""
    bal = get_balance()
    npc_cfg = bal.npc
    income = npc_cfg["income_per_tick"]
    cap = npc_cfg["resource_cap"]
    profiles_cfg = npc_cfg["profiles"]
    fallback_profile = profiles_cfg["defensive"]
    ship_costs = bal.ships
    defense_costs = bal.defenses

    async with session_scope() as session:
        npcs = (await session.execute(select(NpcEmpire))).scalars().all()
        for npc in npcs:
            # baseline beim ersten Tick als Schnappschuss der Soll-Garnison setzen.
            baseline = npc.baseline or {}
            if not baseline:
                baseline = {"fleet": dict(npc.fleet or {}), "defenses": dict(npc.defenses or {})}
                npc.baseline = baseline

            # Passives Einkommen (gedeckelt) -- neues dict.
            resources = _apply_income(npc.resources or {}, income, cap)

            # Arbeitskopien fuer den Behavior-Tree.
            fleet = dict(npc.fleet or {})
            defenses = dict(npc.defenses or {})
            profile = profiles_cfg.get(npc.behavior_profile, fallback_profile)

            ctx = NpcContext(
                fleet=fleet,
                defenses=defenses,
                resources=resources,
                baseline=baseline,
                balance=npc_cfg,
                profile=profile,
                ship_costs=ship_costs,
                defense_costs=defense_costs,
            )
            build_tree(npc.behavior_profile).tick(ctx)

            # JSONB-Felder als NEUE Objekte zuweisen (SQLAlchemy-Change-Tracking).
            npc.resources = ctx.resources
            npc.fleet = ctx.fleet
            npc.defenses = ctx.defenses
            npc.last_action_at = _now()
        await session.commit()
    log.info("NPC-Behavior-Tick: %d NPCs verarbeitet", len(npcs))
