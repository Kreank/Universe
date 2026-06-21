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
    Building,
    Defense,
    Fleet,
    NpcEmpire,
    Planet,
    PlayerDiscovery,
    Research,
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
            # Gebaeudestufen (dieser Planet) + Forschungsstufen (kontoweit, Ziel-Spieler) — fuer
            # das L3-Voll-Dossier. Forschung haengt am Spieler, nicht am Planeten.
            bld_rows = (await session.execute(
                select(Building).where(Building.planet_id == planet.id)
            )).scalars().all()
            res_levels = (await session.execute(
                select(Research).where(Research.player_id == planet.player_id)
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
                "buildings": {b.type: b.level for b in bld_rows if b.level > 0},
                "research": {r.type: r.level for r in res_levels if r.level > 0},
                "kind": "player",
            }

    return None


def _combat_tech(tech: dict) -> dict[str, int]:
    """Reduziert ein Tech-Dict auf die drei kampfrelevanten Kerntechs (Waffen/Schild/Panzerung).

    Genau die Stufen, die ``combat.engine`` fuer Angriff/Schild/Huelle liest und die der
    Combat-Simulator als ``defender_tech`` vorbelegen soll."""
    return {
        "weapons_tech": int(tech.get("weapons_tech", 0)),
        "shield_tech": int(tech.get("shield_tech", 0)),
        "armor_tech": int(tech.get("armor_tech", 0)),
    }


async def _npc_combat_tech(session: AsyncSession, npc: NpcEmpire, bal) -> dict[str, int]:
    """Effektive NPC-Kampftech — EXAKT wie im echten Kampf (``combat.service.resolve_attack``):
    ``tier_tech(npc_tech-Basis, effective_tier(Region+Spieler+Alter), tier_cfg)``.

    Damit stimmt der Combat-Sim-Preload (Gegner-Tech aus Spionage) mit der Realitaet ueberein."""
    from app.npc.scaling import effective_tier, nearest_player_score, tier_tech
    tier_cfg = bal.npc.get("tier", {})
    age = (_now() - npc.created_at).total_seconds() if npc.created_at else 0.0
    eff = effective_tier(
        npc.galaxy, npc.system, npc.position,
        await nearest_player_score(session, npc.galaxy, npc.system, npc.position),
        age, tier_cfg,
    )
    return tier_tech(bal.npc.get("attack", {}).get("npc_tech", {}), eff, tier_cfg)


def _fmt_units(units: dict[str, int]) -> str:
    if not units:
        return "keine"
    return ", ".join(f"{cnt}x {typ}" for typ, cnt in units.items())


def _fmt_levels(levels: dict[str, int]) -> str:
    """Gebaeude/Forschung als Stufen (nicht Stueckzahl): 'metal_mine Stufe 5'."""
    if not levels:
        return "keine"
    return ", ".join(f"{typ} Stufe {lvl}" for typ, lvl in levels.items())


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
        ct = intel.get("combat_tech")
        if ct:
            lines.append(
                f"Kampftech: Waffen {ct.get('weapons_tech', 0)} · "
                f"Schild {ct.get('shield_tech', 0)} · Panzerung {ct.get('armor_tech', 0)}"
            )
    else:
        lines.append("Flotten-/Verteidigungs-Zusammensetzung: unklar (mehr Sonden oder Spionagetech noetig).")
        lines.append("Kampftech: nicht aufgeklaert (mehr Sonden oder Spionagetech noetig).")
    if level >= 3:
        lines.append(f"Ressourcen: {_fmt_resources(intel.get('resources', {}))}")
        if intel.get("buildings"):
            lines.append(f"Gebaeude: {_fmt_levels(intel['buildings'])}")
        if intel.get("research"):
            lines.append(f"Forschung: {_fmt_levels(intel['research'])}")
    else:
        lines.append("Ressourcen/Gebaeude/Forschung: nicht aufgeklaert (Stufe 3 noetig).")
    eco = intel.get("economy")
    if eco:
        lines.append(f"Wirtschaft: Ausbaustufe {eco.get('development', '?')}, "
                     f"Forschung Stufe {eco.get('research', '?')}.")
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

    # Sonnensturm-Event: Zielsystem geblendet -> Spionage scheitert an Interferenz.
    from app.events.buffs import is_blocked as _is_blocked
    if await _is_blocked(session, "spionage_block", galaxy=fleet.target_galaxy, system=fleet.target_system):
        await create_system_transmission(
            session,
            player_id=fleet.player_id,
            subject=f"Spionage blockiert ({coords})",
            body=f"Die Sonden erreichten {coords}, doch ein Sonnensturm schirmt das System "
                 f"durch ionosphaerische Stoerungen ab. Kein Aufklaerungsergebnis.",
            ttype="spy_report",
        )
        log.info("Spionage blockiert (Sonnensturm): player=%s coords=%s", fleet.player_id, coords)
        return

    # Kosmische Anomalie am Ziel? -> Sonde sichert Forschungstempo-Buff (statt normaler Spionage).
    from app.events.service import try_anomaly_probe
    anomaly_msg = await try_anomaly_probe(
        session, fleet.player_id, fleet.target_galaxy, fleet.target_system, fleet.target_position
    )
    if anomaly_msg is not None:
        await create_system_transmission(
            session, player_id=fleet.player_id,
            subject=f"🌀 Anomalie vermessen ({coords})", body=anomaly_msg, ttype="spy_report",
        )
        log.info("Anomalie-Sonde: player=%s coords=%s", fleet.player_id, coords)
        return

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
        "galaxy": fleet.target_galaxy,
        "system": fleet.target_system,
        "position": fleet.target_position,
        "ships_total": ships_total,
        "defenses_total": defenses_total,
        "level": level,
        "scanned_at": _now().isoformat(),
    }
    if level >= 2:
        intel["fleet"] = target["fleet"]
        intel["defenses"] = target["defenses"]
        # Kampftech (Waffen/Schild/Panzerung): attack-relevante Kerninfo -> bereits ab Stufe 2.
        # Spieler-Ziel: aus dessen Forschung. NPC-Ziel: die EFFEKTIVE Tech, mit der das NPC
        # tatsaechlich kaempft (gleiche Quelle wie resolve_attack). Speist den Combat-Sim-Preload.
        if target["kind"] == "player":
            intel["combat_tech"] = _combat_tech(target.get("research", {}))
        else:
            _spy_npc = target.get("npc")
            if _spy_npc is not None:
                try:
                    intel["combat_tech"] = _combat_tech(
                        await _npc_combat_tech(session, _spy_npc, bal)
                    )
                except Exception:  # noqa: BLE001 — Kampftech-Intel darf den Bericht nie stoeren
                    pass
    if level >= 3:
        intel["resources"] = target["resources"]
        # Voll-Dossier (Sascha-Entscheid): Gebaeude- + Forschungsstufen erst ab Stufe 3.
        # Nur fuer Spieler-Ziele (NPCs liefern stattdessen 'economy', s.u.).
        if target["kind"] == "player":
            intel["buildings"] = target.get("buildings", {})
            intel["research"] = target.get("research", {})

    # Haendler-NPC: Spec + aktuelle Kurse ins Intel mergen (Spionage deckt den Markt auf).
    spy_npc = target.get("npc")
    if spy_npc is not None and getattr(spy_npc, "behavior_profile", None) == "merchant":
        # Lazy-Import -> kein Modul-Zyklus (trade.py importiert spionage.py nicht).
        from app.fleet.trade import ensure_market, merchant_intel
        ensure_market(spy_npc, bal.trade)
        intel.update(merchant_intel(spy_npc, bal.trade, _now().isoformat()))

    # NPC-Wirtschaft sichtbar machen (ab Stufe 2): Ausbau- + Forschungsstufe aus dem WIRKSAMEN Tier
    # (Region + naechster Spieler + Alters-Entwicklung) herleiten. Zeigt, dass NPCs wirtschaftlich
    # ueber die Zeit wachsen — nicht bloss Schiffe horten.
    if spy_npc is not None and level >= 2 and getattr(spy_npc, "behavior_profile", None) != "trade_center":
        try:
            from app.npc.scaling import effective_tier, nearest_player_score
            _tcfg = bal.npc.get("tier", {})
            _age = (_now() - spy_npc.created_at).total_seconds() if spy_npc.created_at else 0.0
            _eff = effective_tier(
                spy_npc.galaxy, spy_npc.system, spy_npc.position,
                await nearest_player_score(session, spy_npc.galaxy, spy_npc.system, spy_npc.position),
                _age, _tcfg,
            )
            _tpt = float(_tcfg.get("tech_per_tier", 0.0))
            intel["economy"] = {
                "development": int(round(_eff)),
                "research": 1 + int(round((max(1.0, _eff) - 1.0) * _tpt)),
            }
        except Exception:  # noqa: BLE001 — Wirtschafts-Intel darf den Bericht nie stoeren
            pass

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
        # Entdeckungschance aus balance.json (Befund M-3) statt hartkodiert.
        _detect = float(get_balance().data.get("spy", {}).get("npc_detect_reaction_chance", 0.35))
        # Spaeher-Garnitur (Equipment des Kommandeurs): senkt die Entdeckungschance (stealthier).
        if getattr(fleet, "commander_id", None):
            from app.commander.equipment import commander_stat_bonus
            from app.platform.models import Commander as _Cmd
            _cmd = await session.get(_Cmd, fleet.commander_id)
            _detect *= max(0.0, 1.0 - await commander_stat_bonus(
                session, fleet.commander_id, "spy_success", _cmd.morale if _cmd else 100))
        if _random.random() < _detect:
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
            _kind = "feindliches NPC-Imperium" if spy_npc is not None else "Spieler-Imperium"
            # Bilanz-Hinweis fuer einen zielspezifischen Text: wie steht Flotte zu Verteidigung?
            if defenses_total == 0 and ships_total > 0:
                _balance = "Flotte vorhanden, praktisch KEINE Bodenverteidigung"
            elif ships_total >= max(1, defenses_total) * 4:
                _balance = "stark flottenlastig, duenne Verteidigung"
            elif defenses_total >= max(1, ships_total) * 2:
                _balance = "schwerpunktmaessig Verteidigung, wenig Flotte"
            else:
                _balance = "ausgewogen aus Flotte und Verteidigung"
            _detail = {
                "Ziel-Typ": _kind,
                "Flotte (Schiffe)": ships_total,
                "Verteidigung": defenses_total,
                "Bilanz": _balance,
            }
            _eco = intel.get("economy")
            if _eco:
                _detail["Wirtschaft (Ausbaustufe)"] = _eco.get("development")
                _detail["Forschungsstufe"] = _eco.get("research")
            await enqueue_flavor(
                fleet.player_id, narrator="intel_officer",
                situation=f"Spionage-Aufklaerung gegen {_kind}",
                planet=coords, outcome=_verdict, detail=_detail,
                subject=f"Aufklaerung: {target['name']} ({coords})",
                ttype="spy_report",
            )
        except Exception:  # noqa: BLE001 — Flavor darf die Spionage nie stoeren
            pass

    log.info(
        "Spionage: player=%s coords=%s level=%d probes=%d spy_tech=%d",
        fleet.player_id, coords, level, probes, spy_tech,
    )
