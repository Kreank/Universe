"""Balance-Loader. Laedt ``shared/balance.json`` EINMALIG und stellt typisierte
Zugriffshelfer bereit. NICHTS wird im Code hartkodiert (Single Source of Truth)."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from typing import Any

from app.platform.config import settings


@lru_cache
def load_balance() -> dict[str, Any]:
    """Liest balance.json (gecached). Pfad aus Settings/ENV bzw. Fallback-Suche."""
    path = settings.balance_path()
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def catalog_items(catalog: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Kanonischer Iterator ueber einen Daten-Katalog (ships/defenses/techs ...).

    Filtert ``_``-praefixierte Meta-/Kommentar-Keys (z. B. ``_note``, ``_note_roles``,
    ``_formula_cost``) UND Nicht-Dict-Werte heraus -> jede Aufrufstelle bekommt nur echte
    Eintraege mit ``cfg``-Dict. Vermeidet, dass jede Iteration den Filter neu (und ggf.
    lueckenhaft) baut (Befund #7)."""
    return [(k, v) for k, v in catalog.items() if not k.startswith("_") and isinstance(v, dict)]


class Balance:
    """Bequeme, lesende Sicht auf balance.json. Reine Helfer, keine Mutation."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or load_balance()

    # -- Universum ----------------------------------------------------------
    @property
    def speed(self) -> int:
        return int(self.data["universe"]["speed"])

    @property
    def fleet_speed(self) -> float:
        """Separater Flotten-Tempo-Regler (OGame: eigenes Universumssetting). Teilt die Flugzeit,
        entkoppelt von speed (=Wirtschaft/Bau). Hoeher = schnellere Fluege. Default 1.0."""
        return float(self.data["universe"].get("fleet_speed", 1.0))

    @property
    def base_income(self) -> dict[str, float]:
        return self.data["universe"]["base_income"]

    @property
    def galaxies(self) -> int:
        return int(self.data["universe"]["galaxies"])

    @property
    def systems_per_galaxy(self) -> int:
        return int(self.data["universe"]["systems_per_galaxy"])

    @property
    def positions_per_system(self) -> int:
        return int(self.data["universe"]["positions_per_system"])

    # -- Kataloge -----------------------------------------------------------
    @property
    def buildings(self) -> dict[str, Any]:
        return self.data["buildings"]

    @property
    def ships(self) -> dict[str, Any]:
        return self.data["ships"]

    @property
    def defenses(self) -> dict[str, Any]:
        return self.data["defenses"]

    @property
    def techs(self) -> dict[str, Any]:
        return self.data["research"]["techs"]

    @property
    def combat(self) -> dict[str, Any]:
        return self.data["combat"]

    @property
    def combat_roster(self) -> dict[str, Any]:
        return self.data.get("combat_roster", {})

    @property
    def commander(self) -> dict[str, Any]:
        return self.data["commander"]

    @property
    def fleet(self) -> dict[str, Any]:
        return self.data["fleet"]

    @property
    def protection(self) -> dict[str, Any]:
        return self.data["protection"]

    @property
    def events(self) -> dict[str, Any]:
        return self.data.get("events", {})

    @property
    def npc(self) -> dict[str, Any]:
        return self.data["npc"]

    @property
    def trade(self) -> dict[str, Any]:
        return self.data["trade"]

    @property
    def starting_player(self) -> dict[str, Any]:
        return self.data["starting_player"]

    @property
    def planets(self) -> dict[str, Any]:
        return self.data["planets"]

    @property
    def tech_bonus(self) -> dict[str, Any]:
        return self.data["tech_bonus"]

    # -- Lager-Formel -------------------------------------------------------
    def storage_capacity(self, level: int) -> float:
        """Kapazitaet je Speicherstufe: 5000 * floor(2.5 * e^(20*lvl/33)).
        Stufe 0 ergibt das Start-Lager (10.000)."""
        return 5000.0 * math.floor(2.5 * math.exp(20.0 * level / 33.0))

    # -- Moral-Baender ------------------------------------------------------
    def morale_band(self, morale: int) -> dict[str, Any]:
        """Liefert das Moral-Band (label, combat_mod, ...) fuer einen Wert."""
        for band in self.commander["morale"]["bands"]:
            if band["min"] <= morale <= band["max"]:
                return band
        # Sicherheits-Fallback (sollte durch CHECK 0..100 nie greifen)
        return self.commander["morale"]["bands"][-1]

    # -- Rang-Helfer --------------------------------------------------------
    def ranks(self) -> list[dict[str, Any]]:
        return self.commander["ranks"]

    def rank_for_xp(self, xp: int) -> dict[str, Any]:
        """Hoechster Rang, dessen XP-Schwelle erreicht ist."""
        chosen = self.commander["ranks"][0]
        for rank in self.commander["ranks"]:
            if xp >= rank["xp_threshold"]:
                chosen = rank
        return chosen

    def rank_by_key(self, key: str) -> dict[str, Any]:
        for rank in self.commander["ranks"]:
            if rank["key"] == key:
                return rank
        return self.commander["ranks"][0]

    # -- Gueteklassen (Grade F..SSS, Doku 05a) ------------------------------
    @property
    def grades(self) -> dict[str, Any]:
        return self.commander["grades"]

    def grade_potency(self, grade: str) -> float:
        """Potenz-Faktor einer Gueteklasse (C = 1.00 Baseline). Unbekannt -> 1.0."""
        return float(self.grades["potency"].get(grade, 1.0))

    def training_tier(self, key: str) -> dict[str, Any]:
        """Investitions-Stufe der Akademie-Ausbildung (Fallback: erste Stufe)."""
        tiers = self.grades["training_tiers"]
        for tier in tiers:
            if tier["key"] == key:
                return tier
        return tiers[0]


@lru_cache
def get_balance() -> Balance:
    return Balance()
