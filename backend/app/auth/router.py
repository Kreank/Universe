"""Router fuer Auth (api-contract §1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import AuthResponse, LoginRequest, PlayerOut, RegisterRequest
from app.auth.service import authenticate, register_player
from app.platform.db import get_session
from app.platform.models import Player
from app.platform.security import create_token, get_current_player

router = APIRouter(tags=["auth"])


def _player_out(player: Player) -> PlayerOut:
    return PlayerOut(
        id=player.id,
        email=player.email,
        display_name=player.display_name,
        score=player.score,
        is_protected=player.is_protected,
        created_at=player.created_at,
        last_active=player.last_active,
        dark_matter=float(player.dark_matter or 0),
        antimatter=float(player.antimatter or 0),
    )


@router.post("/auth/register", status_code=201, response_model=AuthResponse)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    try:
        player = await register_player(session, body.email, body.password, body.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.flush()
    token = create_token(player.id)
    return AuthResponse(token=token, player=_player_out(player))


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    player = await authenticate(session, body.email, body.password)
    if player is None:
        raise HTTPException(status_code=401, detail="Ungueltige Zugangsdaten")
    token = create_token(player.id)
    return AuthResponse(token=token, player=_player_out(player))


@router.get("/auth/me", response_model=PlayerOut)
async def me(player: Player = Depends(get_current_player)) -> PlayerOut:
    return _player_out(player)
