"""Tests for the character-creation API (engine-backed options + build)."""

import uuid

import pytest

FIGHTER_BUILD = {
    "name": "Roderick",
    "character_class": "Fighter",
    "species": "Human",
    "background": "Soldier",
    "ability_scores": {
        "strength": 15,
        "dexterity": 14,
        "constitution": 13,
        "intelligence": 12,
        "wisdom": 10,
        "charisma": 8,
    },
    "skill_choices": ["athletics", "perception"],
    "armor_name": "Chain Mail",
    "shield": True,
    "alignment": "Lawful Good",
}


@pytest.mark.asyncio
async def test_creation_options(client):
    r = await client.get("/api/characters/creation/options")
    assert r.status_code == 200
    data = r.json()

    assert len(data["classes"]) == 13
    assert len(data["species"]) == 9
    assert len(data["backgrounds"]) == 16
    assert len(data["skills"]) == 18
    assert data["standard_array"] == [15, 14, 13, 12, 10, 8]
    assert data["point_buy_budget"] == 27
    assert data["point_buy_costs"]["15"] == 9

    fighter = next(c for c in data["classes"] if c["character_class"] == "Fighter")
    assert fighter["hit_die"] == 10
    assert fighter["num_skill_choices"] == 2
    assert fighter["spellcasting"] is False

    soldier = next(b for b in data["backgrounds"] if b["background"] == "Soldier")
    assert soldier["origin_feat"] == "Savage Attacker"
    assert "athletics" in soldier["skill_proficiencies"]

    # Shield is a flag on the build request, not an armor choice.
    assert all(a["armor_type"] != "shield" for a in data["armor"])


@pytest.mark.asyncio
async def test_build_fighter(client, world_id):
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": world_id, **FIGHTER_BUILD},
    )
    assert r.status_code == 201
    data = r.json()
    char = data["character"]

    assert char["world_id"] == world_id
    assert char["type"] == "PC"
    assert char["name"] == "Roderick"
    assert char["race"] == "Human"
    assert char["char_class"] == "Fighter"
    assert char["level"] == 1
    assert char["alignment"] == "Lawful Good"
    # HP: d10 (10) + CON mod (13 → +1) = 11.
    assert char["hp_max"] == 11
    assert char["hp_current"] == 11
    # AC: Chain Mail 16 + shield 2 = 18.
    assert char["ac"] == 18
    # Stats blob is the engine sheet: class skill choices + Soldier
    # background skills + Fighter saving throws, all in "proficiencies".
    proficiencies = char["stats"]["proficiencies"]
    for skill in ("athletics", "perception", "intimidation"):
        assert skill in proficiencies
    assert char["stats"]["feats"] == ["Savage Attacker"]
    assert "Chain Mail" in char["equipment"]
    assert "Shield" in char["equipment"]
    # Fighters must still pick weapon masteries — surfaced as a warning.
    assert any("weapon masteries" in w for w in data["warnings"])

    # The built character is visible through the regular characters API.
    r = await client.get(f"/api/characters/{char['id']}")
    assert r.status_code == 200
    assert r.json()["hp_max"] == 11


@pytest.mark.asyncio
async def test_build_off_list_skill_warns(client, world_id):
    r = await client.post(
        "/api/characters/creation/build",
        json={
            "world_id": world_id,
            **FIGHTER_BUILD,
            "skill_choices": ["arcana", "athletics"],  # arcana is not a Fighter skill
        },
    )
    assert r.status_code == 201
    assert any("arcana" in w for w in r.json()["warnings"])


@pytest.mark.asyncio
async def test_build_unknown_world_404(client):
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": str(uuid.uuid4()), **FIGHTER_BUILD},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_build_invalid_class_422(client, world_id):
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": world_id, **FIGHTER_BUILD, "character_class": "Bloodhunter"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_build_out_of_range_score_422(client, world_id):
    bad_scores = {**FIGHTER_BUILD["ability_scores"], "strength": 25}
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": world_id, **FIGHTER_BUILD, "ability_scores": bad_scores},
    )
    assert r.status_code == 422
