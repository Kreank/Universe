"""Pydantic-Schemas fuer Postfach/Funksprueche (api-contract §8)."""
from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, ConfigDict


class TransmissionOut(BaseModel):
    # from_attributes: FastAPI serialisiert ORM-Transmissionen direkt.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    subject: str
    body: str
    commander_id: uuid.UUID | None = None
    requires_decision: bool
    decision_payload: dict | None = None
    read: bool
    created_at: dt.datetime


class OkResponse(BaseModel):
    ok: bool = True


class DecideRequest(BaseModel):
    choice: str  # "accept" | "reject" | "negotiate"


class DecideResponse(BaseModel):
    ok: bool = True
    morale_delta: int
    message: str
