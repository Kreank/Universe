"""Ranglisten-/Punktesystem (OGame-Stil).

Punkte = **aktueller Imperiumswert** / ``POINTS_DIVISOR``: die in Gebaeude-Stufen,
Forschung, Schiffe (Garnison + fliegend + stationiert) und Verteidigung investierten
Ressourcen (Metall + Kristall + Deuterium). Selbstkorrigierend — verlorene Flotten
oder zerstoerte Gebaeude senken die Punkte automatisch, da immer aus dem aktuellen
Besitz gerechnet wird. 1000 Ressourcen = 1 Punkt.

Gebaeude-Stufenkosten = ``base * factor^(stufe)`` (siehe buildings.service); die bis
Stufe N investierte Summe ist die geometrische Reihe ``base * (factor^N - 1)/(factor - 1)``.
Forschung = ``base * 2^(stufe)`` -> kumuliert ``base * (2^N - 1)``."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import (
    Building,
    Defense,
    Fleet,
    Planet,
    Player,
    Research,
    Ship,
    StationedFleet,
)

POINTS_DIVISOR = 1000.0


def _sum_res(cost: dict) -> float:
    """Summe Metall+Kristall+Deuterium eines Kosten-Dicts (Energie zaehlt nicht)."""
    return (
        float(cost.get("metal", 0))
        + float(cost.get("crystal", 0))
        + float(cost.get("deuterium", 0))
    )


def _cumulative_building_value(btype: str, level: int) -> float:
    if level <= 0:
        return 0.0
    cfg = get_balance().buildings.get(btype)
    if not cfg:
        return 0.0
    factor = float(cfg.get("factor", 1.0))
    base = _sum_res(cfg.get("cost", {}))
    if factor == 1.0:
        return base * level
    return base * (factor ** level - 1) / (factor - 1)


def _cumulative_research_value(ttype: str, level: int) -> float:
    if level <= 0:
        return 0.0
    cfg = get_balance().techs.get(ttype)
    if not cfg:
        return 0.0
    base = _sum_res(cfg.get("cost", {}))
    return base * (2 ** level - 1)


def _unit_value(cfg_map: dict, utype: str, count: int) -> float:
    cfg = cfg_map.get(utype)
    if not cfg or count <= 0:
        return 0.0
    return _sum_res(cfg.get("cost", {})) * count


@dataclass
class Breakdown:
    buildings: float = 0.0
    research: float = 0.0
    fleet: float = 0.0
    defense: float = 0.0

    @property
    def total(self) -> float:
        return self.buildings + self.research + self.fleet + self.defense


def to_points(resources: float) -> int:
    """Investierte Ressourcen -> Punkte (1000 Ress = 1 Punkt, abgerundet)."""
    return int(resources // POINTS_DIVISOR)


async def compute_breakdowns(session: AsyncSession) -> dict[uuid.UUID, Breakdown]:
    """Berechnet den Imperiumswert je Spieler (eine Sammel-Abfrage je Tabelle)."""
    bal = get_balance()

    planet_owner: dict[uuid.UUID, uuid.UUID] = {
        pid: owner
        for pid, owner in (await session.execute(select(Planet.id, Planet.player_id))).all()
    }
    fleet_owner: dict[uuid.UUID, uuid.UUID] = {
        fid: owner
        for fid, owner in (await session.execute(select(Fleet.id, Fleet.player_id))).all()
    }

    out: dict[uuid.UUID, Breakdown] = {}

    def bd(owner: uuid.UUID | None) -> Breakdown | None:
        if owner is None:
            return None
        return out.setdefault(owner, Breakdown())

    # Auch Spieler ohne Besitz sollen mit 0 in der Rangliste erscheinen.
    for (pid,) in (await session.execute(select(Player.id))).all():
        out.setdefault(pid, Breakdown())

    for planet_id, btype, level in (
        await session.execute(select(Building.planet_id, Building.type, Building.level))
    ).all():
        b = bd(planet_owner.get(planet_id))
        if b:
            b.buildings += _cumulative_building_value(btype, level)

    for player_id, ttype, level in (
        await session.execute(select(Research.player_id, Research.type, Research.level))
    ).all():
        b = bd(player_id)
        if b:
            b.research += _cumulative_research_value(ttype, level)

    # Schiffe: in Planet-Garnison (planet_id) ODER in einer Flotte (fleet_id).
    for planet_id, fleet_id, stype, count in (
        await session.execute(select(Ship.planet_id, Ship.fleet_id, Ship.type, Ship.count))
    ).all():
        owner = planet_owner.get(planet_id) if planet_id else fleet_owner.get(fleet_id)
        b = bd(owner)
        if b:
            b.fleet += _unit_value(bal.ships, stype, count)

    # Stationierte Eskort-/Patrouillenflotten (ships als JSONB {type: count}).
    for owner_id, ships in (
        await session.execute(select(StationedFleet.owner_id, StationedFleet.ships))
    ).all():
        b = bd(owner_id)
        if b and isinstance(ships, dict):
            for stype, count in ships.items():
                b.fleet += _unit_value(bal.ships, stype, int(count or 0))

    for planet_id, dtype, count in (
        await session.execute(select(Defense.planet_id, Defense.type, Defense.count))
    ).all():
        b = bd(planet_owner.get(planet_id))
        if b:
            b.defense += _unit_value(bal.defenses, dtype, count)

    return out


async def recompute_and_store(session: AsyncSession) -> dict[uuid.UUID, Breakdown]:
    """Berechnet alle Breakdowns und schreibt den Gesamt-Score in ``Player.score``."""
    breakdowns = await compute_breakdowns(session)
    players = (await session.execute(select(Player))).scalars().all()
    for p in players:
        p.score = to_points(breakdowns.get(p.id, Breakdown()).total)
    return breakdowns


async def score_tick() -> None:
    """Periodischer Job: alle Spieler-Scores neu berechnen und persistieren."""
    async with session_scope() as session:
        await recompute_and_store(session)
