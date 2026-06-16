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

import datetime as dt
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.protection import newbie_protection_active, newbie_threshold
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

log = logging.getLogger("universe.ranking")
POINTS_DIVISOR = 1000.0

# Einmal-Warnung je unbekanntem Typ (Befund R-4): macht balance/DB-Drift sichtbar, ohne
# pro Tick/Spieler zu spammen. Ein in balance.json umbenannter/entfernter Typ wuerde sonst
# still mit 0 bewertet -> der Score eines Spielers stillschweigend zu niedrig.
_warned_unknown: set[str] = set()


def _warn_unknown(kind: str, typ: str) -> None:
    key = f"{kind}:{typ}"
    if key not in _warned_unknown:
        _warned_unknown.add(key)
        log.warning("Ranking: unbekannter %s-Typ '%s' nicht in balance.json -> mit 0 bewertet", kind, typ)


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
        _warn_unknown("building", btype)
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
        _warn_unknown("research", ttype)
        return 0.0
    base = _sum_res(cfg.get("cost", {}))
    return base * (2 ** level - 1)


def _unit_value(cfg_map: dict, utype: str, count: int) -> float:
    cfg = cfg_map.get(utype)
    if cfg is None:
        _warn_unknown("unit", utype)
        return 0.0
    if count <= 0:
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


# Wertungs-Kategorien (OGame-Stil): Gesamt + die vier Imperiumswert-Komponenten. Jede hat eine
# EIGENE Rangliste -> ein Spieler kann z. B. #1 Forschung, aber #10 Flotte sein.
CATEGORIES: tuple[str, ...] = ("total", "buildings", "research", "fleet", "defense")


def category_values(breakdowns: dict[uuid.UUID, Breakdown]) -> dict[uuid.UUID, dict[str, int]]:
    """Punkte je Kategorie und Spieler. ``total`` = Summe der vier Komponenten-Punkte (jeweils
    einzeln gefloored — konsistent mit der Anzeige, Befund R-2)."""
    out: dict[uuid.UUID, dict[str, int]] = {}
    for pid, b in breakdowns.items():
        parts = {
            "buildings": to_points(b.buildings),
            "research": to_points(b.research),
            "fleet": to_points(b.fleet),
            "defense": to_points(b.defense),
        }
        parts["total"] = sum(parts.values())
        out[pid] = parts
    return out


def ranks_in_category(values: dict[uuid.UUID, dict[str, int]], category: str) -> dict[uuid.UUID, int]:
    """ID -> 1-basierter Rang in dieser Kategorie. Gleichstand deterministisch nach ID (Befund R-3),
    damit Raenge zwischen Abrufen nicht springen."""
    ordered = sorted(values.items(), key=lambda kv: (-kv[1].get(category, 0), str(kv[0])))
    return {oid: rank for rank, (oid, _) in enumerate(ordered, start=1)}


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


def _on_vacation(player: Player, now: dt.datetime) -> bool:
    vac = player.vacation_until
    if vac is None:
        return False
    if vac.tzinfo is None:
        vac = vac.replace(tzinfo=dt.timezone.utc)
    return vac > now


async def recompute_and_store(session: AsyncSession) -> dict[uuid.UUID, Breakdown]:
    """Berechnet alle Breakdowns, schreibt den Gesamt-Score in ``Player.score`` und beendet
    den Neulingsschutz (A) fuer Spieler, die ihn ueberwachsen haben."""
    breakdowns = await compute_breakdowns(session)
    # ORDER BY player_id -> deterministische UPDATE-Reihenfolge (Befund R-7: vermeidet
    # Deadlock-Potenzial bei nebenlaeufigen Bulk-Updates).
    players = (await session.execute(select(Player).order_by(Player.id))).scalars().all()
    for p in players:
        p.score = to_points(breakdowns.get(p.id, Breakdown()).total)

    # A — dynamischer Neulingsschutz, REIN punkte-relativ (kein Zeitlimit, kein Fix-Floor).
    # Bezugsgroesse ist der Punkte-Durchschnitt der Spieler mit Punkten>0 (nicht im Urlaub) ->
    # noch-nicht-gestartete 0-Punkte-Accounts ziehen den Schnitt nicht runter, und im jungen
    # Universum (Schnitt 0) graduiert niemand. Graduierung EINMALIG (nur True->False), damit der
    # Schutz nicht an/aus flackert, wenn der Schnitt schwankt; 0-Punkte-Spieler graduieren nie
    # (Cold-Start-Schutz). Eigenes Angreifen beendet den Schutz separat sofort (combat.service).
    cfg = get_balance().protection
    now = dt.datetime.now(dt.timezone.utc)
    scored = [float(p.score) for p in players if p.score > 0 and not _on_vacation(p, now)]
    avg = (sum(scored) / len(scored)) if scored else 0.0
    for p in players:
        if not p.is_protected or _on_vacation(p, now) or p.score <= 0:
            continue
        if not newbie_protection_active(float(p.score), avg, cfg):
            p.is_protected = False
            log.info("Neulingsschutz beendet: player=%s score=%s schwelle=%.0f",
                     p.id, p.score, newbie_threshold(avg, cfg))
    return breakdowns


async def score_tick() -> None:
    """Periodischer Job: alle Spieler-Scores neu berechnen und persistieren."""
    async with session_scope() as session:
        await recompute_and_store(session)
