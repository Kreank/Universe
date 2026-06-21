"""Router fuer die NPC-Diplomatie (Welle 1): Kontaktaufnahme/Verhandlung,
Beziehungsstatus, Pakt-Bruch. Die KI-Entscheidung trifft der ai-worker asynchron;
die Antwort des NPC trifft als Funkspruch (Transmission ``npc_diplomacy``) ein."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.npc.diplomacy import break_pact, initiate_negotiation
from app.npc.schemas import NegotiateRequest, NegotiateResponse, RelationListItem, RelationOut
from app.platform.db import get_session
from app.platform.models import NpcEmpire, NpcRelation, Player
from app.platform.security import get_current_player

router = APIRouter(prefix="/npc", tags=["npc"])

# Fehlercode (initiate_negotiation) -> (HTTP-Status, Meldung).
_ERR = {
    "invalid_offer_type": (400, "Unbekannte Angebotsart"),
    "not_discovered": (403, "Dieses Imperium ist dir noch nicht bekannt — erkunde es zuerst"),
    "cooldown": (429, "Zu schnell — warte, bis das Imperium auf deinen letzten Funkspruch reagiert hat"),
}

# Sortier-Prioritaet der Beziehungs-Uebersicht: aktive Pakte + feindliche zuerst.
_STATUS_ORDER = {"allied": 0, "ceasefire": 1, "hostile": 2, "broken_pact": 3, "neutral": 4}


async def _load_npc(session: AsyncSession, npc_id: uuid.UUID) -> NpcEmpire:
    npc = await session.get(NpcEmpire, npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail="Imperium nicht gefunden")
    return npc


@router.get("/relations", response_model=list[RelationListItem])
async def list_relations(
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> list[RelationListItem]:
    """Alle Beziehungen des aktuellen Spielers zu NPC-Imperien (Diplomatie-Reiter).

    Liefert je Eintrag die NpcRelation-Felder + Name/Koordinaten des Imperiums (Join
    NpcEmpire). Sortiert: aktive Pakte (Buendnis/Waffenstillstand) und feindliche
    Imperien zuerst, danach nach letztem Kontakt (juengster zuerst)."""
    rows = (await session.execute(
        select(NpcRelation, NpcEmpire)
        .join(NpcEmpire, NpcRelation.npc_id == NpcEmpire.id)
        .where(NpcRelation.player_id == player.id)
    )).all()
    items = [
        RelationListItem(
            npc_id=npc.id,
            npc_name=npc.name,
            galaxy=npc.galaxy,
            system=npc.system,
            position=npc.position,
            coords=f"{npc.galaxy}:{npc.system}:{npc.position}",
            status=rel.status,
            alliance_since=rel.alliance_since,
            ceasefire_until=rel.ceasefire_until,
            tribute_metal_per_cycle=rel.tribute_metal_per_cycle,
            betrayed_by_player=rel.betrayed_by_player,
            betrayed_by_npc=rel.betrayed_by_npc,
            broken_at=rel.broken_at,
            message_count=rel.message_count,
            positive_actions=rel.positive_actions,
            negative_actions=rel.negative_actions,
            last_decision_at=rel.last_decision_at,
        )
        for rel, npc in rows
    ]
    items.sort(key=lambda it: (
        _STATUS_ORDER.get(it.status, 9),
        -(it.last_decision_at.timestamp() if it.last_decision_at else 0.0),
    ))
    return items


@router.post("/{npc_id}/negotiate", status_code=202, response_model=NegotiateResponse)
async def negotiate(
    npc_id: uuid.UUID,
    body: NegotiateRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> NegotiateResponse:
    """Kontakt aufnehmen + Angebot unterbreiten. Reiht die KI-Entscheidung ein; die
    in-character Antwort des Imperiums kommt kurz darauf als Funkspruch ins Postfach."""
    npc = await _load_npc(session, npc_id)
    terms = {"tribute_metal": body.tribute_metal, "ceasefire_hours": body.ceasefire_hours}
    try:
        result = await initiate_negotiation(session, player, npc, body.offer_type, terms, body.message)
    except ValueError as exc:
        status, msg = _ERR.get(str(exc), (400, "Verhandlung nicht moeglich"))
        raise HTTPException(status_code=status, detail=msg) from exc
    return NegotiateResponse(
        ok=True, status=result["status"],
        message=f"Funkspruch an {npc.name} gesendet. Die Antwort des Imperiums folgt in Kuerze.",
    )


@router.get("/{npc_id}/relation", response_model=RelationOut)
async def get_relation(
    npc_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> RelationOut:
    """Aktueller Beziehungsstatus zwischen Spieler und Imperium (neutral, wenn nie kontaktiert)."""
    await _load_npc(session, npc_id)
    rel = await session.get(NpcRelation, (player.id, npc_id))
    if rel is None:
        return RelationOut(npc_id=npc_id, status="neutral")
    return RelationOut.model_validate(rel)


@router.post("/{npc_id}/break-pact", response_model=RelationOut)
async def break_pact_endpoint(
    npc_id: uuid.UUID,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
) -> RelationOut:
    """Bestehenden Pakt brechen (Verrat). Macht das Imperium feindlich und erhoeht den
    globalen Verrats-Ruf des Spielers."""
    npc = await _load_npc(session, npc_id)
    rel = await break_pact(session, player, npc)
    return RelationOut.model_validate(rel)
