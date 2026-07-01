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

ELF_WIZARD_BUILD = {
    "name": "Maret Sable",
    "character_class": "Wizard",
    "species": "Elf",
    "background": "Sage",
    "ability_scores": {
        "strength": 8,
        "dexterity": 14,
        "constitution": 13,
        "intelligence": 15,
        "wisdom": 12,
        "charisma": 10,
    },
    "skill_choices": ["arcana", "investigation"],
    "species_trait_choices": {"Elven Lineage": "Drow", "Keen Senses": "perception"},
    "starting_cantrips": ["Fire Bolt", "Light", "Acid Splash"],
    "starting_spells": ["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
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

    # PT-19: classes expose their level-1 cantrip/spell counts.
    assert wizard["cantrips_known"] == 3
    assert wizard["prepared_spells_known"] == 4
    assert fighter["cantrips_known"] == 0
    assert fighter["prepared_spells_known"] == 0

    # PT-19: Elf's choice-bearing traits (Elven Lineage, Keen Senses) expose
    # their closed option sets; non-choice traits (Fey Ancestry, Trance) don't.
    elf = next(s for s in data["species"] if s["species"] == "Elf")
    lineage_trait = next(t for t in elf["traits"] if t["name"] == "Elven Lineage")
    assert set(lineage_trait["choice"]["lineage_options"]) == {"Drow", "High Elf", "Wood Elf"}
    keen_senses_trait = next(t for t in elf["traits"] if t["name"] == "Keen Senses")
    assert set(keen_senses_trait["choice"]["skill_options"]) == {
        "insight",
        "perception",
        "survival",
    }
    fey_ancestry_trait = next(t for t in elf["traits"] if t["name"] == "Fey Ancestry")
    assert fey_ancestry_trait["choice"] is None

    # PT-19: level-1 spells/cantrips are enumerated so the UI can build pickers.
    spell_names = [s["name"] for s in data["spells"]]
    assert "Fire Bolt" in spell_names
    assert "Magic Missile" in spell_names
    assert all(s["level"] <= 1 for s in data["spells"])


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


@pytest.mark.asyncio
async def test_build_rejects_scores_unachievable_by_any_generation_method(client, world_id):
    # PT-26: all-20s passes the per-field 3-20 bound but isn't reachable by
    # Standard Array, Point Buy, or Manual/Rolled (max 18) generation.
    all_twenties = {
        "strength": 20,
        "dexterity": 20,
        "constitution": 20,
        "intelligence": 20,
        "wisdom": 20,
        "charisma": 20,
    }
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": world_id, **FIGHTER_BUILD, "ability_scores": all_twenties},
    )
    assert r.status_code == 422
    assert "Standard Array" in r.json()["detail"]


@pytest.mark.asyncio
async def test_build_elf_wizard_persists_lineage_keen_senses_and_spells(client, world_id):
    """PT-19: species sub-choices and starting cantrips/spells reach the sheet."""
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": world_id, **ELF_WIZARD_BUILD},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["warnings"] == []
    stats = data["character"]["stats"]
    assert stats["species_lineage"] == "Drow"
    assert "perception" in stats["proficiencies"]
    assert stats["known_spells"] == ["Fire Bolt", "Light", "Acid Splash"]
    assert stats["prepared_spells"] == [
        "Magic Missile",
        "Shield",
        "Mage Armor",
        "Detect Magic",
    ]


@pytest.mark.asyncio
async def test_build_illegal_lineage_choice_422(client, world_id):
    """The backend must reject a lineage that isn't a real Elven Lineage option."""
    r = await client.post(
        "/api/characters/creation/build",
        json={
            "world_id": world_id,
            **ELF_WIZARD_BUILD,
            "species_trait_choices": {"Elven Lineage": "Sun Elf", "Keen Senses": "perception"},
        },
    )
    assert r.status_code == 422
    assert "Elven Lineage" in r.json()["detail"]


@pytest.mark.asyncio
async def test_build_illegal_cantrip_for_class_422(client, world_id):
    """The backend must reject a cantrip not on that class's level-1 list,
    never trusting the client-submitted spell name blindly."""
    r = await client.post(
        "/api/characters/creation/build",
        json={
            "world_id": world_id,
            **ELF_WIZARD_BUILD,
            "starting_cantrips": ["Guidance", "Light", "Acid Splash"],
        },
    )
    assert r.status_code == 422
    assert "Guidance" in r.json()["detail"]


@pytest.mark.asyncio
async def test_build_missing_species_and_spell_choices_warns(client, world_id):
    """Omitting the sub-choices still builds (deferred), with warnings — matching
    the existing weapon-masteries warning pattern rather than failing the build."""
    minimal = {**ELF_WIZARD_BUILD}
    del minimal["species_trait_choices"]
    del minimal["starting_cantrips"]
    del minimal["starting_spells"]
    r = await client.post(
        "/api/characters/creation/build",
        json={"world_id": world_id, **minimal},
    )
    assert r.status_code == 201
    warnings = r.json()["warnings"]
    assert any("Elven Lineage requires a choice" in w for w in warnings)
    assert any("Keen Senses requires a choice" in w for w in warnings)
    assert any("starting cantrip" in w for w in warnings)
    assert any("starting spell" in w for w in warnings)
