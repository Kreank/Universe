"""Router fuer Commander & Span (api-contract §7)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commander.bonuses import base_bonuses
from app.commander.schemas import (
    BonusOut,
    CommanderDetailOut,
    CommanderOut,
    SpanOut,
    TrainRequest,
    TrainResponse,
)
from app.commander.equipment import (
    craft_item,
    equip_item,
    equipment_cfg,
    equipment_view,
    inventory_view,
    unequip_slot,
)
from app.commander.service import commander_to_dict, compute_span, start_training
from app.platform.balance import get_balance
from app.messaging.service import transmission_to_dict
from app.platform.db import get_session
from app.platform.models import Commander, Planet, Player, Transmission
from app.platform.security import get_current_player

router = APIRouter(tags=["commander"])


@router.get("/commanders", response_model=list[CommanderOut])
async def list_commanders(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    rows = (await session.execute(
        select(Commander).where(Commander.player_id == player.id).order_by(Commander.created_at)
    )).scalars().all()
    return [await commander_to_dict(session, c) for c in rows]


@router.get("/player/span", response_model=SpanOut)
async def get_span(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> SpanOut:
    span = await compute_span(session, player.id)
    return SpanOut(**span)


@router.get("/commanders/ability-catalog")
async def ability_catalog(player: Player = Depends(get_current_player)) -> dict:
    """Erlernbare Faehigkeiten (RPG) + Progressions-Parameter fuer das UI."""
    cat = dict(get_balance().commander.get("ability_catalog", {}))
    cat.pop("_note", None)
    return {"catalog": cat, "progression": get_balance().commander.get("ability_progression", {})}


@router.post("/commanders/{commander_id}/abilities/train")
async def train_ability(
    commander_id: uuid.UUID,
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Erlernt eine Faehigkeit (Stufe 1) bzw. steigert sie um eine Stufe (kostet Skillpunkte)."""
    from app.commander.service import _rank_index, ability_def, commander_ability_level

    key = body.get("key")
    c = await session.get(Commander, commander_id)
    if c is None or c.player_id != player.id:
        raise HTTPException(status_code=404, detail="Kommandeur nicht gefunden")
    bal = get_balance()
    ab = ability_def(key, bal)
    if ab is None:
        raise HTTPException(status_code=404, detail="Faehigkeit unbekannt")
    if _rank_index(c.rank, bal) < _rank_index(ab.get("requires", {}).get("min_rank", "cadet"), bal):
        raise HTTPException(status_code=409, detail="Rang zu niedrig fuer diese Faehigkeit")
    cur = commander_ability_level(c, key)
    if cur >= int(ab["max_level"]):
        raise HTTPException(status_code=409, detail="Faehigkeit bereits auf Maximalstufe")
    cost = int(ab.get("sp_cost", 1))
    if int(c.skill_points or 0) < cost:
        raise HTTPException(status_code=409, detail="Nicht genug Skillpunkte")
    c.skill_points = int(c.skill_points or 0) - cost
    abilities = [dict(a) for a in (c.abilities or [])]
    for a in abilities:
        if a.get("key") == key:
            a["level"] = cur + 1
            break
    else:
        abilities.append({"key": key, "level": 1})
    c.abilities = abilities
    await session.commit()
    return await commander_to_dict(session, c)


@router.post("/commanders/{commander_id}/abilities/forget")
async def forget_ability(
    commander_id: uuid.UUID,
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Verlernt eine Faehigkeit; erstattet einen Teil der Skillpunkte."""
    from app.commander.service import ability_def, commander_ability_level

    key = body.get("key")
    c = await session.get(Commander, commander_id)
    if c is None or c.player_id != player.id:
        raise HTTPException(status_code=404, detail="Kommandeur nicht gefunden")
    cur = commander_ability_level(c, key)
    if cur <= 0:
        raise HTTPException(status_code=404, detail="Faehigkeit nicht erlernt")
    bal = get_balance()
    ab = ability_def(key, bal) or {"sp_cost": 1}
    refund_ratio = float(bal.commander["ability_progression"].get("unlearn_refund", 0.5))
    # Kaufmaennisch aufrunden (int(x + 0.5)): Pythons round() nutzt Banker's Rounding, dort gibt
    # round(0.5) == 0 -> eine Stufe-1-Faehigkeit (sp_cost 1, ratio 0.5) haette 0 SP erstattet
    # ("Skillpunkt kommt nicht zurueck"-Bug). So bekommt man bei ratio>0 mindestens 1 SP zurueck.
    spent = cur * int(ab.get("sp_cost", 1))
    refund = int(spent * refund_ratio + 0.5)
    c.skill_points = int(c.skill_points or 0) + refund
    c.abilities = [a for a in (c.abilities or []) if a.get("key") != key]
    await session.commit()
    return await commander_to_dict(session, c)


@router.post("/commanders/{commander_id}/retrain-traits")
async def retrain_traits(
    commander_id: uuid.UUID,
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Charakter-Zucht (Ressourcen-Kosten am Heimatplaneten):
    body = {mode: 'reroll'|'replace', trait?: <gewuenscht>, drop?: <zu ersetzen>}."""
    import random as _random

    from app.economy.service import spend_resources

    c = await session.get(Commander, commander_id)
    if c is None or c.player_id != player.id:
        raise HTTPException(status_code=404, detail="Kommandeur nicht gefunden")
    bal = get_balance()
    tt = bal.commander.get("trait_training", {})
    trait_keys = list(bal.commander["personality_traits"].keys())
    mode = body.get("mode", "reroll")

    # Kosten am Heimatplaneten (bzw. erstem Planeten) abziehen.
    home = (await session.execute(
        select(Planet).where(Planet.player_id == player.id)
        .order_by(Planet.is_homeworld.desc(), Planet.created_at.asc())
    )).scalars().first()
    if home is None:
        raise HTTPException(status_code=409, detail="Kein Planet fuer die Ausbildung")

    if mode == "reroll":
        cost = tt.get("reroll_cost", {})
        if not await spend_resources(session, home, cost):
            raise HTTPException(status_code=409, detail="Nicht genug Ressourcen fuer Reroll")
        c.traits = _random.sample(trait_keys, k=_random.randint(1, 2))
    elif mode == "replace":
        desired = body.get("trait")
        if desired not in trait_keys:
            raise HTTPException(status_code=422, detail="Unbekannter Wunsch-Trait")
        cost = tt.get("replace_cost", {})
        if not await spend_resources(session, home, cost):
            raise HTTPException(status_code=409, detail="Nicht genug Ressourcen fuer Trait-Ersatz")
        traits = list(c.traits or [])
        drop = body.get("drop")
        if drop in traits:
            traits.remove(drop)
        elif traits:
            traits.pop(0)
        if desired not in traits:
            traits.append(desired)
        c.traits = traits[:2]
    else:
        raise HTTPException(status_code=400, detail="Ungueltiger Modus")
    await session.commit()
    return await commander_to_dict(session, c)


@router.put("/planets/{planet_id}/governor")
async def set_governor(
    planet_id: uuid.UUID,
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Setzt/entfernt den Gouverneur eines eigenen Planeten (Produktions-Bonus).
    body = {commander_id: <uuid>|null}. Ein Gouverneur kann nicht zugleich eine Flotte fuehren."""
    from app.platform.models import Fleet

    planet = await session.get(Planet, planet_id)
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    cid = body.get("commander_id")
    if not cid:
        planet.governor_commander_id = None
        await session.commit()
        return {"ok": True, "governor_commander_id": None}
    commander = await session.get(Commander, uuid.UUID(str(cid)))
    if commander is None or commander.player_id != player.id:
        raise HTTPException(status_code=404, detail="Kommandeur nicht gefunden")
    if commander.status != "active":
        raise HTTPException(status_code=409, detail="Kommandeur ist nicht einsatzbereit")
    in_fleet = (await session.execute(
        select(Fleet.id).where(
            Fleet.commander_id == commander.id,
            Fleet.status.in_(("flying", "arrived", "returning")),
        )
    )).first() is not None
    if in_fleet:
        raise HTTPException(status_code=409, detail="Kommandeur ist aktuell auf einem Flotteneinsatz")
    # Aus etwaiger anderer Gouverneurs-Position abziehen.
    await session.execute(
        Planet.__table__.update()
        .where(Planet.governor_commander_id == commander.id)
        .values(governor_commander_id=None)
    )
    planet.governor_commander_id = commander.id
    await session.commit()
    return {"ok": True, "governor_commander_id": str(commander.id)}


@router.get("/player/doctrine")
async def get_doctrine(
    player: Player = Depends(get_current_player),
) -> dict:
    from app.platform.doctrine import options
    dcfg = get_balance().data.get("doctrines", {})
    return {
        "current": player.doctrine,
        "options": options(),
        "switch_cost": dcfg.get("switch_cost", {}),
        "switch_cooldown_seconds": dcfg.get("switch_cooldown_seconds", 0),
        "changed_at": player.doctrine_changed_at,
    }


@router.post("/player/doctrine")
async def set_player_doctrine(
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.platform.doctrine import set_doctrine
    try:
        result = await set_doctrine(session, player, str(body.get("doctrine", "")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return result


@router.get("/commanders/bonus-preview", response_model=list[BonusOut])
async def bonus_preview(
    specialization: str = "combat",
    focus: str | None = None,
    rank: str = "cadet",
    grade: str = "C",
    player: Player = Depends(get_current_player),
) -> list[dict]:
    """Vorschau der Boni fuer eine (Spezialisierung, Fokus, Grad)-Kombination — damit der
    Spieler vor der Ausbildung sieht, welches Profil entsteht. Default-Rang Kadett, Grad C.
    Muss VOR /commanders/{commander_id} stehen, sonst matcht der Pfad-Parameter."""
    bal = get_balance()
    valid_specs = bal.commander["specializations"]
    spec = specialization if specialization in valid_specs else "combat"
    valid_classes = [k for k in bal.commander["ship_classes"].keys() if not k.startswith("_")]
    foc = focus if focus in valid_classes else None
    rank_keys = {r["key"] for r in bal.commander["ranks"]}
    rk = rank if rank in rank_keys else "cadet"
    grd = grade if grade in bal.grades["potency"] else "C"
    # Ohne explizite Traits (die kommen bei der Ausbildung zufaellig dazu).
    return base_bonuses(spec, rk, [], foc, grd)


@router.get("/commanders/equipment-catalog")
async def equipment_catalog(player: Player = Depends(get_current_player)) -> dict:
    """Statischer Equipment-Katalog (Slots, Items, Sets, Raritaeten, Fertigungskosten) fuers UI.
    Muss VOR /commanders/{commander_id} stehen, sonst matcht der Pfad-Parameter."""
    cfg = dict(equipment_cfg())
    cfg.pop("_note", None)
    return cfg


@router.get("/player/inventory")
async def get_inventory(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await inventory_view(session, player.id)


@router.post("/commanders/craft", status_code=201)
async def craft_equipment(
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Akademie-Fertigung: stellt ein Katalog-Item gegen Ressourcen her (rarity=common).
    Body: {planet_id, item_key}. Muss VOR /commanders/{commander_id} stehen."""
    planet = await session.get(Planet, uuid.UUID(str(body.get("planet_id"))))
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    try:
        item = await craft_item(session, player.id, planet, str(body.get("item_key")))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    from app.commander.equipment import item_to_dict
    return item_to_dict(item)


@router.get("/commanders/{commander_id}", response_model=CommanderDetailOut)
async def get_commander(
    commander_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    c = await session.get(Commander, commander_id)
    if c is None or c.player_id != player.id:
        raise HTTPException(status_code=404, detail="Commander nicht gefunden")
    data = await commander_to_dict(session, c)
    history = (await session.execute(
        select(Transmission)
        .where(Transmission.commander_id == c.id)
        .order_by(Transmission.created_at.desc())
    )).scalars().all()
    data["history"] = [transmission_to_dict(t) for t in history]
    return data


@router.post("/commanders/train", status_code=202, response_model=TrainResponse)
async def train_commander(
    body: TrainRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> TrainResponse:
    planet = await session.get(Planet, uuid.UUID(body.planet_id))
    if planet is None or planet.player_id != player.id:
        raise HTTPException(status_code=404, detail="Planet nicht gefunden")
    try:
        commander = await start_training(
            session, planet, body.specialization, body.focus, body.tier
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    data = await commander_to_dict(session, commander)
    return TrainResponse(commander=CommanderOut(**data))


async def _owned_commander(session: AsyncSession, player: Player, commander_id: uuid.UUID) -> Commander:
    c = await session.get(Commander, commander_id)
    if c is None or c.player_id != player.id:
        raise HTTPException(status_code=404, detail="Commander nicht gefunden")
    return c


@router.get("/commanders/{commander_id}/equipment")
async def get_equipment(
    commander_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    c = await _owned_commander(session, player, commander_id)
    return await equipment_view(session, c)


@router.post("/commanders/{commander_id}/equip")
async def equip(
    commander_id: uuid.UUID,
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Ruestet ein Inventar-Item (Body: {item_id}) in seinen Slot; vorheriges Item des Slots
    wandert zurueck ins Inventar."""
    c = await _owned_commander(session, player, commander_id)
    try:
        await equip_item(session, c, uuid.UUID(str(body.get("item_id"))))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return await equipment_view(session, c)


@router.post("/commanders/{commander_id}/unequip")
async def unequip(
    commander_id: uuid.UUID,
    body: dict,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Legt das Item eines Slots (Body: {slot}) ab — zurueck ins Inventar."""
    c = await _owned_commander(session, player, commander_id)
    await unequip_slot(session, c, str(body.get("slot")))
    return await equipment_view(session, c)