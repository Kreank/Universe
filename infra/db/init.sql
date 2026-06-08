-- =====================================================================
--  UNIVERSE — Datenbank-Schema (Vertical Slice v0.1)
--  Basis: ARCHITECTURE.md §7. PostgreSQL + pgvector.
--  Dieses Skript wird beim ersten Hochfahren des postgres-Containers
--  automatisch ausgefuehrt (docker-entrypoint-initdb.d).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector (Embeddings)

-- ---------------------------------------------------------------------
--  ENUM-Typen
-- ---------------------------------------------------------------------
CREATE TYPE resource_type   AS ENUM ('metal', 'crystal', 'deuterium', 'energy');
CREATE TYPE commander_status AS ENUM ('active', 'training', 'wounded', 'captured', 'dead');
CREATE TYPE commander_rank  AS ENUM ('cadet', 'officer', 'veteran', 'elite', 'legend');
CREATE TYPE specialization  AS ENUM ('combat', 'logistics', 'spy', 'research', 'trade');
CREATE TYPE fleet_mission   AS ENUM ('attack', 'transport', 'deploy', 'hold', 'colonize', 'spy', 'recycle', 'expedition', 'return', 'mine');
CREATE TYPE fleet_status    AS ENUM ('flying', 'arrived', 'returning', 'done');
CREATE TYPE occupant_type   AS ENUM ('empty', 'player', 'npc', 'debris');
CREATE TYPE transmission_type AS ENUM ('routine', 'reaction', 'demand', 'combat_report', 'big_moment', 'system', 'spy_report');

-- ---------------------------------------------------------------------
--  Spieler & Auth
-- ---------------------------------------------------------------------
CREATE TABLE players (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT UNIQUE NOT NULL,
    pw_hash       TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active   TIMESTAMPTZ NOT NULL DEFAULT now(),
    score         BIGINT NOT NULL DEFAULT 0,
    is_protected  BOOLEAN NOT NULL DEFAULT TRUE,
    vacation_until TIMESTAMPTZ,
    doctrine      TEXT,                                 -- Imperiums-Doktrin (Doku 03b §9)
    doctrine_changed_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------
--  Planeten & Wirtschaft
-- ---------------------------------------------------------------------
CREATE TABLE planets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id    UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    galaxy       INT NOT NULL,
    system       INT NOT NULL,
    position     INT NOT NULL,
    name         TEXT NOT NULL DEFAULT 'Heimatplanet',
    planet_type  TEXT NOT NULL DEFAULT 'normal',
    temp_max     INT NOT NULL DEFAULT 40,
    fields_used  INT NOT NULL DEFAULT 0,
    fields_max   INT NOT NULL DEFAULT 163,
    is_homeworld BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (galaxy, system, position)
);
CREATE INDEX idx_planets_player ON planets(player_id);

-- Lazy-Ressourcen (ADR-002): amount + rate + last_updated. Energie als Bilanz.
CREATE TABLE resources (
    planet_id    UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
    type         resource_type NOT NULL,
    amount       DOUBLE PRECISION NOT NULL DEFAULT 0,
    rate         DOUBLE PRECISION NOT NULL DEFAULT 0,   -- pro Stunde (bereits speed-skaliert)
    last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (planet_id, type)
);

CREATE TABLE buildings (
    planet_id          UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
    type               TEXT NOT NULL,
    level              INT NOT NULL DEFAULT 0,
    upgrade_finishes_at TIMESTAMPTZ,
    PRIMARY KEY (planet_id, type)
);

CREATE TABLE research (
    player_id    UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    type         TEXT NOT NULL,
    level        INT NOT NULL DEFAULT 0,
    finishes_at  TIMESTAMPTZ,
    PRIMARY KEY (player_id, type)
);

-- Genau EINE aktive Forschung pro Spieler (Doku 02). Partial unique index.
CREATE UNIQUE INDEX idx_one_research_active
    ON research (player_id)
    WHERE finishes_at IS NOT NULL;

-- ---------------------------------------------------------------------
--  Commander (USP)
-- ---------------------------------------------------------------------
CREATE TABLE commanders (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id      UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    persona        JSONB NOT NULL DEFAULT '{}'::jsonb,   -- Name, Hintergrund, Sprechstil
    traits         JSONB NOT NULL DEFAULT '[]'::jsonb,   -- ["aggressive","loyal"]
    specialization specialization NOT NULL DEFAULT 'combat',
    rank           commander_rank NOT NULL DEFAULT 'cadet',
    grade          TEXT NOT NULL DEFAULT 'C',            -- Gueteklasse F..SSS (angeborenes Potenzial)
    xp             INT NOT NULL DEFAULT 0,
    morale         INT NOT NULL DEFAULT 60 CHECK (morale BETWEEN 0 AND 100),
    loyalty        INT NOT NULL DEFAULT 100 CHECK (loyalty BETWEEN 0 AND 100),
    span_capacity  INT NOT NULL DEFAULT 1,
    status         commander_status NOT NULL DEFAULT 'active',
    training_finishes_at TIMESTAMPTZ,
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- fuer Neglect-Decay
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_commanders_player ON commanders(player_id);

-- Befehlskette (ARCHITECTURE §7)
CREATE TABLE commander_links (
    superior_id    UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
    subordinate_id UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
    PRIMARY KEY (superior_id, subordinate_id)
);

-- ---------------------------------------------------------------------
--  Flotten & Schiffe
-- ---------------------------------------------------------------------
CREATE TABLE fleets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id    UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    commander_id UUID REFERENCES commanders(id) ON DELETE SET NULL,
    origin_planet_id UUID REFERENCES planets(id) ON DELETE SET NULL,
    target_galaxy  INT NOT NULL,
    target_system  INT NOT NULL,
    target_position INT NOT NULL,
    mission      fleet_mission NOT NULL,
    status       fleet_status NOT NULL DEFAULT 'flying',
    depart_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    arrive_at    TIMESTAMPTZ NOT NULL,
    return_at    TIMESTAMPTZ,
    cargo        JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {metal, crystal, deuterium}
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_fleets_player ON fleets(player_id);
CREATE INDEX idx_fleets_arrive ON fleets(arrive_at) WHERE status = 'flying';

-- Schiffe: entweder auf Planet (planet_id) oder in Flotte (fleet_id).
CREATE TABLE ships (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    planet_id  UUID REFERENCES planets(id) ON DELETE CASCADE,
    fleet_id   UUID REFERENCES fleets(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    count      INT NOT NULL DEFAULT 0 CHECK (count >= 0),
    CHECK (planet_id IS NOT NULL OR fleet_id IS NOT NULL)
);
CREATE INDEX idx_ships_planet ON ships(planet_id);
CREATE INDEX idx_ships_fleet ON ships(fleet_id);

CREATE TABLE defenses (
    planet_id UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
    type      TEXT NOT NULL,
    count     INT NOT NULL DEFAULT 0 CHECK (count >= 0),
    PRIMARY KEY (planet_id, type)
);

-- Persistente Werft-Bau-Warteschlange: ueberlebt Neustarts (Scheduler-Recovery).
CREATE TABLE shipyard_queue (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    planet_id   UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    count       INT  NOT NULL CHECK (count > 0),
    category    TEXT NOT NULL,                       -- 'ship' | 'defense'
    finishes_at TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_shipyard_queue_finishes ON shipyard_queue(finishes_at);
CREATE INDEX idx_shipyard_queue_planet ON shipyard_queue(planet_id);

-- ---------------------------------------------------------------------
--  KI-Content: Reaktions-Banken, Flavor, Transmissionen (GDD §10)
-- ---------------------------------------------------------------------
-- Die "Munition": pro Commander vorgenerierte Funksprueche je Situation.
CREATE TABLE reaction_banks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commander_id  UUID NOT NULL REFERENCES commanders(id) ON DELETE CASCADE,
    situation     TEXT NOT NULL,           -- 'victory','defeat','mutiny','close_win',...
    template_text TEXT NOT NULL,           -- mit {enemy} {planet} {loot} Slots
    embedding     vector(768),             -- pgvector: Dedup + RAG (ADR-004)
    used          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reaction_lookup ON reaction_banks(commander_id, situation, used);

-- Ebene-3-Flavor: rotierender Pool (Crew-Gespraeche, Lore).
CREATE TABLE flavor_pool (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope      TEXT NOT NULL,
    text       TEXT NOT NULL,
    embedding  vector(768),
    week_tag   TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Postfach des Spielers.
CREATE TABLE transmissions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id        UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    commander_id     UUID REFERENCES commanders(id) ON DELETE SET NULL,
    type             transmission_type NOT NULL DEFAULT 'routine',
    subject          TEXT NOT NULL,
    body             TEXT NOT NULL,
    requires_decision BOOLEAN NOT NULL DEFAULT FALSE,
    decision_payload JSONB,                -- {demand_id, options:[...]}
    read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_transmissions_player ON transmissions(player_id, read, created_at DESC);

-- ---------------------------------------------------------------------
--  Kampf
-- ---------------------------------------------------------------------
CREATE TABLE combat_reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attacker_id UUID REFERENCES players(id) ON DELETE SET NULL,
    defender_id UUID REFERENCES players(id) ON DELETE SET NULL,
    location    TEXT NOT NULL,            -- "G:S:P"
    seed        BIGINT NOT NULL,
    outcome     JSONB NOT NULL,           -- rounds, survivors, winner
    loot        JSONB NOT NULL DEFAULT '{}'::jsonb,
    debris      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
--  Universum
-- ---------------------------------------------------------------------
CREATE TABLE universe_cells (
    galaxy        INT NOT NULL,
    system        INT NOT NULL,
    position      INT NOT NULL,
    occupant_type occupant_type NOT NULL DEFAULT 'empty',
    ref_id        UUID,                    -- planet_id oder npc_id
    debris_field  JSONB NOT NULL DEFAULT '{}'::jsonb,  -- Truemmer am Ort {metal, crystal}
    PRIMARY KEY (galaxy, system, position)
);

CREATE TABLE npc_empires (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    behavior_profile TEXT NOT NULL DEFAULT 'defensive',
    galaxy           INT NOT NULL,
    system           INT NOT NULL,
    position         INT NOT NULL,
    fleet            JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {light_fighter: 10, ...}
    defenses         JSONB NOT NULL DEFAULT '{}'::jsonb,
    resources        JSONB NOT NULL DEFAULT '{}'::jsonb,
    baseline         JSONB NOT NULL DEFAULT '{}'::jsonb,   -- Soll-Garnison {fleet:{...}, defenses:{...}}
    last_action_at   TIMESTAMPTZ,                          -- Zeitpunkt der letzten NPC-Tick-Aktion
    last_attack_at   TIMESTAMPTZ,                          -- Zeitpunkt des letzten ausgehenden Angriffs
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_npc_location ON npc_empires(galaxy, system, position);

-- Eingehende NPC-Angriffe auf Spieler-Planeten (im Anflug; bei Ankunft aufgeloest).
CREATE TABLE npc_attacks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    npc_id           UUID NOT NULL REFERENCES npc_empires(id) ON DELETE CASCADE,
    target_player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    target_planet_id UUID NOT NULL REFERENCES planets(id) ON DELETE CASCADE,
    target_galaxy    INT NOT NULL,
    target_system    INT NOT NULL,
    target_position  INT NOT NULL,
    fleet            JSONB NOT NULL DEFAULT '{}'::jsonb,    -- {type: count} der Angreifer
    status           TEXT NOT NULL DEFAULT 'incoming',      -- 'incoming' | 'resolved'
    arrive_at        TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_npc_attacks_status ON npc_attacks(status);
CREATE INDEX idx_npc_attacks_target ON npc_attacks(target_player_id);

-- ---------------------------------------------------------------------
--  Seed: ein paar NPC-Ziele fuer den Vertical-Slice-Loop (PvE)
-- ---------------------------------------------------------------------
INSERT INTO npc_empires (name, behavior_profile, galaxy, system, position, fleet, defenses, resources) VALUES
  ('Verlassene Schmugglerbasis', 'defensive', 1, 42, 8,
   '{"light_fighter": 8, "small_cargo": 3}'::jsonb,
   '{"rocket_launcher": 5}'::jsonb,
   '{"metal": 4000, "crystal": 2000, "deuterium": 800}'::jsonb),
  ('Piraten-Aussenposten K17', 'defensive', 1, 58, 4,
   '{"light_fighter": 15, "heavy_fighter": 4}'::jsonb,
   '{"rocket_launcher": 10, "light_laser": 4}'::jsonb,
   '{"metal": 9000, "crystal": 5000, "deuterium": 1500}'::jsonb),
  ('Treibendes Wrackfeld', 'defensive', 1, 31, 12,
   '{"light_fighter": 3}'::jsonb,
   '{}'::jsonb,
   '{"metal": 2000, "crystal": 1500, "deuterium": 300}'::jsonb);

INSERT INTO universe_cells (galaxy, system, position, occupant_type, ref_id)
  SELECT galaxy, system, position, 'npc', id FROM npc_empires;

-- ---------------------------------------------------------------------
--  Spionage: pro Spieler aufgedeckte Ziele (Doku 04 §6)
-- ---------------------------------------------------------------------
-- Ziele werden erst per Spionagesonde sichtbar; intel haelt den letzten
-- Aufklaerungs-Schnappschuss (Flotte/Verteidigung/Resschen je nach Stufe).
CREATE TABLE player_discoveries (
    player_id     UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    galaxy        INT NOT NULL,
    system        INT NOT NULL,
    position      INT NOT NULL,
    intel         JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {name, fleet, defenses, resources, ...}
    level         INT NOT NULL DEFAULT 1,               -- Aufklaerungs-Detailstufe (1..3)
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (player_id, galaxy, system, position)
);
CREATE INDEX idx_discoveries_player ON player_discoveries(player_id);
