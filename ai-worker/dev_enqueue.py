"""Dev-Hilfsskript: einen Beispiel-Job in die Redis-Queue `ai:jobs` legen.

Zum manuellen Testen des Workers ohne game-server.

Beispiele (vom Host aus, Redis-Port via docker-compose gemappt):
    python dev_enqueue.py big_moment --commander <UUID> --player <UUID>
    python dev_enqueue.py nightly_batch --commander <UUID>
    python dev_enqueue.py persona_init --commander <UUID>

Ohne UUIDs werden Platzhalter verwendet — die zugehoerigen Datensaetze muessen
in der DB existieren, sonst verwirft der Worker den Job sauber (mit Log).
Setze REDIS_URL passend, falls Redis nicht unter redis://localhost:6379/0 laeuft.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone

import redis.asyncio as aioredis

from config import settings


def build_job(args: argparse.Namespace) -> dict:
    job: dict = {
        "job_type": args.job_type,
        "commander_id": args.commander,
        "player_id": args.player,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    }
    if args.job_type == "big_moment":
        job["context"] = {
            "situation": args.situation,
            "enemy": "Piraten-Aussenposten K17",
            "planet": "1:58:4",
            "loot": {"metal": 9000, "crystal": 5000, "deuterium": 1500},
            "outcome": "win",
        }
    else:
        job["context"] = {"situation": args.situation}
    return job


async def main() -> None:
    parser = argparse.ArgumentParser(description="Beispiel-Job in ai:jobs einreihen")
    parser.add_argument(
        "job_type",
        choices=["big_moment", "nightly_batch", "persona_init"],
        nargs="?",
        default="big_moment",
    )
    parser.add_argument("--commander", default="00000000-0000-0000-0000-000000000001",
                        help="Commander-UUID (muss in der DB existieren)")
    parser.add_argument("--player", default="00000000-0000-0000-0000-000000000002",
                        help="Player-UUID (fuer big_moment / PubSub)")
    parser.add_argument("--situation", default="victory",
                        help="victory|defeat|close_win|mutiny|demand|idle_bored")
    args = parser.parse_args()

    job = build_job(args)
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Producer-Konvention: LPUSH (Worker konsumiert per BRPOP vom Ende -> FIFO).
        length = await redis.lpush(settings.job_queue, json.dumps(job, ensure_ascii=False))
    finally:
        await redis.aclose()

    print(f"Job eingereiht in '{settings.job_queue}' (Queue-Laenge: {length}):")
    print(json.dumps(job, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
