"""Auth-Logik: Registrierung legt Spieler + Heimatwelt + Startzustand + Commander an."""
from __future__ import annotations

import datetime as dt
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commander.service import create_commander
from app.economy.service import RESOURCE_KEYS, refresh_resources
from app.platform.balance import get_balance
from app.platform.models import Building, Planet, Player, Resource
from app.platform.security import hash_password
from app.universe.service import find_free_cell, occupy_cell


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


async def register_player(
    session: AsyncSession, email: str, password: str, display_name: str
) -> Player:
    """Legt einen neuen Spieler mit vollstaendigem Start-Setup an (api-contract §1)."""
    bal = get_balance()
    start = bal.starting_player

    # Email-Eindeutigkeit pruefen.
    existing = (await session.execute(
        select(Player).where(Player.email == email)
    )).scalar_one_or_none()
    if existing is not None:
        raise ValueError("E-Mail bereits registriert")

    player = Player(
        email=email,
        pw_hash=hash_password(password),
        display_name=display_name,
        is_protected=True,
    )
    session.add(player)
    await session.flush()

    # Heimatplanet auf freier Zelle.
    g, s, p = await find_free_cell(session)
    planet = Planet(
        player_id=player.id,
        galaxy=g, system=s, position=p,
        name="Heimatplanet",
        is_homeworld=True,
    )
    session.add(planet)
    await session.flush()
    await occupy_cell(session, g, s, p, "player", planet.id)

    # Start-Ressourcen.
    now = _now()
    for key in RESOURCE_KEYS:
        amount = float(start["resources"].get(key, 0))
        session.add(Resource(planet_id=planet.id, type=key, amount=amount, rate=0.0, last_updated=now))

    # Start-Gebaeude.
    for btype, level in start["buildings"].items():
        session.add(Building(planet_id=planet.id, type=btype, level=level))

    await session.flush()
    # Erste Raten-Berechnung (setzt rate korrekt auf Basis der Start-Gebaeude).
    await refresh_resources(session, planet)

    # Start-Commander (balance.starting_player.commander).
    if start.get("commander", {}).get("give_starter"):
        await create_commander(
            session, player.id,
            rank_key=start["commander"].get("rank", "officer"),
            specialization=start["commander"].get("specialization", "combat"),
            status="active",
            rng=random.Random(),
        )

    return player


async def authenticate(session: AsyncSession, email: str, password: str) -> Player | None:
    from app.platform.security import verify_password

    player = (await session.execute(
        select(Player).where(Player.email == email)
    )).scalar_one_or_none()
    if player is None or not verify_password(password, player.pw_hash):
        return None
    player.last_active = _now()
    return player
