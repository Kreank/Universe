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

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.models import AsteroidField, UniverseCell

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
    metal_remaining: float, crystal_remaining: float, cargo_capacity: float,
) -> tuple[dict[str, float], float, float]:
    """Modell 'fuelle deinen Frachtraum': Die Flotte baut so viel ab, wie ihr Frachtraum fasst,
    gedeckelt durch den Restvorrat des Feldes. Metall/Kristall kommen ANTEILIG zur Zusammensetzung
    des Feld-Vorrats heim; der Rest bleibt im Feld. Liefert (gewonnen, metal_rest, crystal_rest)."""
    cap = max(0.0, float(cargo_capacity))
    am = max(0.0, float(metal_remaining))
    ac = max(0.0, float(crystal_remaining))
    avail = am + ac
    take = min(cap, avail)
    if avail > 0:
        take_metal = take * am / avail
        take_crystal = take - take_metal
    else:
        take_metal = take_crystal = 0.0
    gained = {"metal": round(take_metal, 1), "crystal": round(take_crystal, 1)}
    return gained, round(am - gained["metal"], 1), round(ac - gained["crystal"], 1)


# -- DB: Regeneration eines Feldes ----------------------------------------------

def projected_remaining(field: AsteroidField) -> tuple[float, float]:
    """Aktueller Vorrat inkl. der seit ``last_regen_at`` aufgelaufenen Regeneration — OHNE das
    Feld zu mutieren. Fuer die Galaxie-Anzeige, damit man das Feld wirklich nachwachsen sieht."""
    last = field.last_regen_at or _now()
    if last.tzinfo is None:
        last = last.replace(tzinfo=dt.timezone.utc)
    hours = max(0.0, (_now() - last).total_seconds() / 3600.0)
    ratio = float(_cfg().get("regen_ratio_per_hour", 0.0))
    return apply_regen(
        field.metal_remaining, field.crystal_remaining,
        field.metal_max, field.crystal_max, hours, ratio,
    )


def regen_field(field: AsteroidField) -> None:
    """Wendet die seit ``last_regen_at`` aufgelaufene Regeneration an (in-place)."""
    field.metal_remaining, field.crystal_remaining = projected_remaining(field)
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
    """Stellt je Galaxie die Ziel-Dichte an Asteroidenfeldern her (idempotent: spawnt nur das
    Defizit). Asteroidenfelder sind ein OVERLAY (eigene Tabelle, geteilt mit der Position wie ein
    Mond) — sie belegen die Zelle NICHT und blockieren keine Kolonisierung. Liefert neu erzeugte Felder."""
    from app.platform.db import session_scope
    if session is None:
        async with session_scope() as s:
            n = await ensure_asteroid_fields(s)
            await s.commit()
            return n

    bal = get_balance()
    cfg = _cfg()

    # Einmalige Normalisierung: frueher belegten Asteroiden die Zelle (occupant 'asteroid_field').
    # Jetzt Overlay -> Zelle zurueck auf 'empty' (Feld lebt in asteroid_fields, per Koordinate).
    await session.execute(
        update(UniverseCell)
        .where(UniverseCell.occupant_type == "asteroid_field")
        .values(occupant_type="empty", ref_id=None)
    )

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
        # Bereits belegte Asteroiden-Koordinaten dieser Galaxie (UNIQUE-Schutz, kein Doppel-Spawn).
        existing = {
            (s, p) for s, p in (await session.execute(
                select(AsteroidField.system, AsteroidField.position).where(AsteroidField.galaxy == g)
            )).all()
        }
        spawned = 0
        tries = 0
        max_tries = deficit * 20 + 50
        occ_cache: dict[int, set[int]] = {}
        while spawned < deficit and tries < max_tries:
            tries += 1
            s_idx = rng.randint(1, bal.systems_per_galaxy)
            p = rng.randint(pos_min, pos_max)
            if (s_idx, p) in existing:
                continue
            occ = occ_cache.get(s_idx)
            if occ is None:
                occ = await _occupied_positions(session, g, s_idx)
                occ_cache[s_idx] = occ
            if p in occ:
                continue  # bevorzugt freie Sektoren beim Seeden (kein Spawn auf Planet/NPC)
            existing.add((s_idx, p))
            name, mult = roll_richness(rng, cfg)
            m_max, c_max = field_capacity(mult, cfg)
            session.add(AsteroidField(
                galaxy=g, system=s_idx, position=p,
                richness=name, mult=mult,
                metal_remaining=m_max, crystal_remaining=c_max,
                metal_max=m_max, crystal_max=c_max,
            ))
            spawned += 1
            created += 1

    if created:
        log.info("Asteroiden-Seeding: %d neue Felder erzeugt", created)
    return created
