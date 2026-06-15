"""Bonus-Resolver — das Kernstueck des Doppel-Dip-Schutzes.

Allianz-Boni stapeln NIE dieselbe globale Zahl wie die Spieler-Forschung, weil jeder Knoten nur in
einem Kontext greift, den es solo nicht gibt (kodiert in node.context):
  - 'passive_collective': immer fuer Mitglieder (rein soziale Hebel: Pool/Bounty).
  - 'zone': nur wenn das Ziel-System in der Einflusszone einer aktiven, getankten Station liegt.
  - 'coop': nur wenn >=2 Mitglieder gemeinsam handeln (Aufrufer setzt coop=True).
  - 'ally': nur wenn die Aktion ein anderes Mitglied schuetzt/transportiert (Aufrufer setzt ally=True).

Wirkung = level * per_level (Zonen-Boni zusaetzlich per zone_bonus_softcap gedeckelt). Ein Lever ist
ueber alle Baeume eindeutig -> direkter Lookup an den Hook-Punkten via ``alliance_bonus(...)``.
"""
from __future__ import annotations


from sqlalchemy.ext.asyncio import AsyncSession

from app.alliance import station as station_mod
from app.alliance.research import level_of
from app.alliance.service import _acfg
from app.platform.models import Alliance, Player

# lever -> (tree, node, cfg). Lazy gecached.
_LEVER_INDEX: dict[str, tuple[str, str, dict]] | None = None


def _lever_index() -> dict[str, tuple[str, str, dict]]:
    global _LEVER_INDEX
    if _LEVER_INDEX is None:
        idx: dict[str, tuple[str, str, dict]] = {}
        trees = _acfg().get("research", {}).get("trees", {})
        for tree, tdef in trees.items():
            for node, ncfg in (tdef.get("nodes", {}) or {}).items():
                lever = ncfg.get("lever")
                if lever:
                    idx[lever] = (tree, node, ncfg)
        _LEVER_INDEX = idx
    return _LEVER_INDEX


def magnitude_for(alliance: Alliance, lever: str) -> tuple[float, str]:
    """Reine Wirkung eines Levers (level * per_level) + sein context — OHNE Kontext-Gate.
    Liefert (magnitude, context)."""
    entry = _lever_index().get(lever)
    if entry is None:
        return 0.0, ""
    tree, node, ncfg = entry
    level = level_of(alliance, tree, node)
    if level <= 0:
        return 0.0, ncfg.get("context", "")
    return level * float(ncfg.get("per_level", 0)), ncfg.get("context", "")


async def alliance_bonus(
    session: AsyncSession,
    player: Player | None,
    lever: str,
    *,
    galaxy: int | None = None,
    system: int | None = None,
    coop: bool = False,
    ally: bool = False,
) -> float:
    """Kontext-gegateter Allianz-Bonus fuer einen Lever. 0.0, wenn solo / nichts erforscht /
    Kontext nicht erfuellt."""
    if player is None or player.alliance_id is None:
        return 0.0
    alliance = await session.get(Alliance, player.alliance_id)
    if alliance is None:
        return 0.0
    magnitude, context = magnitude_for(alliance, lever)
    if magnitude <= 0:
        return 0.0

    if context == "passive_collective":
        return magnitude
    if context == "coop":
        return magnitude if coop else 0.0
    if context == "ally":
        return magnitude if ally else 0.0
    if context == "zone":
        if galaxy is None or system is None:
            return 0.0
        st = await station_mod.active_station_in_zone(session, alliance.id, galaxy, system)
        if st is None:
            return 0.0
        cap = float(_acfg().get("station", {}).get("zone_bonus_softcap", 0))
        return min(magnitude, cap) if cap > 0 else magnitude
    return 0.0
