"""Tests for the combat API endpoints."""

import uuid

import pytest


async def _create_session(client, world_id):
    """Helper to create a session and return its ID."""
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Combat Session"},
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_start_combat(client, world_id):
    session_id = await _create_session(client, world_id)

    r = await client.post(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 201
    data = r.json()
    assert data["session_id"] == session_id
    assert data["ended_at"] is None
    assert data["round_number"] == 1
    assert data["current_turn_index"] == 0
    assert "id" in data


@pytest.mark.asyncio
async def test_start_combat_session_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.post(f"/api/sessions/{fake_id}/combat")
    assert r.status_code == 404
    assert r.json()["detail"] == "Session not found"


@pytest.mark.asyncio
async def test_start_combat_conflict(client, world_id):
    """Starting a second combat when one is active should return 409."""
    session_id = await _create_session(client, world_id)

    # Start first combat
    r = await client.post(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 201

    # Try to start another
    r = await client.post(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_get_combat(client, world_id):
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == session_id
    assert data["ended_at"] is None


@pytest.mark.asyncio
async def test_get_combat_not_found(client, world_id):
    session_id = await _create_session(client, world_id)
    # No combat started
    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 404
    assert r.json()["detail"] == "No active combat for this session"


@pytest.mark.asyncio
async def test_end_combat(client, world_id):
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200
    data = r.json()
    assert data["ended_at"] is not None


@pytest.mark.asyncio
async def test_end_combat_not_found(client, world_id):
    session_id = await _create_session(client, world_id)
    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submit_combat_action(client, world_id):
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": "char-001",
            "action_type": "attack",
            "target_id": "enemy-001",
        },
    )
    assert r.status_code == 200
    data = r.json()
    # combat_log should have one entry
    assert data["combat_log"] is not None
    assert len(data["combat_log"]) == 1
    assert data["combat_log"][0]["actor_id"] == "char-001"
    assert data["combat_log"][0]["action_type"] == "attack"


@pytest.mark.asyncio
async def test_submit_combat_action_no_active_combat(client, world_id):
    session_id = await _create_session(client, world_id)
    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={"actor_id": "char-001", "action_type": "attack"},
    )
    assert r.status_code == 404
