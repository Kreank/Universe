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

from app.npc.attack import maybe_launch_attack
from app.npc.behavior import NpcContext
from app.npc.expansion import first_free_position, should_expand
from app.npc.profiles import build_tree
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.eventbus import event_bus
from app.platform.models import NpcEmpire, Planet, UniverseCell
from app.universe.service import occupy_cell

log = logging.getLogger("universe.npc")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


_RESOURCES = ("metal", "crystal", "deuterium")


async def _occupied_positions(session, galaxy: int, system: int) -> set[int]:
    """Belegte Positionen in einem System (Zellen != empty UND existierende Planeten)."""
    occ: set[int] = set()
    cells = (await session.execute(
        select(UniverseCell.position, UniverseCell.occupant_type).where(
            UniverseCell.galaxy == galaxy, UniverseCell.system == system
        )
    )).all()
    occ.update(pos for pos, otype in cells if otype != "empty")
    planets = (await session.execute(
        select(Planet.position).where(Planet.galaxy == galaxy, Planet.system == system)
    )).scalars().all()
    occ.update(planets)
    return occ


async def _try_expand(session, npc: NpcEmpire, exp_cfg: dict, max_positions: int) -> bool:
    """Versucht eine NPC-Expansion auf eine freie Position im eigenen System. True bei Erfolg.

    Vorbedingung (should_expand) wird vom Aufrufer geprueft. Zieht Kosten ab, legt eine neue
    'defensive' NPC-Garnison an und belegt die Zelle."""
    occupied = await _occupied_positions(session, npc.galaxy, npc.system)
    pos = first_free_position(occupied, max_positions)
    if pos is None:
        return False

    cost = exp_cfg.get("cost", {})
    resources = dict(npc.resources or {})
    for res in _RESOURCES:
        resources[res] = resources.get(res, 0) - float(cost.get(res, 0))
    npc.resources = resources  # neues dict -> Change-Tracking

    garrison = exp_cfg.get("garrison", {})
    fleet = dict(garrison.get("fleet", {}))
    defenses = dict(garrison.get("defenses", {}))
    colony = NpcEmpire(
        name=f"Aussenposten {npc.galaxy}:{npc.system}:{pos}",
        behavior_profile="defensive",
        galaxy=npc.galaxy, system=npc.system, position=pos,
        fleet=fleet, defenses=defenses,
        resources=dict(exp_cfg.get("colony_resources", {})),
        baseline={"fleet": dict(fleet), "defenses": dict(defenses)},
        last_action_at=_now(),
    )
    session.add(colony)
    await session.flush()
    await occupy_cell(session, npc.galaxy, npc.system, pos, "npc", colony.id)
    log.info("NPC %s expandiert -> %d:%d:%d", npc.name, npc.galaxy, npc.system, pos)
    return True


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

    exp_cfg = npc_cfg.get("expansion", {})
    max_positions = bal.positions_per_system
    max_exp = int(exp_cfg.get("max_expansions_per_tick", 0))
    expansions_done = 0

    atk_cfg = npc_cfg.get("attack", {})
    max_attacks = int(atk_cfg.get("max_attacks_per_tick", 0))
    attacks_done = 0
    pending_warnings: list[dict] = []

    async with session_scope() as session:
        npcs = (await session.execute(select(NpcEmpire))).scalars().all()
        # NPC-Dichte je System (inkl. im selben Tick neu gegruendeter).
        system_counts: dict[tuple[int, int], int] = {}
        for n in npcs:
            key = (n.galaxy, n.system)
            system_counts[key] = system_counts.get(key, 0) + 1

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

            # Expansion (expansive NPCs): freie Position im eigenen System besiedeln.
            key = (npc.galaxy, npc.system)
            if (expansions_done < max_exp
                    and should_expand(npc.behavior_profile, exp_cfg, ctx.resources, system_counts.get(key, 0))):
                if await _try_expand(session, npc, exp_cfg, max_positions):
                    expansions_done += 1
                    system_counts[key] = system_counts.get(key, 0) + 1

            # Angriff (aggressive NPCs): ungeschuetzten Spieler-Planeten attackieren.
            if attacks_done < max_attacks:
                warning = await maybe_launch_attack(session, npc, atk_cfg)
                if warning is not None:
                    attacks_done += 1
                    pending_warnings.append(warning)
        await session.commit()

    # WS-Warnungen erst NACH dem Commit pushen (keine Phantom-Warnung bei Rollback).
    for w in pending_warnings:
        await event_bus.publish_ws(w["player_id"], {
            "type": "attack_warning",
            "location": w["location"],
            "arrive_at": w["arrive_at"],
            "ships_total": w["ships_total"],
            "attacker_name": w["attacker_name"],
        })
    log.info("NPC-Behavior-Tick: %d NPCs verarbeitet", len(npcs))
