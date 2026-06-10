"""Idempotente Startup-Migrationen.

Das kanonische Schema lebt in ``infra/db/init.sql`` und wird vom Postgres-Container
nur beim ERSTEN Hochfahren (frisches Volume) angewandt. Damit neue Tabellen und
ENUM-Werte auch in eine BESTEHENDE Datenbank gelangen — ohne ``docker compose down -v``
und damit ohne Datenverlust — werden sie hier zusaetzlich beim Startup als idempotentes
DDL ausgefuehrt.

Regeln fuer Eintraege in ``_STATEMENTS``:
- Jede Anweisung muss gefahrlos WIEDERHOLBAR sein (``CREATE TABLE IF NOT EXISTS``,
  ``CREATE INDEX IF NOT EXISTS``, ``ALTER TYPE ... ADD VALUE IF NOT EXISTS``).
- Reihenfolge zaehlt: Tabellen vor ihren Indizes, ENUM-Werte vor ihrer Nutzung.
- Spiegelt exakt, was auch in ``infra/db/init.sql`` steht (init.sql bleibt die
  kanonische Quelle fuer frische Universen)."""
from __future__ import annotations

import logging

from sqlalchemy import text

from app.platform.db import engine

log = logging.getLogger("universe.migrations")

# Idempotente DDL-Anweisungen, in Reihenfolge angewandt. Siehe Modul-Docstring.
_STATEMENTS: list[str] = [
    # -- Feature 1: persistente Werft-Bau-Warteschlange (Tech-Debt #2) -------
    """
    CREATE TABLE IF NOT EXISTS shipyard_queue (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        planet_id   UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
        type        TEXT NOT NULL,
        count       INT  NOT NULL CHECK (count > 0),
        category    TEXT NOT NULL,                       -- 'ship' | 'defense'
        finishes_at TIMESTAMPTZ NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_shipyard_queue_finishes ON shipyard_queue(finishes_at)",
    "CREATE INDEX IF NOT EXISTS idx_shipyard_queue_planet ON shipyard_queue(planet_id)",
    # -- Feature: NPC-Verhalten (Behavior Trees) -----------------------------
    "ALTER TABLE npc_empires ADD COLUMN IF NOT EXISTS baseline JSONB NOT NULL DEFAULT '{}'::jsonb",
    "ALTER TABLE npc_empires ADD COLUMN IF NOT EXISTS last_action_at TIMESTAMPTZ",
    # -- Feature: Spionage (Discovery + Spionagebericht) ---------------------
    "ALTER TYPE transmission_type ADD VALUE IF NOT EXISTS 'spy_report'",
    """
    CREATE TABLE IF NOT EXISTS player_discoveries (
        player_id     UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        galaxy        INT NOT NULL,
        system        INT NOT NULL,
        position      INT NOT NULL,
        intel         JSONB NOT NULL DEFAULT '{}'::jsonb,
        level         INT NOT NULL DEFAULT 1,
        discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (player_id, galaxy, system, position)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_discoveries_player ON player_discoveries(player_id)",
    # -- Feature: Planetentypen + Felder (Doku 06a) --------------------------
    "ALTER TABLE planets ADD COLUMN IF NOT EXISTS planet_type TEXT NOT NULL DEFAULT 'normal'",
    # -- Feature: Commander-Gueteklassen F..SSS (Doku 05a) -------------------
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS grade TEXT NOT NULL DEFAULT 'C'",
    # -- Feature: Truemmerfeld + Recycler-Harvest ----------------------------
    "ALTER TABLE universe_cells ADD COLUMN IF NOT EXISTS debris_field JSONB NOT NULL DEFAULT '{}'::jsonb",
    # -- Feature: Eingehende NPC-Angriffe auf Spieler ------------------------
    "ALTER TABLE npc_empires ADD COLUMN IF NOT EXISTS last_attack_at TIMESTAMPTZ",
    """
    CREATE TABLE IF NOT EXISTS npc_attacks (
        id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        npc_id           UUID NOT NULL REFERENCES npc_empires(id) ON DELETE CASCADE,
        target_player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        target_planet_id UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
        target_galaxy    INT NOT NULL,
        target_system    INT NOT NULL,
        target_position  INT NOT NULL,
        fleet            JSONB NOT NULL DEFAULT '{}'::jsonb,
        status           TEXT NOT NULL DEFAULT 'incoming',
        arrive_at        TIMESTAMPTZ NOT NULL,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_npc_attacks_status ON npc_attacks(status)",
    "CREATE INDEX IF NOT EXISTS idx_npc_attacks_target ON npc_attacks(target_player_id)",
    # -- Feature: Mining-Mission (Bergbauschiff) ------------------------------
    "ALTER TYPE fleet_mission ADD VALUE IF NOT EXISTS 'mine'",
    # -- Feature: Imperiums-Doktrinen ----------------------------------------
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS doctrine TEXT",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS doctrine_changed_at TIMESTAMPTZ",
    # -- Feature: Handel (Anfliegen-Modell) ----------------------------------
    # ENUM-Wert MUSS vor seiner Nutzung committet sein. Da jede Anweisung im
    # AUTOCOMMIT-Modus laeuft (siehe ensure_schema), ist 'trade' nach diesem
    # Statement persistent und nutzbar — identisch zu 'mine' oben.
    "ALTER TYPE fleet_mission ADD VALUE IF NOT EXISTS 'trade'",
    # Auftragsdaten der Flotte (Handel: {offer_res, offer_amount, want_res}).
    "ALTER TABLE fleets ADD COLUMN IF NOT EXISTS mission_data JSONB NOT NULL DEFAULT '{}'::jsonb",
    # Haendler-Markt am NPC ({spec, stock:{...}}), lazy initialisiert.
    "ALTER TABLE npc_empires ADD COLUMN IF NOT EXISTS market JSONB NOT NULL DEFAULT '{}'::jsonb",
    # Handelsreputation Spieler<->Haendler (kumuliertes Volumen).
    """
    CREATE TABLE IF NOT EXISTS trade_reputation (
        player_id  UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        npc_id     UUID NOT NULL REFERENCES npc_empires(id) ON DELETE CASCADE,
        volume     DOUBLE PRECISION NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (player_id, npc_id)
    )
    """,
    # Globaler Handelsindex: ein-Zeilen-Singleton mit EMA-geglaettetem Weltvorrat
    # (liquider Spieler-Vorrat je Ressource) -> speist den Kurs der Handelszentren.
    """
    CREATE TABLE IF NOT EXISTS world_market (
        id           SMALLINT PRIMARY KEY DEFAULT 1,
        supply       JSONB NOT NULL DEFAULT '{}'::jsonb,
        players      INTEGER NOT NULL DEFAULT 1,
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT world_market_singleton CHECK (id = 1)
    )
    """,
]


async def ensure_schema() -> None:
    """Wendet alle idempotenten DDL-Anweisungen an.

    Jede Anweisung laeuft im AUTOCOMMIT-Modus (noetig u. a. fuer
    ``ALTER TYPE ... ADD VALUE``, das nicht in einer Transaktion stehen darf)."""
    applied = 0
    async with engine.connect() as conn:
        conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in _STATEMENTS:
            await conn.execute(text(stmt))
            applied += 1
    log.info("Startup-Migration: %d idempotente DDL-Anweisungen angewandt", applied)
