"""Ableitung von Planetentyp, Temperatur und Feldern aus der Systemposition.

Die Position im System bestimmt (Doku 06a):
- ``planet_type`` ueber Typ-Baender (erstes Band mit ``pos <= max_pos`` gewinnt) — deterministisch,
- ``temp_max``  ueber lineare Interpolation innen (heiss) -> aussen (kalt) — deterministisch,
- ``fields_max`` ueber die Stuetzkurve ``field_curve`` als ZENTRUM, plus einen per Slot-Koordinate
  (galaxy:system:position) geseedeten Zufalls-Roll (``field_roll``). Dadurch hat jeder Slot eine
  feste, aber gegenueber den Nachbarn variierende Groesse: einen Max-Feld-Planeten zu erwischen ist
  Glueck. Der Seed haengt nur an der Koordinate -> der Roll ist ueber Neustarts/Backfill stabil
  (idempotent, keine Migration noetig). ``variance=0`` stellt das alte deterministische Verhalten her.

Alle Zahlen leben in ``balance.planets``."""
from __future__ import annotations

import random

from sqlalchemy import select

from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import Planet


def _planets_cfg() -> dict:
    return get_balance().planets


def homeworld_min_fields() -> int:
    """Garantiertes Mindest-Feldbudget eines Heimatplaneten (fairer Start)."""
    return int(_planets_cfg()["homeworld_min_fields"])


def _field_center(position: int) -> int:
    """Zentrum-Feldwert (Stuetzkurve) fuer eine geklemmte Position."""
    curve = _planets_cfg()["field_curve"]
    n = len(curve)
    pos = max(1, min(int(position), n))
    return int(curve[pos - 1])


def _temp_center(position: int) -> float:
    """Deterministischer Temperatur-Stuetzwert: linear inner (Pos 1) -> outer (Pos n)."""
    cfg = _planets_cfg()
    n = len(cfg["field_curve"])
    pos = max(1, min(int(position), n))
    inner = float(cfg["temp"]["inner"])
    outer = float(cfg["temp"]["outer"])
    return inner if n <= 1 else inner + (outer - inner) * (pos - 1) / (n - 1)


def rolled_temp(galaxy: int, system: int, position: int) -> int:
    """Temperatur eines Slots: Positions-Wert +/- variance, mittenlastig und per Koordinate
    geseedet (eigener Salt 'temp' -> entkoppelt vom Feld-Roll). variance 0 = deterministisch."""
    center = _temp_center(position)
    variance = float(_planets_cfg()["temp"].get("variance", 0.0))
    if variance <= 0.0:
        return int(round(center))
    rng = random.Random(f"temp:{int(galaxy)}:{int(system)}:{int(position)}")
    return int(round(rng.triangular(center - variance, center + variance, center)))


def rolled_fields(galaxy: int, system: int, position: int) -> int:
    """Tatsaechliche Feldanzahl eines Slots: mittenlastiger Roll um den Stuetzwert,
    geseedet per Koordinate -> stabil und pro Slot verschieden."""
    cfg = _planets_cfg()
    center = _field_center(position)
    roll = cfg.get("field_roll", {})
    variance = float(roll.get("variance", 0.0))
    if variance <= 0.0:
        return center  # deterministischer Fallback
    floor = int(roll.get("floor", 1))
    low = center * (1.0 - variance)
    high = center * (1.0 + variance)
    rng = random.Random(f"{int(galaxy)}:{int(system)}:{int(position)}")
    value = rng.triangular(low, high, center)  # mode=center -> Extreme selten
    return max(floor, int(round(value)))


def derive_planet(galaxy: int, system: int, position: int) -> dict:
    """Leitet ``{planet_type, temp_max, fields_max}`` aus der Position ab.

    Typ ist deterministisch (Positions-Band); ``temp_max`` und ``fields_max`` sind koordinaten-
    geseedete Rolls (feste, aber je Slot variierende Werte). Position wird auf ``1..len`` geklemmt."""
    cfg = _planets_cfg()
    n = len(cfg["field_curve"])
    pos = max(1, min(int(position), n))

    fields_max = rolled_fields(galaxy, system, position)
    temp_max = rolled_temp(galaxy, system, position)

    # Typ: erstes Band, dessen max_pos die Position abdeckt.
    planet_type = "normal"
    for band in cfg["type_bands"]:
        if pos <= int(band["max_pos"]):
            planet_type = str(band["type"])
            break

    return {"planet_type": planet_type, "temp_max": temp_max, "fields_max": fields_max}


def fields_max_for(galaxy: int, system: int, position: int, is_homeworld: bool) -> int:
    """fields_max inkl. Heimatplanet-Mindestgrenze (Glueck darf nach oben abweichen)."""
    base = rolled_fields(galaxy, system, position)
    return max(base, homeworld_min_fields()) if is_homeworld else base


async def backfill_planets() -> None:
    """Startup-Backfill: leitet fuer JEDEN Planeten Typ/Temp/Felder aus der Koordinate neu ab
    (Heimatplanet-Minimum beachtet). Idempotent, da der Feld-Roll koordinaten-geseedet ist.
    Monde haben eigene Feld-Logik (effective_fields_max) -> werden hier nicht ueberschrieben."""
    async with session_scope() as session:
        planets = (await session.execute(select(Planet))).scalars().all()
        for planet in planets:
            if planet.planet_type == "moon":
                continue
            derived = derive_planet(planet.galaxy, planet.system, planet.position)
            planet.planet_type = derived["planet_type"]
            planet.temp_max = derived["temp_max"]
            rolled = fields_max_for(
                planet.galaxy, planet.system, planet.position, planet.is_homeworld
            )
            # Etablierte Planeten nie unter ihre bereits bebauten Felder schrumpfen lassen
            # (Roll darf nur nach oben Glueck bringen, nicht bestehenden Bau entwerten).
            planet.fields_max = max(rolled, int(planet.fields_used or 0))
        await session.commit()
