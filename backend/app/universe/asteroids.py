"""Asteroidenfelder: endliche, regenerierende Erz-Vorkommen im Universum.

Reichtums-Tier (gewichtet gerollt) skaliert Vorrat (capacity x mult) UND Mining-Ertrag.
Vorrat erschoepft beim Minen und regeneriert lazy (regen_ratio_per_hour x Max, gedeckelt).
Verteilung: pro Galaxie wird eine Ziel-Dichte (density_per_galaxy) auf leeren Zellen geseedet.

Reine Logik (roll_richness/field_capacity/apply_regen/mine_from_field) ist DB-frei und
direkt testbar; die ``async``-Funktionen kapseln nur das Seeding/Persistieren."""
from __future__ import annotations

import datetime as dt
import logging
import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import AsteroidField, UniverseCell
from app.universe.service import occupy_cell

log = logging.getLogger("universe.asteroids")


def _cfg() -> dict:
    return get_balance().data.get("asteroids", {})


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# -- Reine Logik ----------------------------------------------------------------

def roll_richness(rng: random.Random, cfg: dict | None = None) -> tuple[str, float]:
    """Gewichtete Wahl eines Reichtums-Tiers -> (name, mult)."""
    cfg = cfg if cfg is not None else _cfg()
    tiers = cfg.get("richness_tiers") or [{"name": "normal", "weight": 1, "mult": 1.0}]
    total = sum(float(t.get("weight", 0)) for t in tiers) or 1.0
    pick = rng.random() * total
    acc = 0.0
    for t in tiers:
        acc += float(t.get("weight", 0))
        if pick <= acc:
            return str(t.get("name", "normal")), float(t.get("mult", 1.0))
    last = tiers[-1]
    return str(last.get("name", "normal")), float(last.get("mult", 1.0))


def field_capacity(mult: float, cfg: dict | None = None) -> tuple[float, float]:
    """Max-Vorrat eines Feldes = capacity x Reichtums-Multiplikator."""
    cfg = cfg if cfg is not None else _cfg()
    cap = cfg.get("capacity", {})
    return float(cap.get("metal", 0)) * mult, float(cap.get("crystal", 0)) * mult


def apply_regen(
    metal_remaining: float, crystal_remaining: float,
    metal_max: float, crystal_max: float,
    hours: float, regen_ratio_per_hour: float,
) -> tuple[float, float]:
    """Lazy-Regeneration: + regen_ratio x Max je Stunde, gedeckelt auf Max."""
    if hours <= 0 or regen_ratio_per_hour <= 0:
        return metal_remaining, crystal_remaining
    m = min(metal_max, metal_remaining + metal_max * regen_ratio_per_hour * hours)
    c = min(crystal_max, crystal_remaining + crystal_max * regen_ratio_per_hour * hours)
    return m, c


def mine_from_field(
    miners: int, base_yield: dict, mult: float,
    metal_remaining: float, crystal_remaining: float,
    cargo_capacity: float,
) -> tuple[dict[str, float], float, float]:
    """Ertrag = miners x base_yield x Reichtum, gedeckelt durch Restvorrat UND Fracht
    (Metall zuerst, dann Kristall). Liefert (gewonnen, neuer_metal_rest, neuer_crystal_rest)."""
    remaining_cargo = max(0.0, float(cargo_capacity))
    gained = {"metal": 0.0, "crystal": 0.0}
    stock = {"metal": metal_remaining, "crystal": crystal_remaining}
    for key in ("metal", "crystal"):
        want = miners * float(base_yield.get(key, 0)) * mult
        take = min(want, max(0.0, stock[key]), remaining_cargo)
        gained[key] = round(take, 1)
        stock[key] -= take
        remaining_cargo -= take
    return gained, round(stock["metal"], 1), round(stock["crystal"], 1)


# -- DB: Regeneration eines Feldes ----------------------------------------------

def regen_field(field: AsteroidField) -> None:
    """Wendet die seit ``last_regen_at`` aufgelaufene Regeneration an (in-place)."""
    last = field.last_regen_at or _now()
    if last.tzinfo is None:
        last = last.replace(tzinfo=dt.timezone.utc)
    hours = max(0.0, (_now() - last).total_seconds() / 3600.0)
    ratio = float(_cfg().get("regen_ratio_per_hour", 0.0))
    field.metal_remaining, field.crystal_remaining = apply_regen(
        field.metal_remaining, field.crystal_remaining,
        field.metal_max, field.crystal_max, hours, ratio,
    )
    field.last_regen_at = _now()


# -- DB: Seeding ----------------------------------------------------------------

async def _occupied_positions(session: AsyncSession, galaxy: int, system: int) -> set[int]:
    rows = (await session.execute(
        select(UniverseCell.position).where(
            UniverseCell.galaxy == galaxy,
            UniverseCell.system == system,
            UniverseCell.occupant_type != "empty",
        )
    )).scalars().all()
    return set(rows)


async def ensure_asteroid_fields(session: AsyncSession | None = None) -> int:
    """Stellt je Galaxie die Ziel-Dichte an Asteroidenfeldern her (idempotent: spawnt nur
    das Defizit auf freien Zellen). Liefert die Anzahl neu erzeugter Felder."""
    from app.platform.db import session_scope
    if session is None:
        async with session_scope() as s:
            n = await ensure_asteroid_fields(s)
            await s.commit()
            return n

    bal = get_balance()
    cfg = _cfg()
    target = int(cfg.get("density_per_galaxy", 0))
    if target <= 0:
        return 0
    pos_min = int(cfg.get("position_min", 1))
    pos_max = int(cfg.get("position_max", bal.positions_per_system))
    rng = random.Random()
    created = 0

    for g in range(1, bal.galaxies + 1):
        have = int((await session.execute(
            select(func.count()).select_from(AsteroidField).where(AsteroidField.galaxy == g)
        )).scalar() or 0)
        deficit = target - have
        if deficit <= 0:
            continue
        spawned = 0
        tries = 0
        max_tries = deficit * 20 + 50
        occ_cache: dict[int, set[int]] = {}
        while spawned < deficit and tries < max_tries:
            tries += 1
            s_idx = rng.randint(1, bal.systems_per_galaxy)
            p = rng.randint(pos_min, pos_max)
            occ = occ_cache.get(s_idx)
            if occ is None:
                occ = await _occupied_positions(session, g, s_idx)
                occ_cache[s_idx] = occ
            if p in occ:
                continue
            occ.add(p)  # innerhalb dieses Laufs nicht doppelt belegen
            name, mult = roll_richness(rng, cfg)
            m_max, c_max = field_capacity(mult, cfg)
            field = AsteroidField(
                galaxy=g, system=s_idx, position=p,
                richness=name, mult=mult,
                metal_remaining=m_max, crystal_remaining=c_max,
                metal_max=m_max, crystal_max=c_max,
            )
            session.add(field)
            await session.flush()
            await occupy_cell(session, g, s_idx, p, "asteroid_field", field.id)
            spawned += 1
            created += 1

    if created:
        log.info("Asteroiden-Seeding: %d neue Felder erzeugt", created)
    return created
