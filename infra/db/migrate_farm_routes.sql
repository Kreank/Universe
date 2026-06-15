-- Migration: Farm-Routinen (farm_routes). Idempotent — gefahrlos mehrfach ausführbar.
-- Anwenden auf die LAUFENDE DB (init.sql läuft nur bei frischem Volume):
--   docker compose -f infra/docker-compose.yml --env-file infra/.env exec -T postgres \
--     psql -U universe -d universe < infra/db/migrate_farm_routes.sql
-- (User/DB ggf. an POSTGRES_USER/POSTGRES_DB aus infra/.env anpassen.)

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
);
CREATE INDEX IF NOT EXISTS idx_farm_routes_player ON farm_routes(player_id);
