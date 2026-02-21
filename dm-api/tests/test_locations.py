"""Tests for the locations API endpoints."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_create_location(client, world_id):
    r = await client.post(
        "/api/locations/",
        json={
            "world_id": world_id,
            "type": "town",
            "name": "Rivendell",
            "description": "An elven outpost",
            "lore": "Home of Lord Elrond",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Rivendell"
    assert data["type"] == "town"
    assert data["world_id"] == world_id
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_location_minimal(client, world_id):
    r = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "room", "name": "Dark Cave"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Dark Cave"
    assert data["description"] is None


@pytest.mark.asyncio
async def test_create_location_with_parent(client, world_id):
    # Create parent location
    r = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "town", "name": "ParentTown"},
    )
    assert r.status_code == 201
    parent_id = r.json()["id"]

    # Create child location
    r = await client.post(
        "/api/locations/",
        json={
            "world_id": world_id,
            "type": "building",
            "name": "The Inn",
            "parent_id": parent_id,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_get_location(client, world_id):
    r = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "dungeon", "name": "Moria"},
    )
    assert r.status_code == 201
    loc_id = r.json()["id"]

    r = await client.get(f"/api/locations/{loc_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == loc_id
    assert data["name"] == "Moria"


@pytest.mark.asyncio
async def test_get_location_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/locations/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Location not found"


@pytest.mark.asyncio
async def test_patch_location(client, world_id):
    r = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "wilderness", "name": "Forest"},
    )
    assert r.status_code == 201
    loc_id = r.json()["id"]

    r = await client.patch(
        f"/api/locations/{loc_id}",
        json={"description": "A deep, dark forest"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "A deep, dark forest"


@pytest.mark.asyncio
async def test_delete_location(client, world_id):
    r = await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "room", "name": "ToDelete"},
    )
    assert r.status_code == 201
    loc_id = r.json()["id"]

    r = await client.delete(f"/api/locations/{loc_id}")
    assert r.status_code == 204

    r = await client.get(f"/api/locations/{loc_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_world_locations_populated(client, world_id):
    # Create a location in the world
    await client.post(
        "/api/locations/",
        json={"world_id": world_id, "type": "town", "name": "Bree"},
    )

    r = await client.get(f"/api/worlds/{world_id}/locations")
    assert r.status_code == 200
    names = [loc["name"] for loc in r.json()]
    assert "Bree" in names
