import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base

target_metadata = Base.metadata


_OUR_TABLES = {m.name for m in Base.metadata.sorted_tables}


def _include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in _OUR_TABLES
    return True


def _do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = os.environ["DATABASE_URL"]
    async_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    connectable = create_async_engine(async_url)

    async def _run():
        async with connectable.connect() as conn:
            await conn.run_sync(_do_run_migrations)
        await connectable.dispose()

    asyncio.run(_run())


if context.is_offline_mode():
    raise RuntimeError("Offline mode not supported — run with DATABASE_URL set")
else:
    run_migrations_online()
