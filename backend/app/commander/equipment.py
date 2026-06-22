"""Kommandeurs-Equipment: Katalog, Bonus-Berechnung, Inventar/Equip-Logik, Drops, Fertigung.

Items sind Instanzen (``CommanderItem``) im Spieler-Inventar; ein Item ist getragen, wenn
``equipped_commander_id`` gesetzt ist (genau eines je Slot/Kommandeur). Item-Boni haben dieselbe
Form ``{stat,target,pct}`` wie ``bonuses.py`` und werden (moral-skaliert) in die Schiffsboni
gemischt. Set-Boni greifen bei 2/4 getragenen Teilen eines Sets. Quellen: Quests/Expeditionen/
globale Events (Drops) + Akademie-Fertigung. P2W-frei — nur erspielt."""
from __future__ import annotations

import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.economy.service import get_building_levels, spend_resources
from app.messaging.service import create_system_transmission
from app.platform.balance import get_balance
from app.platform.models import Commander, CommanderItem, Planet


# -- Katalog-Zugriff ----------------------------------------------------------
def equipment_cfg() -> dict:
    return get_balance().commander.get("equipment", {})


def item_def(item_key: str) -> dict | None:
    return equipment_cfg().get("items", {}).get(item_key)


def rarity_mult(rarity: str) -> float:
    return float(equipment_cfg().get("rarities", {}).get(rarity, {}).get("mult", 1.0))


def _weighted_choice(weights: dict[str, float], rng: random.Random) -> str:
    items = [(k, float(v)) for k, v in weights.items() if float(v) > 0]
    if not items:
        return "common"
    total = sum(w for _, w in items)
    r = rng.random() * total
    acc = 0.0
    for key, w in items:
        acc += w
        if r <= acc:
            return key
    return items[-1][0]


# -- Bonus-Berechnung (rein, ohne DB) -----------------------------------------
def equipment_bonuses(items: list[CommanderItem]) -> list[dict]:
    """Flache Bonus-Liste ``[{stat,target,pct}]`` aus getragenen Items + aktiven Set-Boni.

    Item-pct wird mit dem Raritaets-Multiplikator skaliert; Set-Boni sind fix (raritaets-
    unabhaengig) und greifen ab 2/4 getragenen Teilen. Gleiche (stat,target) werden summiert."""
    cfg = equipment_cfg()
    catalog = cfg.get("items", {})
    sets_cfg = cfg.get("sets", {})
    raw: list[dict] = []
    set_counts: dict[str, int] = {}

    for it in items:
        d = catalog.get(it.item_key)
        if not d:
            continue
        mult = rarity_mult(it.rarity)
        for b in d.get("bonuses", []):
            raw.append({"stat": b["stat"], "target": b["target"], "pct": float(b["pct"]) * mult})
        s = d.get("set")
        if s:
            set_counts[s] = set_counts.get(s, 0) + 1

    for s, cnt in set_counts.items():
        sc = sets_cfg.get(s)
        if not sc:
            continue
        for thr_str, blist in sc.get("bonus", {}).items():
            if cnt >= int(thr_str):
                for b in blist:
                    raw.append({"stat": b["stat"], "target": b["target"], "pct": float(b["pct"])})

    merged: dict[tuple[str, str], float] = {}
    for b in raw:
        key = (b["stat"], b["target"])
        merged[key] = merged.get(key, 0.0) + b["pct"]
    return [
        {"stat": st, "target": tg, "pct": round(p, 4)}
        for (st, tg), p in merged.items()
        if abs(p) > 1e-9
    ]


def set_progress(items: list[CommanderItem]) -> dict[str, int]:
    """{set_key: Anzahl getragener Teile} fuer die UI-Anzeige."""
    catalog = equipment_cfg().get("items", {})
    counts: dict[str, int] = {}
    for it in items:
        d = catalog.get(it.item_key)
        s = d.get("set") if d else None
        if s:
            counts[s] = counts.get(s, 0) + 1
    return counts


# -- DB-Helfer ----------------------------------------------------------------
async def equipped_items(session: AsyncSession, commander_id: uuid.UUID) -> list[CommanderItem]:
    return list((await session.execute(
        select(CommanderItem).where(CommanderItem.equipped_commander_id == commander_id)
    )).scalars().all())


async def equipment_bonuses_for(session: AsyncSession, commander_id: uuid.UUID) -> list[dict]:
    """Equipment-Bonus-Liste eines Kommandeurs (zum Anhaengen an die Basis-Boni vor resolve)."""
    return equipment_bonuses(await equipped_items(session, commander_id))


async def commander_stat_bonus(
    session: AsyncSession, commander_id, stat: str, morale: int | float = 100
) -> float:
    """Moral-skalierter Gesamt-Prozentsatz eines NICHT-Schiffs-Bonus (mining_yield, trade_margin,
    spy_success, expedition_yield, research_speed, production, shipbuild_speed) aus der Ausrüstung
    eines Kommandeurs. 0.0 ohne Kommandeur/ohne passende Boni. Für Missions-/Gouverneurs-Effekte."""
    if not commander_id:
        return 0.0
    from app.commander.bonuses import morale_factor
    items = await equipped_items(session, commander_id)
    total = sum(float(b["pct"]) for b in equipment_bonuses(items) if b["stat"] == stat)
    return round(total * morale_factor(int(morale)), 4)


def item_to_dict(it: CommanderItem) -> dict:
    cfg = equipment_cfg()
    d = cfg.get("items", {}).get(it.item_key, {})
    rar = cfg.get("rarities", {}).get(it.rarity, {})
    mult = float(rar.get("mult", 1.0))
    return {
        "id": str(it.id),
        "item_key": it.item_key,
        "slot": it.slot,
        "rarity": it.rarity,
        "rarity_label": rar.get("label", it.rarity),
        "label": d.get("label", it.item_key),
        "set": d.get("set"),
        "equipped_commander_id": str(it.equipped_commander_id) if it.equipped_commander_id else None,
        "bonuses": [
            {"stat": b["stat"], "target": b["target"], "pct": round(float(b["pct"]) * mult, 4)}
            for b in d.get("bonuses", [])
        ],
    }


async def inventory_view(session: AsyncSession, player_id: uuid.UUID) -> list[dict]:
    items = list((await session.execute(
        select(CommanderItem).where(CommanderItem.player_id == player_id)
        .order_by(CommanderItem.acquired_at.desc())
    )).scalars().all())
    return [item_to_dict(it) for it in items]


async def equipment_view(session: AsyncSession, commander: Commander) -> dict:
    cfg = equipment_cfg()
    items = await equipped_items(session, commander.id)
    by_slot = {it.slot: item_to_dict(it) for it in items}
    counts = set_progress(items)
    sets_out = []
    for s, cnt in counts.items():
        sc = cfg.get("sets", {}).get(s, {})
        active = [int(t) for t in sc.get("bonus", {}) if cnt >= int(t)]
        sets_out.append({
            "key": s, "label": sc.get("label", s), "count": cnt,
            "active_thresholds": sorted(active),
        })
    return {
        "slots": [
            {"slot": sl, "label": cfg.get("slot_labels", {}).get(sl, sl), "item": by_slot.get(sl)}
            for sl in cfg.get("slots", [])
        ],
        "sets": sets_out,
        "bonuses": equipment_bonuses(items),
    }


# -- Equip / Unequip ----------------------------------------------------------
_BLOCKED_STATUS = {"dead", "captured", "defected"}


async def equip_item(session: AsyncSession, commander: Commander, item_id: uuid.UUID) -> CommanderItem:
    if commander.status in _BLOCKED_STATUS:
        raise RuntimeError("Kommandeur kann keine Ausruestung tragen")
    item = await session.get(CommanderItem, item_id)
    if item is None or item.player_id != commander.player_id:
        raise RuntimeError("Item nicht gefunden")
    # Vorhandenes Item im selben Slot dieses Kommandeurs zurueck ins Inventar.
    for existing in await equipped_items(session, commander.id):
        if existing.slot == item.slot and existing.id != item.id:
            existing.equipped_commander_id = None
    item.equipped_commander_id = commander.id
    await session.commit()
    return item


async def unequip_slot(session: AsyncSession, commander: Commander, slot: str) -> None:
    for it in await equipped_items(session, commander.id):
        if it.slot == slot:
            it.equipped_commander_id = None
    await session.commit()


# -- Fertigung (Akademie) -----------------------------------------------------
async def craft_item(
    session: AsyncSession, player_id: uuid.UUID, planet: Planet, item_key: str
) -> CommanderItem:
    cfg = equipment_cfg()
    d = cfg.get("items", {}).get(item_key)
    if not d:
        raise RuntimeError("Unbekanntes Item")
    craft = cfg.get("craft", {})
    levels = await get_building_levels(session, planet.id)
    need = int(craft.get("academy_min", 2))
    if levels.get("command_academy", 0) < need:
        raise RuntimeError(f"Kommando-Akademie Stufe {need} erforderlich")
    if not await spend_resources(session, planet, dict(craft.get("cost", {}))):
        raise RuntimeError("Nicht genug Ressourcen")
    item = CommanderItem(player_id=player_id, item_key=item_key, slot=d["slot"], rarity="common")
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


# -- Drops (Quests / Expeditionen / globale Events) ---------------------------
async def maybe_grant_item(
    session: AsyncSession, player_id: uuid.UUID, source: str,
    rng: random.Random | None = None, chance_override: float | None = None,
) -> CommanderItem | None:
    """Wuerfelt Drop-Chance der Quelle; bei Treffer wird ein zufaelliges Item (gewichtete
    Raritaet der Quelle) ins Inventar gelegt + eine Transmission gepusht. Caller committet (nur
    flush hier). ``chance_override`` ersetzt die Quellen-Chance (z. B. Piraten-Bestechung)."""
    cfg = equipment_cfg()
    drops = cfg.get("drops", {})
    chance = float(chance_override) if chance_override is not None else float(drops.get("chance", {}).get(source, 0.0))
    if chance <= 0:
        return None
    r = rng or random.Random()
    if r.random() > chance:
        return None
    keys = list(cfg.get("items", {}).keys())
    if not keys:
        return None
    item_key = r.choice(keys)
    d = cfg["items"][item_key]
    rarity = _weighted_choice(drops.get("rarity_weights", {}).get(source, {"common": 1}), r)
    item = CommanderItem(player_id=player_id, item_key=item_key, slot=d["slot"], rarity=rarity)
    session.add(item)
    await session.flush()
    rar_label = cfg.get("rarities", {}).get(rarity, {}).get("label", rarity)
    # Expeditions-Drops erscheinen im Expeditionen-Screen (2026-06-22), andere Quellen im Postfach.
    drop_ttype = "expedition" if source == "expedition" else "system"
    await create_system_transmission(
        session,
        player_id=player_id,
        subject="Ausruestung erbeutet",
        body=f"Geborgen: {d.get('label', item_key)} ({rar_label}). Ruest sie einem Kommandeur "
             f"im Slot „{cfg.get('slot_labels', {}).get(d['slot'], d['slot'])}\" aus.",
        ttype=drop_ttype,
        publish=False,
    )
    return item
