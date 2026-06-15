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
    # Stueckweise Fertigstellung: Stueck-Dauer pro Auftrag (finishes_at = naechste Einheit).
    "ALTER TABLE shipyard_queue ADD COLUMN IF NOT EXISTS seconds_each INT NOT NULL DEFAULT 0",
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
    # P2P-Handelsprofil (klassisch, unverbindlich): Spieler wirbt offen ein Tausch-Angebot.
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS trade_enabled BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS trade_offer TEXT",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS trade_want TEXT",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS trade_rate DOUBLE PRECISION",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS trade_note TEXT",
    # Spieler-zu-Spieler-Nachrichten ueber das Postfach (Absender + neuer Typ).
    "ALTER TABLE transmissions ADD COLUMN IF NOT EXISTS from_player_id UUID REFERENCES players(id) ON DELETE SET NULL",
    "ALTER TYPE transmission_type ADD VALUE IF NOT EXISTS 'player_message'",
    # Stationierte Patrouillen-/Eskortflotten (deploy-Mission).
    """
    CREATE TABLE IF NOT EXISTS stationed_fleets (
        id              UUID PRIMARY KEY,
        owner_id        UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        home_planet_id  UUID REFERENCES planets(id) ON DELETE SET NULL,
        galaxy          INTEGER NOT NULL,
        system          INTEGER NOT NULL,
        position        INTEGER NOT NULL,
        ships           JSONB NOT NULL DEFAULT '{}'::jsonb,
        escort_enabled  BOOLEAN NOT NULL DEFAULT false,
        escort_radius   INTEGER NOT NULL DEFAULT 0,
        escort_fee_pct  DOUBLE PRECISION NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_stationed_owner ON stationed_fleets(owner_id)",
    "CREATE INDEX IF NOT EXISTS idx_stationed_coords ON stationed_fleets(galaxy, system, position)",
    # Abfang-Modus der Patrouillen (A): Abfangen durchreisender Feindflotten.
    "ALTER TABLE stationed_fleets ADD COLUMN IF NOT EXISTS intercept_enabled BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE stationed_fleets ADD COLUMN IF NOT EXISTS intercept_radius INTEGER NOT NULL DEFAULT 0",
    # Kommandeur-Zufriedenheit: Unmut-Akkumulator + Zeitpunkt der letzten Forderung.
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS unrest DOUBLE PRECISION NOT NULL DEFAULT 0",
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS last_demand_at TIMESTAMPTZ",
    # Ueberlauf (Loyalitaets-Folge): neuer Kommandeur-Status.
    "ALTER TYPE commander_status ADD VALUE IF NOT EXISTS 'defected'",
    # Aktive Faehigkeiten: Cooldown-Zeitstempel.
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS last_ability_at TIMESTAMPTZ",
    # Gouverneurs-Rolle: Verwaltungs-Spezialisierung + Planet-Gouverneur.
    "ALTER TYPE specialization ADD VALUE IF NOT EXISTS 'admin'",
    "ALTER TABLE planets ADD COLUMN IF NOT EXISTS governor_commander_id UUID REFERENCES commanders(id) ON DELETE SET NULL",
    # RPG-Entwicklung: Skillpunkte + erlernte Faehigkeiten + Cooldowns.
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS skill_points INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS abilities JSONB NOT NULL DEFAULT '[]'::jsonb",
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS ability_cooldowns JSONB NOT NULL DEFAULT '{}'::jsonb",
    # Monde: an einen Planeten gebunden (planet_type='moon'), + Sprungtor-Cooldown.
    "ALTER TABLE planets ADD COLUMN IF NOT EXISTS parent_planet_id UUID REFERENCES planets(id) ON DELETE CASCADE",
    "ALTER TABLE planets ADD COLUMN IF NOT EXISTS last_jump_at TIMESTAMPTZ",
    # Treibstoff-Unterhalt vorgeschobener Stationierung: NULL = eigenes Gebiet (gratis),
    # Zahl = mitgefuehrter Deuterium-Vorrat (zehrt per Tick, leer -> Zwangs-Rueckkehr).
    "ALTER TABLE stationed_fleets ADD COLUMN IF NOT EXISTS fuel DOUBLE PRECISION",
    # -- Feature: Asteroidenfelder (endliche, regenerierende Erz-Vorkommen) ---
    # ENUM-Wert MUSS vor seiner Nutzung committet sein (AUTOCOMMIT je Statement).
    "ALTER TYPE occupant_type ADD VALUE IF NOT EXISTS 'asteroid_field'",
    """
    CREATE TABLE IF NOT EXISTS asteroid_fields (
        id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        galaxy            INT NOT NULL,
        system            INT NOT NULL,
        position          INT NOT NULL,
        richness          TEXT NOT NULL DEFAULT 'normal',
        mult              DOUBLE PRECISION NOT NULL DEFAULT 1.0,
        metal_remaining   DOUBLE PRECISION NOT NULL DEFAULT 0,
        crystal_remaining DOUBLE PRECISION NOT NULL DEFAULT 0,
        metal_max         DOUBLE PRECISION NOT NULL DEFAULT 0,
        crystal_max       DOUBLE PRECISION NOT NULL DEFAULT 0,
        last_regen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (galaxy, system, position)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_asteroid_coords ON asteroid_fields(galaxy, system, position)",
    # -- Feature: KI-Personas/Funksprueche fuer NPC-Imperien (Phase 1) ---------
    # reaction_banks fuer NPCs verallgemeinern: commander_id nullable + npc_id (eines von beiden).
    "ALTER TABLE reaction_banks ALTER COLUMN commander_id DROP NOT NULL",
    "ALTER TABLE reaction_banks ADD COLUMN IF NOT EXISTS npc_id UUID REFERENCES npc_empires(id) ON DELETE CASCADE",
    "CREATE INDEX IF NOT EXISTS idx_reaction_npc ON reaction_banks(npc_id, situation)",
    # NPC-Persona (background/voice), vom ai-worker per persona_init angereichert.
    "ALTER TABLE npc_empires ADD COLUMN IF NOT EXISTS persona JSONB NOT NULL DEFAULT '{}'::jsonb",
    # -- Feature: Stationierungs-Modi auseinandergezogen (park/intercept/escort) ---
    # Flug-Missionen 'intercept' (Abfangen) und 'escort' (Eskorte) als eigene fleet_mission-
    # Werte. ENUM-Wert MUSS vor seiner Nutzung committet sein (AUTOCOMMIT je Statement) —
    # identisch zu 'mine'/'trade' oben.
    "ALTER TYPE fleet_mission ADD VALUE IF NOT EXISTS 'intercept'",
    "ALTER TYPE fleet_mission ADD VALUE IF NOT EXISTS 'escort'",
    # -- Feature: exotische Endgame-Ressourcen (kontoweit, erspielt) ---------
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS dark_matter DOUBLE PRECISION NOT NULL DEFAULT 0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS antimatter DOUBLE PRECISION NOT NULL DEFAULT 0",
    # -- Feature: Endgame-Megastrukturen (kontoweit, stufenweiser Bau) -------
    """
    CREATE TABLE IF NOT EXISTS megastructures (
        player_id      UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        type           TEXT NOT NULL,
        level          INT NOT NULL DEFAULT 0,
        building_until TIMESTAMPTZ,
        PRIMARY KEY (player_id, type)
    )
    """,
    # -- Feature: Exo-Minen (positions-gebundene Quelle exotischer Materie) ---
    # Exotischer Ertrag wird pro Planet als resources-Zeile lazy akkumuliert und aufs Konto
    # ausgekehrt -> der resource_type-ENUM braucht die zwei Werte (Wert vor Nutzung committet,
    # AUTOCOMMIT je Statement).
    "ALTER TYPE resource_type ADD VALUE IF NOT EXISTS 'antimatter'",
    "ALTER TYPE resource_type ADD VALUE IF NOT EXISTS 'dark_matter'",
    # -- Feature: Farm-Routinen (automatisiertes Farmen von Asteroiden-/Truemmerfeldern) --
    """
    CREATE TABLE IF NOT EXISTS farm_routes (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        player_id       UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        home_planet_id  UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
        name            TEXT NOT NULL,
        ships           JSONB NOT NULL DEFAULT '{}'::jsonb,
        waypoints       JSONB NOT NULL DEFAULT '[]'::jsonb,
        enabled         BOOLEAN NOT NULL DEFAULT true,
        status          TEXT NOT NULL DEFAULT 'idle',
        pause_reason    TEXT,
        cursor          INT NOT NULL DEFAULT 0,
        active_fleet_id UUID REFERENCES fleets(id) ON DELETE SET NULL,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_farm_routes_player ON farm_routes(player_id)",
    # -- Feature: Allianzen (kooperative Ebene: Pool, Forschung, Station/Zone) --
    """
    CREATE TABLE IF NOT EXISTS alliances (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name            TEXT NOT NULL UNIQUE,
        tag             TEXT NOT NULL UNIQUE,
        founder_id      UUID REFERENCES players(id) ON DELETE SET NULL,
        pool            JSONB NOT NULL DEFAULT '{}'::jsonb,
        research_levels JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alliance_members (
        player_id    UUID PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
        alliance_id  UUID NOT NULL REFERENCES alliances(id) ON DELETE CASCADE,
        role         TEXT NOT NULL DEFAULT 'member',
        joined_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_alliance_members_alliance ON alliance_members(alliance_id)",
    """
    CREATE TABLE IF NOT EXISTS alliance_stations (
        id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        alliance_id            UUID NOT NULL REFERENCES alliances(id) ON DELETE CASCADE,
        galaxy                 INT NOT NULL,
        system                 INT NOT NULL,
        position               INT NOT NULL,
        research_radius_level  INT NOT NULL DEFAULT 0,
        fuel                   DOUBLE PRECISION NOT NULL DEFAULT 0,
        hp                     DOUBLE PRECISION NOT NULL DEFAULT 0,
        status                 TEXT NOT NULL DEFAULT 'active',
        built_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_upkeep_at         TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_alliance_stations_alliance ON alliance_stations(alliance_id)",
    "CREATE INDEX IF NOT EXISTS idx_alliance_stations_coords ON alliance_stations(galaxy, system, position)",
    """
    CREATE TABLE IF NOT EXISTS alliance_invites (
        alliance_id  UUID NOT NULL REFERENCES alliances(id) ON DELETE CASCADE,
        player_id    UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        invited_by   UUID REFERENCES players(id) ON DELETE SET NULL,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (alliance_id, player_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_alliance_invites_player ON alliance_invites(player_id)",
    # Spieler -> Allianz (denormalisierter Schnell-Zugriff fuer den Bonus-Resolver; mit
    # alliance_members synchron gehalten). Einziger Eingriff am Spieler-Modell.
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS alliance_id UUID REFERENCES alliances(id) ON DELETE SET NULL",
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
