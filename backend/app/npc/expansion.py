"""NPC-Expansion: 'expansive' NPCs gründen auf freien Positionen neue Garnisonen (Doku 08).

Die reine Entscheidung (``should_expand``, ``first_free_position``) ist DB-frei und testbar;
die Orchestrierung (Zelle belegen, NpcEmpire anlegen) läuft im Behavior-Tick (npc/service.py),
der eine Session hat. Throttle gegen Wildwuchs: hohe Ressourcen-Schwelle + Kosten + Caps.
"""
from __future__ import annotations


def should_expand(
    profile_name: str, cfg: dict, resources: dict, system_npc_count: int
) -> bool:
    """Reine Entscheidung, ob ein NPC in diesem Tick expandieren darf."""
    if not cfg or profile_name not in cfg.get("enabled_profiles", []):
        return False
    if system_npc_count >= int(cfg.get("max_per_system", 0)):
        return False
    min_res = cfg.get("min_resources", {})
    return all(float(resources.get(k, 0)) >= float(v) for k, v in min_res.items())


def first_free_position(occupied: set[int], max_positions: int) -> int | None:
    """Erste unbesetzte Position 1..max_positions (oder None, wenn alle belegt)."""
    for pos in range(1, int(max_positions) + 1):
        if pos not in occupied:
            return pos
    return None
