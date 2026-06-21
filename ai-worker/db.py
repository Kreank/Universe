"""PostgreSQL-Zugriff (asyncpg + pgvector).

Der ai-worker spricht NUR ueber PostgreSQL (Ergebnisse) und Redis (Jobs/PubSub)
mit dem Rest des Systems — nie direkt mit dem game-server (ARCHITECTURE §3).

Dedup/RAG laufen ueber den pgvector-Cosine-Operator `<=>` (Cosine-Distanz,
0 = identisch, 2 = gegensaetzlich). Schwelle in config.dedup_cosine_threshold.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import asyncpg
from pgvector.asyncpg import register_vector

from config import settings

log = logging.getLogger("db")


async def _init_connection(conn: asyncpg.Connection) -> None:
    # JSONB automatisch als dict/list dekodieren statt als str.
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    # vector(768) <-> Python-Liste.
    await register_vector(conn)


class Database:
    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or settings.asyncpg_dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            self._dsn, min_size=1, max_size=5, init=_init_connection
        )
        log.info("PostgreSQL-Pool verbunden")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.connect() wurde nicht aufgerufen")
        return self._pool

    # --------------------------------------------------------------- commanders
    async def get_commander(self, commander_id: str) -> Optional[asyncpg.Record]:
        return await self.pool.fetchrow(
            """
            SELECT id, player_id, name, persona, traits,
                   specialization::text AS specialization,
                   rank::text AS rank, morale, status::text AS status
            FROM commanders WHERE id = $1
            """,
            commander_id,
        )

    async def update_persona(self, commander_id: str, persona: dict[str, Any]) -> None:
        await self.pool.execute(
            "UPDATE commanders SET persona = $2 WHERE id = $1", commander_id, persona
        )

    # ------------------------------------------- commander memory (Welle 2)
    async def get_commander_memories(self, commander_id: str, limit: int = 40) -> list[asyncpg.Record]:
        """Die juengsten Erinnerungen eines Kommandeurs (fuer das Erinnerungs-Narrativ)."""
        return await self.pool.fetch(
            """
            SELECT event_type, context, sentiment, created_at
            FROM commander_memories WHERE commander_id = $1
            ORDER BY created_at DESC LIMIT $2
            """,
            commander_id, limit,
        )

    async def get_commander_opinions(self, commander_id: str, limit: int = 20) -> list[asyncpg.Record]:
        """Meinungen eines Kommandeurs ueber Gegner (Spieler-/NPC-Name aufgeloest)."""
        return await self.pool.fetch(
            """
            SELECT o.opinion_type, o.strength,
                   COALESCE(p.display_name, n.name) AS target_name
            FROM commander_opinions o
            LEFT JOIN players p ON p.id = o.about_player_id
            LEFT JOIN npc_empires n ON n.id = o.about_npc_id
            WHERE o.commander_id = $1
            ORDER BY o.strength DESC LIMIT $2
            """,
            commander_id, limit,
        )

    async def get_commander_relationships(self, commander_id: str, limit: int = 20) -> list[asyncpg.Record]:
        """Beziehungen eines Kommandeurs zu anderen Kommandeuren (Gegen-Name aufgeloest)."""
        return await self.pool.fetch(
            """
            SELECT r.rel_type, r.strength,
                   CASE WHEN r.commander_a_id = $1 THEN cb.name ELSE ca.name END AS other_name
            FROM commander_relationships r
            JOIN commanders ca ON ca.id = r.commander_a_id
            JOIN commanders cb ON cb.id = r.commander_b_id
            WHERE r.commander_a_id = $1 OR r.commander_b_id = $1
            ORDER BY r.strength DESC LIMIT $2
            """,
            commander_id, limit,
        )

    async def get_commander_opinion_about(
        self, commander_id: str, about_player_id: Optional[str], about_npc_id: Optional[str]
    ) -> Optional[asyncpg.Record]:
        """Die EINE Meinung des Kommandeurs ueber einen konkreten Gegner (oder None)."""
        if about_player_id:
            return await self.pool.fetchrow(
                """
                SELECT opinion_type, strength FROM commander_opinions
                WHERE commander_id = $1 AND about_player_id = $2
                """,
                commander_id, about_player_id,
            )
        if about_npc_id:
            return await self.pool.fetchrow(
                """
                SELECT opinion_type, strength FROM commander_opinions
                WHERE commander_id = $1 AND about_npc_id = $2
                """,
                commander_id, about_npc_id,
            )
        return None

    async def save_memory_summary(self, commander_id: str, summary: str) -> None:
        """Schreibt das verdichtete Erinnerungs-Narrativ in persona.memory_summary (jsonb_set,
        legt persona an, falls NULL/leer) und setzt last_digest_at = now()."""
        await self.pool.execute(
            """
            UPDATE commanders
            SET persona = jsonb_set(COALESCE(persona, '{}'::jsonb), '{memory_summary}', to_jsonb($2::text), true),
                last_digest_at = now()
            WHERE id = $1
            """,
            commander_id, summary,
        )

    # --------------------------------------------------------------- npc_empires
    async def get_npc(self, npc_id: str) -> Optional[asyncpg.Record]:
        return await self.pool.fetchrow(
            """
            SELECT id, name, behavior_profile, persona, galaxy, system, position
            FROM npc_empires WHERE id = $1
            """,
            npc_id,
        )

    async def update_npc_persona(self, npc_id: str, persona: dict[str, Any]) -> None:
        await self.pool.execute(
            "UPDATE npc_empires SET persona = $2 WHERE id = $1", npc_id, persona
        )

    async def update_npc_name(self, npc_id: str, name: str) -> None:
        await self.pool.execute(
            "UPDATE npc_empires SET name = $2 WHERE id = $1", npc_id, name
        )

    # ------------------------------------------------------- npc_relations (Welle 1)
    async def get_npc_relation(self, player_id: str, npc_id: str) -> Optional[asyncpg.Record]:
        return await self.pool.fetchrow(
            """
            SELECT player_id, npc_id, status, alliance_since, ceasefire_until,
                   tribute_metal_per_cycle, tribute_last_paid, betrayed_by_player,
                   betrayed_by_npc, message_count, positive_actions, negative_actions,
                   last_decision_at
            FROM npc_relations WHERE player_id = $1 AND npc_id = $2
            """,
            player_id, npc_id,
        )

    async def upsert_npc_relation(self, player_id: str, npc_id: str, fields: dict[str, Any]) -> None:
        """Schreibt die vom Worker berechneten Beziehungsfelder zurueck (Diplomatie-Apply).

        ``fields`` enthaelt nur die Spalten, die der Worker setzt: status, alliance_since,
        ceasefire_until, tribute_metal_per_cycle, tribute_last_paid, positive_actions,
        last_decision_at. Die Zeile existiert i. d. R. schon (vom Backend angelegt); ON CONFLICT
        deckt den seltenen Race ab."""
        cols = list(fields.keys())
        set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols)
        insert_cols = ", ".join(["player_id", "npc_id", *cols])
        placeholders = ", ".join(f"${i}" for i in range(1, len(cols) + 3))
        await self.pool.execute(
            f"""
            INSERT INTO npc_relations ({insert_cols})
            VALUES ({placeholders})
            ON CONFLICT (player_id, npc_id) DO UPDATE SET {set_clause}
            """,
            player_id, npc_id, *[fields[c] for c in cols],
        )

    async def insert_npc_decision(
        self, npc_id: str, player_id: str, offer_type: str, offered_terms: dict[str, Any],
        npc_choice: str, npc_reasoning: str, terms_result: dict[str, Any],
    ) -> Any:
        return await self.pool.fetchval(
            """
            INSERT INTO npc_decisions
                (npc_id, player_id, offer_type, offered_terms, npc_choice, npc_reasoning, terms_result)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            npc_id, player_id, offer_type, offered_terms, npc_choice, npc_reasoning, terms_result,
        )

    async def insert_diplomacy_transmission(
        self, player_id: str, subject: str, body: str,
        requires_decision: bool, decision_payload: Optional[dict[str, Any]],
    ) -> asyncpg.Record:
        """Diplomatie-Funkspruch (type 'npc_diplomacy') ins Spieler-Postfach. ``requires_decision``
        + ``decision_payload`` tragen ein Gegenangebot (counter)."""
        return await self.pool.fetchrow(
            """
            INSERT INTO transmissions
                (player_id, commander_id, type, subject, body, requires_decision, decision_payload)
            VALUES ($1, NULL, 'npc_diplomacy'::transmission_type, $2, $3, $4, $5)
            RETURNING id, player_id, commander_id, type::text AS type, subject, body,
                      requires_decision, decision_payload, read, created_at
            """,
            player_id, subject, body, requires_decision, decision_payload,
        )

    # ------------------------------------------------------ game_chronicle (Welle 3)
    async def update_chronicle(self, chronicle_id: str, title: str, body: str) -> None:
        """Schreibt Titel+Text in eine pending-Chronik und veroeffentlicht sie."""
        await self.pool.execute(
            """
            UPDATE game_chronicle
            SET title = $2, body = $3, status = 'published', published_at = now()
            WHERE id = $1
            """,
            chronicle_id, title, body,
        )

    async def active_player_ids(self) -> list[str]:
        """Alle Spieler-IDs (fuer Galaxie-News-Broadcast). MVP: alle Spieler."""
        rows = await self.pool.fetch("SELECT id FROM players")
        return [str(r["id"]) for r in rows]

    # ------------------------------------------------------------ reaction_banks
    # kind ∈ {"commander","npc"} -> waehlt die FK-Spalte (commander_id ODER npc_id).
    @staticmethod
    def _entity_col(kind: str) -> str:
        return "npc_id" if kind == "npc" else "commander_id"

    async def count_bank(self, entity_id: str, situation: str, kind: str = "commander") -> int:
        col = self._entity_col(kind)
        val = await self.pool.fetchval(
            f"SELECT count(*) FROM reaction_banks WHERE {col} = $1 AND situation = $2",
            entity_id, situation,
        )
        return int(val or 0)

    async def nearest_reaction_distance(
        self, entity_id: str, situation: str, embedding: list[float], kind: str = "commander"
    ) -> Optional[float]:
        """Cosine-Distanz zum aehnlichsten vorhandenen Bank-Eintrag (oder None)."""
        col = self._entity_col(kind)
        val = await self.pool.fetchval(
            f"""
            SELECT embedding <=> $3 AS dist
            FROM reaction_banks
            WHERE {col} = $1 AND situation = $2 AND embedding IS NOT NULL
            ORDER BY embedding <=> $3
            LIMIT 1
            """,
            entity_id, situation, embedding,
        )
        return float(val) if val is not None else None

    async def insert_reaction(
        self, entity_id: str, situation: str, template_text: str, embedding: list[float],
        kind: str = "commander",
    ) -> Any:
        col = self._entity_col(kind)
        return await self.pool.fetchval(
            f"""
            INSERT INTO reaction_banks ({col}, situation, template_text, embedding)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            entity_id, situation, template_text, embedding,
        )

    # --------------------------------------------------------------- flavor_pool
    async def retrieve_lore(self, embedding: list[float], limit: int = 3) -> list[str]:
        """RAG: die aehnlichsten Flavor/Lore-Schnipsel zum Kontext holen."""
        rows = await self.pool.fetch(
            """
            SELECT text FROM flavor_pool
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $2
            """,
            embedding, limit,
        )
        return [r["text"] for r in rows]

    # ------------------------------------------------------------- transmissions
    async def insert_transmission(
        self,
        player_id: str,
        commander_id: Optional[str],
        ttype: str,
        subject: str,
        body: str,
    ) -> asyncpg.Record:
        return await self.pool.fetchrow(
            """
            INSERT INTO transmissions (player_id, commander_id, type, subject, body)
            VALUES ($1, $2, $3::transmission_type, $4, $5)
            RETURNING id, player_id, commander_id, type::text AS type,
                      subject, body, requires_decision, decision_payload, read, created_at
            """,
            player_id, commander_id, ttype, subject, body,
        )
