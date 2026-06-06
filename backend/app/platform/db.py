"""Async-Datenbankzugriff (SQLAlchemy 2.0 + asyncpg).

Stellt Engine, Session-Factory und eine FastAPI-Dependency ``get_session`` bereit.
Das Schema wird NICHT von hier erzeugt (siehe infra/db/init.sql), wir mappen nur
gegen die existierenden Tabellen."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.platform.config import settings


class Base(DeclarativeBase):
    """Gemeinsame Declarative-Base fuer alle ORM-Modelle."""


# echo=False -> kein SQL-Spam; pool_pre_ping haelt Verbindungen frisch.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

SessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-Dependency: liefert eine Session, committed/rollbacked automatisch."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Session-Kontext fuer Hintergrund-Jobs (Scheduler, WS), ausserhalb von Requests."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
