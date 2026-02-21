"""
Test configuration and fixtures for dm-api.

IMPORTANT: pgvector and asyncpg mocks MUST be set up before any dm_api imports.
"""
import sys
import types as _types

import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Mock pgvector before any dm_api imports
# ---------------------------------------------------------------------------
_pgvector = _types.ModuleType("pgvector")
_pgvector_sa = _types.ModuleType("pgvector.sqlalchemy")


class _FakeVector(sa.types.TypeDecorator):
    """Fake Vector type that stores data as Text for SQLite compatibility."""
    impl = sa.Text
    cache_ok = True

    def __init__(self, dim=None):
        super().__init__()
        self.dim = dim

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        return value


# pgvector.sqlalchemy.Vector is used as Vector(1536) in column definitions
_pgvector_sa.Vector = _FakeVector
_pgvector.sqlalchemy = _pgvector_sa
sys.modules["pgvector"] = _pgvector
sys.modules["pgvector.sqlalchemy"] = _pgvector_sa

# ---------------------------------------------------------------------------
# Mock asyncpg (SQLite uses aiosqlite instead)
# ---------------------------------------------------------------------------
_asyncpg = _types.ModuleType("asyncpg")
sys.modules["asyncpg"] = _asyncpg

# ---------------------------------------------------------------------------
# Now safe to import test utilities and dm_api modules
# ---------------------------------------------------------------------------
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    # Import Base AFTER pgvector mock is in place
    from dm_api.db.session import Base
    # IMPORTANT: import all models so they register with Base.metadata
    import dm_api.db.models  # noqa: F401 — triggers all model imports

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine):
    from dm_api.main import app
    from dm_api.db.session import get_db
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def world_id(client):
    """Create a World and return its UUID string."""
    r = await client.post(
        "/api/worlds/",
        json={"name": "Test World", "setting_description": "A world for testing"},
    )
    assert r.status_code == 201, f"Failed to create world: {r.text}"
    return r.json()["id"]
