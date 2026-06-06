"""Pydantic-Schemas fuer Auth (api-contract §1)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PlayerOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    score: int
    is_protected: bool
    created_at: dt.datetime
    last_active: dt.datetime


class AuthResponse(BaseModel):
    token: str
    player: PlayerOut
