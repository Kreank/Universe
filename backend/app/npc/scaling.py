"""NPC-Tier-Skalierung (2026-06-12): macht NPCs zu mitwachsenden PvE-Zielen.

Das Tier wird HERGELEITET (nicht in der DB gespeichert -> kein Schema-Feld noetig): KOMBI aus
**Region** (Entfernung vom Kern -> raeumliche Grund-Ladder) und **lokalem Spieler** (Score des
naechsten Spielers -> die NPCs wachsen mit der Spielerstaerke mit). Aus dem Tier folgt ein
``strength_mult`` (skaliert Garnison/Einkommen/Loot-Cap) und ein Tech-Aufschlag (Waffen/Schild/
Panzerung). Die reinen Funktionen sind DB-frei und direkt testbar; ``nearest_player_score`` ist
der einzige DB-Helfer (eine Abfrage).
"""
from __future__ import annotations


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def npc_tier(galaxy: int, system: int, position: int, nearest_player_score: float, cfg: dict) -> float:
    """Hergeleitetes NPC-Tier (>= min_tier, <= max_tier).

    tier = base + Region + Spieler. Region = |Galaxie-Diff|*region_per_galaxy +
    |System-Diff|*region_per_system (Entfernung vom Kern). Spieler = (Score des naechsten
    Spielers / player_score_per_tier) * player_weight."""
    base = float(cfg.get("base", 1.0))
    ref_g = int(cfg.get("region_reference_galaxy", 1))
    ref_s = int(cfg.get("region_reference_system", 1))
    region = (abs(int(galaxy) - ref_g) * float(cfg.get("region_per_galaxy", 0.0))
              + abs(int(system) - ref_s) * float(cfg.get("region_per_system", 0.0)))
    per_tier_score = max(1.0, float(cfg.get("player_score_per_tier", 50000)))
    player = (max(0.0, float(nearest_player_score or 0)) / per_tier_score) * float(cfg.get("player_weight", 1.0))
    tier = base + region + player
    return max(float(cfg.get("min_tier", 1.0)), min(float(cfg.get("max_tier", 12.0)), tier))


def tier_strength_mult(tier: float, cfg: dict) -> float:
    """Garnison-/Einkommen-/Cap-Multiplikator: Tier 1 = 1.0, jedes weitere Tier +per_tier_strength."""
    return 1.0 + (max(1.0, float(tier)) - 1.0) * float(cfg.get("per_tier_strength", 0.5))


def scale_counts(group: dict, mult: float) -> dict[str, int]:
    """Skaliert ein {typ: anzahl}-Dict um mult (mind. 1 je vorhandenem Typ, ganze Stueck)."""
    return {t: max(1, int(round(int(c) * mult))) for t, c in (group or {}).items() if int(c) > 0}


def scale_garrison(baseline: dict, mult: float) -> dict:
    """Skaliert eine Soll-Garnison {fleet:{}, defenses:{}} um mult -> Tier-Ziel fuer den Rebuild."""
    return {
        "fleet": scale_counts(baseline.get("fleet", {}), mult),
        "defenses": scale_counts(baseline.get("defenses", {}), mult),
    }


def scale_resources(res: dict, mult: float) -> dict[str, float]:
    """Skaliert ein Ressourcen-Dict (Einkommen oder Cap) um mult."""
    return {k: float(v) * mult for k, v in (res or {}).items()}


def tier_tech(base_tech: dict, tier: float, cfg: dict) -> dict[str, int]:
    """NPC-Tech-Stufen = Basis + (tier-1)*tech_per_tier (gerundet). Hoeheres Tier = Qualitaet, nicht nur Masse."""
    add = (max(1.0, float(tier)) - 1.0) * float(cfg.get("tech_per_tier", 0.0))
    return {k: int(round(int(v) + add)) for k, v in (base_tech or {}).items()}


def nearest_score_from_rows(rows, galaxy: int, system: int, position: int) -> float:
    """Score des naechsten Spielers aus vorgeladenen (galaxy, system, position, score)-Zeilen.
    Distanz vereinfacht: selbe Galaxie -> |System-Diff| (+|Pos|/100); andere Galaxie -> grosse Strafe.
    0, wenn keine Zeilen. (Pure -> testbar; der Behavior-Tick laedt die Zeilen EINMAL und ruft das hier
    pro NPC, statt N Abfragen.)"""
    best_d: float | None = None
    best_score = 0.0
    for g, s, p, score in rows:
        d = abs(int(s) - int(system)) + abs(int(p) - int(position)) / 100.0
        if int(g) != int(galaxy):
            d += 10000.0
        if best_d is None or d < best_d:
            best_d = d
            best_score = float(score or 0)
    return best_score


async def nearest_player_score(session: AsyncSession, galaxy: int, system: int, position: int) -> float:
    """Score des dem Punkt naechsten Spielers (ueber dessen Planeten). 0, wenn kein Spieler existiert."""
    from app.platform.models import Planet, Player
    rows = (await session.execute(
        select(Planet.galaxy, Planet.system, Planet.position, Player.score)
        .join(Player, Planet.player_id == Player.id)
    )).all()
    return nearest_score_from_rows(rows, galaxy, system, position)
