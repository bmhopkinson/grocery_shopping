import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_engine() -> None:
    """Initialize the SQLAlchemy async engine and create all tables."""
    global _engine, _session_factory

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return

    # SQLAlchemy async psycopg3 driver requires postgresql+psycopg:// scheme
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    _engine = create_async_engine(async_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_session():
    """Yield an AsyncSession, or None if no database is configured."""
    if _session_factory is None:
        yield None
        return
    async with _session_factory() as session:
        yield session
