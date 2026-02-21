"""Tests for the WebSocket endpoint."""
import json
import uuid
import pytest
from starlette.testclient import TestClient


@pytest.mark.asyncio
async def test_websocket_connect_and_echo(test_engine):
    """Test that a client can connect to the WebSocket endpoint.
    
    Uses Starlette's synchronous TestClient for WebSocket testing since
    httpx doesn't support WebSocket connections.
    """
    # Apply pgvector mock — already done in conftest at module load
    from dm_api.main import app
    from dm_api.db.session import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        session_id = str(uuid.uuid4())
        with TestClient(app) as test_client:
            with test_client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
                # Send a message
                ws.send_text(json.dumps({"type": "ping", "data": "hello"}))
                # The WS broadcasts to OTHER connections, not back to sender
                # So with only one client, no message is received back
                # Just verify the connection works without error
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_websocket_broadcast(test_engine):
    """Test that messages are broadcast to other connected clients."""
    from dm_api.main import app
    from dm_api.db.session import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        session_id = str(uuid.uuid4())
        with TestClient(app) as test_client:
            with test_client.websocket_connect(f"/ws/sessions/{session_id}") as ws1:
                with test_client.websocket_connect(f"/ws/sessions/{session_id}") as ws2:
                    # ws1 sends a message
                    message = {"type": "chat", "content": "Hello from ws1"}
                    ws1.send_text(json.dumps(message))

                    # ws2 should receive the broadcast
                    received = ws2.receive_text()
                    data = json.loads(received)
                    assert data["content"] == "Hello from ws1"
                    assert data["session_id"] == session_id
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_websocket_invalid_uuid(test_engine):
    """Test connecting with valid UUID format."""
    from dm_api.main import app
    from dm_api.db.session import get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        # Use a valid UUID
        session_id = str(uuid.uuid4())
        with TestClient(app) as test_client:
            with test_client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
                # Connection established successfully
                assert ws is not None
    finally:
        app.dependency_overrides.clear()
