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

from app.fleet.trade import ensure_market, merchant_intel
from app.fleet.trade_index import compute_supply, count_active_players, index_prices
from app.npc.expansion import first_free_position
from app.platform.balance import get_balance
from app.platform.db import session_scope
from app.platform.models import NpcEmpire, Planet, Player, PlayerDiscovery, UniverseCell
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
    reserve = int(cfg.get("reserve_positions_per_system", 0))
    # NPC-Belegungsgrenze je System: laesst immer >= reserve Positionen fuer Spieler frei.
    npc_system_cap = max(1, max_positions - reserve)
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
            # Wächter (Welle 4) NIE eine baseline geben -> er soll nicht nachbauen/heilen.
            if npc.behavior_profile == "warden":
                continue
            if not (npc.baseline or {}):
                npc.baseline = {"fleet": dict(npc.fleet or {}), "defenses": dict(npc.defenses or {})}

        # 7b) NPC-Abbau (Muellabfuhr): verwaiste FEINDLICHE NPCs entfernen, deren naechster Spieler
        # weiter als decay.radius_systems weg ist (> Spawn-Radius -> frische/aktive NPCs nie betroffen).
        # Handelszentren (permanente Infrastruktur) ausgenommen; Schonfrist nach Spawn (min_age_seconds).
        decay_cfg = cfg.get("decay", {})
        if decay_cfg.get("enabled", False) and player_systems:
            from app.universe.service import vacate_cell
            d_radius = int(decay_cfg.get("radius_systems", 0))
            d_max = int(decay_cfg.get("max_removals_per_tick", 0))
            d_min_age = float(decay_cfg.get("min_age_seconds", 0))
            now = dt.datetime.now(dt.timezone.utc)
            removed = 0
            for npc in seeds:
                if removed >= d_max:
                    break
                if npc.behavior_profile in ("trade_center", "warden"):
                    continue  # Wächter (Welle 4) wird nie als "verwaist" entfernt
                created = npc.created_at
                if created is not None:
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=dt.timezone.utc)
                    if (now - created).total_seconds() < d_min_age:
                        continue
                nearest = min((abs(int(npc.system) - ps) for ps in player_systems), default=None)
                if nearest is not None and nearest > d_radius:
                    await vacate_cell(session, npc.galaxy, npc.system, npc.position)
                    await session.delete(npc)
                    removed += 1
            if removed:
                log.info("NPC-Decay: %d verwaiste NPC(s) entfernt (Galaxie %d)", removed, galaxy)

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
                # Reserve-Garantie: nur platzieren, wenn danach noch >= reserve Positionen frei sind.
                pos = first_free_position(occ_set, max_positions)
                if pos is not None and len(occ_set) < npc_system_cap:
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
                    # Haendler-Markt sofort initialisieren (lazy spaeter waere auch ok,
                    # aber so liefert die Auto-Discovery direkt Spec + Kurse).
                    if profile == "merchant":
                        ensure_market(npc, get_balance().trade)
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
            # Haendler: Spec + aktuelle Kurse gleich mitliefern (Spieler sieht den Markt
            # naher Haendler sofort, ohne erst handeln/spionieren zu muessen).
            if profile == "merchant":
                intel.update(merchant_intel(npc, get_balance().trade, now.isoformat()))
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


async def ensure_trade_centers() -> None:
    """Garantiert ``balance.trade.index.target_centers`` unangreifbare Handelszentren.

    Anders als die Dichte-Spawns (nahe Spielern, respawnend) sind Handelszentren feste,
    persistente Infrastruktur: ueber die Galaxien gestreut, einmal geseedet, fuer ALLE
    Spieler sichtbar (oeffentlicher globaler Kurs). Idempotent — seedet nur das Defizit
    zur Zielzahl. Profil ``trade_center`` (unangreifbar, siehe fleet/service.py)."""
    bal = get_balance()
    idx = bal.trade["index"]
    target = int(idx.get("target_centers", 0))
    if target <= 0:
        return
    galaxies = bal.galaxies
    max_systems = bal.systems_per_galaxy
    max_positions = bal.positions_per_system
    name_pool = list(idx.get("center_name_pool", []))
    rng = random.Random()
    created = 0

    async with session_scope() as session:
        existing = (await session.execute(
            select(NpcEmpire).where(NpcEmpire.behavior_profile == "trade_center")
        )).scalars().all()
        deficit = target - len(existing)
        if deficit <= 0:
            return

        used_names = {n.name for n in existing}
        # Aktuelle Index-Kurse fuer den Discovery-Snapshot (live kommt aus dem Endpoint).
        supply = await compute_supply(session)
        players = await count_active_players(session)
        prices = index_prices(supply, players, bal.trade)
        all_players = (await session.execute(select(Player.id))).scalars().all()
        now = _now()

        for n in range(deficit):
            # Galaxien gleichmaessig bestuecken; freie (system, position) suchen.
            galaxy = (len(existing) + n) % max(galaxies, 1) + 1
            placed = False
            for _attempt in range(40):
                system = rng.randint(1, max_systems)
                position = rng.randint(1, max_positions)
                name = next(
                    (nm for nm in name_pool if nm not in used_names),
                    f"Handelszentrum {galaxy}-{system}",
                )
                npc = NpcEmpire(
                    name=name,
                    behavior_profile="trade_center",
                    galaxy=galaxy,
                    system=system,
                    position=position,
                    fleet={},
                    defenses={},
                    resources={},
                    baseline={},
                    last_action_at=now,
                )
                session.add(npc)
                try:
                    async with session.begin_nested():
                        await session.flush()
                        await occupy_cell(session, galaxy, system, position, "npc", npc.id)
                except Exception:
                    session.expunge(npc)
                    continue
                used_names.add(name)
                placed = True
                # Oeffentlich sichtbar: fuer alle Spieler discovern (globaler Kurs).
                intel = {
                    "name": name,
                    "ships_total": 0,
                    "defenses_total": 0,
                    "merchant": True,
                    "trade_center": True,
                    "spec": "trade_center",
                    "prices": prices,
                    "prices_at": now.isoformat(),
                }
                for pid in all_players:
                    await _upsert_discovery(session, pid, galaxy, system, position, intel, 3, now)
                created += 1
                break
            if not placed:
                log.warning("Handelszentrum-Seed: keine freie Position in Galaxie %d", galaxy)

        await session.commit()

    if created:
        log.info("Handelszentren geseedet: %d neu (Ziel %d)", created, target)


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
