"""Pydantic-Schemas fuer Spieler-Feedback (Testphase)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Kategorien bewusst klein gehalten — schnelle Auswahl statt Formular-Roman.
FeedbackCategory = Literal["bug", "idea", "other"]


class FeedbackRequest(BaseModel):
    category: FeedbackCategory = "bug"
    message: str = Field(min_length=3, max_length=4000)
    # Optionaler Kontext, vom Frontend automatisch mitgeschickt (Spieler tippt das nicht).
    page: str | None = Field(default=None, max_length=300)


class FeedbackResponse(BaseModel):
    ok: bool
