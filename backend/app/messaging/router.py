"""Router fuer Postfach/Funksprueche (api-contract §8)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.schemas import (
    DecideRequest,
    DecideResponse,
    OkResponse,
    SendMessageRequest,
    TransmissionOut,
)
from app.platform.balance import get_balance
from app.platform.db import get_session
from app.platform.models import Commander, Player, Transmission
from app.platform.security import get_current_player

router = APIRouter(tags=["messaging"])


@router.post("/advisor", status_code=202, response_model=OkResponse)
async def request_advisor_endpoint(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> OkResponse:
    """KI-Berater anfordern (Phase 5): fasst die Imperiums-Lage zusammen + reiht einen advisor-
    flavor-Job ein. Der Rat trifft kurz darauf als Funkspruch im Postfach ein (WS-Push)."""
    from app.messaging.advisor import request_advisor
    await request_advisor(session, player)
    return OkResponse(ok=True)


@router.get("/transmissions", response_model=list[TransmissionOut])
async def list_transmissions(
    unread: bool = False,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[TransmissionOut]:
    stmt = select(Transmission).where(Transmission.player_id == player.id)
    if unread:
        stmt = stmt.where(Transmission.read.is_(False))
    stmt = stmt.order_by(Transmission.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()

    # Absendernamen fuer Spieler-Nachrichten aufloesen (ein Lookup je Batch).
    sender_ids = {t.from_player_id for t in rows if t.from_player_id}
    names: dict = {}
    if sender_ids:
        srows = (await session.execute(
            select(Player.id, Player.display_name).where(Player.id.in_(sender_ids))
        )).all()
        names = {pid: nm for pid, nm in srows}

    out: list[TransmissionOut] = []
    for t in rows:
        item = TransmissionOut.model_validate(t)
        item.from_name = names.get(t.from_player_id) if t.from_player_id else None
        out.append(item)
    return out


@router.post("/messages", status_code=202, response_model=TransmissionOut)
async def send_message(
    body: SendMessageRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> TransmissionOut:
    """Schickt eine Spieler-zu-Spieler-Nachricht ins Postfach des Empfaengers.

    Klassisch/async — fuer Handels-Verhandlung. Landet als 'player_message' beim
    Empfaenger mit Absender; eine Antwort ist erneut ein send_message."""
    subject = (body.subject or "").strip()[:140] or "(ohne Betreff)"
    text = (body.body or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Nachricht darf nicht leer sein")
    if body.to_player_id == player.id:
        raise HTTPException(status_code=422, detail="Nachricht an sich selbst nicht moeglich")
    recipient = await session.get(Player, body.to_player_id)
    if recipient is None:
        raise HTTPException(status_code=404, detail="Empfaenger nicht gefunden")

    t = Transmission(
        player_id=recipient.id,
        from_player_id=player.id,
        type="player_message",
        subject=subject,
        body=text[:4000],
        requires_decision=False,
        read=False,
    )
    session.add(t)
    await session.flush()
    await session.commit()
    item = TransmissionOut.model_validate(t)
    item.from_name = player.display_name
    return item


@router.post("/transmissions/{transmission_id}/read", response_model=OkResponse)
async def mark_read(
    transmission_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> OkResponse:
    t = await session.get(Transmission, transmission_id)
    if t is None or t.player_id != player.id:
        raise HTTPException(status_code=404, detail="Transmission nicht gefunden")
    t.read = True
    return OkResponse(ok=True)


@router.delete("/transmissions/read", response_model=OkResponse)
async def delete_read(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> OkResponse:
    """Loescht alle gelesenen Funksprueche (offene Forderungen bleiben erhalten)."""
    await session.execute(
        delete(Transmission).where(
            Transmission.player_id == player.id,
            Transmission.read.is_(True),
            Transmission.requires_decision.is_(False),
        )
    )
    return OkResponse(ok=True)


@router.delete("/transmissions/{transmission_id}", response_model=OkResponse)
async def delete_transmission(
    transmission_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> OkResponse:
    """Loescht einen einzelnen Funkspruch des Spielers."""
    t = await session.get(Transmission, transmission_id)
    if t is None or t.player_id != player.id:
        raise HTTPException(status_code=404, detail="Transmission nicht gefunden")
    await session.delete(t)
    return OkResponse(ok=True)


@router.post("/transmissions/{transmission_id}/decide", response_model=DecideResponse)
async def decide(
    transmission_id: uuid.UUID,
    body: DecideRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> DecideResponse:
    """Forderungs-Mechanik (Doku 05 §7). Kein LLM noetig."""
    t = await session.get(Transmission, transmission_id)
    if t is None or t.player_id != player.id:
        raise HTTPException(status_code=404, detail="Transmission nicht gefunden")
    if not t.requires_decision:
        raise HTTPException(status_code=409, detail="Diese Transmission erfordert keine Entscheidung")
    if body.choice not in ("accept", "reject", "negotiate"):
        raise HTTPException(status_code=400, detail="Ungueltige Wahl")

    bal = get_balance()
    deltas = bal.commander["morale"]["deltas"]
    if body.choice == "accept":
        morale_delta = deltas["demand_fulfilled"]
        message = "Forderung erfuellt. Die Crew ist zufrieden."
    elif body.choice == "reject":
        morale_delta = deltas["demand_ignored"]
        message = "Forderung abgelehnt. Die Moral leidet."
    else:  # negotiate -> halber positiver Effekt
        morale_delta = deltas["demand_fulfilled"] // 2
        message = "Kompromiss gefunden. Teilweise zufrieden."

    if t.commander_id:
        commander = await session.get(Commander, t.commander_id)
        if commander is not None:
            commander.morale = max(0, min(100, commander.morale + morale_delta))
            # Loyalitaets-/Unmut-Folgen (Zufriedenheits-Oekonomie).
            sat = bal.commander.get("satisfaction", {})
            fulfil = int(sat.get("loyalty_fulfil_gain", 12))
            ignore = int(sat.get("loyalty_ignore_loss", 15))
            relief = float(sat.get("relief_on_fulfil", 100))
            import datetime as _dt
            if body.choice == "accept":
                loyalty_delta = fulfil
                commander.unrest = max(0.0, float(commander.unrest or 0.0) - relief)
            elif body.choice == "negotiate":
                loyalty_delta = fulfil // 2
                commander.unrest = max(0.0, float(commander.unrest or 0.0) - relief / 2)
            else:  # reject -> Treue sinkt, Unmut bleibt (eskaliert nach Cooldown)
                loyalty_delta = -ignore
            commander.loyalty = max(0, min(100, commander.loyalty + loyalty_delta))
            commander.last_demand_at = _dt.datetime.now(_dt.timezone.utc)

    t.requires_decision = False
    t.read = True
    return DecideResponse(ok=True, morale_delta=morale_delta, message=message)
