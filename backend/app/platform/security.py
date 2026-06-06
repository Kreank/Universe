"""Sicherheit: bcrypt-Passwoerter (passlib) und HS256-JWTs (PyJWT).

Stellt zusaetzlich die FastAPI-Dependency ``get_current_player`` bereit, die das
Bearer-Token validiert und den zugehoerigen Spieler laedt."""
from __future__ import annotations

import datetime as dt
import uuid

import jwt
from fastapi import Depends, Header, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.config import settings
from app.platform.db import get_session
from app.platform.models import Player

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, pw_hash: str) -> bool:
    return _pwd.verify(password, pw_hash)


def create_token(player_id: uuid.UUID | str) -> str:
    """Erzeugt ein signiertes JWT (sub = player_id, exp)."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(player_id),
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(hours=settings.JWT_EXPIRE_HOURS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> uuid.UUID:
    """Validiert ein JWT und gibt die player_id zurueck (oder wirft 401)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungueltiges oder abgelaufenes Token",
        ) from exc


async def get_current_player(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> Player:
    """Liest den Bearer-Header, validiert das JWT und laedt den Spieler."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization-Header fehlt",
        )
    token = authorization.split(" ", 1)[1].strip()
    player_id = decode_token(token)
    player = await session.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Spieler nicht gefunden")
    # last_active aktualisieren (leichtgewichtige Aktivitaetsspur)
    player.last_active = dt.datetime.now(dt.timezone.utc)
    return player
