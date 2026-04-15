"""Tests for the worlds API endpoints."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_create_world(client):
    r = await client.post(
        "/api/worlds/",
        json={
            "name": "Middle Earth",
            "setting_description": "A high fantasy world",
            "themes": [{"name": "adventure"}],
            "lore_summary": "Hobbits, elves, and dark lords.",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Middle Earth"
    assert data["setting_description"] == "A high fantasy world"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_world_minimal(client):
    r = await client.post("/api/worlds/", json={"name": "Minimal World"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Minimal World"
    assert data["setting_description"] is None
    assert data["themes"] is None
    assert data["lore_summary"] is None


@pytest.mark.asyncio
async def test_get_world(client, world_id):
    r = await client.get(f"/api/worlds/{world_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == world_id
    assert data["name"] == "Test World"


@pytest.mark.asyncio
async def test_get_world_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/worlds/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "World not found"


@pytest.mark.asyncio
async def test_get_world_locations_empty(client, world_id):
    r = await client.get(f"/api/worlds/{world_id}/locations")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_world_locations_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/worlds/{fake_id}/locations")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_world(client):
    # Create a world
    r = await client.post("/api/worlds/", json={"name": "ToDelete"})
    assert r.status_code == 201
    wid = r.json()["id"]

    # Delete it
    r = await client.delete(f"/api/worlds/{wid}")
    assert r.status_code == 204

    # Verify it's gone
    r = await client.get(f"/api/worlds/{wid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_world_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.delete(f"/api/worlds/{fake_id}")
    assert r.status_code == 404
