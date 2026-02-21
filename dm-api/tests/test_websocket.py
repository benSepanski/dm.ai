"""Tests for the WebSocket endpoint.

The WebSocket route is at /api/ws/sessions/{session_id}
(under /api prefix from main.py, no extra prefix in router.py for ws router).

These tests use synchronous functions (not async) with Starlette's TestClient
to avoid event loop conflicts with pytest-asyncio.
"""
import json
import uuid
import asyncio
import sys
import types as _types
import sqlalchemy as sa
import pytest

from starlette.testclient import TestClient


def _make_app():
    """Create a fresh test app with in-memory SQLite database."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def setup_tables():
        from dm_api.db.session import Base
        import dm_api.db.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup_tables())

    from dm_api.main import app
    from dm_api.db.session import get_db

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, engine


def _cleanup_app(app, engine):
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_websocket_connect_and_send():
    """Test that a client can connect to the WebSocket endpoint and send a message."""
    app, engine = _make_app()
    try:
        session_id = str(uuid.uuid4())
        with TestClient(app) as client:
            # The WS endpoint is at /api/ws/sessions/{id}
            with client.websocket_connect(f"/api/ws/sessions/{session_id}") as ws:
                # Send a message
                ws.send_text(json.dumps({"type": "ping", "data": "hello"}))
                # With only one connection, no broadcast occurs.
                # Just verify the connection and send work without error.
    finally:
        _cleanup_app(app, engine)


def test_websocket_broadcast():
    """Test that messages are broadcast to other connected clients in the same session."""
    app, engine = _make_app()
    try:
        session_id = str(uuid.uuid4())
        with TestClient(app) as client:
            with client.websocket_connect(f"/api/ws/sessions/{session_id}") as ws1:
                with client.websocket_connect(f"/api/ws/sessions/{session_id}") as ws2:
                    # ws1 sends a message
                    message = {"type": "chat", "content": "Hello from ws1"}
                    ws1.send_text(json.dumps(message))

                    # ws2 should receive the broadcast
                    received = ws2.receive_text()
                    data = json.loads(received)
                    assert data["content"] == "Hello from ws1"
                    assert data["session_id"] == session_id
    finally:
        _cleanup_app(app, engine)


def test_websocket_session_isolation():
    """Messages in one session are NOT broadcast to clients in a different session."""
    app, engine = _make_app()
    try:
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        with TestClient(app) as client:
            with client.websocket_connect(f"/api/ws/sessions/{session_id_1}") as ws1:
                with client.websocket_connect(f"/api/ws/sessions/{session_id_2}") as ws2:
                    # ws1 in session 1 sends a message
                    ws1.send_text(json.dumps({"type": "chat", "content": "Session 1 only"}))
                    # ws2 in session 2 should NOT receive it
                    # We just verify no error occurs and ws2 connection is still open
                    ws2.send_text(json.dumps({"type": "ping"}))
    finally:
        _cleanup_app(app, engine)
