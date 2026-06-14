"""Flotten-Upkeep — die fehlende OGame-Anti-Snowball-Bremse (ewiges Universum).

Über einer Versorgungskapazität (skaliert mit der Zahl der Planeten) kosten stationierte/
fliegende Schiffe pro Stunde Deuterium. Riesenflotten im Dauer-Standby werden so teuer →
einsetzen oder abrüsten, statt unbegrenzt zu horten. Die Kapazität ist NICHT kaufbar →
P2W-frei. Bewusst diskreter Stunden-Job (kein Eingriff in die Lazy-Accrual, ADR-002).

Neulinge mit 1–2 Planeten liegen praktisch immer unter der Kapazität → zahlen nie Upkeep;
die Bremse trifft gezielt die ganz großen Veteranen-Flotten."""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import Fleet, Planet, Player, Resource, Ship

log = logging.getLogger("universe.upkeep")

# Stationaere/Nicht-Kampf-Einheiten zahlen keinen Flotten-Upkeep.
_EXEMPT = ("solar_satellite",)


def supply_capacity(num_planets: int, cfg: dict) -> int:
    """Kostenlose Flotten-Versorgungskapazität (Schiffe) eines Spielers."""
    return int(cfg.get("supply_base", 500)) + int(cfg.get("supply_per_planet", 200)) * max(0, num_planets)


def upkeep_deut(unit_count: int, capacity: int, cfg: dict) -> float:
    """Deuterium-Upkeep pro Stunde: nur Einheiten ÜBER der Kapazität kosten."""
    excess = max(0, int(unit_count) - int(capacity))
    return round(excess * float(cfg.get("deut_per_excess_unit_per_hour", 0.5)), 2)


async def fleet_upkeep_tick() -> None:
    """Stündlicher Job: zieht Deuterium-Upkeep großer Flotten vom Heimatplaneten ab."""
    cfg = get_balance().data.get("fleet", {}).get("upkeep", {})
    if not cfg.get("enabled"):
        return
    from app.economy.service import refresh_resources

    charged = 0
    async with session_scope() as session:
        players = (await session.execute(select(Player.id))).scalars().all()
        for pid in players:
            num_planets = int((await session.execute(
                select(func.count(Planet.id)).where(
                    Planet.player_id == pid, Planet.planet_type != "moon"
                )
            )).scalar() or 0)
            # Schiffe auf eigenen Planeten + in eigenen Flotten (ohne stationaere Einheiten).
            on_planets = int((await session.execute(
                select(func.coalesce(func.sum(Ship.count), 0))
                .join(Planet, Ship.planet_id == Planet.id)
                .where(Planet.player_id == pid, Ship.type.not_in(_EXEMPT))
            )).scalar() or 0)
            in_fleets = int((await session.execute(
                select(func.coalesce(func.sum(Ship.count), 0))
                .join(Fleet, Ship.fleet_id == Fleet.id)
                .where(Fleet.player_id == pid, Ship.type.not_in(_EXEMPT))
            )).scalar() or 0)
            units = on_planets + in_fleets
            cap = supply_capacity(num_planets, cfg)
            cost = upkeep_deut(units, cap, cfg)
            if cost <= 0:
                continue
            # Heimatplanet (Deuterium-Quelle des Upkeeps).
            home = (await session.execute(
                select(Planet)
                .where(Planet.player_id == pid, Planet.planet_type != "moon")
                .order_by(Planet.is_homeworld.desc(), Planet.created_at)
            )).scalars().first()
            if home is None:
                continue
            await refresh_resources(session, home)
            deut = (await session.execute(
                select(Resource).where(
                    Resource.planet_id == home.id, Resource.type == "deuterium"
                )
            )).scalar_one_or_none()
            if deut is not None:
                deut.amount = max(0.0, float(deut.amount) - cost)
                charged += 1
        await session.commit()
    if charged:
        log.info("Flotten-Upkeep abgezogen bei %s Spieler(n)", charged)
