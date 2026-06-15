"""Allianz-Forschung: Kauf aus dem Pool (Soft-Cap via max_level, Kosten skalieren mit
Mitgliederzahl als Schneeball-Guardrail) + Reset als Ressourcen-Sink.

Levels liegen in ``Alliance.research_levels`` als ``{"<tree>.<node>": level}``. Die Knoten-
Definitionen kommen aus ``balance.alliance.research.trees``.
"""
from __future__ import annotations


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alliance.service import RES_KEYS, _acfg, _member_count, _require_role
from app.platform.models import Alliance, Player

RES_KEYS_ALL = RES_KEYS


def _trees() -> dict:
    return _acfg().get("research", {}).get("trees", {})


def node_key(tree: str, node: str) -> str:
    return f"{tree}.{node}"


def find_node(tree: str, node: str) -> dict | None:
    return (_trees().get(tree, {}).get("nodes", {}) or {}).get(node)


def level_of(alliance: Alliance, tree: str, node: str) -> int:
    return int((alliance.research_levels or {}).get(node_key(tree, node), 0))


def _member_mult(member_count: int) -> float:
    rcfg = _acfg().get("research", {})
    if not rcfg.get("cost_scales_with_members", True):
        return 1.0
    factor = float(rcfg.get("member_cost_factor_per_member", 0.0))
    return 1.0 + factor * max(0, member_count - 1)


def cost_for_next_level(node_cfg: dict, current_level: int, member_count: int) -> dict[str, float]:
    """Kosten der naechsten Stufe. Repeatable: linear (base*(level+1)); sonst exponentiell
    (base*2^level). Zusaetzlich Mitglieder-Multiplikator (Guardrail gegen Groessen-Schneeball)."""
    base = node_cfg.get("cost", {})
    if node_cfg.get("repeatable"):
        level_mult = current_level + 1
    else:
        level_mult = 2 ** current_level
    member_mult = _member_mult(member_count)
    return {k: round(float(base.get(k, 0)) * level_mult * member_mult, 2) for k in RES_KEYS_ALL}


def _pool_has(pool: dict, cost: dict) -> bool:
    return all(float(pool.get(k, 0)) >= float(cost.get(k, 0)) for k in RES_KEYS_ALL)


async def spend_research(session: AsyncSession, player: Player, tree: str, node: str) -> dict:
    """Erforscht die naechste Stufe eines Knotens aus dem Pool. Liefert {level, cost, pool}."""
    min_role = _acfg().get("min_role_for_spend", "officer")
    m = await _require_role(session, player, min_role)
    node_cfg = find_node(tree, node)
    if node_cfg is None:
        raise ValueError("Unbekannter Forschungsknoten.")

    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()

    key = node_key(tree, node)
    current = int((al.research_levels or {}).get(key, 0))
    max_level = int(node_cfg.get("max_level", 0))
    if max_level and current >= max_level:
        raise ValueError(f"Maximalstufe erreicht ({max_level}).")

    member_count = await _member_count(session, al.id)
    cost = cost_for_next_level(node_cfg, current, member_count)
    pool = dict(al.pool or {})
    if not _pool_has(pool, cost):
        raise ValueError("Der Allianz-Pool hat nicht genug Ressourcen.")
    for k in RES_KEYS_ALL:
        pool[k] = round(float(pool.get(k, 0)) - float(cost.get(k, 0)), 2)
    al.pool = pool

    levels = dict(al.research_levels or {})
    levels[key] = current + 1
    al.research_levels = levels
    return {"node": key, "level": current + 1, "cost": cost, "pool": pool}


async def reset_research(session: AsyncSession, player: Player) -> dict:
    """Setzt die gesamte Allianz-Forschung zurueck (Governance: nur Gruender). Refund =
    reset_refund_ratio * Summe aller bisher gezahlten Stufenkosten (Default 0 = voller Sink)."""
    m = await _require_role(session, player, "founder")
    al = (await session.execute(
        select(Alliance).where(Alliance.id == m.alliance_id).with_for_update()
    )).scalar_one()
    ratio = float(_acfg().get("research", {}).get("reset_refund_ratio", 0.0))
    member_count = await _member_count(session, al.id)

    refund = {k: 0.0 for k in RES_KEYS_ALL}
    if ratio > 0:
        for key, level in (al.research_levels or {}).items():
            tree, _, node = key.partition(".")
            node_cfg = find_node(tree, node)
            if not node_cfg:
                continue
            for lvl in range(int(level)):
                c = cost_for_next_level(node_cfg, lvl, member_count)
                for k in RES_KEYS_ALL:
                    refund[k] += float(c.get(k, 0)) * ratio

    al.research_levels = {}
    if ratio > 0:
        pool = dict(al.pool or {})
        for k in RES_KEYS_ALL:
            pool[k] = round(float(pool.get(k, 0)) + refund[k], 2)
        al.pool = pool
    return {"reset": True, "refund": {k: round(v, 2) for k, v in refund.items()}, "pool": al.pool or {}}


def research_catalog(alliance: Alliance | None, member_count: int) -> dict:
    """Vollstaendiger Baum-Katalog inkl. aktueller Stufen + Kosten der naechsten Stufe — fuers UI."""
    out: dict = {}
    for tree, tdef in _trees().items():
        nodes_out = {}
        for node, ncfg in (tdef.get("nodes", {}) or {}).items():
            current = level_of(alliance, tree, node) if alliance else 0
            max_level = int(ncfg.get("max_level", 0))
            at_max = bool(max_level and current >= max_level)
            nodes_out[node] = {
                "context": ncfg.get("context"),
                "lever": ncfg.get("lever"),
                "effect": ncfg.get("effect"),
                "repeatable": bool(ncfg.get("repeatable")),
                "max_level": max_level,
                "level": current,
                "per_level": ncfg.get("per_level"),
                "next_cost": None if at_max else cost_for_next_level(ncfg, current, member_count),
            }
        out[tree] = {"label": tdef.get("label", tree), "nodes": nodes_out}
    return out
