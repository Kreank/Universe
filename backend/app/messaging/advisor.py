"""Spieler-Berater (Phase 5).

Fasst den Imperiumsstatus eines Spielers aus BESTEHENDEN Daten zusammen (Planeten, Gebaeude,
Forschung, Flotte/Verteidigung + heuristische Schwachstellen) und laesst den ai-worker daraus
KONKRETE Handlungsempfehlungen generieren (Erzaehler 'advisor', flavor-Job). On-demand via
POST /api/advisor; der Rat landet als Transmission im Postfach (+ WS-Push). Keine neue LLM-Logik
im Spiel-Loop — nur Aggregation + Enqueue.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import get_building_levels, get_research_levels
from app.platform.balance import get_balance
from app.platform.models import Defense, Planet, Player, Ship

log = logging.getLogger("universe.advisor")

_KEY_RESEARCH = [
    "energy_tech", "computer_tech", "weapons_tech", "shield_tech",
    "armor_tech", "astrophysics", "spy_tech",
]


async def build_advisor_context(session: AsyncSession, player: Player) -> dict:
    """Kompakte, handlungsrelevante Zusammenfassung des Imperiums (+ Auffaelligkeiten)."""
    planets = (await session.execute(
        select(Planet).where(Planet.player_id == player.id, Planet.planet_type != "moon")
    )).scalars().all()
    research = await get_research_levels(session, player.id)

    planet_lines: list[str] = []
    issues: list[str] = []
    total_ships = 0
    total_def = 0
    for p in planets:
        b = await get_building_levels(session, p.id)
        defs = int((await session.execute(
            select(func.coalesce(func.sum(Defense.count), 0)).where(Defense.planet_id == p.id)
        )).scalar_one() or 0)
        ships = int((await session.execute(
            select(func.coalesce(func.sum(Ship.count), 0)).where(
                Ship.planet_id == p.id, Ship.fleet_id.is_(None))
        )).scalar_one() or 0)
        total_def += defs
        total_ships += ships
        coord = f"{p.galaxy}:{p.system}:{p.position}"
        planet_lines.append(
            f"{p.name} [{coord}]{' (Heimat)' if p.is_homeworld else ''}: "
            f"Felder {p.fields_used}/{p.fields_max}, "
            f"Minen M{b.get('metal_mine', 0)}/K{b.get('crystal_mine', 0)}/D{b.get('deuterium_synth', 0)}, "
            f"Solar {b.get('solar_plant', 0)}, Werft {b.get('shipyard', 0)}, Labor {b.get('research_lab', 0)}, "
            f"Verteidigung {defs}"
        )
        if defs == 0:
            issues.append(f"{coord} ist voellig unverteidigt")
        if p.fields_max and p.fields_used >= p.fields_max - 1:
            issues.append(f"{coord} ist fast voll bebaut ({p.fields_used}/{p.fields_max} Felder)")

    # Kolonie-Limit aus balance.json (Befund M-3) statt Magic-Numbers — exakt wie planets/colonize:
    # min(max_colonies, base_colonies + astro_per_level * astrophysics). Nur raten, Astrophysik zu
    # erforschen, wenn dadurch ueberhaupt noch eine Kolonie freigeschaltet wird (nicht am Hartcap).
    _bal = get_balance()
    _ccfg = _bal.data.get("colonization", {})
    _reff = _bal.data["research"].get("effects", {})
    base_colonies = int(_ccfg.get("base_colonies", 3))
    max_colonies = int(_ccfg.get("max_colonies", 20))
    per_level = int(_reff.get("astrophysics_colonies_per_level", 1))
    astro = int(research.get("astrophysics", 0))
    allowed_colonies = min(max_colonies, base_colonies + per_level * astro)
    colonies = max(0, len(planets) - 1)
    if colonies >= allowed_colonies and allowed_colonies < max_colonies:
        issues.append("Kolonie-Limit erreicht — Astrophysik erforschen fuer weitere Kolonien")
    if total_ships < 20:
        issues.append("sehr kleine Flotte — angreifbar und kaum offensivfaehig")

    return {
        "Imperium": player.display_name,
        "Imperiumswert": int(player.score or 0),
        "Planeten (Anzahl)": len(planets),
        "Planeten": " | ".join(planet_lines) or "(keine)",
        "Forschung": ", ".join(f"{k} {research.get(k, 0)}" for k in _KEY_RESEARCH),
        "Flotte gesamt (Schiffe)": total_ships,
        "Verteidigung gesamt": total_def,
        "Auffaelligkeiten": "; ".join(issues) or "keine offensichtlichen Schwachstellen",
    }


async def request_advisor(session: AsyncSession, player: Player) -> None:
    """Berater anfordern: Zustand zusammenfassen + flavor-Job (Erzaehler 'advisor') einreihen."""
    from app.platform.ai_jobs import enqueue_flavor
    detail = await build_advisor_context(session, player)
    await enqueue_flavor(
        player.id,
        narrator="advisor",
        situation="Lagebericht und Empfehlung",
        subject="🧠 Berater: Lagebericht",
        detail=detail,
    )
    log.info("Berater angefordert: player=%s planeten=%s", player.id, detail.get("Planeten (Anzahl)"))
