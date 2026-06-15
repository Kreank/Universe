"""Allianz-Koop-Kampf (Phase 2) — ACS-lite + verbuendete Verteidigung.

Zwei kooperative Mechaniken, beide aktivieren die Kontext-Gates des Bonus-Resolvers
(``coop`` / ``ally``), die solo nie feuern:

- **Gemeinsamer Angriff (ACS-lite):** Mehrere ``attack``-Flotten verbuendeter Spieler auf
  DIESELBE Koordinate, deren Ankuenfte hoechstens ``stage_window_seconds`` auseinanderliegen,
  verschmelzen zu EINER Schlacht. Die zuerst eintreffende Flotte *staged* (wartet) und wird von
  der spaeter (oder zuletzt) eintreffenden Flotte mit aufgeloest. Verluste werden je Flotte
  greedy zurueckverteilt (``distribute_losses``), Beute nach ueberlebendem Frachtanteil.
- **Verbuendete Verteidigung:** stationierte Patrouillen von Allianz-Mitgliedern am Ziel
  treten der Verteidigung bei (Kontext ``ally``/``coop``).

Reine Koordinations-/Aufteilungs-Logik; die eigentliche Schlacht + Persistenz bleibt in
``combat/service.resolve_attack``.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alliance.service import _acfg
from app.platform.models import Fleet, Player, Ship, StationedFleet

UTC = dt.timezone.utc


def _ccfg() -> dict:
    return _acfg().get("coop", {})


def _aware(t: dt.datetime | None) -> dt.datetime | None:
    if t is None:
        return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t


def stage_window() -> float:
    return float(_ccfg().get("stage_window_seconds", 600))


# -- Verbuendete Angriffsflotten auf dieselbe Koordinate ----------------------

async def _allied_attack_fleets(
    session: AsyncSession, fleet: Fleet, alliance_id: uuid.UUID, statuses: tuple[str, ...]
) -> list[Fleet]:
    """Andere ``attack``-Flotten von Allianz-Mitgliedern auf exakt dieselbe Zielkoordinate."""
    rows = (await session.execute(
        select(Fleet).join(Player, Player.id == Fleet.player_id).where(
            Player.alliance_id == alliance_id,
            Fleet.id != fleet.id,
            Fleet.mission == "attack",
            Fleet.target_galaxy == fleet.target_galaxy,
            Fleet.target_system == fleet.target_system,
            Fleet.target_position == fleet.target_position,
            Fleet.status.in_(statuses),
        )
    )).scalars().all()
    cap = int(_ccfg().get("max_allied_fleets", 8))
    return list(rows)[:cap]


def _is_staged(f: Fleet) -> bool:
    md = f.mission_data or {}
    return bool(md.get("coop_staged")) and not md.get("coop_consumed")


async def coop_attack_decision(
    session: AsyncSession, fleet: Fleet, alliance_id: uuid.UUID, now: dt.datetime
) -> tuple[str, object]:
    """Entscheidet beim Eintreffen einer Angriffsflotte ueber Koordination.

    Liefert:
      ("stage",   stage_until: datetime)   -> diese Flotte wartet auf spaeter eintreffende Verbuendete.
      ("resolve", staged: list[Fleet])     -> jetzt aufloesen; ``staged`` sind mitzuverschmelzende,
                                              bereits wartende verbuendete Flotten (ohne diese Flotte).
    """
    window = stage_window()
    allied = await _allied_attack_fleets(session, fleet, alliance_id, ("flying", "arrived"))
    # Verbuendete, die NACH dieser Flotte, aber noch im Fenster eintreffen -> auf sie warten.
    inbound_later = [
        f for f in allied
        if f.status == "flying"
        and _aware(f.arrive_at) is not None
        and now < _aware(f.arrive_at) <= now + dt.timedelta(seconds=window)
    ]
    if inbound_later:
        latest = max(_aware(f.arrive_at) for f in inbound_later)
        stage_until = min(latest, now + dt.timedelta(seconds=window)) + dt.timedelta(seconds=2)
        return ("stage", stage_until)
    staged = [f for f in allied if f.status == "arrived" and _is_staged(f)]
    return ("resolve", staged)


async def gather_staged_allies(
    session: AsyncSession, fleet: Fleet, alliance_id: uuid.UUID
) -> list[Fleet]:
    """Bereits wartende (gestagte, nicht konsumierte) verbuendete Angriffsflotten am Ziel —
    fuer den Selbstheilungs-Pfad (resolve_staged_attack), wenn der erwartete Aufloeser ausfaellt."""
    allied = await _allied_attack_fleets(session, fleet, alliance_id, ("arrived",))
    return [f for f in allied if _is_staged(f)]


async def build_attacker_sources(
    session: AsyncSession, primary: Fleet, allies: list[Fleet]
) -> list[dict]:
    """Quellen-Liste fuer die verschmolzene Angreiferseite (kompatibel mit distribute_losses).
    Jede Quelle: {"kind","obj","rows","ships","is_primary"}. Leere Flotten werden uebersprungen."""
    sources: list[dict] = []
    for f, is_primary in [(primary, True)] + [(a, False) for a in allies]:
        rows = (await session.execute(
            select(Ship).where(Ship.fleet_id == f.id)
        )).scalars().all()
        ships = {r.type: r.count for r in rows if r.count > 0}
        if not ships:
            continue
        sources.append({"kind": "fleet", "obj": f, "rows": rows, "ships": ships, "is_primary": is_primary})
    return sources


def merge_ships(sources: list[dict]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for src in sources:
        for typ, cnt in (src.get("ships") or {}).items():
            merged[typ] = merged.get(typ, 0) + int(cnt)
    return merged


def distinct_players(sources: list[dict]) -> set[uuid.UUID]:
    out: set[uuid.UUID] = set()
    for src in sources:
        pid = getattr(src["obj"], "player_id", None) or getattr(src["obj"], "owner_id", None)
        if pid is not None:
            out.add(pid)
    return out


def mark_consumed(fleet: Fleet, now: dt.datetime) -> None:
    """Markiert eine in eine fremde Schlacht verschmolzene (gestagte) Flotte als verbraucht,
    damit ihr Selbstheilungs-Job ins Leere laeuft. Setzt sie auf 'returning' — ihr bereits
    geplanter fleet_return-Job bringt die ueberlebenden Schiffe + Beute heim."""
    fleet.mission_data = {**(fleet.mission_data or {}), "coop_consumed": now.isoformat()}
    if fleet.status == "arrived":
        fleet.status = "returning"


def split_loot_by_capacity(
    survivor_caps: list[float], total_loot: dict[str, float]
) -> list[dict[str, float]]:
    """Teilt die Gesamtbeute proportional zur ueberlebenden Frachtkapazitaet je Quelle auf."""
    total_cap = sum(max(0.0, c) for c in survivor_caps)
    out: list[dict[str, float]] = []
    if total_cap <= 0:
        return [{k: 0.0 for k in total_loot} for _ in survivor_caps]
    for cap in survivor_caps:
        share = max(0.0, cap) / total_cap
        out.append({k: round(v * share, 1) for k, v in total_loot.items()})
    return out


# -- Verbuendete Verteidiger (stationierte Patrouillen von Mitgliedern) -------

async def gather_allied_defenders(
    session: AsyncSession,
    def_player: Player,
    galaxy: int,
    system: int,
    position: int,
    attacker_player_id: uuid.UUID,
) -> list[dict]:
    """Stationierte Patrouillen von Allianz-Mitgliedern (inkl. des Verteidigers selbst) an der
    Zielkoordinate. Liefert Quellen [{"kind":"station","obj":StationedFleet,"ships":..,"owner_id":..}].
    Leer, wenn der Verteidiger keiner Allianz angehoert."""
    if def_player.alliance_id is None:
        return []
    rows = (await session.execute(
        select(StationedFleet).join(Player, Player.id == StationedFleet.owner_id).where(
            Player.alliance_id == def_player.alliance_id,
            StationedFleet.owner_id != attacker_player_id,
            StationedFleet.galaxy == galaxy,
            StationedFleet.system == system,
            StationedFleet.position == position,
        )
    )).scalars().all()
    out: list[dict] = []
    for st in rows:
        ships = {t: c for t, c in (st.ships or {}).items() if c > 0}
        if ships:
            out.append({"kind": "station", "obj": st, "ships": ships, "owner_id": st.owner_id})
    return out
