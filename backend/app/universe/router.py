"""Router fuer das Universum/Galaxie-Ansicht (api-contract §6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import AsteroidField, NpcEmpire, Planet, Player, PlayerDiscovery, UniverseCell
from app.platform.security import get_current_player

router = APIRouter(tags=["universe"])


class CellOut(BaseModel):
    position: int
    occupant_type: str
    name: str | None = None
    player_id: str | None = None
    player_name: str | None = None  # Imperiumsname des Spielers (fuer Handel/Nachricht)
    npc_id: str | None = None
    discovered: bool = False  # hat dieser Spieler das Ziel schon aufgeklaert?
    trade: dict | None = None  # P2P-Handelsanzeige des Spielers (falls aktiviert)
    asteroid: dict | None = None  # Asteroidenfeld am Ort {richness, mult, metal, crystal} (Restvorrat)
    moon: dict | None = None  # Mond am Ort {name, player_id, player_name, own} — eigenes Angriffs-/Spionageziel
    station: dict | None = None  # Allianz-Station am Ort {alliance_id, tag, mine, status, hp, max_hp, hp_pct}
    mining_fleet: dict | None = None  # geparkte Schuerf-Flotte am Ort {owner, mine, ships_total} — fremde sind angreifbar
    event: dict | None = None  # Game-Event am Ort {event_type, data, expires_at} — Komet/Anomalie/Schwarzmarkt/...
    debris: dict | None = None  # Truemmerfeld am Ort {metal, crystal} (nach Kaempfen) — mit Recyclern abbaubar


class ZoneOut(BaseModel):
    """Allianz-Einflusszone, die dieses System abdeckt (aktive, getankte Station in Reichweite)."""
    alliance_id: str
    tag: str
    center_system: int
    radius: int
    mine: bool  # gehoert die Zone der eigenen Allianz?


class GalaxyViewOut(BaseModel):
    cells: list[CellOut]
    zones: list[ZoneOut] = []  # Allianz-Einflusszonen, die dieses System abdecken


class TargetOut(BaseModel):
    """Ein aufgeklaertes (PvE-)Ziel — erst nach Spionage sichtbar (Doku 04 §6)."""
    npc_id: str | None = None
    name: str
    galaxy: int
    system: int
    position: int
    coords: str
    ships_total: int
    defenses_total: int
    level: int = 1
    discovered_at: str | None = None
    intel: dict | None = None  # voller Aufklaerungs-Schnappschuss (Zusammensetzung/Resschen ab L2/L3)


async def _player_discoveries(
    session: AsyncSession, player_id
) -> dict[tuple[int, int, int], PlayerDiscovery]:
    """Aufgedeckte Ziele eines Spielers, indexiert nach Koordinaten."""
    rows = (await session.execute(
        select(PlayerDiscovery).where(PlayerDiscovery.player_id == player_id)
    )).scalars().all()
    return {(d.galaxy, d.system, d.position): d for d in rows}


@router.get("/galaxy/targets", response_model=list[TargetOut])
async def galaxy_targets(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[TargetOut]:
    """Verzeichnis AUFGEKLAERTER Ziele (PvE). Erst nach Spionage sichtbar.

    Liefert nur Ziele, die dieser Spieler per Sonde aufgedeckt hat
    (``player_discoveries``); Staerke/Zusammensetzung stammen aus dem letzten
    Aufklaerungs-Schnappschuss und koennen veraltet sein."""
    import datetime as _dt

    from app.fleet.trade import ensure_market, merchant_intel
    bal = get_balance()
    _now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()

    discoveries = sorted(
        (await _player_discoveries(session, player.id)).values(),
        key=lambda d: (d.galaxy, d.system, d.position),
    )
    out: list[TargetOut] = []
    for d in discoveries:
        intel = d.intel or {}
        # npc_id fuer den Angriffs-Deep-Link aufloesen (falls Ziel ein NPC ist).
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == d.galaxy,
                NpcEmpire.system == d.system,
                NpcEmpire.position == d.position,
            )
        )).scalar_one_or_none()
        # Haendler/Handelszentren sind OHNE Spionage handelbar (Wunsch 2026-06-19):
        # ist das entdeckte Ziel ein Haendler, das Handels-Intel (Flag + Kurse) direkt
        # beilegen, auch wenn es nie spioniert wurde -> Galaxie zeigt den "Handeln"-Button.
        prof = getattr(npc, "behavior_profile", None) if npc is not None else None
        if npc is not None and prof == "merchant" and not intel.get("merchant"):
            # Legacy-Haendler: lokalen Markt + aktuelle Kurse beilegen.
            ensure_market(npc, bal.trade)
            intel = {**intel, **merchant_intel(npc, bal.trade, _now_iso)}
        elif npc is not None and prof == "trade_center" and not intel.get("merchant"):
            # Handelszentren handeln zum globalen Indexkurs (keine lokalen Kurse erfinden);
            # nur die Flags setzen, damit der Handeln-Button erscheint.
            intel = {**intel, "merchant": True, "trade_center": True, "spec": "trade_center"}
        out.append(TargetOut(
            npc_id=str(npc.id) if npc else None,
            name=intel.get("name") or (npc.name if npc else f"{d.galaxy}:{d.system}:{d.position}"),
            galaxy=d.galaxy,
            system=d.system,
            position=d.position,
            coords=f"{d.galaxy}:{d.system}:{d.position}",
            ships_total=int(intel.get("ships_total", 0)),
            defenses_total=int(intel.get("defenses_total", 0)),
            level=d.level,
            discovered_at=d.discovered_at.isoformat() if d.discovered_at else None,
            intel=intel,
        ))
    return out


@router.get("/mining/fields")
async def mining_fields(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Asteroiden-Übersicht (Bergbau): alle AKTIVEN Felder in Reichweite der Ortungs-Forschung.

    Stufe 1 = nur die Heimat-Galaxie; jede weitere Stufe erweitert die Reichweite um
    ``prospecting_range_per_level`` Galaxien. Ohne Ortung (Stufe 0) ist die Liste leer/gesperrt.
    Restvorrat wird inkl. aufgelaufener Regeneration projiziert (wie in der Galaxie-Ansicht)."""
    from app.economy.service import get_research_levels
    from app.fleet.mining import deuterium_params
    from app.universe.asteroids import projected_remaining

    levels = await get_research_levels(session, player.id)
    prospecting = int(levels.get("prospecting", 0))
    # Aktuelle Deuterium-Fund-Chance des Spielers (inkl. Forschung) fuer die Anzeige.
    _bal = get_balance()
    _dp = deuterium_params(
        int(levels.get("deuterium_prospecting", 0)),
        _bal.data.get("mining", {}),
        _bal.data.get("research", {}).get("effects", {}),
    )
    deuterium_chance = round(_dp["chance"], 3)
    if prospecting < 1:
        return {"prospecting": 0, "range": 0, "home_galaxy": None,
                "deuterium_chance": deuterium_chance, "fields": []}

    home = (await session.execute(
        select(Planet.galaxy).where(Planet.player_id == player.id, Planet.is_homeworld.is_(True)).limit(1)
    )).scalar_one_or_none()
    if home is None:
        home = (await session.execute(
            select(Planet.galaxy).where(Planet.player_id == player.id).limit(1)
        )).scalar_one_or_none()
    if home is None:
        return {"prospecting": prospecting, "range": 0, "home_galaxy": None,
                "deuterium_chance": deuterium_chance, "fields": []}

    per = int(get_balance().data["research"]["effects"].get("prospecting_range_per_level", 1))
    reach = (prospecting - 1) * per  # Stufe 1 = Reichweite 0 = nur Heimat-Galaxie
    rows = (await session.execute(
        select(AsteroidField)
        .where(AsteroidField.galaxy >= home - reach, AsteroidField.galaxy <= home + reach)
        .order_by(AsteroidField.galaxy, AsteroidField.system, AsteroidField.position)
    )).scalars().all()
    fields = []
    for f in rows:
        m_now, c_now = projected_remaining(f)
        fields.append({
            "galaxy": f.galaxy, "system": f.system, "position": f.position,
            "coords": f"{f.galaxy}:{f.system}:{f.position}",
            "richness": f.richness, "mult": round(f.mult, 2),
            "composition": f.composition or "balanced",
            "metal": round(m_now, 0), "crystal": round(c_now, 0),
            "metal_max": round(f.metal_max, 0), "crystal_max": round(f.crystal_max, 0),
            "expires_at": f.expires_at.isoformat() if f.expires_at else None,
        })
    return {"prospecting": prospecting, "range": reach, "home_galaxy": home,
            "deuterium_chance": deuterium_chance, "fields": fields}


@router.get("/conjunctions")
async def conjunctions(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Welle 5 — aktive + kommende Konjunktions-Fenster fuer den Spieler (Frontend-Countdown).

    Schlank gehalten: betrachtet nur Nachbar-Systeme im ``radius`` (balance.conjunction.radius) um
    die eigenen Planeten-Systeme (KEIN O(n^2) ueber das Universum). Pro Eintrag: Quell-/Zielsystem
    (g:s), aktueller Faktor + Rabatt-%, und entweder ``ends_at`` (laufendes Fenster) oder
    ``starts_at``/``next_at`` (naechstes Fenster). Inter-Galaxie wird hier nicht aufgelistet."""
    import datetime as _dt

    from app.fleet.conjunction import (
        active_window_end,
        distance_factor,
        is_conjunction,
        load_cfg,
        next_conjunction,
    )

    cfg = load_cfg()
    if not cfg.get("enabled", True):
        return {"enabled": False, "active": [], "upcoming": []}

    bal = get_balance()
    now = _dt.datetime.now(_dt.timezone.utc)
    now_e = now.timestamp()
    radius = int(cfg.get("radius", 12))
    half_window = float(cfg.get("conjunction_window_hours", 0.5)) * 3600.0 / 2.0
    max_sys = bal.systems_per_galaxy

    def _iso(epoch: float) -> str:
        return _dt.datetime.fromtimestamp(epoch, tz=_dt.timezone.utc).isoformat()

    rows = (await session.execute(
        select(Planet.galaxy, Planet.system).where(Planet.player_id == player.id)
    )).all()
    systems = sorted({(int(g), int(s)) for g, s in rows})

    active: list[dict] = []
    upcoming: list[dict] = []
    seen: set[tuple[int, int, int]] = set()
    for g, s in systems:
        lo = max(1, s - radius)
        hi = min(max_sys, s + radius)
        for ts in range(lo, hi + 1):
            if ts == s or (g, s, ts) in seen:
                continue
            seen.add((g, s, ts))
            origin = (g, s, 1)
            target = (g, ts, 1)
            factor = distance_factor(origin, target, now_e, cfg)
            entry = {
                "from": f"{g}:{s}",
                "to": f"{g}:{ts}",
                "from_coords": {"galaxy": g, "system": s},
                "to_coords": {"galaxy": g, "system": ts},
                "factor": round(factor, 4),
                "discount_pct": round((1.0 - factor) * 100.0, 1),
            }
            if is_conjunction(origin, target, now_e, cfg):
                end = active_window_end(origin, target, now_e, cfg)
                entry["active"] = True
                entry["ends_at"] = _iso(end) if end is not None else None
                active.append(entry)
            else:
                nc = next_conjunction(origin, target, now_e, cfg)
                if nc is not None:
                    entry["active"] = False
                    entry["next_at"] = _iso(nc)
                    entry["starts_at"] = _iso(nc - half_window)
                    upcoming.append(entry)

    active.sort(key=lambda e: e["discount_pct"], reverse=True)
    upcoming.sort(key=lambda e: e["next_at"])
    return {
        "enabled": True,
        "now": now.isoformat(),
        "radius": radius,
        "active": active,
        "upcoming": upcoming[: int(cfg.get("max_upcoming", radius))],
    }


@router.get("/galaxy/{galaxy}/{system}", response_model=GalaxyViewOut)
async def galaxy_view(
    galaxy: int,
    system: int,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> GalaxyViewOut:
    bal = get_balance()
    rows = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == galaxy, UniverseCell.system == system
        )
    )).scalars().all()
    by_pos = {c.position: c for c in rows}
    discovered = await _player_discoveries(session, player.id)

    # Asteroidenfelder sind ein OVERLAY (geteilte Position wie ein Mond) -> per Koordinate laden
    # und an die Zelle haengen, unabhaengig vom Belegungstyp (auch auf 'empty'/'player'/'npc').
    ast_rows = (await session.execute(
        select(AsteroidField).where(
            AsteroidField.galaxy == galaxy, AsteroidField.system == system
        )
    )).scalars().all()

    def _asteroid_overlay(pos: int) -> dict | None:
        field = next((f for f in ast_rows if f.position == pos), None)
        if not field:
            return None
        # Vorrat inkl. aufgelaufener Regeneration projizieren (ohne Mutation) -> das Feld waechst
        # sichtbar nach. Beim Abbau wird dieselbe Regen-Formel real angewandt.
        from app.universe.asteroids import projected_remaining
        metal_now, crystal_now = projected_remaining(field)
        return {
            "richness": field.richness,
            "mult": round(field.mult, 2),
            "metal": round(metal_now, 0),
            "crystal": round(crystal_now, 0),
            "metal_max": round(field.metal_max, 0),
            "crystal_max": round(field.crystal_max, 0),
        }

    # Game-Events sind ein OVERLAY (Komet/Anomalie/Schwarzmarkt/Wrack/Werft) -> per Koordinate laden.
    import datetime as _dt

    from app.platform.models import CosmicEvent as _CosmicEvent
    _now_ev = _dt.datetime.now(_dt.timezone.utc)
    ev_rows = (await session.execute(
        select(_CosmicEvent).where(
            _CosmicEvent.galaxy == galaxy, _CosmicEvent.system == system,
            _CosmicEvent.status == "active", _CosmicEvent.expires_at > _now_ev,
            _CosmicEvent.position.is_not(None),
        )
    )).scalars().all()

    def _event_overlay(pos: int) -> dict | None:
        ev = next((e for e in ev_rows if e.position == pos), None)
        if not ev:
            return None
        public = {k: v for k, v in (ev.data or {}).items() if k not in ("npc_id",)}
        return {"event_type": ev.event_type, "data": public, "expires_at": ev.expires_at.isoformat()}

    # Truemmerfeld ist ein OVERLAY (UniverseCell.debris_field, nach Kaempfen) -> mit Recyclern abbaubar.
    def _debris_overlay(pos: int) -> dict | None:
        c = by_pos.get(pos)
        df = (c.debris_field if c is not None else None) or {}
        metal = float(df.get("metal", 0) or 0)
        crystal = float(df.get("crystal", 0) or 0)
        if metal + crystal <= 0:
            return None
        return {"metal": round(metal, 0), "crystal": round(crystal, 0)}

    # Monde sind ein OVERLAY (teilen die Position des Planeten) -> eigenes Angriffs-/Spionageziel.
    moon_rows = (await session.execute(
        select(Planet).where(
            Planet.galaxy == galaxy, Planet.system == system, Planet.planet_type == "moon"
        )
    )).scalars().all()
    moon_by_pos = {m.position: m for m in moon_rows}

    # Allianz-Stationen in diesem System (nicht-zerstoert): als angreifbare Zellen-Overlays.
    from app.platform.models import Alliance as _Alliance
    from app.platform.models import AllianceStation as _AllStation
    _st_rows = (await session.execute(
        select(_AllStation).where(
            _AllStation.galaxy == galaxy, _AllStation.system == system,
            _AllStation.status != "destroyed",
        )
    )).scalars().all()
    station_by_pos: dict[int, dict] = {}
    _max_hp = float(bal.data.get("alliance", {}).get("station", {}).get("hp", 1)) or 1.0
    for _st in _st_rows:
        _al = await session.get(_Alliance, _st.alliance_id)
        station_by_pos[_st.position] = {
            "alliance_id": str(_st.alliance_id),
            "tag": _al.tag if _al else "?",
            "mine": player.alliance_id is not None and _st.alliance_id == player.alliance_id,
            "status": _st.status,
            "hp": round(float(_st.hp or 0), 1),
            "max_hp": _max_hp,
            "hp_pct": max(0.0, round(100.0 * float(_st.hp or 0) / _max_hp, 1)),
        }

    # Geparkte Schuerf-Flotten als OVERLAY: wer GERADE am Feld farmt, ist angreifbar (Fracht-Beute).
    import datetime as _dt

    from app.fleet.mining import is_parked_mining
    from app.platform.models import Fleet as _Fleet
    from app.platform.models import Ship as _Ship
    _now_m = _dt.datetime.now(_dt.timezone.utc)
    _mine_rows = (await session.execute(
        select(_Fleet).where(
            _Fleet.target_galaxy == galaxy, _Fleet.target_system == system,
            _Fleet.mission == "mine", _Fleet.status != "done",
        )
    )).scalars().all()
    _parked: dict[int, list[tuple[bool, str | None, int]]] = {}
    for _f in _mine_rows:
        if not is_parked_mining(_f, galaxy, system, _f.target_position, _now_m):
            continue
        _total = int(sum(
            int(c[0]) for c in (await session.execute(
                select(_Ship.count).where(_Ship.fleet_id == _f.id)
            )).all()
        ))
        if _total <= 0:
            continue
        _owner = await session.get(Player, _f.player_id)
        _parked.setdefault(_f.target_position, []).append(
            (_f.player_id == player.id, _owner.display_name if _owner else None, _total)
        )
    mining_by_pos: dict[int, dict] = {}
    for _pos, _lst in _parked.items():
        _enemies = [x for x in _lst if not x[0]]
        _shown = _enemies if _enemies else _lst
        _names = {x[1] for x in _shown}
        mining_by_pos[_pos] = {
            "owner": (next(iter(_names)) if len(_names) == 1 else "Mehrere"),
            "mine": not _enemies,  # nur eigene Flotten -> Info; sonst (auch gemischt) angreifbar
            "ships_total": sum(x[2] for x in _shown),
        }

    cells: list[CellOut] = []
    for pos in range(1, bal.positions_per_system + 1):
        cell = by_pos.get(pos)
        asteroid = _asteroid_overlay(pos)
        station_info = station_by_pos.get(pos)
        mining_info = mining_by_pos.get(pos)
        moon_obj = moon_by_pos.get(pos)
        moon = None
        if moon_obj is not None:
            m_owner = await session.get(Player, moon_obj.player_id)
            moon = {
                "name": moon_obj.name,
                "player_id": str(moon_obj.player_id),
                "player_name": m_owner.display_name if m_owner else None,
                "own": moon_obj.player_id == player.id,
            }
        if cell is None or cell.occupant_type == "empty":
            cells.append(CellOut(position=pos, occupant_type="empty", asteroid=asteroid,
                                 moon=moon, station=station_info, mining_fleet=mining_info,
                                 event=_event_overlay(pos), debris=_debris_overlay(pos)))
            continue
        name = None
        player_id = None
        player_name = None
        npc_id = None
        trade = None
        if cell.occupant_type == "player" and cell.ref_id:
            planet = await session.get(Planet, cell.ref_id)
            if planet:
                name = planet.name
                player_id = str(planet.player_id)
                owner = await session.get(Player, planet.player_id)
                if owner:
                    player_name = owner.display_name
                    if owner.trade_enabled:
                        trade = {
                            "offer": owner.trade_offer,
                            "want": owner.trade_want,
                            "rate": owner.trade_rate,
                            "note": owner.trade_note,
                        }
        elif cell.occupant_type == "npc" and cell.ref_id:
            npc = await session.get(NpcEmpire, cell.ref_id)
            if npc:
                name = npc.name
                npc_id = str(npc.id)
        cells.append(CellOut(
            position=pos,
            occupant_type=cell.occupant_type,
            name=name,
            player_id=player_id,
            player_name=player_name,
            npc_id=npc_id,
            discovered=(galaxy, system, pos) in discovered,
            trade=trade,
            asteroid=asteroid,
            moon=moon,
            station=station_info,
            mining_fleet=mining_info,
            event=_event_overlay(pos),
            debris=_debris_overlay(pos),
        ))

    # Galaktische Weiten: synthetischer Deep-Space-Slot (nur per Expedition erreichbar).
    deep = int(bal.data.get("expedition", {}).get("deep_space_position", 0))
    if deep:
        cells.append(CellOut(position=deep, occupant_type="deep_space", name="Galaktische Weiten"))

    # Allianz-Einflusszonen, die dieses System abdecken (aktive + getankte Station in Reichweite).
    from app.alliance.station import covers, zone_radius
    from app.platform.models import Alliance, AllianceStation
    zones: list[ZoneOut] = []
    st_rows = (await session.execute(
        select(AllianceStation).where(
            AllianceStation.galaxy == galaxy, AllianceStation.status == "active"
        )
    )).scalars().all()
    for st in st_rows:
        if not covers(st, galaxy, system):
            continue
        al = await session.get(Alliance, st.alliance_id)
        zones.append(ZoneOut(
            alliance_id=str(st.alliance_id),
            tag=al.tag if al else "?",
            center_system=st.system,
            radius=zone_radius(st),
            mine=(player.alliance_id is not None and st.alliance_id == player.alliance_id),
        ))
    return GalaxyViewOut(cells=cells, zones=zones)
