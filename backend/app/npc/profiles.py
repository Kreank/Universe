"""Baut je ``behavior_profile`` einen Behavior-Tree aus den Primitiven (behavior.py).

Die Baeume sind bewusst klein und priorisieren genau EINE Aufbau-Aktion pro Tick
(Selector: erste erfolgreiche Aktion gewinnt). Profil-Gewichte und Wachstums-Caps
stammen aus ``balance.npc.profiles[profile]``. Unbekannte Profile fallen auf
'defensive' zurueck. Alle Aktionen sind deterministisch (nur State + Balance)."""
from __future__ import annotations

import math

from app.npc.behavior import Action, Condition, NpcContext, Node, Selector, Sequence

# Bekannte Profile (mit Fallback). Reihenfolge irrelevant.
_KNOWN_PROFILES = ("defensive", "aggressive", "expansive", "merchant")
_FALLBACK_PROFILE = "defensive"


# -- Kosten/Kauf-Helfer -------------------------------------------------------

def _affordable_units(resources: dict, cost: dict, wanted: int) -> int:
    """Maximale Stueckzahl <= ``wanted``, die ``resources`` bei ``cost`` je Stueck zulaesst."""
    if wanted <= 0:
        return 0
    limit = wanted
    for res, price in cost.items():
        if price <= 0:
            continue
        limit = min(limit, int(resources.get(res, 0) // price))
    return max(0, limit)


def _pay(resources: dict, cost: dict, units: int) -> None:
    """Zieht ``units``-faches ``cost`` von ``resources`` ab (in-place auf der Tick-Kopie)."""
    for res, price in cost.items():
        resources[res] = resources.get(res, 0) - price * units


def _rebuild(
    current: dict[str, int],
    baseline: dict[str, int],
    costs: dict[str, dict],
    resources: dict,
    fraction: float,
    growth_cap_mult: float,
) -> bool:
    """Schliesst die Luecke ``current`` -> ``baseline*growth_cap_mult`` anteilig.

    Pro Typ wird ``ceil(gap * fraction)`` als Tick-Kontingent angesetzt und davon
    so viel gekauft, wie ``resources`` (Kosten aus ``costs``) hergeben. Mutiert
    ``current`` und ``resources`` in-place. Gibt True zurueck, wenn mindestens eine
    Einheit gebaut wurde (sonst False -> Baum faellt auf naechste Option zurueck)."""
    built_any = False
    for typ, base_count in baseline.items():
        cost = (costs.get(typ) or {}).get("cost") if costs.get(typ) else None
        if cost is None:
            continue
        target = int(math.floor(base_count * growth_cap_mult))
        have = current.get(typ, 0)
        gap = target - have
        if gap <= 0:
            continue
        allotment = min(gap, max(1, math.ceil(gap * fraction)))
        units = _affordable_units(resources, cost, allotment)
        if units <= 0:
            continue
        _pay(resources, cost, units)
        current[typ] = have + units
        built_any = True
    return built_any


# -- Bedingungen --------------------------------------------------------------

def _below_defense_baseline(ctx: NpcContext) -> bool:
    base = ctx.baseline.get("defenses", {})
    return any(ctx.defenses.get(typ, 0) < count for typ, count in base.items())


def _below_fleet_baseline(ctx: NpcContext) -> bool:
    base = ctx.baseline.get("fleet", {})
    mult = float(ctx.profile.get("growth_cap_mult", 1.0))
    return any(
        ctx.fleet.get(typ, 0) < int(math.floor(count * mult))
        for typ, count in base.items()
    )


# -- Aktionen -----------------------------------------------------------------

def _rebuild_defenses(ctx: NpcContext) -> bool:
    fraction = float(ctx.balance["rebuild_fraction_per_tick"]) * float(ctx.profile.get("rebuild_defense", 0.0))
    ok = _rebuild(
        ctx.defenses,
        ctx.baseline.get("defenses", {}),
        ctx.defense_costs,
        ctx.resources,
        fraction,
        growth_cap_mult=1.0,  # Verteidigung wird nur zur baseline regeneriert
    )
    ctx.acted = ctx.acted or ok
    return ok


def _reinforce_fleet(ctx: NpcContext) -> bool:
    fraction = float(ctx.balance["rebuild_fraction_per_tick"]) * float(ctx.profile.get("reinforce_fleet", 0.0))
    ok = _rebuild(
        ctx.fleet,
        ctx.baseline.get("fleet", {}),
        ctx.ship_costs,
        ctx.resources,
        fraction,
        growth_cap_mult=float(ctx.profile.get("growth_cap_mult", 1.0)),
    )
    ctx.acted = ctx.acted or ok
    return ok


def _hoard(ctx: NpcContext) -> bool:
    """Keine Kaeufe -- Resschen sammeln sich (Einkommen wurde im Service gutgeschrieben)."""
    return True


# -- Baum-Konstruktion --------------------------------------------------------

def build_tree(profile_name: str) -> Node:
    """Liefert den Behavior-Tree fuer ein Profil (Fallback: 'defensive').

    Die Profile unterscheiden sich nur in der PRIORITAET (Reihenfolge der Aeste);
    die Profil-Gewichte/Caps wirken in den Aktionen ueber ``balance.npc.profiles``."""
    name = profile_name if profile_name in _KNOWN_PROFILES else _FALLBACK_PROFILE

    defend = Sequence(Condition(_below_defense_baseline), Action(_rebuild_defenses))
    reinforce = Sequence(Condition(_below_fleet_baseline), Action(_reinforce_fleet))
    hoard = Action(_hoard)

    if name in ("aggressive", "expansive"):
        # Offensive Profile: Flotte hat Vorrang vor Verteidigung.
        return Selector(reinforce, defend, hoard)
    # defensive & merchant: Verteidigung zuerst.
    return Selector(defend, reinforce, hoard)
