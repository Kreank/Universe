"""NPC-Populations-Spawner: haelt das Universum NAHE bei Spielern lebendig (Doku 08).

Waehrend ``npc/service.py`` bestehende NPCs leben laesst (Garnison-Wiederaufbau,
Angriff, Expansion), sorgt dieser Tick fuer NACHSCHUB: er zaehlt je Spieler die
NPC-Dichte im Umkreis (``radius_systems``) und spawnt bei Defizit neue NPC-Imperien
mit gemischten Profilen (gewichtete Zufallswahl). Zerstoerte NPCs werden so ueber die
Zeit nachgespawnt, ohne dass die Gesamtdichte ueber das Ziel hinaus waechst.

Determinismus-Grenze: Im Gegensatz zum Behavior-Tick nutzt der Spawner BEWUSST
``random`` (Profilwahl, Zielsystem) -- ein lebendiges Universum soll nicht
vorhersehbar gerastert sein. Die Kernrechnung (Dichte/Defizit, gewichtete Wahl,
Namensvergabe) ist als reine, DB-freie Funktion ausgelagert und damit testbar.

JSONB-Felder werden als NEUE dict-Objekte gesetzt (SQLAlchemy-Change-Tracking).
"""
from __future__ import annotations

import datetime as dt
import logging
import random

from sqlalchemy import select

from app.npc.expansion import first_free_position
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import NpcEmpire, Planet, PlayerDiscovery, UniverseCell
from app.universe.service import occupy_cell

log = logging.getLogger("universe.npc")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# ---------------------------------------------------------------------------
# Reine, DB-/FastAPI-freie Hilfsfunktionen (testbar)
# ---------------------------------------------------------------------------

def _weighted_profile(weights: dict[str, float], rnd: float) -> str:
    """Deterministische gewichtete Profil-Wahl fuer ``rnd`` in [0, 1).

    Die Gewichte werden auf ihre Summe normiert (robust gegen Summen != 1.0).
    ``rnd=0`` liefert das erste Profil, ``rnd`` nahe 1 das letzte. Leere/0-Gewichte
    -> Fallback auf das erste Profil bzw. ``"defensive"``."""
    items = [(name, float(w)) for name, w in weights.items() if float(w) > 0]
    if not items:
        return "defensive"
    total = sum(w for _, w in items)
    # rnd auf [0, total) skalieren und das passende Band finden.
    threshold = max(0.0, min(rnd, 0.999999)) * total
    cumulative = 0.0
    for name, w in items:
        cumulative += w
        if threshold < cumulative:
            return name
    return items[-1][0]


def _density_deficit(
    player_systems: list[int], npc_systems: list[int], cfg: dict
) -> int:
    """Gesamt-Spawn-Bedarf diesen Tick (reine Rechnung, gedeckelt).

    Fuer jeden Spieler wird die Anzahl NPCs im Umkreis ``radius_systems`` gezaehlt;
    das Defizit zur Zielzahl ``target_per_player`` (>= 0) wird aufsummiert. Damit
    sich nahe beieinander liegende Spieler dieselben NPCs teilen, wird das Defizit
    NICHT mehrfach voll gewertet, sondern als Maximum der Einzeldefizite genommen
    (verhindert Ueberspawn in dichten Spieler-Clustern). Ergebnis ist auf
    ``max_spawns_per_tick`` gedeckelt."""
    radius = int(cfg.get("radius_systems", 0))
    target = int(cfg.get("target_per_player", 0))
    cap = int(cfg.get("max_spawns_per_tick", 0))
    if not player_systems or target <= 0:
        return 0
    max_deficit = 0
    for psys in player_systems:
        count = sum(1 for nsys in npc_systems if abs(nsys - psys) <= radius)
        deficit = max(0, target - count)
        if deficit > max_deficit:
            max_deficit = deficit
    return min(max_deficit, cap)


def _underserved_players(
    player_systems: list[int], npc_systems: list[int], cfg: dict
) -> list[int]:
    """Spieler-Systeme mit Dichte-Defizit (Kandidaten fuer Spawn-Platzierung)."""
    radius = int(cfg.get("radius_systems", 0))
    target = int(cfg.get("target_per_player", 0))
    out: list[int] = []
    for psys in player_systems:
        count = sum(1 for nsys in npc_systems if abs(nsys - psys) <= radius)
        if target - count > 0:
            out.append(psys)
    return out


def _pick_name(profile: str, templates: dict, used_names: set[str], designation: int) -> str:
    """Eindeutiger NPC-Name aus dem Profil-Namenspool + fortlaufender Kennung.

    Basis = ein noch unbenutzter Pool-Eintrag (sonst der erste); angehaengt wird eine
    numerische Designation, damit auch bei erschoepftem Pool kein Duplikat entsteht.
    ``used_names`` wird vom Aufrufer ueber mehrere Spawns hinweg fortgefuehrt."""
    pool = list(templates.get(profile, {}).get("name_pool", [])) or [profile.capitalize()]
    base = next((n for n in pool if n not in used_names), pool[0])
    name = f"{base} {designation}"
    # Falls die kombinierte Kennung doch kollidiert, hochzaehlen.
    while name in used_names:
        designation += 1
        name = f"{base} {designation}"
    used_names.add(name)
    return name


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


# ---------------------------------------------------------------------------
# Async-Tick (Orchestrierung)
# ---------------------------------------------------------------------------

async def npc_population_tick() -> None:
    """Periodischer Job (balance.npc.population.tick_interval_seconds).

    Haelt nahe bei Spielern eine Ziel-NPC-Dichte, spawnt gemischte Profile und macht
    neue NPCs im Umkreis sofort sichtbar (Auto-Discovery). Direkt aufrufbar (Tests).
    Bei ``population.enabled == False`` -> frueher Return."""
    bal = get_balance()
    cfg = bal.npc.get("population", {})
    if not cfg.get("enabled"):
        return

    galaxy = int(cfg["galaxy"])
    max_systems = bal.systems_per_galaxy
    max_positions = bal.positions_per_system
    radius = int(cfg.get("radius_systems", 0))
    auto_radius = int(cfg.get("auto_discover_radius", 0))
    templates = cfg.get("templates", {})
    weights = cfg.get("profile_weights", {})

    spawned = 0

    async with session_scope() as session:
        # 1) Spieler-Planeten dieser Galaxie -> ohne Spieler nichts zu beleben.
        player_rows = (await session.execute(
            select(Planet.player_id, Planet.system).where(Planet.galaxy == galaxy)
        )).all()
        if not player_rows:
            return
        player_systems = [int(s) for _pid, s in player_rows]
        # (player_id, system) je Planet -- fuer die Auto-Discovery pro Spieler.
        player_planets = [(pid, int(s)) for pid, s in player_rows]

        # 2) Belegte Zellen der Galaxie laden (!= empty): Positionsset je System + NPC-Dichte.
        cell_rows = (await session.execute(
            select(UniverseCell.system, UniverseCell.position, UniverseCell.occupant_type).where(
                UniverseCell.galaxy == galaxy, UniverseCell.occupant_type != "empty"
            )
        )).all()
        occupied: dict[int, set[int]] = {}
        npc_systems: list[int] = []
        for s, p, otype in cell_rows:
            occupied.setdefault(int(s), set()).add(int(p))
            if otype == "npc":
                npc_systems.append(int(s))
        # Spieler-Planeten belegen ebenfalls Positionen (Zelle ggf. noch nicht angelegt).
        for _pid, psys in player_rows:
            occupied.setdefault(int(psys), set())  # System sicher im Dict
        planet_pos = (await session.execute(
            select(Planet.system, Planet.position).where(Planet.galaxy == galaxy)
        )).all()
        for s, p in planet_pos:
            occupied.setdefault(int(s), set()).add(int(p))

        # 7) BONUS: einmaliger Backfill -- Seeds ohne baseline bauen sonst nie nach.
        seeds = (await session.execute(
            select(NpcEmpire).where(NpcEmpire.galaxy == galaxy)
        )).scalars().all()
        for npc in seeds:
            if not (npc.baseline or {}):
                npc.baseline = {"fleet": dict(npc.fleet or {}), "defenses": dict(npc.defenses or {})}

        # 4) Wie viele NPCs sind zu spawnen? (Dichte-Defizit, gedeckelt)
        to_spawn = _density_deficit(player_systems, list(npc_systems), cfg)
        candidates = _underserved_players(player_systems, list(npc_systems), cfg)
        if to_spawn <= 0 or not candidates:
            await session.commit()
            return

        used_names: set[str] = set()
        rng = random.Random()

        # 5) Spawns platzieren.
        for i in range(to_spawn):
            profile = _weighted_profile(weights, rng.random())
            tpl = templates.get(profile)
            if not tpl:  # Profil ohne Template -> ueberspringen (Config-Luecke)
                continue

            # Zielsystem nahe einem unterversorgten Spieler suchen (begrenzte Versuche).
            anchor = candidates[i % len(candidates)]
            system = None
            position = None
            for _attempt in range(8):
                cand_sys = _clamp(
                    anchor + rng.randint(-radius, radius), 1, max_systems
                )
                occ_set = occupied.setdefault(cand_sys, set())
                pos = first_free_position(occ_set, max_positions)
                if pos is not None:
                    system, position = cand_sys, pos
                    break
            if system is None:  # alle Versuche voll -> diesen Spawn ueberspringen
                continue

            # Belegt-Set SOFORT aktualisieren (kein Doppel-Spawn im selben Tick).
            occupied[system].add(position)

            fleet = dict(tpl.get("fleet", {}))
            defenses = dict(tpl.get("defenses", {}))
            resources = dict(tpl.get("resources", {}))
            name = _pick_name(profile, templates, used_names, designation=system * 100 + position)
            now = _now()

            npc = NpcEmpire(
                name=name,
                behavior_profile=profile,
                galaxy=galaxy,
                system=system,
                position=position,
                fleet=fleet,
                defenses=defenses,
                resources=resources,
                # baseline = Template-Soll, sonst baut der Behavior-Tree nicht nach.
                baseline={"fleet": dict(fleet), "defenses": dict(defenses)},
                last_action_at=now,
            )
            session.add(npc)
            try:
                # SAVEPOINT: bei Race (parallele Belegung) nur DIESEN Spawn verwerfen,
                # nicht den ganzen Tick (Seeds-Backfill + vorige Spawns bleiben erhalten).
                async with session.begin_nested():
                    await session.flush()  # npc.id fuer occupy_cell
                    await occupy_cell(session, galaxy, system, position, "npc", npc.id)
            except Exception:
                log.warning(
                    "Populations-Spawn uebersprungen (Konflikt) @ %d:%d:%d",
                    galaxy, system, position,
                )
                # npc wurde VOR dem Savepoint zur Session hinzugefuegt -> nach dem
                # Savepoint-Rollback bliebe es "pending" und wuerde beim finalen Commit
                # als verwaister NPC ohne Zelle re-inserted. Explizit entfernen.
                session.expunge(npc)
                continue

            # Auto-Discovery: NPC fuer nahe Spieler sofort sichtbar machen.
            ships_total = sum(fleet.values())
            defenses_total = sum(defenses.values())
            intel = {
                "name": name,
                "ships_total": ships_total,
                "defenses_total": defenses_total,
            }
            level = 1 + ships_total // 10
            for pid, psys in player_planets:
                if abs(psys - system) > auto_radius:
                    continue
                await _upsert_discovery(
                    session, pid, galaxy, system, position, intel, level, now
                )

            spawned += 1

        await session.commit()

    log.info("NPC-Populations-Tick: %d NPC(s) gespawnt (Galaxie %d)", spawned, galaxy)


async def _upsert_discovery(
    session, player_id, galaxy: int, system: int, position: int,
    intel: dict, level: int, now: dt.datetime,
) -> None:
    """Discovery-Upsert nach (player_id, galaxy, system, position) -- wie spionage.py."""
    disc = (await session.execute(
        select(PlayerDiscovery).where(
            PlayerDiscovery.player_id == player_id,
            PlayerDiscovery.galaxy == galaxy,
            PlayerDiscovery.system == system,
            PlayerDiscovery.position == position,
        )
    )).scalar_one_or_none()
    if disc is None:
        disc = PlayerDiscovery(
            player_id=player_id, galaxy=galaxy, system=system, position=position
        )
        session.add(disc)
    disc.intel = intel
    disc.level = level
    disc.discovered_at = now
