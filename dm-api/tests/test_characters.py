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
async def test_create_character_rejects_negative_hp(client, world_id):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "MONSTER",
            "name": "Test Illegal Monster",
            "hp_max": -10,
            "hp_current": -10,
            "ac": 0,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_character_rejects_negative_hp(client, world_id):
    r = await client.post(
        "/api/characters/",
        json={"world_id": world_id, "type": "MONSTER", "name": "Ogre"},
    )
    char_id = r.json()["id"]

    r = await client.patch(f"/api/characters/{char_id}", json={"hp_max": -5, "ac": 0})
    assert r.status_code == 422


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


@pytest.mark.asyncio
async def test_list_world_characters_world_not_found(client):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/characters/world/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "World not found"


# ---------------------------------------------------------------------------
# PATCH semantics — stats merge + write-through to active combat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_stats_merges_instead_of_replacing(client, world_id):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Kira",
            "char_class": "Wizard",
            "level": 3,
            "hp_current": 14,
            "hp_max": 14,
            "ac": 12,
            "stats": {"ability_scores": {"intelligence": 16, "dexterity": 14}},
        },
    )
    char_id = r.json()["id"]

    r = await client.patch(
        f"/api/characters/{char_id}",
        json={"stats": {"conditions": ["poisoned"]}},
    )
    assert r.status_code == 200
    stats = r.json()["stats"]
    assert stats["conditions"] == ["poisoned"]
    # The previously-set keys survive the partial update.
    assert stats["ability_scores"]["intelligence"] == 16

    # A key set to null is removed.
    r = await client.patch(f"/api/characters/{char_id}", json={"stats": {"conditions": None}})
    assert "conditions" not in r.json()["stats"]
    assert r.json()["stats"]["ability_scores"]["intelligence"] == 16


@pytest.mark.asyncio
async def test_patch_writes_through_to_active_combat(client, world_id):
    from tests.combat_helpers import _create_character, _create_session

    char_id = await _create_character(client, world_id, name="Dorn", hp=20)
    session_id = await _create_session(client, world_id)
    r = await client.post(f"/api/sessions/{session_id}/combat", json={"character_ids": [char_id]})
    assert r.status_code == 201

    r = await client.patch(f"/api/characters/{char_id}", json={"hp_current": 5, "ac": 18})
    assert r.status_code == 200

    # The live combat snapshot reflects the patch …
    r = await client.get(f"/api/sessions/{session_id}/combat")
    combatant = r.json()["combatants"][0]
    assert combatant["hp_current"] == 5
    assert combatant["ac"] == 18

    # … and ending combat does NOT write the stale snapshot over it.
    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200
    r = await client.get(f"/api/characters/{char_id}")
    assert r.json()["hp_current"] == 5


# ---------------------------------------------------------------------------
# Rests
# ---------------------------------------------------------------------------


async def _create_resting_wizard(client, world_id, *, hp_current=5, hp_max=14):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Kira",
            "char_class": "Wizard",
            "level": 3,
            "hp_current": hp_current,
            "hp_max": hp_max,
            "ac": 12,
            "stats": {
                "ability_scores": {"intelligence": 16, "constitution": 14},
                "spell_slots": [
                    {"slot_level": 1, "maximum": 4, "remaining": 0},
                    {"slot_level": 2, "maximum": 2, "remaining": 1},
                ],
            },
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_long_rest_restores_hp_and_spell_slots(client, world_id):
    char_id = await _create_resting_wizard(client, world_id)

    r = await client.post(f"/api/characters/{char_id}/rest", json={"rest_type": "long"})
    assert r.status_code == 200
    data = r.json()
    assert data["rest_type"] == "long"
    assert data["hp_restored"] == 9
    assert data["slots_restored"] is True
    assert data["character"]["hp_current"] == 14
    slots = {s["slot_level"]: s["remaining"] for s in data["character"]["stats"]["spell_slots"]}
    assert slots == {1: 4, 2: 2}


@pytest.mark.asyncio
async def test_short_rest_spends_hit_dice(client, world_id):
    char_id = await _create_resting_wizard(client, world_id, hp_current=1)

    r = await client.post(
        f"/api/characters/{char_id}/rest",
        json={"rest_type": "short", "hit_dice_to_spend": 2},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["hit_dice_spent"] == 2
    # 2d6 + CON(+2) each, floored at 0 per die — always at least some healing.
    assert data["hp_restored"] >= 1
    assert data["character"]["hp_current"] > 1
    # A level-3 wizard has 3 hit dice; 2 were spent.
    pools = data["character"]["stats"]["hit_dice"]
    assert pools[0]["remaining"] == 1


@pytest.mark.asyncio
async def test_rest_during_active_combat_is_409(client, world_id):
    from tests.combat_helpers import _create_character, _create_session

    char_id = await _create_character(client, world_id, name="Dorn")
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat", json={"character_ids": [char_id]})

    r = await client.post(f"/api/characters/{char_id}/rest", json={"rest_type": "long"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_rest_character_not_found(client):
    r = await client.post(f"/api/characters/{uuid.uuid4()}/rest", json={"rest_type": "long"})
    assert r.status_code == 404
