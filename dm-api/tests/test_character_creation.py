"""Tests for the character-creation API (engine-backed options + build)."""

import uuid
from unittest.mock import AsyncMock, patch

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
    # Fighter gets 3 weapon masteries at level 1.
    assert fighter["weapon_mastery_count"] == 3

    barbarian = next(c for c in data["classes"] if c["character_class"] == "Barbarian")
    assert barbarian["weapon_mastery_count"] == 2

    rogue = next(c for c in data["classes"] if c["character_class"] == "Rogue")
    assert rogue["weapon_mastery_count"] == 2

    wizard = next(c for c in data["classes"] if c["character_class"] == "Wizard")
    assert wizard["weapon_mastery_count"] == 0

    # Weapon mastery options include every weapon (sorted by category, then name).
    options = data["weapon_mastery_options"]
    assert len(options) > 0
    names = [o["name"] for o in options]
    assert "Greatsword" in names
    assert "Dagger" in names
    # Each option has required fields.
    greatsword = next(o for o in options if o["name"] == "Greatsword")
    assert greatsword["category"] == "martial"
    assert greatsword["mastery_property"] == "graze"
    assert greatsword["is_melee"] is True

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
    # No weapon_masteries in FIGHTER_BUILD → warning emitted.
    assert any("weapon masteries" in w for w in data["warnings"])
    # The warning is human-facing: no internal field paths leak to the user.
    assert not any("sheet.weapon_masteries" in w for w in data["warnings"])
    # Sheet should have empty masteries list (deferred).
    assert char["stats"]["weapon_masteries"] == []

    # The built character is visible through the regular characters API.
    r = await client.get(f"/api/characters/{char['id']}")
    assert r.status_code == 200
    assert r.json()["hp_max"] == 11


@pytest.mark.asyncio
async def test_build_fighter_with_masteries(client, world_id):
    """Providing weapon_masteries removes the warning and sets them on the sheet."""
    r = await client.post(
        "/api/characters/creation/build",
        json={
            "world_id": world_id,
            **FIGHTER_BUILD,
            "weapon_masteries": ["Greatsword", "Longsword", "Handaxe"],
        },
    )
    assert r.status_code == 201
    data = r.json()
    # No mastery warning when masteries are supplied.
    assert not any("weapon masteri" in w for w in data["warnings"])
    assert data["character"]["stats"]["weapon_masteries"] == [
        "Greatsword",
        "Longsword",
        "Handaxe",
    ]


@pytest.mark.asyncio
async def test_build_fighter_wrong_mastery_count_warns(client, world_id):
    """Supplying the wrong number of masteries produces a warning but still builds."""
    r = await client.post(
        "/api/characters/creation/build",
        json={
            "world_id": world_id,
            **FIGHTER_BUILD,
            "weapon_masteries": ["Greatsword"],  # Fighter expects 3
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert any("expects 3" in w for w in data["warnings"])
    assert data["character"]["stats"]["weapon_masteries"] == ["Greatsword"]


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
async def test_build_with_session_broadcasts_roster_update(client, world_id):
    """Building inside a session broadcasts an entity_update so players sync."""
    r = await client.post("/api/sessions/", json={"world_id": world_id, "name": "S"})
    session_id = r.json()["id"]

    with patch(
        "dm_api.api.character_creation.broadcast_entity_update", new_callable=AsyncMock
    ) as mock_bcast:
        r = await client.post(
            "/api/characters/creation/build",
            json={"world_id": world_id, "session_id": session_id, **FIGHTER_BUILD},
        )
    assert r.status_code == 201
    char_id = r.json()["character"]["id"]
    mock_bcast.assert_awaited_once()
    args = mock_bcast.await_args.args
    assert str(args[0]) == session_id
    assert args[1] == "character"
    assert str(args[2]) == char_id


@pytest.mark.asyncio
async def test_build_without_session_does_not_broadcast(client, world_id):
    """No session id → no roster broadcast (nothing to notify)."""
    with patch(
        "dm_api.api.character_creation.broadcast_entity_update", new_callable=AsyncMock
    ) as mock_bcast:
        r = await client.post(
            "/api/characters/creation/build",
            json={"world_id": world_id, **FIGHTER_BUILD},
        )
    assert r.status_code == 201
    mock_bcast.assert_not_awaited()


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
