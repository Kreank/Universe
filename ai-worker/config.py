"""Konfiguration des ai-worker.

Alle Werte kommen aus Umgebungsvariablen (docker-compose / .env). Die Defaults
sind so gewaehlt, dass der Worker auch lokal (ausserhalb von Docker) gegen einen
Host-Stack laeuft.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    # --- Verbindungen -------------------------------------------------------
    # Hinweis: docker-compose liefert die URL im SQLAlchemy-Stil
    # (postgresql+asyncpg://...). asyncpg.connect() erwartet aber das reine
    # postgresql://-Schema -> siehe asyncpg_dsn unten.
    database_url: str = "postgresql+asyncpg://universe:universe@localhost:5432/universe"
    redis_url: str = "redis://localhost:6379/0"

    # --- Ollama -------------------------------------------------------------
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"

    # --- Pfade --------------------------------------------------------------
    balance_path: str = "/app/shared/balance.json"

    # --- Queue / Pipeline-Tuning -------------------------------------------
    job_queue: str = "ai:jobs"
    embed_dim: int = 768                      # passt zu vector(768) im Schema
    dedup_cosine_threshold: float = 0.10      # < Schwelle => zu aehnlich => verwerfen
    bank_target_per_situation: int = 10       # nightly_batch: Ziel je Situation
    persona_init_bank_count: int = 5          # persona_init: kleinere Erst-Bank
    generation_overshoot: int = 3             # so viele Varianten extra anfragen (Dedup-Puffer)
    max_generation_attempts: int = 3          # big_moment: Versuche bis nicht-Duplikat

    # --- Laufzeit-Verhalten ------------------------------------------------
    brpop_timeout: int = 5                    # s; erlaubt regelmaessigen Stop-Check
    ollama_outage_backoff_seconds: float = 5.0
    generate_timeout_seconds: float = 120.0
    embed_timeout_seconds: float = 60.0

    @property
    def asyncpg_dsn(self) -> str:
        """DATABASE_URL in eine von asyncpg verstandene DSN umschreiben."""
        return (
            self.database_url
            .replace("postgresql+asyncpg://", "postgresql://")
            .replace("+asyncpg", "")
        )


settings = Settings()
