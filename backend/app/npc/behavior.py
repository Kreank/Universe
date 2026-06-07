"""Minimale Behavior-Tree-Primitive fuer NPC-Verhalten (Doku 08, Behavior Trees).

Bewusst schlank gehalten: nur die Knotentypen, die ``profiles.py`` braucht.
Jeder Knoten implementiert ``tick(ctx) -> bool`` und meldet Erfolg/Misserfolg.
Der ``NpcContext`` buendelt den veraenderlichen NPC-State plus Balance/Profil,
sodass Bedingungen und Aktionen rein aus State + Balance ableitbar (deterministisch)
sind -- keine Zufallsquellen."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NpcContext:
    """Veraenderlicher Arbeitskontext eines NPC waehrend eines Ticks.

    ``fleet``/``defenses``/``resources`` sind NEUE dict-Kopien des NPC-State,
    die der Service nach dem Tick zurueckschreibt (komplette Neuzuweisung, damit
    SQLAlchemy die JSONB-Aenderung erkennt). ``baseline`` ist die Soll-Garnison.
    ``balance`` ist das ``balance.npc``-Subdict, ``profile`` dessen Profil-Eintrag."""

    fleet: dict[str, int]
    defenses: dict[str, int]
    resources: dict[str, float]
    baseline: dict[str, dict[str, int]]
    balance: dict[str, Any]
    profile: dict[str, Any]
    # Kostentabellen (aus balance.ships[typ].cost bzw. balance.defenses[typ].cost).
    ship_costs: dict[str, dict[str, float]] = field(default_factory=dict)
    defense_costs: dict[str, dict[str, float]] = field(default_factory=dict)
    # Markiert, ob in diesem Tick bereits eine Aufbau-Aktion lief (genau eine pro Tick).
    acted: bool = field(default=False)


class Node:
    """Basisknoten. Konkrete Knoten ueberschreiben ``tick``."""

    def tick(self, ctx: NpcContext) -> bool:  # pragma: no cover - abstrakt
        raise NotImplementedError


class Selector(Node):
    """ODER-Knoten: tickt Kinder der Reihe nach; erstes erfolgreiches gewinnt."""

    def __init__(self, *children: Node) -> None:
        self.children = children

    def tick(self, ctx: NpcContext) -> bool:
        for child in self.children:
            if child.tick(ctx):
                return True
        return False


class Sequence(Node):
    """UND-Knoten: tickt Kinder der Reihe nach; bricht beim ersten Misserfolg ab."""

    def __init__(self, *children: Node) -> None:
        self.children = children

    def tick(self, ctx: NpcContext) -> bool:
        for child in self.children:
            if not child.tick(ctx):
                return False
        return True


class Condition(Node):
    """Blatt mit Praedikat. Liefert das Ergebnis von ``predicate(ctx)``."""

    def __init__(self, predicate: Callable[[NpcContext], bool]) -> None:
        self.predicate = predicate

    def tick(self, ctx: NpcContext) -> bool:
        return bool(self.predicate(ctx))


class Action(Node):
    """Blatt mit Effekt. ``effect(ctx)`` fuehrt eine Mutation aus und meldet Erfolg."""

    def __init__(self, effect: Callable[[NpcContext], bool]) -> None:
        self.effect = effect

    def tick(self, ctx: NpcContext) -> bool:
        return bool(self.effect(ctx))
