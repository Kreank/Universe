"""Universum-Logik: freie Zelle finden, Zellen belegen."""
from __future__ import annotations

import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import Planet, UniverseCell


async def find_free_cell(session: AsyncSession, max_tries: int = 200) -> tuple[int, int, int]:
    """Sucht eine freie (unbelegte) Zelle fuer einen neuen Heimatplaneten."""
    bal = get_balance()
    rng = random.Random()
    # Bevorzugt mittlere Positionen (4-12), wie in OGame ueblich.
    for _ in range(max_tries):
        g = rng.randint(1, bal.galaxies)
        s = rng.randint(1, bal.systems_per_galaxy)
        p = rng.randint(4, min(12, bal.positions_per_system))
        cell = (await session.execute(
            select(UniverseCell).where(
                UniverseCell.galaxy == g, UniverseCell.system == s, UniverseCell.position == p
            )
        )).scalar_one_or_none()
        if cell is not None and cell.occupant_type != "empty":
            continue
        # Zusaetzlich sicherstellen, dass kein Planet die Koordinate belegt.
        exists = (await session.execute(
            select(Planet).where(Planet.galaxy == g, Planet.system == s, Planet.position == p)
        )).scalar_one_or_none()
        if exists is None:
            return g, s, p
    raise RuntimeError("Keine freie Zelle gefunden")


async def occupy_cell(
    session: AsyncSession, galaxy: int, system: int, position: int,
    occupant_type: str, ref_id: uuid.UUID,
) -> None:
    """Belegt eine Zelle (insert oder update)."""
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == galaxy,
            UniverseCell.system == system,
            UniverseCell.position == position,
        )
    )).scalar_one_or_none()
    if cell is None:
        cell = UniverseCell(galaxy=galaxy, system=system, position=position)
        session.add(cell)
    cell.occupant_type = occupant_type
    cell.ref_id = ref_id
