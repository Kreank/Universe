"""Router fuer Spieler-Feedback (Testphase: Bug-Report / Idee / Sonstiges)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.feedback.schemas import FeedbackRequest, FeedbackResponse
from app.feedback.service import notify_telegram
from app.platform.db import get_session
from app.platform.models import Feedback, Player
from app.platform.security import get_current_player

router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=201, response_model=FeedbackResponse)
async def submit_feedback(
    body: FeedbackRequest,
    player: Player = Depends(get_current_player),
    session: AsyncSession = Depends(get_session),
    user_agent: str | None = Header(default=None, alias="User-Agent"),
) -> FeedbackResponse:
    """Nimmt Spieler-Feedback entgegen: speichert es dauerhaft in der DB und meldet es
    zusaetzlich per Telegram an den Entwickler (best-effort, siehe service.py)."""
    row = Feedback(
        player_id=player.id,
        display_name=player.display_name,
        category=body.category,
        message=body.message.strip(),
        page=body.page,
        user_agent=(user_agent or "")[:500] or None,
    )
    session.add(row)
    await session.commit()

    await notify_telegram(
        category=row.category,
        message=row.message,
        display_name=row.display_name,
        page=row.page,
    )
    return FeedbackResponse(ok=True)
