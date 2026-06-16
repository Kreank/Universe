"""Reine, testbare Logik fuer den Spieler-Schutz (keine DB, keine Mutation).

A — Neulingsschutz (Grundsystem): dynamische Punkte-Schwelle, die mit dem Universum mitwaechst
    (relativ zum Durchschnitt der etablierten Spieler), mit Mindest-Schwelle + Schonfrist.
B — Bashing-Schutz (Zusatz): relatives Punkte-Band, damit ein deutlich staerkerer Spieler ein
    viel schwaecheres Ziel nicht "wegsnacken" kann (Platz 1 vs. Platz 500).

Alle Stellschrauben kommen aus ``balance.json -> protection`` (siehe dort den ``_note``)."""
from __future__ import annotations

from typing import Any


def newbie_threshold(avg_score: float, cfg: dict[str, Any]) -> float:
    """Dynamische Punkte-Schwelle, ab der ein Spieler kein Neuling mehr ist: rein ein Anteil des
    Punkte-Durchschnitts. Kein fester Floor -> die Schwelle ergibt sich nur aus dem Schnitt und
    waechst mit dem Universum mit."""
    factor = float(cfg.get("newbie_avg_factor", 0.30) or 0)
    return factor * max(0.0, avg_score)


def newbie_protection_active(score: float, avg_score: float, cfg: dict[str, Any]) -> bool:
    """True, solange der Spieler Neulingsschutz GENIESST: solange sein Imperiumswert unter der
    dynamischen Schwelle (Anteil des Punkte-Durchschnitts) liegt. Kein Zeitlimit."""
    return score < newbie_threshold(avg_score, cfg)


def bash_blocked(attacker_score: float, defender_score: float, cfg: dict[str, Any]) -> bool:
    """B: True, wenn der Angreifer fuer dieses (viel schwaechere) Ziel gesperrt ist.

    Greift nur fuer bereits etablierte Angreifer (>= ``bash_min_attacker_score``) — kleine Spieler
    duerfen also auch deutlich groessere angreifen (David gegen Goliath bleibt erlaubt)."""
    factor = float(cfg.get("bash_band_factor", 5) or 0)
    if factor <= 0:
        return False
    if attacker_score < float(cfg.get("bash_min_attacker_score", 5000) or 0):
        return False
    return attacker_score > factor * max(0.0, defender_score)
