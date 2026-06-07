"""Ableitung von Planetentyp, Temperatur und Feldern aus der Systemposition.

Die Position im System bestimmt deterministisch drei Eigenschaften (Doku 06a):
- ``planet_type`` ueber Typ-Baender (erstes Band mit ``pos <= max_pos`` gewinnt),
- ``temp_max``  ueber lineare Interpolation innen (heiss) -> aussen (kalt),
- ``fields_max`` ueber die Stuetzkurve ``field_curve`` (1 Feld je Gebaeudestufe).

Keine Zufallsquellen -> reproduzierbar. Alle Zahlen leben in ``balance.planets``."""
from __future__ import annotations

from sqlalchemy import select

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import Planet


def _planets_cfg() -> dict:
    return get_balance().planets


def homeworld_min_fields() -> int:
    """Garantiertes Mindest-Feldbudget eines Heimatplaneten (fairer Start)."""
    return int(_planets_cfg()["homeworld_min_fields"])


def derive_planet(position: int) -> dict:
    """Leitet ``{planet_type, temp_max, fields_max}`` aus der Position ab.

    Position wird auf ``1..len(field_curve)`` geklemmt. Deterministisch."""
    cfg = _planets_cfg()
    curve = cfg["field_curve"]
    n = len(curve)
    pos = max(1, min(int(position), n))

    # Felder: direkter Stuetzwert nach Index (Position 1 -> Index 0).
    fields_max = int(curve[pos - 1])

    # Typ: erstes Band, dessen max_pos die Position abdeckt.
    planet_type = "normal"
    for band in cfg["type_bands"]:
        if pos <= int(band["max_pos"]):
            planet_type = str(band["type"])
            break

    # Temperatur: linear von inner (Pos 1) nach outer (Pos n).
    inner = float(cfg["temp"]["inner"])
    outer = float(cfg["temp"]["outer"])
    temp = inner if n <= 1 else inner + (outer - inner) * (pos - 1) / (n - 1)
    temp_max = int(round(temp))

    return {"planet_type": planet_type, "temp_max": temp_max, "fields_max": fields_max}


def fields_max_for(position: int, is_homeworld: bool) -> int:
    """fields_max inkl. Heimatplanet-Mindestgrenze."""
    base = derive_planet(position)["fields_max"]
    return max(base, homeworld_min_fields()) if is_homeworld else base


async def backfill_planets() -> None:
    """Startup-Backfill: leitet fuer JEDEN Planeten Typ/Temp/Felder aus der
    Position neu ab (Heimatplanet-Minimum beachtet). Idempotent, da deterministisch."""
    async with session_scope() as session:
        planets = (await session.execute(select(Planet))).scalars().all()
        for planet in planets:
            derived = derive_planet(planet.position)
            planet.planet_type = derived["planet_type"]
            planet.temp_max = derived["temp_max"]
            planet.fields_max = fields_max_for(planet.position, planet.is_homeworld)
        await session.commit()
