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
