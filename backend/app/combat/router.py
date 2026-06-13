"""Router fuer Combat-Reports (api-contract §10) und den Was-waere-wenn-Simulator."""
from __future__ import annotations

import random
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.combat.engine import simulate_battle
from app.combat.service import _debris
from app.economy.service import get_research_levels
from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import CombatReport, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["combat"])

# Obergrenze fuer die Gesamt-Stueckzahl beider Seiten. Die Engine expandiert JEDE Einheit
# zu einem Einzelobjekt -> ohne Cap koennte ein bewusst riesiger Request den Server fluten.
MAX_SIM_UNITS = 50_000


def serialize_combat_report(report: CombatReport, viewer_id: uuid.UUID) -> dict:
    """Serialisiert einen Kampfbericht aus Sicht des abrufenden Spielers.

    Reicht die volle Engine-Ausgabe (Runden mit Distanz/Fliehen, Ueberlebende,
    gekaperte/gestrandete Schiffe) ans Frontend durch und markiert ueber ``role``,
    welche Seite der Betrachter war (wichtig bei eingehenden Angriffen, an denen der
    Spieler nicht selbst teilnimmt).
    """
    outcome = report.outcome or {}
    role = "attacker" if report.attacker_id == viewer_id else "defender"
    return {
        "id": str(report.id),
        "location": report.location,
        "role": role,
        "npc_name": outcome.get("npc_name"),
        "attacker": outcome.get("attacker_initial", {}),
        "defender": outcome.get("defender_initial", {}),
        "rounds": outcome.get("rounds", []),
        "winner": outcome.get("winner"),
        "attacker_survivors": outcome.get("attacker_survivors", {}),
        "defender_survivors": outcome.get("defender_survivors", {}),
        "attacker_losses": outcome.get("attacker_losses", {}),
        "defender_losses": outcome.get("defender_losses", {}),
        "attacker_fled": outcome.get("attacker_fled", {}),
        "defender_fled": outcome.get("defender_fled", {}),
        "attacker_captured": outcome.get("attacker_captured", {}),
        "defender_captured": outcome.get("defender_captured", {}),
        "attacker_drive_disabled": outcome.get("attacker_drive_disabled", {}),
        "defender_drive_disabled": outcome.get("defender_drive_disabled", {}),
        "loot": report.loot,
        "debris": report.debris,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


class CombatSimRequest(BaseModel):
    """Eingabe fuer den Kampf-Simulator (rein hypothetisch, kein Spielstand)."""
    attacker_ships: dict[str, int]
    defender_ships: dict[str, int] = {}
    defender_defenses: dict[str, int] = {}
    # Optionale Verteidiger-Forschung (weapons_/shield_/armor_tech). Default 0 = unerforschter
    # Gegner (abwaertskompatibel); gesetzt erlaubt "gegen Tech-N simulieren" (Befund #14).
    defender_tech: dict[str, int] = {}
    seed: int | None = None


def _prepare_sim_input(
    attacker_ships: dict[str, int],
    defender_ships: dict[str, int],
    defender_defenses: dict[str, int],
    ship_catalog: dict,
    defense_catalog: dict,
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Validiert + bereinigt die Sim-Eingabe. Reine Funktion (nur ``HTTPException``,
    keine DB/FastAPI-Abhaengigkeit) -> direkt testbar.

    - Counts muessen ganze Zahlen >= 0 sein; 0-Eintraege werden entfernt.
    - Jeder Typ muss im jeweiligen Katalog als echte Konfiguration (dict) existieren.
    - Beide Seiten brauchen >= 1 Einheit; Gesamtsumme <= ``MAX_SIM_UNITS``.
    """
    def clean(raw: dict[str, int], catalog: dict, kind: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for typ, count in raw.items():
            # bool ist Subklasse von int -> explizit ausschliessen.
            if isinstance(count, bool) or not isinstance(count, int):
                raise HTTPException(status_code=400, detail=f"Ungueltige Stueckzahl fuer '{typ}'.")
            if count < 0:
                raise HTTPException(status_code=400, detail=f"Stueckzahl fuer '{typ}' darf nicht negativ sein.")
            if count == 0:
                continue
            if not isinstance(catalog.get(typ), dict):
                raise HTTPException(status_code=400, detail=f"Unbekannter {kind}: '{typ}'.")
            out[typ] = count
        return out

    a_ships = clean(attacker_ships, ship_catalog, "Schiffstyp")
    d_ships = clean(defender_ships, ship_catalog, "Schiffstyp")
    d_def = clean(defender_defenses, defense_catalog, "Verteidigungstyp")

    if not a_ships or (not d_ships and not d_def):
        raise HTTPException(status_code=400, detail="Beide Seiten brauchen mindestens eine Einheit.")

    total = sum(a_ships.values()) + sum(d_ships.values()) + sum(d_def.values())
    if total > MAX_SIM_UNITS:
        raise HTTPException(status_code=400, detail="Zu viele Einheiten fuer die Simulation (max. 50.000).")

    return a_ships, d_ships, d_def


@router.post("/combat/simulate")
async def simulate_combat(
    body: CombatSimRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Simuliert eine hypothetische Schlacht ohne jeden Spielstand-Effekt.

    Angreifer nutzt die ECHTE Forschung des Spielers; der Gegner kaempft mit den optional
    uebergebenen ``defender_tech``-Stufen (Default 0 = unerforscht). Es wird NICHTS persistiert.
    Die Antwort hat exakt die Form von ``serialize_combat_report``, damit der Frontend-Viewer
    sie direkt rendert.
    """
    bal = get_balance()
    attacker_ships, defender_ships, defender_defenses = _prepare_sim_input(
        body.attacker_ships, body.defender_ships, body.defender_defenses,
        bal.ships, bal.defenses,
    )

    # Angreifer-Tech = echte Forschung des Spielers, Gegner-Tech = 0.
    research = await get_research_levels(session, player.id)
    atk_tech = {
        "weapons_tech": research.get("weapons_tech", 0),
        "shield_tech": research.get("shield_tech", 0),
        "armor_tech": research.get("armor_tech", 0),
    }
    # Verteidiger-Tech: Default 0, mit optional uebergebenen Stufen ueberschrieben (nur die
    # drei Kampf-Stufen, defensiv gegen Negativwerte geklemmt).
    def_tech = {"weapons_tech": 0, "shield_tech": 0, "armor_tech": 0}
    for _k in def_tech:
        _v = body.defender_tech.get(_k)
        if isinstance(_v, int) and not isinstance(_v, bool) and _v > 0:
            def_tech[_k] = _v

    seed = body.seed if body.seed is not None else random.randrange(1, 2 ** 62)
    attacker = {"ships": attacker_ships, "tech": atk_tech, "attack_mult": 1.0, "ship_bonuses": {}}
    defender = {"ships": defender_ships, "defenses": defender_defenses, "tech": def_tech, "attack_mult": 1.0}

    result = simulate_battle(attacker, defender, seed, bal.data)

    debris_a = _debris(result["attacker_losses"])
    debris_d = _debris(result["defender_losses"])
    return {
        "id": "sim", "location": "Simulation", "role": "attacker", "npc_name": None,
        "attacker": result["attacker_initial"], "defender": result["defender_initial"],
        "rounds": result["rounds"], "winner": result["winner"],
        "attacker_survivors": result["attacker_survivors"], "defender_survivors": result["defender_survivors"],
        "attacker_losses": result["attacker_losses"], "defender_losses": result["defender_losses"],
        "attacker_fled": result.get("attacker_fled", {}), "defender_fled": result.get("defender_fled", {}),
        "attacker_captured": result.get("attacker_captured", {}), "defender_captured": result.get("defender_captured", {}),
        "attacker_drive_disabled": result.get("attacker_drive_disabled", {}),
        "defender_drive_disabled": result.get("defender_drive_disabled", {}),
        "loot": {"metal": 0, "crystal": 0, "deuterium": 0},
        "debris": {"metal": round(debris_a["metal"] + debris_d["metal"], 1),
                   "crystal": round(debris_a["crystal"] + debris_d["crystal"], 1)},
        "created_at": None, "seed": result["seed"],
    }


@router.get("/combat-reports/{report_id}")
async def get_combat_report(
    report_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    report = await session.get(CombatReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Combat-Report nicht gefunden")
    if report.attacker_id != player.id and report.defender_id != player.id:
        raise HTTPException(status_code=403, detail="Kein Zugriff auf diesen Report")

    return serialize_combat_report(report, player.id)
