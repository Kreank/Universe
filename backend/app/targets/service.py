"""Auswahl-/Sortierlogik fuer den Ziele/Bedrohungen-Screen (Welle 1).

Trennt REINE, DB-freie Helfer (Aufbau eines Eintrags, Distanz, Sortierung,
Bedrohungs-Zusammenstellung) von den DB-Joins (``list_*``-Funktionen). Die reinen
Helfer sind in tests/test_targets.py ohne DB/Engine getestet. Die DB-Funktionen
nutzen vorhandene Logik wieder: ``_player_discoveries`` (universe.router) und
``list_incoming_attacks`` (fleet.service)."""
from __future__ import annotations

import datetime as _dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.models import NpcEmpire, NpcRelation, Planet, Player

# Reihenfolge der Diplomatie-Status fuer die NPC-Ziel-Sortierung: feindlich zuerst,
# Pakte/Buendnisse (sollte man NICHT angreifen) zuletzt. None == nie kontaktiert -> neutral.
NPC_STATUS_ORDER: dict[str | None, int] = {
    "hostile": 0,
    "broken_pact": 1,
    "neutral": 2,
    None: 2,
    "ceasefire": 3,
    "allied": 4,
}

# Handelszentren leben im Handel-Reiter, nicht in der Ziel-Liste (nicht angreifbar).
EXCLUDED_NPC_PROFILES = ("trade_center",)

# Feindliche NPCs gelten als "nah" (latente Bedrohung), wenn ihre Galaxien-Distanz
# zum naechsten eigenen Planeten <= diesem Wert ist.
HOSTILE_NPC_NEAR_GALAXIES = 1

# Sehr grosse Ersatz-Distanz, damit Eintraege ohne ermittelbare Distanz nach hinten sortieren.
_FAR = 10**9


# --------------------------------------------------------------- reine Helfer

def galaxy_distance(home_galaxy: int | None, galaxy: int) -> int | None:
    """Galaxien-Distanz zur Heimat (None, wenn keine Heimat-Galaxie bekannt)."""
    if home_galaxy is None:
        return None
    return abs(int(home_galaxy) - int(galaxy))


def is_attackable_npc(behavior_profile: str | None) -> bool:
    """True, wenn das NPC ein relevantes Angriffsziel ist (KEIN Handelszentrum)."""
    return (behavior_profile or "") not in EXCLUDED_NPC_PROFILES


def is_near_hostile(distance_galaxies: int | None, max_distance: int = HOSTILE_NPC_NEAR_GALAXIES) -> bool:
    """True, wenn ein (feindliches) NPC nah genug an einem eigenen Planeten steht."""
    if distance_galaxies is None:
        return False
    return distance_galaxies <= max_distance


def build_npc_item(
    *,
    npc_id: str,
    name: str,
    behavior_profile: str,
    galaxy: int,
    system: int,
    position: int,
    intel: dict | None,
    level: int,
    relation_status: str | None,
    discovered_at: str | None,
    home_galaxy: int | None,
) -> dict:
    """Baut einen NPC-Ziel-Eintrag (rein) aus Discovery-Intel + Relation."""
    intel = intel or {}
    return {
        "npc_id": npc_id,
        "name": name or f"{galaxy}:{system}:{position}",
        "behavior_profile": behavior_profile or "defensive",
        "galaxy": galaxy,
        "system": system,
        "position": position,
        "coords": f"{galaxy}:{system}:{position}",
        "intel_level": int(level or 1),
        "ships_total": int(intel.get("ships_total", 0)),
        "defenses_total": int(intel.get("defenses_total", 0)),
        "relation_status": relation_status,
        "distance_galaxies": galaxy_distance(home_galaxy, galaxy),
        "last_intel_at": discovered_at,
    }


def build_player_item(
    *,
    player_id: str | None,
    name: str,
    galaxy: int,
    system: int,
    position: int,
    intel: dict | None,
    level: int,
    has_trade_offer: bool,
    discovered_at: str | None,
    home_galaxy: int | None,
) -> dict:
    """Baut einen Spieler-Ziel-Eintrag (rein) aus Discovery-Intel."""
    intel = intel or {}
    return {
        "player_id": player_id,
        "name": name or f"{galaxy}:{system}:{position}",
        "galaxy": galaxy,
        "system": system,
        "position": position,
        "coords": f"{galaxy}:{system}:{position}",
        "intel_level": int(level or 1),
        "ships_total": int(intel.get("ships_total", 0)),
        "has_trade_offer": bool(has_trade_offer),
        "distance_galaxies": galaxy_distance(home_galaxy, galaxy),
        "last_intel_at": discovered_at,
    }


def npc_target_sort_key(item: dict) -> tuple:
    """Sortierung NPC-Ziele: feindlich zuerst, dann nahe, dann staerkste, dann Name."""
    rank = NPC_STATUS_ORDER.get(item.get("relation_status"), 2)
    dist = item.get("distance_galaxies")
    dist = dist if dist is not None else _FAR
    return (rank, dist, -int(item.get("ships_total", 0)), item.get("name") or "")


def player_target_sort_key(item: dict) -> tuple:
    """Sortierung Spieler-Ziele: nah zuerst, dann staerkste, dann Name."""
    dist = item.get("distance_galaxies")
    dist = dist if dist is not None else _FAR
    return (dist, -int(item.get("ships_total", 0)), item.get("name") or "")


def _arrive_epoch(value) -> float:
    """Hilft beim Sortieren: arrive_at kann datetime, ISO-String oder None sein."""
    if value is None:
        return _FAR
    if isinstance(value, _dt.datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return _dt.datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return _FAR


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    return str(value)


def assemble_threats(incoming: list[dict], hostile_npcs: list[dict]) -> list[dict]:
    """Stellt die Bedrohungs-Liste zusammen + sortiert nach Dringlichkeit.

    ``incoming`` = Rohformat aus ``list_incoming_attacks`` (attacker/kind/origin/target/
    ships_total/arrive_at/mission/intel_level). ``hostile_npcs`` = bereits gebaute
    'hostile_npc'-Eintraege. Reihenfolge: eingehende Angriffe (Ankunft zuerst), danach
    feindliche NPCs (nach Distanz)."""
    threats: list[dict] = []
    for a in incoming:
        threats.append({
            "kind": "incoming",
            "name": a.get("attacker") or "Unbekannte Flotte",
            "attacker_kind": a.get("kind"),
            "npc_id": None,
            "origin": a.get("origin"),
            "target": a.get("target"),
            "arrive_at": _iso(a.get("arrive_at")),
            "ships_total": int(a.get("ships_total", 0)),
            "intel_level": int(a.get("intel_level", 1)),
            "distance_galaxies": None,
            "mission": a.get("mission", "attack"),
            "priority": 0,
            "_arrive_epoch": _arrive_epoch(a.get("arrive_at")),
        })
    for n in hostile_npcs:
        item = dict(n)
        item.setdefault("kind", "hostile_npc")
        item.setdefault("priority", 1)
        item["_arrive_epoch"] = _FAR
        threats.append(item)

    def _key(t: dict) -> tuple:
        if t.get("kind") == "incoming":
            return (0, t.get("_arrive_epoch", _FAR), 0)
        dist = t.get("distance_galaxies")
        dist = dist if dist is not None else _FAR
        return (1, dist, -int(t.get("ships_total", 0)))

    threats.sort(key=_key)
    for t in threats:
        t.pop("_arrive_epoch", None)
    return threats


# --------------------------------------------------------------- DB-Funktionen

async def _home_galaxy(session: AsyncSession, player_id) -> int | None:
    """Heimat-Galaxie des Spielers (Heimatwelt bevorzugt, sonst erster Planet)."""
    home = (await session.execute(
        select(Planet.galaxy).where(
            Planet.player_id == player_id, Planet.is_homeworld.is_(True)
        ).limit(1)
    )).scalar_one_or_none()
    if home is None:
        home = (await session.execute(
            select(Planet.galaxy).where(Planet.player_id == player_id).limit(1)
        )).scalar_one_or_none()
    return int(home) if home is not None else None


async def _relations_by_npc(session: AsyncSession, player_id) -> dict:
    """NpcRelation-Zeilen des Spielers, indexiert nach npc_id."""
    rows = (await session.execute(
        select(NpcRelation).where(NpcRelation.player_id == player_id)
    )).scalars().all()
    return {r.npc_id: r for r in rows}


async def list_npc_targets(session: AsyncSession, player: Player) -> list[dict]:
    """Entdeckte, angreifbare NPC-Imperien des Spielers (ohne Handelszentren)."""
    from app.universe.router import _player_discoveries

    discoveries = await _player_discoveries(session, player.id)
    home = await _home_galaxy(session, player.id)
    relations = await _relations_by_npc(session, player.id)

    out: list[dict] = []
    for (g, s, p), d in discoveries.items():
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == g, NpcEmpire.system == s, NpcEmpire.position == p
            )
        )).scalar_one_or_none()
        if npc is None or not is_attackable_npc(npc.behavior_profile):
            continue
        rel = relations.get(npc.id)
        intel = d.intel or {}
        out.append(build_npc_item(
            npc_id=str(npc.id),
            name=intel.get("name") or npc.name,
            behavior_profile=npc.behavior_profile,
            galaxy=g, system=s, position=p,
            intel=intel,
            level=d.level,
            relation_status=rel.status if rel is not None else None,
            discovered_at=d.discovered_at.isoformat() if d.discovered_at else None,
            home_galaxy=home,
        ))
    out.sort(key=npc_target_sort_key)
    return out


async def list_player_targets(session: AsyncSession, player: Player) -> list[dict]:
    """Entdeckte fremde Spieler-Imperien des Spielers (leer, wenn keine vorhanden)."""
    from app.universe.router import _player_discoveries

    discoveries = await _player_discoveries(session, player.id)
    home = await _home_galaxy(session, player.id)

    out: list[dict] = []
    for (g, s, p), d in discoveries.items():
        # An dieser Koordinate ein NPC? Dann ist es kein Spieler-Ziel.
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == g, NpcEmpire.system == s, NpcEmpire.position == p
            )
        )).scalar_one_or_none()
        if npc is not None:
            continue
        # Spieler-Planet an der Koordinate (Mond ausgenommen) -> Eigentuemer aufloesen.
        planet = (await session.execute(
            select(Planet).where(
                Planet.galaxy == g, Planet.system == s, Planet.position == p,
                Planet.planet_type != "moon",
            )
        )).scalars().first()
        intel = d.intel or {}
        if planet is None:
            # Kein lebender Planet mehr (zerstoert/verlassen) — nur uebernehmen, wenn das
            # Intel das Ziel als Spieler markiert; Name dann aus dem Snapshot.
            if intel.get("kind") != "player":
                continue
            out.append(build_player_item(
                player_id=None,
                name=intel.get("name") or f"{g}:{s}:{p}",
                galaxy=g, system=s, position=p,
                intel=intel, level=d.level,
                has_trade_offer=False,
                discovered_at=d.discovered_at.isoformat() if d.discovered_at else None,
                home_galaxy=home,
            ))
            continue
        if planet.player_id == player.id:
            continue  # eigener Planet ist kein Ziel
        owner = await session.get(Player, planet.player_id)
        out.append(build_player_item(
            player_id=str(planet.player_id),
            name=(owner.display_name if owner else None) or intel.get("name") or planet.name,
            galaxy=g, system=s, position=p,
            intel=intel, level=d.level,
            has_trade_offer=bool(owner.trade_enabled) if owner else False,
            discovered_at=d.discovered_at.isoformat() if d.discovered_at else None,
            home_galaxy=home,
        ))
    out.sort(key=player_target_sort_key)
    return out


async def _hostile_npcs_near(session: AsyncSession, player: Player, home: int | None) -> list[dict]:
    """Feindliche NPCs (NpcRelation.status == 'hostile') nahe eigenen Planeten."""
    # Galaxien, in denen der Spieler Planeten hat (Naehe-Massstab pro Galaxie).
    gal_rows = (await session.execute(
        select(Planet.galaxy).where(Planet.player_id == player.id)
    )).all()
    my_galaxies = {int(g) for (g,) in gal_rows}
    if not my_galaxies:
        return []

    rows = (await session.execute(
        select(NpcRelation, NpcEmpire)
        .join(NpcEmpire, NpcRelation.npc_id == NpcEmpire.id)
        .where(NpcRelation.player_id == player.id, NpcRelation.status == "hostile")
    )).all()
    if not rows:
        return []

    from app.universe.router import _player_discoveries
    discoveries = await _player_discoveries(session, player.id)

    out: list[dict] = []
    for rel, npc in rows:
        if not is_attackable_npc(npc.behavior_profile):
            continue
        dist = min(abs(npc.galaxy - g) for g in my_galaxies)
        if not is_near_hostile(dist):
            continue
        d = discoveries.get((npc.galaxy, npc.system, npc.position))
        intel = (d.intel if d is not None else {}) or {}
        out.append({
            "kind": "hostile_npc",
            "name": npc.name,
            "attacker_kind": None,
            "npc_id": str(npc.id),
            "origin": f"{npc.galaxy}:{npc.system}:{npc.position}",
            "target": None,
            "arrive_at": None,
            "ships_total": int(intel.get("ships_total", 0)),
            "intel_level": int(d.level if d is not None else 1),
            "distance_galaxies": galaxy_distance(home, npc.galaxy),
            "mission": None,
            "priority": 1,
        })
    return out


async def list_threats(session: AsyncSession, player: Player) -> list[dict]:
    """Bedrohungen: eingehende Angriffe + feindliche NPCs in der Naehe (Ankunft zuerst)."""
    from app.fleet.service import list_incoming_attacks

    incoming = await list_incoming_attacks(session, player.id)
    home = await _home_galaxy(session, player.id)
    hostile = await _hostile_npcs_near(session, player, home)
    return assemble_threats(incoming, hostile)
