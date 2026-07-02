"""Tests for the sessions API endpoints: create/get/end lifecycle + location patch.

Split from a larger ``test_sessions.py`` (file-length guideline); chat and
proposal-gated-narration tests live in ``test_sessions_chat.py``.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_create_session(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={
            "world_id": world_id,
            "name": "Adventure Begins",
            "rule_engine_version": "dnd_5_5e",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Adventure Begins"
    assert data["world_id"] == world_id
    assert data["rule_engine_version"] == "dnd_5_5e"
    assert data["ended_at"] is None
    assert "id" in data
    assert "started_at" in data


@pytest.mark.asyncio
async def test_create_session_minimal(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Quick Session"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Quick Session"
    assert data["rule_engine_version"] == "dnd_5_5e"


@pytest.mark.asyncio
async def test_get_session(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Test Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    r = await client.get(f"/api/sessions/{session_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == session_id
    assert data["name"] == "Test Session"


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/sessions/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_get_session_messages_empty(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Empty Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_end_session(client, world_id):
    """Test ending a session — mock the AI backend to avoid real API calls."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Session To End"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Mock the AI orchestrator so it doesn't make real Anthropic calls
    mock_orchestrator = MagicMock()
    mock_orchestrator.summarize = AsyncMock(return_value="A brief adventure summary.")

    with patch("dm_api.api.sessions.DMOrchestrator", return_value=mock_orchestrator):
        r = await client.put(f"/api/sessions/{session_id}/end")

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == session_id
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_session_no_messages(client, world_id):
    """End a session with no chat history — should not call summarize."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Empty Session To End"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # No messages means no summarize call needed
    r = await client.put(f"/api/sessions/{session_id}/end")
    assert r.status_code == 200
    data = r.json()
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_session_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.put(f"/api/sessions/{fake_id}/end")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_session_sets_location(client, world_id):
    """PATCH /sessions/{id} with current_location_id updates the session location."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Location Test Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Create a location first.
    r = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "town", "name": "Testtown"},
    )
    assert r.status_code == 201
    loc_id = r.json()["id"]

    r = await client.patch(
        f"/api/sessions/{session_id}",
        json={"current_location_id": loc_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["current_location_id"] == loc_id


@pytest.mark.asyncio
async def test_patch_session_location_wrong_world_is_404(client, world_id):
    """PATCH with a location from a different world returns 404."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Another Session"},
    )
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Create a second world and a location in it.
    r2 = await client.post("/api/worlds/", json={"name": "Other World"})
    assert r2.status_code == 201
    other_world_id = r2.json()["id"]
    r3 = await client.post(
        "/api/locations/",
        json={"world_id": other_world_id, "type": "town", "name": "Wrongtown"},
    )
    assert r3.status_code == 201
    other_loc_id = r3.json()["id"]

    r = await client.patch(
        f"/api/sessions/{session_id}",
        json={"current_location_id": other_loc_id},
    )
    assert r.status_code == 404
    assert "Location not found" in r.json()["detail"]


@pytest.mark.asyncio
async def test_patch_session_not_found(client):
    """PATCH /sessions/{id} with a non-existent session returns 404."""
    r = await client.patch(
        f"/api/sessions/{uuid.uuid4()}",
        json={"current_location_id": None},
    )
    assert r.status_code == 404
