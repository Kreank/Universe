"""Sensorphalanx — Scan fremder Flottenbewegungen (Voraussetzung fuers Abfangen).

Ein Spieler mit dem Gebaeude ``sensorphalanx`` kann Koordinaten in Reichweite
(``level^2 - 1`` Systeme, gleiche Galaxie) scannen und sieht alle Flottenbewegungen
ZU und VON dieser Koordinate — inkl. ``arrive_at``/``return_at``. Das liefert die ETA,
auf die ein Jaeger seinen Angriff timed. Jeder Scan kostet Deuterium am scannenden
Planeten. Flotten im Flug bleiben unantastbar; sichtbar wird nur ihr Fahrplan.
"""
from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func

from app.economy.service import refresh_resources
from app.platform.balance import get_balance
from app.platform.models import Building, Fleet, Planet, Player, Resource, Ship

log = logging.getLogger("universe.phalanx")


def phalanx_range(level: int) -> int:
    """Reichweite in Systemen = level^2 - 1 (OGame-Formel). Level 1 -> 0 (nur eigenes System)."""
    if level < 1:
        return -1
    return level * level - 1


async def _planet_at(session: AsyncSession, galaxy: int, system: int, position: int) -> Planet | None:
    return (await session.execute(
        select(Planet).where(
            Planet.galaxy == galaxy, Planet.system == system, Planet.position == position
        )
    )).scalar_one_or_none()


async def phalanx_scan(
    session: AsyncSession, player: Player, galaxy: int, system: int, position: int
) -> dict:
    """Scannt Flottenbewegungen zu/von (galaxy:system:position).

    Wirft ValueError (kein Phalanx in Reichweite) bzw. RuntimeError (zu wenig Deuterium).
    Liefert {coords, movements:[...]} — eigener ``session_scope``-frei (Router committet)."""
    bal = get_balance()
    cfg = bal.data["phalanx"]
    cost = float(cfg["scan_cost_deuterium"])

    # -- Scanner-Planet in Reichweite finden (eigener Planet mit sensorphalanx) --
    own = (await session.execute(
        select(Planet).where(Planet.player_id == player.id, Planet.galaxy == galaxy)
    )).scalars().all()
    scanner: Planet | None = None
    for p in own:
        b = await session.get(Building, (p.id, "sensorphalanx"))
        lvl = b.level if b else 0
        rng = phalanx_range(lvl)
        if rng >= 0 and abs(p.system - system) <= rng:
            scanner = p
            break
    if scanner is None:
        raise ValueError("Kein Sensorphalanx in Reichweite dieses Ziels")
    # Eigenes System ohne Bewegung zu scannen ist sinnlos, aber erlaubt.

    # -- Deuterium-Kosten am Scanner-Planeten abziehen --
    res = await refresh_resources(session, scanner)
    if res["deuterium"]["amount"] < cost:
        raise RuntimeError(f"Nicht genug Deuterium fuer den Scan (benoetigt {int(cost)})")
    deut = (await session.execute(
        select(Resource).where(Resource.planet_id == scanner.id, Resource.type == "deuterium")
    )).scalar_one_or_none()
    if deut is not None:
        deut.amount = max(0.0, deut.amount - cost)

    # -- Flotten ZU der Koordinate (Anflug/angekommen/Rueckflug) --
    target_planet = await _planet_at(session, galaxy, system, position)
    conds = [
        (Fleet.target_galaxy == galaxy) & (Fleet.target_system == system)
        & (Fleet.target_position == position)
    ]
    if target_planet is not None:
        conds.append(Fleet.origin_planet_id == target_planet.id)
    fleets = (await session.execute(
        select(Fleet).where(
            Fleet.status.in_(("flying", "arrived", "returning")),
            or_(*conds),
        ).order_by(Fleet.arrive_at.asc())
    )).scalars().all()

    movements: list[dict] = []
    for f in fleets:
        owner = await session.get(Player, f.player_id)
        origin = await session.get(Planet, f.origin_planet_id) if f.origin_planet_id else None
        tgt_coords = f"{f.target_galaxy}:{f.target_system}:{f.target_position}"
        scanned = f"{galaxy}:{system}:{position}"
        direction = "incoming" if tgt_coords == scanned else "outgoing"
        ships_total = int((await session.execute(
            select(func.coalesce(func.sum(Ship.count), 0)).where(Ship.fleet_id == f.id)
        )).scalar_one() or 0)
        movements.append({
            "id": str(f.id),
            "owner": owner.display_name if owner else "Unbekannt",
            "mission": f.mission,
            "status": f.status,
            "direction": direction,
            "origin": f"{origin.galaxy}:{origin.system}:{origin.position}" if origin else None,
            "target": tgt_coords,
            "ships_total": ships_total,
            "arrive_at": f.arrive_at.isoformat() if f.arrive_at else None,
            "return_at": f.return_at.isoformat() if f.return_at else None,
        })

    log.info("Phalanx-Scan player=%s -> %d:%d:%d (%d Bewegungen)",
             player.id, galaxy, system, position, len(movements))
    return {"coords": f"{galaxy}:{system}:{position}", "movements": movements}
