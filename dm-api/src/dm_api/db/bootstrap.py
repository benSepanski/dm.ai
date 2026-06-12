"""Create the database schema directly from the SQLAlchemy models.

Alembic migrations remain the canonical schema path for PostgreSQL
deployments. This module exists for the local playtest harness
(``scripts/playtest.sh``), which runs the API against SQLite where the
migrations' PostgreSQL-specific DDL (pgvector extension, ``ALTER`` history)
cannot run.

Usage::

    python -m dm_api.db.bootstrap
"""

from __future__ import annotations

import asyncio

import dm_api.db.models  # noqa: F401 — import all models so they register with Base.metadata
from dm_api.db.session import Base, engine


async def create_all() -> None:
    """Create every table known to ``Base.metadata`` in the configured database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_all())
