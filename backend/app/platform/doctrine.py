"""Imperiums-Doktrinen (Doku 03b §9): datengetriebene Boni-Helfer + Wahl/Wechsel-Logik.

Doktrinen geben passive Boni (Flottenslots, guenstigere/schnellere Signatur-Schiffe, Kampf-
Angriff) — KEINE harten Locks. Werte in ``balance.doctrines``. Wechsel kostet + Cooldown.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import RESOURCE_KEYS
from app.platform.balance import get_balance
from app.platform.models import Planet, Player


def _doctrines() -> dict:
    return get_balance().data.get("doctrines", {})


def _list() -> dict:
    return _doctrines().get("list", {})


def doctrine_cfg(key: str | None) -> dict:
    return _list().get(key or "", {})


def is_valid(key: str | None) -> bool:
    return key in _list()


def fleet_slot_bonus(key: str | None) -> int:
    return int(doctrine_cfg(key).get("fleet_slot_bonus", 0))


def combat_attack_mult(key: str | None) -> float:
    return float(doctrine_cfg(key).get("combat_attack_mult", 1.0))


def signature_mult(key: str | None, ship_type: str) -> tuple[float, float]:
    """(cost_mult, time_mult) fuer ein Schiff unter der Doktrin (1.0/1.0 wenn nicht Signatur)."""
    cfg = doctrine_cfg(key)
    if ship_type in cfg.get("signature_ships", []):
        return float(cfg.get("signature_cost_mult", 1.0)), float(cfg.get("signature_time_mult", 1.0))
    return 1.0, 1.0


def options() -> list[dict]:
    """Liste waehlbarer Doktrinen (key + label + Kurzprofil) fuer die UI."""
    out = []
    for key, cfg in _list().items():
        out.append({
            "key": key,
            "label": cfg.get("label", key),
            "fleet_slot_bonus": cfg.get("fleet_slot_bonus", 0),
            "combat_attack_mult": cfg.get("combat_attack_mult", 1.0),
            "signature_ships": cfg.get("signature_ships", []),
        })
    return out


async def set_doctrine(session: AsyncSession, player: Player, key: str) -> dict:
    """Waehlt/wechselt die Doktrin. Erstwahl ist gratis; ein Wechsel kostet switch_cost und
    unterliegt einem Cooldown. Liefert {doctrine, changed}."""
    if not is_valid(key):
        raise ValueError(f"Unbekannte Doktrin: {key}")
    if player.doctrine == key:
        return {"doctrine": key, "changed": False}

    dcfg = _doctrines()
    now = dt.datetime.now(dt.timezone.utc)

    if player.doctrine is not None:
        # Wechsel: Cooldown pruefen ...
        last = player.doctrine_changed_at
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=dt.timezone.utc)
            cd = float(dcfg.get("switch_cooldown_seconds", 0))
            if (now - last).total_seconds() < cd:
                raise RuntimeError("Doktrin-Wechsel noch im Cooldown")
        # ... und Kosten vom Heimatplaneten abziehen.
        from app.economy.service import spend_resources
        from sqlalchemy import select
        home = (await session.execute(
            select(Planet).where(Planet.player_id == player.id, Planet.is_homeworld.is_(True))
        )).scalars().first()
        cost = {k: float(dcfg.get("switch_cost", {}).get(k, 0)) for k in RESOURCE_KEYS}
        if home is None or not await spend_resources(session, home, cost):
            raise RuntimeError("Nicht genug Ressourcen fuer den Doktrin-Wechsel")

    player.doctrine = key
    player.doctrine_changed_at = now
    return {"doctrine": key, "changed": True}
