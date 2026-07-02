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
    # -- Feature: Bevoelkerung & Nahrung (Phase 1) -> zwei neue resource_type-Werte (pro Planet
    # als resources-Zeile lazy akkumuliert; population.rate = Wachstum/Schrumpf, food.rate = netto).
    "ALTER TYPE resource_type ADD VALUE IF NOT EXISTS 'population'",
    "ALTER TYPE resource_type ADD VALUE IF NOT EXISTS 'food'",
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
    # Belagerungs-Status (Phase 2): {"attackers": {player_id: {"damage": float, "at": iso}}, "last_attack_at": iso}.
    # Speichert je Spieler den im siege_window beigetragenen Schaden -> Gate destroy_min_attackers.
    "ALTER TABLE alliance_stations ADD COLUMN IF NOT EXISTS siege JSONB NOT NULL DEFAULT '{}'::jsonb",
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
    # Stationierte Flotte: mitgefuehrte Nicht-Treibstoff-Fracht behalten (Rueckruf liefert sie
    # zurueck) — verhindert den stillen Frachtverlust beim vorgeschobenen Stationieren.
    "ALTER TABLE stationed_fleets ADD COLUMN IF NOT EXISTS cargo JSONB NOT NULL DEFAULT '{}'::jsonb",
    # -- Feature: Spieler-Feedback (Testphase: Bug-Report / Idee / Sonstiges) --
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        player_id    UUID REFERENCES players(id) ON DELETE SET NULL,
        display_name TEXT NOT NULL,
        category     TEXT NOT NULL,                       -- 'bug' | 'idea' | 'other'
        message      TEXT NOT NULL,
        page         TEXT,
        user_agent   TEXT,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at DESC)",
    # -- Feature: Game-Events / Quests (dynamische Welt-/Karten-Events) --------
    """
    CREATE TABLE IF NOT EXISTS cosmic_events (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        event_type  TEXT NOT NULL,
        scope       TEXT NOT NULL DEFAULT 'global',   -- global | system | personal
        galaxy      INT,
        system      INT,
        position    INT,
        player_id   UUID REFERENCES players(id) ON DELETE CASCADE,
        data        JSONB NOT NULL DEFAULT '{}'::jsonb,
        status      TEXT NOT NULL DEFAULT 'active',    -- active | resolved | expired
        spawned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at  TIMESTAMPTZ NOT NULL,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cosmic_events_active ON cosmic_events(status, expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_cosmic_events_coords ON cosmic_events(galaxy, system, position)",
    "CREATE INDEX IF NOT EXISTS idx_cosmic_events_player ON cosmic_events(player_id)",
    """
    CREATE TABLE IF NOT EXISTS event_buffs (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        source_event_id UUID REFERENCES cosmic_events(id) ON DELETE CASCADE,
        scope           TEXT NOT NULL,                -- player | planet | system
        player_id       UUID REFERENCES players(id) ON DELETE CASCADE,
        planet_id       UUID REFERENCES planets(id) ON DELETE CASCADE,
        galaxy          INT,
        system          INT,
        buff_type       TEXT NOT NULL,                -- production | build_speed | research_speed | morale_adjust | scan_block | spionage_block
        magnitude       DOUBLE PRECISION NOT NULL DEFAULT 1.0,
        expires_at      TIMESTAMPTZ NOT NULL,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_event_buffs_lookup ON event_buffs(buff_type, scope, expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_event_buffs_player ON event_buffs(player_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_buffs_planet ON event_buffs(planet_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_buffs_system ON event_buffs(galaxy, system)",
    # -- Feature: Stations-Umstationieren (2026-06-17) --
    # Transit-Status der Allianz-Station {origin,target,depart_at,arrive_at,returning,escort,...}.
    "ALTER TABLE alliance_stations ADD COLUMN IF NOT EXISTS transit JSONB NOT NULL DEFAULT '{}'::jsonb",
    # Montierte Stations-Module {module_type: count} (Slots).
    "ALTER TABLE alliance_stations ADD COLUMN IF NOT EXISTS modules JSONB NOT NULL DEFAULT '{}'::jsonb",
    # Slot-Ausbaustufe (eigener Pfad, getrennt vom Radius).
    "ALTER TABLE alliance_stations ADD COLUMN IF NOT EXISTS slot_level INTEGER NOT NULL DEFAULT 0",
    # Verteidigungs-Tech der Station (eigene Stations-Forschung, startet bei 1, bis max_tech).
    "ALTER TABLE alliance_stations ADD COLUMN IF NOT EXISTS defense_tech_level INTEGER NOT NULL DEFAULT 1",
    # Sonder-Flags eines NPC-Angriffs (z. B. nach Piraten-Bestechung: besseres Truemmerfeld + Item-Chance).
    "ALTER TABLE npc_attacks ADD COLUMN IF NOT EXISTS data JSONB NOT NULL DEFAULT '{}'::jsonb",
    # -- Feature: Kommandeurs-Equipment (2026-06-17) --
    # Item-Instanzen im Spieler-Inventar; equipped_commander_id != NULL => auf einem
    # Kommandeur in seinem Slot getragen (SET NULL => faellt bei Kommandeur-Tod ins Inventar).
    """
    CREATE TABLE IF NOT EXISTS commander_items (
        id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        player_id             UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        item_key              TEXT NOT NULL,
        slot                  TEXT NOT NULL,                   -- head | hands | chest | shoes
        rarity                TEXT NOT NULL DEFAULT 'common',  -- common | rare | epic
        equipped_commander_id UUID REFERENCES commanders(id) ON DELETE SET NULL,
        acquired_at           TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_commander_items_player ON commander_items(player_id)",
    "CREATE INDEX IF NOT EXISTS idx_commander_items_equipped ON commander_items(equipped_commander_id)",
    # -- Feature: Asteroidenfelder wandern (2026-06-19) --
    # Ablaufzeit eines Asteroidenfeldes; danach despawnt es und ein neues spawnt woanders
    # (Anti-Hot-Spotting). Backfill: Alt-Felder bekommen eine gestaffelte Ablaufzeit (24-48h).
    "ALTER TABLE asteroid_fields ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
    "UPDATE asteroid_fields SET expires_at = now() + (interval '24 hours') + (random() * interval '24 hours') WHERE expires_at IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_asteroid_expires ON asteroid_fields(expires_at)",
    # -- Feature: Verhandelbare KI-NPC-Imperien (Welle 1, 2026-06-20) ----------
    # Diplomatischer Funkspruch des NPC an den Spieler (Antwort auf eine Verhandlung). Eigener
    # Transmission-Typ, damit das Frontend die Verhandlungs-Antwort gezielt rendern kann
    # (requires_decision + decision_payload tragen das Gegenangebot). ENUM-Wert MUSS vor seiner
    # Nutzung committet sein (AUTOCOMMIT je Statement) — identisch zu 'spy_report'/'player_message'.
    "ALTER TYPE transmission_type ADD VALUE IF NOT EXISTS 'npc_diplomacy'",
    # Beziehung Spieler<->NPC-Imperium (eine Zeile je Paar). Status treibt NPC-Verhalten
    # (allied/ceasefire = nicht angreifen), Tribut/Verrats-Flags + pos/neg Aktionen sind die
    # Historie, die die KI-Entscheidung (npc_decision) faerbt.
    """
    CREATE TABLE IF NOT EXISTS npc_relations (
        player_id               UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        npc_id                  UUID NOT NULL REFERENCES npc_empires(id) ON DELETE CASCADE,
        status                  TEXT NOT NULL DEFAULT 'neutral',  -- neutral|allied|ceasefire|hostile|broken_pact
        alliance_since          TIMESTAMPTZ,
        ceasefire_until         TIMESTAMPTZ,
        tribute_metal_per_cycle DOUBLE PRECISION NOT NULL DEFAULT 0,
        tribute_last_paid       TIMESTAMPTZ,
        betrayed_by_player      BOOLEAN NOT NULL DEFAULT false,
        betrayed_by_npc         BOOLEAN NOT NULL DEFAULT false,
        broken_at               TIMESTAMPTZ,
        message_count           INT NOT NULL DEFAULT 0,
        positive_actions        INT NOT NULL DEFAULT 0,
        negative_actions        INT NOT NULL DEFAULT 0,
        last_decision_at        TIMESTAMPTZ,
        created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
        PRIMARY KEY (player_id, npc_id)
    )
    """,
    # Schnell-Zugriff fuer die Angriffs-Zielauswahl (welche Spieler sind bei DIESEM NPC geschuetzt)
    # und fuer den Tribut-Tick (alle Zeilen mit laufendem Tribut).
    "CREATE INDEX IF NOT EXISTS idx_npc_relations_npc ON npc_relations(npc_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_npc_relations_tribute ON npc_relations(tribute_metal_per_cycle)",
    # Audit der KI-Entscheidungen (Nachvollziehbarkeit + spaetere Chronik/Analyse).
    """
    CREATE TABLE IF NOT EXISTS npc_decisions (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        npc_id        UUID NOT NULL REFERENCES npc_empires(id) ON DELETE CASCADE,
        player_id     UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        offer_type    TEXT NOT NULL,                       -- alliance|ceasefire|tribute
        offered_terms JSONB NOT NULL DEFAULT '{}'::jsonb,  -- vom Spieler angeboten (geklemmt)
        npc_choice    TEXT,                                -- accept|reject|counter
        npc_reasoning TEXT,
        terms_result  JSONB NOT NULL DEFAULT '{}'::jsonb,  -- tatsaechlich angewandte/gegen-Konditionen
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_npc_decisions_player ON npc_decisions(player_id, npc_id)",
    # Globaler Verrats-Ruf eines Spielers (wird in W3/Chronik wiederverwendet): wie oft hat er
    # Pakte gebrochen, wie viele Buendnisse gehalten. Schlank gehalten.
    """
    CREATE TABLE IF NOT EXISTS player_reputation (
        player_id         UUID PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
        betrayals         INT NOT NULL DEFAULT 0,
        alliances_honored INT NOT NULL DEFAULT 0,
        updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # -- Feature: Kommandeure mit Gedaechtnis & Eigenleben (Welle 2, 2026-06-20) --
    # Erlebnisse eines Kommandeurs (Schlachten/Expeditionen/Forderungen/Verluste). context traegt
    # Gegner-Identitaet + Details; sentiment faerbt das Erinnerungs-Narrativ (ai-worker memory_digest)
    # und damit die kuenftigen Funksprueche.
    """
    CREATE TABLE IF NOT EXISTS commander_memories (
        id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        commander_id UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
        event_type   TEXT NOT NULL,
        context      JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {enemy_name, planet, outcome, value, ...}
        sentiment    TEXT NOT NULL DEFAULT 'neutral',       -- positive | negative | neutral
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_commander_memories_lookup ON commander_memories(commander_id, created_at DESC)",
    # Beziehungen zwischen zwei Kommandeuren DESSELBEN Spielers (a<b-Konvention in der PK).
    """
    CREATE TABLE IF NOT EXISTS commander_relationships (
        commander_a_id   UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
        commander_b_id   UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
        rel_type         TEXT NOT NULL,                     -- rivalry | respect | grudge | bond
        strength         DOUBLE PRECISION NOT NULL DEFAULT 0,
        last_interaction TIMESTAMPTZ,
        context          JSONB NOT NULL DEFAULT '{}'::jsonb,
        PRIMARY KEY (commander_a_id, commander_b_id)
    )
    """,
    # Meinung eines Kommandeurs ueber einen Gegner (Spieler ODER NPC). Eindeutigkeit pro
    # (commander, ziel) ueber zwei partielle Unique-Indizes (genau eines von player/npc gesetzt).
    """
    CREATE TABLE IF NOT EXISTS commander_opinions (
        id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        commander_id     UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
        about_player_id  UUID REFERENCES players(id) ON DELETE CASCADE,
        about_npc_id     UUID REFERENCES npc_empires(id) ON DELETE CASCADE,
        opinion_type     TEXT NOT NULL,                     -- respects | despises | fears | envies
        strength         DOUBLE PRECISION NOT NULL DEFAULT 0,
        last_reinforced_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_commander_opinion_player ON commander_opinions(commander_id, about_player_id) WHERE about_player_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_commander_opinion_npc ON commander_opinions(commander_id, about_npc_id) WHERE about_npc_id IS NOT NULL",
    # Aufgestaute Kraenkungen -> Meuterei-Treiber. accumulated_count + severity je Vorfall.
    """
    CREATE TABLE IF NOT EXISTS commander_grievances (
        id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        commander_id      UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
        grievance_type    TEXT NOT NULL,   -- ignored_demand | risky_missions | denied_promotion | combat_neglect
        severity          INT NOT NULL DEFAULT 0,
        accumulated_count INT NOT NULL DEFAULT 1,
        created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at       TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_commander_grievances_open ON commander_grievances(commander_id) WHERE resolved_at IS NULL",
    # Meuterei-Status (Welle 2): neue Kommandeur-Stati. 'mutinous' = Vorwarnung/akut, verweigert den
    # naechsten Befehl; 'defected' existiert bereits. Telegrafiert + idempotent.
    "ALTER TYPE commander_status ADD VALUE IF NOT EXISTS 'mutinous'",
    # Anker fuer den Meuterei-Cooldown + Zeitpunkt des letzten Memory-Digests (ai-worker).
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS last_mutiny_check_at TIMESTAMPTZ",
    "ALTER TABLE commanders ADD COLUMN IF NOT EXISTS last_digest_at TIMESTAMPTZ",
    # -- Feature: Lebende Galaxie-Chronik (Welle 3, 2026-06-20) ----------------
    # Ein fortlaufendes „Geschichtsbuch" des Servers: der ai-worker (Erzaehler 'historian')
    # verdichtet die echten Spieler-Taten eines Zeitfensters (groesste Schlachten, Auf-/Abstiege,
    # Verrat, grosse Welt-Events) zu einem epischen, faktentreuen Saga-Eintrag. ``key_events``
    # haelt sowohl die erzaehlwuerdigen Fakten ALS AUCH den Score-/Ruf-Snapshot des Fensters
    # ({"events":[...],"snapshot":{...}}), damit die naechste Chronik die Veraenderung erkennt —
    # ohne extra Snapshot-Tabelle. ``status`` = pending (Backend angelegt) -> published (ai-worker).
    """
    CREATE TABLE IF NOT EXISTS game_chronicle (
        id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title        TEXT NOT NULL DEFAULT '',
        body         TEXT NOT NULL DEFAULT '',
        narrator     TEXT NOT NULL DEFAULT 'historian',
        span_start   TIMESTAMPTZ,
        span_end     TIMESTAMPTZ,
        key_events   JSONB NOT NULL DEFAULT '[]'::jsonb,
        status       TEXT NOT NULL DEFAULT 'pending',   -- pending | published
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        published_at TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_game_chronicle_published ON game_chronicle(published_at DESC)",
    # -- Welle 4: Die erwachende Galaxie (Feature 7) -------------------------
    # Stuendliche Aggressions-Metrik des GESAMTEN Universums (eine Zeile je Stunde): aus den
    # combat_reports des Fensters aggregiert. ``level`` ist der gewichtete Gesamt-Aggressionswert,
    # ``status`` das Band (peaceful|tense|war|apocalypse). Dient als Verlauf + Frontend-Anzeige.
    """
    CREATE TABLE IF NOT EXISTS aggression_history (
        hour            TIMESTAMPTZ PRIMARY KEY,
        combat_count    INT NOT NULL DEFAULT 0,
        total_debris    DOUBLE PRECISION NOT NULL DEFAULT 0,
        unique_attackers INT NOT NULL DEFAULT 0,
        level           DOUBLE PRECISION NOT NULL DEFAULT 0,
        status          TEXT NOT NULL DEFAULT 'peaceful'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_aggression_history_hour ON aggression_history(hour DESC)",
    # Der uralte Waechter ("Der Erwachte"): server-weite Bedrohung, die erwacht, wenn das
    # Aggressionsniveau aller Spieler eine Schwelle ueberschreitet. Der eigentliche KAMPF-Koerper
    # ist ein NpcEmpire (``npc_id`` -> Wiederverwendung des Spieler<->NPC-Kampfes + NpcAttack);
    # diese Zeile haelt nur den server-weiten LEBENSZYKLUS-Zustand (Aggression bei Geburt,
    # Ablauf, Status, besiegt-Zeitpunkt, Teilnehmer + Beruhigungs-Cooldown). Es ist immer
    # hoechstens EINE Zeile mit status='active' (Einzel-Waechter-Garantie ueber den Code-Pfad).
    """
    CREATE TABLE IF NOT EXISTS awakening_warden (
        id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        npc_id           UUID REFERENCES npc_empires(id) ON DELETE SET NULL,
        spawned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        aggression_level DOUBLE PRECISION NOT NULL DEFAULT 0,
        fleet            JSONB NOT NULL DEFAULT '{}'::jsonb,
        target_scope     TEXT NOT NULL DEFAULT 'global',
        data             JSONB NOT NULL DEFAULT '{}'::jsonb,
        expires_at       TIMESTAMPTZ,
        status           TEXT NOT NULL DEFAULT 'active',   -- active | defeated | dormant
        last_threat_at   TIMESTAMPTZ,
        defeated_at      TIMESTAMPTZ,
        calm_until       TIMESTAMPTZ,
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_awakening_warden_status ON awakening_warden(status)",
    # Handelshistorie (Handels-Umbau): eine Zeile je abgeschlossenem Handel. partner_id ist
    # bewusst KEIN FK (Partner — NPC oder Spieler — soll nach Loeschung lesbar bleiben);
    # partner_name haelt den Klartext. Best-effort aus resolve_trade geschrieben.
    """
    CREATE TABLE IF NOT EXISTS trade_log (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        player_id       UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        partner_kind    TEXT NOT NULL DEFAULT 'npc',
        partner_id      UUID,
        partner_name    TEXT,
        offered_res     TEXT NOT NULL,
        offered_amount  DOUBLE PRECISION NOT NULL DEFAULT 0,
        received_res    TEXT NOT NULL,
        received_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_trade_log_player ON trade_log(player_id, created_at DESC)",
    # -- Feature: Eskort-Gesuche-Board (Nachfrage-Seite, 2026-06-21) -----------
    # Ein Trader postet aktiv einen Eskort-Auftrag (Route + geschaetzter Frachtwert + max. Gebuehr),
    # Eskort-Anbieter nehmen ihn mit einer ihrer Eskort-Stationen (stationed_fleets) an. Spiegelt das
    # bestehende Angebots-Modell (escort_covers); abgelaufene Gesuche werden beim Listen lazy auf
    # 'expired' gesetzt. accepted_station_id/accepted_by ON DELETE SET NULL: Historie ueberlebt die
    # Zerstoerung der Station / Loeschung des Anbieters.
    """
    CREATE TABLE IF NOT EXISTS escort_job (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        requester_id        UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
        origin_galaxy       INT NOT NULL,
        origin_system       INT NOT NULL,
        origin_position     INT NOT NULL,
        target_galaxy       INT NOT NULL,
        target_system       INT NOT NULL,
        target_position     INT NOT NULL,
        cargo_value         DOUBLE PRECISION NOT NULL DEFAULT 0,
        max_fee_pct         DOUBLE PRECISION NOT NULL DEFAULT 0,
        min_power           DOUBLE PRECISION NOT NULL DEFAULT 0,
        status              TEXT NOT NULL DEFAULT 'open',   -- open|accepted|cancelled|expired|done
        accepted_station_id UUID REFERENCES stationed_fleets(id) ON DELETE SET NULL,
        accepted_by         UUID REFERENCES players(id) ON DELETE SET NULL,
        accepted_fee_pct    DOUBLE PRECISION,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
        expires_at          TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_escort_job_open ON escort_job(status, expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_escort_job_requester ON escort_job(requester_id, created_at DESC)",
    # 2026-06-21: Asteroidenfelder bekommen eine Metall:Kristall-KOMPOSITION (gewichtet gerollt
    # beim Spawn). Alt-Felder/Default = 'balanced' (1.0/1.0) -> kein Einfluss auf bestehende Vorraete.
    "ALTER TABLE asteroid_fields ADD COLUMN IF NOT EXISTS composition TEXT NOT NULL DEFAULT 'balanced'",
    # 2026-06-22: eigener Transmissions-Typ fuer Expeditionsberichte -> erscheinen NUR im
    # Expeditionen-Screen, nicht mehr im allgemeinen Postfach.
    "ALTER TYPE transmission_type ADD VALUE IF NOT EXISTS 'expedition'",
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
