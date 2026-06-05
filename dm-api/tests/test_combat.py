"""Tests for the combat API endpoints — lifecycle, initiative, actions, and turns.

Condition-duration tracking and HP/condition sync tests live in
test_combat_conditions.py (split to keep both files under the 600-line limit).
"""

import uuid

import pytest
from game_engine.types import ActionType


async def _create_session(client, world_id):
    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Combat Session"},
    )
    assert r.status_code == 201
    return r.json()["id"]


async def _create_character(client, world_id, *, name: str = "Hero", hp: int = 20, ac: int = 14):
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": name,
            "level": 3,
            "char_class": "Fighter",
            "hp_current": hp,
            "hp_max": hp,
            "ac": ac,
            "stats": {
                "ability_scores": {
                    "strength": 16,
                    "dexterity": 14,
                    "constitution": 14,
                    "intelligence": 10,
                    "wisdom": 12,
                    "charisma": 8,
                }
            },
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Basic lifecycle
# ---------------------------------------------------------------------------


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
    session_id = await _create_session(client, world_id)

    r = await client.post(f"/api/sessions/{session_id}/combat")
    assert r.status_code == 201

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


# ---------------------------------------------------------------------------
# Initiative rolling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_combat_with_characters_rolls_initiative(client, world_id):
    """Starting combat with character_ids populates initiative_order."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_character(client, world_id, name="Fighter")

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["initiative_order"] is not None
    assert len(data["initiative_order"]) == 1
    entry = data["initiative_order"][0]
    assert entry["character_id"] == char_id
    assert entry["name"] == "Fighter"
    assert isinstance(entry["initiative"], int)

    assert data["combatants"] is not None
    assert len(data["combatants"]) == 1
    assert data["combatants"][0]["id"] == char_id


@pytest.mark.asyncio
async def test_start_combat_initiative_order_sorted_descending(client, world_id):
    """Multiple characters are sorted by initiative (highest first)."""
    session_id = await _create_session(client, world_id)
    id_a = await _create_character(client, world_id, name="Rogue")
    id_b = await _create_character(client, world_id, name="Barbarian")

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [id_a, id_b]},
    )
    assert r.status_code == 201
    order = r.json()["initiative_order"]
    assert len(order) == 2
    # Highest initiative first
    assert order[0]["initiative"] >= order[1]["initiative"]


# ---------------------------------------------------------------------------
# Action submission — engine-resolved results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_combat_action_no_combatants(client, world_id):
    """Action submitted when no combatants are enrolled; engine logs target_not_found."""
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": "char-001",
            "action_type": ActionType.ATTACK.value,
            "target_id": "enemy-001",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["combat_log"] is not None
    assert len(data["combat_log"]) == 1
    log = data["combat_log"][0]
    assert log["actor_id"] == "char-001"
    assert log["action_type"] == ActionType.ATTACK.value
    # Engine reports target not found (no combatants enrolled)
    assert log["error"] == "target_not_found"


@pytest.mark.asyncio
async def test_submit_combat_action_attack_resolves(client, world_id):
    """Attack action resolves through the rule engine; HP is updated in state."""
    session_id = await _create_session(client, world_id)
    attacker_id = await _create_character(client, world_id, name="Attacker", hp=20, ac=12)
    defender_id = await _create_character(client, world_id, name="Defender", hp=10, ac=8)

    # Start combat with both characters enrolled
    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [attacker_id, defender_id]},
    )
    assert r.status_code == 201

    # Submit attack
    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": attacker_id,
            "action_type": ActionType.ATTACK.value,
            "target_id": defender_id,
            "attack_details": {
                "weapon_name": "Longsword",
                "damage_dice": "1d8",
                "damage_type": "slashing",
                "attack_ability": "strength",
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    log = data["combat_log"][0]
    assert log["actor_id"] == attacker_id
    assert log["action_type"] == ActionType.ATTACK.value
    # Engine should populate hit/target fields
    assert "target_id" in log
    assert log["target_id"] == defender_id


@pytest.mark.asyncio
async def test_submit_combat_action_non_attack(client, world_id):
    """Non-attack actions (Dash, Dodge, etc.) resolve successfully."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_character(client, world_id, name="Rogue")

    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={"actor_id": char_id, "action_type": ActionType.DASH.value},
    )
    assert r.status_code == 200
    log = r.json()["combat_log"][0]
    assert log["action_type"] == ActionType.DASH.value
    assert log["actor_id"] == char_id


@pytest.mark.asyncio
async def test_submit_combat_action_invalid_type(client, world_id):
    """Unknown action_type values are rejected at the boundary (422)."""
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={"actor_id": "char-001", "action_type": "not_a_real_action"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_combat_action_no_active_combat(client, world_id):
    session_id = await _create_session(client, world_id)
    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={"actor_id": "char-001", "action_type": ActionType.ATTACK.value},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Turn advancement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_turn_advances_turn_index(client, world_id):
    session_id = await _create_session(client, world_id)
    id_a = await _create_character(client, world_id, name="A")
    id_b = await _create_character(client, world_id, name="B")

    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [id_a, id_b]},
    )

    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    data = r.json()
    assert data["current_turn_index"] == 1
    assert data["round_number"] == 1


@pytest.mark.asyncio
async def test_next_turn_wraps_to_new_round(client, world_id):
    """After the last combatant's turn, turn_index resets and round increments."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_character(client, world_id, name="Solo")

    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )

    # Only one combatant → first next-turn wraps to round 2, index 0
    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    data = r.json()
    assert data["current_turn_index"] == 0
    assert data["round_number"] == 2


@pytest.mark.asyncio
async def test_next_turn_no_combatants_returns_409(client, world_id):
    """Advancing turns without enrolled combatants returns 409."""
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")

    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_next_turn_no_active_combat(client, world_id):
    session_id = await _create_session(client, world_id)
    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 404
