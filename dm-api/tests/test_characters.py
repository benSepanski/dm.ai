"""Tests for the characters API endpoints."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_create_character_pc(client, world_id):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Gandalf",
            "race": "Maia",
            "char_class": "Wizard",
            "level": 20,
            "hp_current": 150,
            "hp_max": 150,
            "ac": 18,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Gandalf"
    assert data["type"] == "PC"
    assert data["world_id"] == world_id
    assert data["level"] == 20
    assert data["hp_current"] == 150
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_character_npc(client, world_id):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "NPC",
            "name": "Innkeeper Bob",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "NPC"
    assert data["name"] == "Innkeeper Bob"


@pytest.mark.asyncio
async def test_create_character_monster(client, world_id):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "MONSTER",
            "name": "Dragon",
            "hp_current": 300,
            "hp_max": 300,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "MONSTER"


@pytest.mark.asyncio
async def test_get_character(client, world_id):
    # Create first
    r = await client.post(
        "/api/characters/",
        json={"world_id": world_id, "type": "PC", "name": "Aragorn"},
    )
    assert r.status_code == 201
    char_id = r.json()["id"]

    # Get it
    r = await client.get(f"/api/characters/{char_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == char_id
    assert data["name"] == "Aragorn"


@pytest.mark.asyncio
async def test_get_character_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/characters/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Character not found"


@pytest.mark.asyncio
async def test_patch_character_hp(client, world_id):
    # Create
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Frodo",
            "hp_current": 30,
            "hp_max": 30,
        },
    )
    assert r.status_code == 201
    char_id = r.json()["id"]

    # Update hp_current
    r = await client.patch(
        f"/api/characters/{char_id}",
        json={"hp_current": 15},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["hp_current"] == 15
    assert data["hp_max"] == 30  # unchanged


@pytest.mark.asyncio
async def test_patch_character_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.patch(f"/api/characters/{fake_id}", json={"hp_current": 10})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_world_characters(client, world_id):
    # Create two characters
    for name in ["Legolas", "Gimli"]:
        r = await client.post(
            "/api/characters/",
            json={"world_id": world_id, "type": "PC", "name": name},
        )
        assert r.status_code == 201

    r = await client.get(f"/api/characters/world/{world_id}")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "Legolas" in names
    assert "Gimli" in names
