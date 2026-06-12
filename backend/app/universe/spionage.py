"""Spionage-Aufloesung (Doku 04 §6): Sonden decken Ziele auf.

Bei Ankunft einer ``spy``-Mission wird das Ziel (NPC oder Spieler-Planet) aufgeklaert.
Die Detailstufe (1..3) steigt mit Sondenanzahl bzw. Spionagetech-Vorsprung:
- L1: nur Gesamtstaerke (Schiffe/Verteidigung als Summe),
- L2: + Flotten- und Verteidigungs-Zusammensetzung,
- L3: + Ressourcen.

Ergebnis je Aufklaerung:
1. Upsert in ``player_discoveries`` -> Ziel erscheint im Galaxie-Verzeichnis,
2. Spionagebericht ins Postfach (transmission ``spy_report``) inkl. WS-Push."""
from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import get_research_levels
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import (
    Defense,
    Fleet,
    NpcEmpire,
    Planet,
    PlayerDiscovery,
    Resource,
    Ship,
    UniverseCell,
)

log = logging.getLogger("universe.spionage")

_RES_LABELS = {"metal": "Metall", "crystal": "Kristall", "deuterium": "Deuterium"}


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _intel_level(probes: int, spy_tech: int, cfg: dict) -> int:
    """Detailstufe aus Sondenanzahl bzw. Spionagetech (je nachdem, was mehr hergibt)."""
    level = 1
    if probes >= cfg["level2_probes"] or spy_tech >= cfg["level2_spy_tech"]:
        level = 2
    if probes >= cfg["level3_probes"] or spy_tech >= cfg["level3_spy_tech"]:
        level = 3
    return level


async def _gather_target(
    session: AsyncSession, galaxy: int, system: int, position: int, target_moon: bool = False
) -> dict | None:
    """Sammelt den IST-Zustand eines Ziels (NPC oder Spieler-Planet).

    Liefert ``{name, fleet, defenses, resources, kind}`` oder ``None``, wenn an den
    Koordinaten nichts Spionierbares liegt (leere Zelle / nur Truemmer)."""
    cell = (await session.execute(
        select(UniverseCell).where(
            UniverseCell.galaxy == galaxy,
            UniverseCell.system == system,
            UniverseCell.position == position,
        )
    )).scalar_one_or_none()

    # -- NPC-Ziel ----------------------------------------------------------
    npc: NpcEmpire | None = None
    if cell is not None and cell.occupant_type == "npc" and cell.ref_id:
        npc = await session.get(NpcEmpire, cell.ref_id)
    if npc is None:
        # Fallback: direkter Koordinaten-Lookup (wie in combat/service.py).
        npc = (await session.execute(
            select(NpcEmpire).where(
                NpcEmpire.galaxy == galaxy,
                NpcEmpire.system == system,
                NpcEmpire.position == position,
            )
        )).scalar_one_or_none()
    if npc is not None:
        return {
            "name": npc.name,
            "fleet": {k: int(v) for k, v in (npc.fleet or {}).items()},
            "defenses": {k: int(v) for k, v in (npc.defenses or {}).items()},
            "resources": {k: int(v) for k, v in (npc.resources or {}).items()},
            "kind": "npc",
            # NPC-Objekt durchreichen -> Haendler-Markt-Intel ohne erneuten Lookup.
            "npc": npc,
        }

    # -- Spieler-Planet (oder dessen Mond) ---------------------------------
    if cell is not None and cell.occupant_type == "player" and cell.ref_id:
        planet = await session.get(Planet, cell.ref_id)
        if planet is not None and target_moon:
            from app.planets.moon import moon_of
            planet = await moon_of(session, planet.id)  # None -> kein Mond -> nichts spionierbar
        if planet is not None:
            ships = (await session.execute(
                select(Ship).where(Ship.planet_id == planet.id, Ship.fleet_id.is_(None))
            )).scalars().all()
            defs = (await session.execute(
                select(Defense).where(Defense.planet_id == planet.id)
            )).scalars().all()
            res_rows = (await session.execute(
                select(Resource).where(Resource.planet_id == planet.id)
            )).scalars().all()
            fleet_map: dict[str, int] = {}
            for s in ships:
                if s.count > 0:
                    fleet_map[s.type] = fleet_map.get(s.type, 0) + s.count
            return {
                "name": planet.name,
                "fleet": fleet_map,
                "defenses": {d.type: d.count for d in defs if d.count > 0},
                "resources": {
                    r.type: int(r.amount)
                    for r in res_rows
                    if r.type in _RES_LABELS and r.amount > 0
                },
                "kind": "player",
            }

    return None


def _fmt_units(units: dict[str, int]) -> str:
    if not units:
        return "keine"
    return ", ".join(f"{cnt}x {typ}" for typ, cnt in units.items())


def _fmt_resources(res: dict[str, int]) -> str:
    parts = [
        f"{int(res[k]):,}".replace(",", ".") + f" {_RES_LABELS[k]}"
        for k in ("metal", "crystal", "deuterium")
        if res.get(k)
    ]
    return ", ".join(parts) if parts else "keine"


def _build_report_body(coords: str, intel: dict) -> str:
    """Formatiert den Spionagebericht als lesbaren Funkspruch je Detailstufe."""
    level = intel["level"]
    lines = [
        f"Spionagebericht — {intel['name']} ({coords})",
        f"Aufklaerungsstufe {level}/3.",
        f"Gesamtstaerke: {intel['ships_total']} Schiffe, {intel['defenses_total']} Verteidigungsanlagen.",
    ]
    if level >= 2:
        lines.append(f"Flotte: {_fmt_units(intel.get('fleet', {}))}")
        lines.append(f"Verteidigung: {_fmt_units(intel.get('defenses', {}))}")
    else:
        lines.append("Flotten-/Verteidigungs-Zusammensetzung: unklar (mehr Sonden oder Spionagetech noetig).")
    if level >= 3:
        lines.append(f"Ressourcen: {_fmt_resources(intel.get('resources', {}))}")
    else:
        lines.append("Ressourcen: nicht aufgeklaert (Stufe 3 noetig).")
    return "\n".join(lines)


async def resolve_spy(session: AsyncSession, fleet: Fleet) -> None:
    """Klaert das Flotten-Ziel auf: Discovery-Upsert + Spionagebericht ins Postfach."""
    bal = get_balance()
    cfg = bal.data["spy"]
    coords = f"{fleet.target_galaxy}:{fleet.target_system}:{fleet.target_position}"

    # Sondenanzahl in der Flotte + Spionagetech des Spielers.
    probe_type = cfg["probe_type"]
    probe_row = (await session.execute(
        select(Ship).where(Ship.fleet_id == fleet.id, Ship.type == probe_type)
    )).scalar_one_or_none()
    probes = probe_row.count if probe_row else 0
    rlevels = await get_research_levels(session, fleet.player_id)
    spy_tech = int(rlevels.get("spy_tech", 0))

    target_moon = (fleet.mission_data or {}).get("target_type") == "moon"
    target = await _gather_target(
        session, fleet.target_galaxy, fleet.target_system, fleet.target_position, target_moon
    )
    if target is None:
        await create_system_transmission(
            session,
            player_id=fleet.player_id,
            subject=f"Spionage erfolglos ({coords})",
            body=f"Die Sonden erreichten {coords}, fanden aber kein spionierbares Ziel.",
            ttype="spy_report",
        )
        log.info("Spionage ohne Ziel: player=%s coords=%s", fleet.player_id, coords)
        return

    level = _intel_level(probes, spy_tech, cfg)
    ships_total = sum(target["fleet"].values())
    defenses_total = sum(target["defenses"].values())

    intel: dict = {
        "name": target["name"],
        "kind": target["kind"],
        "ships_total": ships_total,
        "defenses_total": defenses_total,
        "level": level,
        "scanned_at": _now().isoformat(),
    }
    if level >= 2:
        intel["fleet"] = target["fleet"]
        intel["defenses"] = target["defenses"]
    if level >= 3:
        intel["resources"] = target["resources"]

    # Haendler-NPC: Spec + aktuelle Kurse ins Intel mergen (Spionage deckt den Markt auf).
    spy_npc = target.get("npc")
    if spy_npc is not None and getattr(spy_npc, "behavior_profile", None) == "merchant":
        # Lazy-Import -> kein Modul-Zyklus (trade.py importiert spionage.py nicht).
        from app.fleet.trade import ensure_market, merchant_intel
        ensure_market(spy_npc, bal.trade)
        intel.update(merchant_intel(spy_npc, bal.trade, _now().isoformat()))

    # Discovery-Upsert (Ziel wird im Galaxie-Verzeichnis sichtbar).
    disc = (await session.execute(
        select(PlayerDiscovery).where(
            PlayerDiscovery.player_id == fleet.player_id,
            PlayerDiscovery.galaxy == fleet.target_galaxy,
            PlayerDiscovery.system == fleet.target_system,
            PlayerDiscovery.position == fleet.target_position,
        )
    )).scalar_one_or_none()
    if disc is None:
        disc = PlayerDiscovery(
            player_id=fleet.player_id,
            galaxy=fleet.target_galaxy,
            system=fleet.target_system,
            position=fleet.target_position,
        )
        session.add(disc)
    disc.intel = intel
    disc.level = level
    disc.discovered_at = _now()

    await create_system_transmission(
        session,
        player_id=fleet.player_id,
        subject=f"Spionagebericht: {target['name']} ({coords})",
        body=_build_report_body(coords, intel),
        ttype="spy_report",
        decision_payload=intel,
    )

    # NPC-Funkspruch (Phase 1): manchmal entdeckt ein feindliches Imperium die Sonden und warnt.
    if spy_npc is not None and getattr(spy_npc, "behavior_profile", None) not in ("trade_center", "merchant"):
        import random as _random
        if _random.random() < 0.35:
            try:
                from app.messaging.service import npc_reaction
                from app.platform.models import Player
                _spy = await session.get(Player, fleet.player_id)
                await npc_reaction(
                    session, player_id=fleet.player_id, npc=spy_npc, situation="spied",
                    context={"enemy": _spy.display_name if _spy else "Admiral", "planet": coords},
                    big_moment=False,
                )
            except Exception:  # noqa: BLE001 — Funkspruch darf die Spionage nie stoeren
                pass

    # Flavor (Phase 2): ab Detailstufe 2 fasst der Aufklaerungs-Offizier den Bericht erzaehlerisch
    # zusammen (additiv zum nuechternen Bericht; gedrosselt, da Spionage haeufig ist).
    if level >= 2:
        try:
            from app.platform.ai_jobs import enqueue_flavor
            _strength = ships_total + defenses_total
            _verdict = ("stark verteidigt" if _strength > 50
                        else "maessig verteidigt" if _strength > 10 else "schwach verteidigt")
            await enqueue_flavor(
                fleet.player_id, narrator="intel_officer", situation="Spionage-Aufklaerung",
                planet=coords, outcome=_verdict,
                detail={"Ziel": target["name"], "Flotte (Schiffe)": ships_total, "Verteidigung": defenses_total},
                subject=f"Aufklaerung: {target['name']} ({coords})",
            )
        except Exception:  # noqa: BLE001 — Flavor darf die Spionage nie stoeren
            pass

    log.info(
        "Spionage: player=%s coords=%s level=%d probes=%d spy_tech=%d",
        fleet.player_id, coords, level, probes, spy_tech,
    )
