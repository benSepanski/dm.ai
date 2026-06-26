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
            "themes": ["adventure", "found family"],
            "lore_summary": "Hobbits, elves, and dark lords.",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Middle Earth"
    assert data["setting_description"] == "A high fantasy world"
    assert data["themes"] == ["adventure", "found family"]
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


# ---------------------------------------------------------------------------
# PATCH /api/worlds/{world_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_world_updates_name(client, world_id):
    r = await client.patch(f"/api/worlds/{world_id}", json={"name": "Renamed World"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == world_id
    assert data["name"] == "Renamed World"


@pytest.mark.asyncio
async def test_patch_world_updates_lore_summary(client, world_id):
    """DMs update lore_summary as the campaign reveals new facts."""
    r = await client.patch(
        f"/api/worlds/{world_id}",
        json={"lore_summary": "The Serpent Crown lies beneath the ocean."},
    )
    assert r.status_code == 200
    assert r.json()["lore_summary"] == "The Serpent Crown lies beneath the ocean."


@pytest.mark.asyncio
async def test_patch_world_partial_leaves_other_fields_unchanged(client):
    r = await client.post(
        "/api/worlds/",
        json={
            "name": "Full World",
            "setting_description": "A lush jungle world.",
            "lore_summary": "Ancient ruins dot the landscape.",
            "themes": ["exploration", "mystery"],
        },
    )
    assert r.status_code == 201
    wid = r.json()["id"]

    r = await client.patch(f"/api/worlds/{wid}", json={"name": "Renamed Full World"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Renamed Full World"
    assert data["setting_description"] == "A lush jungle world."
    assert data["lore_summary"] == "Ancient ruins dot the landscape."
    assert data["themes"] == ["exploration", "mystery"]


@pytest.mark.asyncio
async def test_patch_world_clears_optional_field(client):
    """Passing null for an optional field clears it."""
    r = await client.post(
        "/api/worlds/",
        json={"name": "Lore World", "lore_summary": "Dragons once ruled."},
    )
    assert r.status_code == 201
    wid = r.json()["id"]

    r = await client.patch(f"/api/worlds/{wid}", json={"lore_summary": None})
    assert r.status_code == 200
    assert r.json()["lore_summary"] is None


@pytest.mark.asyncio
async def test_patch_world_not_found(client):
    r = await client.patch(f"/api/worlds/{uuid.uuid4()}", json={"name": "Ghost"})
    assert r.status_code == 404
    assert r.json()["detail"] == "World not found"


@pytest.mark.asyncio
async def test_patch_world_requires_dm(client):
    r = await client.post("/api/worlds/", json={"name": "Test"})
    assert r.status_code == 201
    wid = r.json()["id"]

    from httpx import AsyncClient

    player_client = AsyncClient(transport=client._transport, base_url=client.base_url, headers={})
    r = await player_client.patch(f"/api/worlds/{wid}", json={"name": "Hacked"})
    assert r.status_code == 403
