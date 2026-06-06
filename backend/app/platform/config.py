"""Zentrale Konfiguration. Liest alles aus Environment-Variablen mit sinnvollen
Defaults fuer die lokale Entwicklung (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_balance_fallback() -> str:
    """Sucht ``shared/balance.json`` aufwaerts vom Datei-Standort aus, damit der
    Server auch lokal (ohne gemountetes /app/shared-Volume) startet."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "shared" / "balance.json"
        if candidate.is_file():
            return str(candidate)
    # Letzter Fallback: Pfad relativ zur Datei (../../../shared/balance.json)
    return str(here.parents[3] / "shared" / "balance.json")


class Settings(BaseSettings):
    """Alle Laufzeit-Einstellungen. Override per ENV oder .env-Datei."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres (async, asyncpg-Treiber)
    DATABASE_URL: str = "postgresql+asyncpg://universe:universe@localhost:5432/universe"
    # Redis (async client)
    REDIS_URL: str = "redis://localhost:6379/0"
    # JWT-Signatur (HS256)
    JWT_SECRET: str = "dev-only-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24 * 7
    # Pfad zur Balance-Datei (Container: /app/shared/balance.json)
    BALANCE_PATH: str = ""

    # WebSocket: Intervall fuer periodische resource_tick-Nachrichten (Sekunden)
    WS_TICK_SECONDS: int = 15

    def balance_path(self) -> str:
        return self.BALANCE_PATH or _find_balance_fallback()


@lru_cache
def get_settings() -> Settings:
    """Singleton-Settings (gecached)."""
    return Settings()


settings = get_settings()
