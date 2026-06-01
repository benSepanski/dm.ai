"""Tests for the WebSocket broadcast helper and server-initiated push events.

Server-push events are tested at two levels:
1. Unit tests for ``broadcast_to_session`` — mock WebSockets verify the
   delivery, dead-connection cleanup, and no-op behaviour.
2. Integration tests via Starlette's sync TestClient — connect a WS client,
   trigger an HTTP action that mutates state, verify the broadcast arrives.
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests — mock WebSocket objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_no_clients_is_noop():
    """No error when broadcasting to a session with no connected clients."""
    from dm_api.api.ws import _connections, broadcast_to_session

    session_id = str(uuid.uuid4())
    assert session_id not in _connections  # should not exist yet

    # Must not raise.
    await broadcast_to_session(session_id, {"type": "test"})


@pytest.mark.asyncio
async def test_broadcast_delivers_to_connected_client():
    """broadcast_to_session sends JSON to all clients registered for the session."""
    from dm_api.api.ws import _connections, broadcast_to_session

    session_id = str(uuid.uuid4())
    mock_ws = MagicMock()
    mock_ws.send_text = AsyncMock()

    _connections[session_id].append(mock_ws)
    try:
        await broadcast_to_session(session_id, {"type": "chat_message", "content": "hello"})
        mock_ws.send_text.assert_called_once()
        payload = json.loads(mock_ws.send_text.call_args[0][0])
        assert payload["type"] == "chat_message"
        assert payload["content"] == "hello"
    finally:
        _connections.pop(session_id, None)


@pytest.mark.asyncio
async def test_broadcast_delivers_to_multiple_clients():
    """All connected clients for a session receive the event."""
    from dm_api.api.ws import _connections, broadcast_to_session

    session_id = str(uuid.uuid4())
    clients = [MagicMock() for _ in range(3)]
    for c in clients:
        c.send_text = AsyncMock()
        _connections[session_id].append(c)
    try:
        await broadcast_to_session(session_id, {"type": "combat_update"})
        for c in clients:
            c.send_text.assert_called_once()
    finally:
        _connections.pop(session_id, None)


@pytest.mark.asyncio
async def test_broadcast_removes_dead_connections():
    """Clients that raise on send are removed from the registry silently."""
    from dm_api.api.ws import _connections, broadcast_to_session

    session_id = str(uuid.uuid4())
    dead_ws = MagicMock()
    dead_ws.send_text = AsyncMock(side_effect=RuntimeError("connection closed"))
    alive_ws = MagicMock()
    alive_ws.send_text = AsyncMock()

    _connections[session_id].extend([dead_ws, alive_ws])
    try:
        await broadcast_to_session(session_id, {"type": "test"})
        # The dead connection should have been pruned.
        assert dead_ws not in _connections.get(session_id, [])
        # The alive connection should still be there.
        assert alive_ws in _connections[session_id]
        # The alive client received the event.
        alive_ws.send_text.assert_called_once()
    finally:
        _connections.pop(session_id, None)


@pytest.mark.asyncio
async def test_broadcast_cleans_up_empty_session_key():
    """The session key is removed from _connections when all clients die."""
    from dm_api.api.ws import _connections, broadcast_to_session

    session_id = str(uuid.uuid4())
    only_ws = MagicMock()
    only_ws.send_text = AsyncMock(side_effect=RuntimeError("gone"))

    _connections[session_id].append(only_ws)
    await broadcast_to_session(session_id, {"type": "test"})
    assert session_id not in _connections


@pytest.mark.asyncio
async def test_broadcast_session_isolation():
    """Events for session A are NOT delivered to clients in session B."""
    from dm_api.api.ws import _connections, broadcast_to_session

    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())
    client_a = MagicMock()
    client_a.send_text = AsyncMock()
    client_b = MagicMock()
    client_b.send_text = AsyncMock()

    _connections[session_a].append(client_a)
    _connections[session_b].append(client_b)
    try:
        await broadcast_to_session(session_a, {"type": "test", "data": "only A"})
        client_a.send_text.assert_called_once()
        client_b.send_text.assert_not_called()
    finally:
        _connections.pop(session_a, None)
        _connections.pop(session_b, None)


# ---------------------------------------------------------------------------
# Integration tests — real WS connection via TestClient + HTTP trigger
# ---------------------------------------------------------------------------


def _make_sync_app():
    """Set up an in-memory SQLite app for synchronous TestClient tests."""
    import sys
    import types as _types

    import sqlalchemy as sa

    # Mock pgvector (same technique as conftest.py)
    if "pgvector" not in sys.modules:
        _pgvector = _types.ModuleType("pgvector")
        _pgvector_sa = _types.ModuleType("pgvector.sqlalchemy")

        class _FakeVector(sa.types.TypeDecorator):
            impl = sa.Text
            cache_ok = True

            def __init__(self, dim=None):
                super().__init__()
                self.dim = dim

            def process_bind_param(self, value, dialect):
                return None if value is None else str(value)

            def process_result_value(self, value, dialect):
                return value

        _pgvector_sa.Vector = _FakeVector
        _pgvector.sqlalchemy = _pgvector_sa
        sys.modules["pgvector"] = _pgvector
        sys.modules["pgvector.sqlalchemy"] = _pgvector_sa

    if "asyncpg" not in sys.modules:
        sys.modules["asyncpg"] = _types.ModuleType("asyncpg")

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def setup():
        import dm_api.db.models  # noqa: F401
        from dm_api.db.session import Base

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup())

    from dm_api.db.session import get_db
    from dm_api.main import app

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, engine


def _cleanup_sync_app(app, engine):
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_combat_start_broadcasts_update():
    """Starting combat emits a combat_update event to connected WS clients."""

    app, engine = _make_sync_app()
    try:
        with TestClient(app) as http:
            # Create world + session via HTTP.
            world_r = http.post("/api/worlds/", json={"name": "Broadcast Test World"})
            assert world_r.status_code == 201
            world_id = world_r.json()["id"]

            session_r = http.post(
                "/api/sessions/",
                json={"world_id": world_id, "name": "Broadcast Session"},
            )
            assert session_r.status_code == 201
            session_id = session_r.json()["id"]

            received: queue.Queue = queue.Queue()

            def ws_listener():
                with http.websocket_connect(f"/api/ws/sessions/{session_id}") as ws:
                    # Signal the main thread that we're ready.
                    received.put("ready")
                    # Wait for the server-pushed combat_update.
                    msg = ws.receive_text()
                    received.put(json.loads(msg))

            t = threading.Thread(target=ws_listener, daemon=True)
            t.start()

            # Wait until the WS client is connected.
            assert received.get(timeout=5) == "ready"

            # Start combat — this should trigger a broadcast.
            combat_r = http.post(f"/api/sessions/{session_id}/combat")
            assert combat_r.status_code == 201

            # The WS listener should have received the combat_update event.
            event = received.get(timeout=5)
            assert event["type"] == "combat_update"
            assert event["session_id"] == session_id
            assert "combat" in event

            t.join(timeout=1)
    finally:
        _cleanup_sync_app(app, engine)


def test_chat_with_proposal_broadcasts_proposal_ready_with_status():
    """A chat response that includes a proposal emits a proposal_ready event
    with a 'status' field set to 'pending'.

    Regression test: the initial proposal_ready broadcast was missing 'status',
    while accept/reject broadcasts included it, causing inconsistency on the
    client side.
    """
    from game_engine.types import ProposalType

    from dm_api.ai.dm_orchestrator import DMResponse, ProposalPayload

    app, engine = _make_sync_app()
    try:
        with TestClient(app) as http:
            world_r = http.post("/api/worlds/", json={"name": "Proposal Status World"})
            assert world_r.status_code == 201
            world_id = world_r.json()["id"]

            session_r = http.post(
                "/api/sessions/",
                json={"world_id": world_id, "name": "Proposal Status Session"},
            )
            assert session_r.status_code == 201
            session_id = session_r.json()["id"]

            # Collect both WS events: chat_message + proposal_ready.
            received: queue.Queue = queue.Queue()

            def ws_listener():
                with http.websocket_connect(f"/api/ws/sessions/{session_id}") as ws:
                    received.put("ready")
                    for _ in range(2):  # chat_message + proposal_ready
                        received.put(json.loads(ws.receive_text()))

            t = threading.Thread(target=ws_listener, daemon=True)
            t.start()
            assert received.get(timeout=5) == "ready"

            mock_orch = MagicMock()
            mock_orch.handle_message = AsyncMock(
                return_value=DMResponse(
                    response="You find a hidden village.",
                    proposal=ProposalPayload(
                        type=ProposalType.LOCATION,
                        content={"name": "Hidden Village"},
                    ),
                    was_condensed=False,
                    tokens_in=10,
                    tokens_out=15,
                )
            )

            with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
                chat_r = http.post(
                    f"/api/sessions/{session_id}/chat",
                    json={"message": "Explore the forest."},
                )
            assert chat_r.status_code == 200

            ev1 = received.get(timeout=5)
            ev2 = received.get(timeout=5)
            events_by_type = {ev1["type"]: ev1, ev2["type"]: ev2}

            assert "proposal_ready" in events_by_type, (
                f"Expected a 'proposal_ready' event; got: {list(events_by_type)}"
            )
            proposal_event = events_by_type["proposal_ready"]
            assert "status" in proposal_event, (
                "proposal_ready event must include 'status' field"
            )
            assert proposal_event["status"] == "pending", (
                f"Expected status='pending', got status={proposal_event['status']!r}"
            )

            t.join(timeout=1)
    finally:
        _cleanup_sync_app(app, engine)


def test_chat_broadcasts_chat_message():
    """A successful chat call emits a chat_message event to WS clients."""
    from dm_api.ai.dm_orchestrator import DMResponse

    app, engine = _make_sync_app()
    try:
        with TestClient(app) as http:
            world_r = http.post("/api/worlds/", json={"name": "Chat Broadcast World"})
            assert world_r.status_code == 201
            world_id = world_r.json()["id"]

            session_r = http.post(
                "/api/sessions/",
                json={"world_id": world_id, "name": "Chat Broadcast Session"},
            )
            assert session_r.status_code == 201
            session_id = session_r.json()["id"]

            received: queue.Queue = queue.Queue()

            def ws_listener():
                with http.websocket_connect(f"/api/ws/sessions/{session_id}") as ws:
                    received.put("ready")
                    msg = ws.receive_text()
                    received.put(json.loads(msg))

            t = threading.Thread(target=ws_listener, daemon=True)
            t.start()
            assert received.get(timeout=5) == "ready"

            mock_orch = MagicMock()
            mock_orch.handle_message = AsyncMock(
                return_value=DMResponse(
                    response="The tavern is quiet.",
                    proposal=None,
                    was_condensed=False,
                    tokens_in=10,
                    tokens_out=10,
                )
            )
            mock_orch.condense = AsyncMock()

            with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orch):
                chat_r = http.post(
                    f"/api/sessions/{session_id}/chat",
                    json={"message": "Look around."},
                )
            assert chat_r.status_code == 200

            event = received.get(timeout=5)
            assert event["type"] == "chat_message"
            assert event["role"] == "ai"
            assert event["content"] == "The tavern is quiet."
            assert event["session_id"] == session_id

            t.join(timeout=1)
    finally:
        _cleanup_sync_app(app, engine)
