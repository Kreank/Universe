"""Pydantic-Schemas fuer die Rangliste (OGame-Stil: Reiter Spieler/Allianzen + Kategorien)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class RankBoardEntry(BaseModel):
    rank: int                       # Rang in der AKTUELL gewaehlten Kategorie
    id: uuid.UUID                   # player_id (Spieler-Board) ODER alliance_id (Allianz-Board)
    name: str
    tag: str | None = None          # Allianz-Tag (nur Allianz-Board)
    member_count: int | None = None  # Mitgliederzahl (nur Allianz-Board)
    is_self: bool                   # eigener Eintrag bzw. eigene Allianz
    value: int                      # Punkte in der gewaehlten Kategorie
    # Vollstaendige Aufschluesselung (fuer die Mini-Spalten + Tooltips).
    total: int
    buildings: int
    research: int
    fleet: int
    defense: int


class RankBoardResponse(BaseModel):
    board: str                      # 'players' | 'alliances'
    category: str                   # 'total' | 'buildings' | 'research' | 'fleet' | 'defense'
    entries: list[RankBoardEntry]
    me: RankBoardEntry | None       # eigener Eintrag / eigene Allianz (auch ausserhalb der Top-Liste)
    my_ranks: dict[str, int] | None  # eigener Rang JE Kategorie auf diesem Board ("Dein Platz")
    total: int                      # Anzahl gewerteter Eintraege auf diesem Board
