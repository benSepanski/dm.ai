"""Tests for the combat API endpoints: lifecycle, initiative, actions, turns."""

import uuid

import pytest
from game_engine.types import ActionType

from tests.combat_helpers import _create_character, _create_session, _create_statless_npc

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


@pytest.mark.asyncio
async def test_end_combat_writes_system_summary_message(client, world_id):
    """Ending combat appends a SYSTEM chat message with the mechanical outcome
    so the AI DM (which never sees the combat log) doesn't confabulate the
    result when narration resumes."""
    session_id = await _create_session(client, world_id)
    char_id = await _create_character(client, world_id, name="Borin", hp=24)

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201

    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.status_code == 200
    messages = r.json()
    assert len(messages) == 1
    summary = messages[0]
    assert summary["role"] == "system"
    assert "Combat ended" in summary["content"]
    assert "Borin: 24/24 HP" in summary["content"]


@pytest.mark.asyncio
async def test_end_combat_without_combatants_writes_no_summary(client, world_id):
    """Silent on success: an empty combat produces no system chatter."""
    session_id = await _create_session(client, world_id)
    await client.post(f"/api/sessions/{session_id}/combat")
    r = await client.put(f"/api/sessions/{session_id}/combat/end")
    assert r.status_code == 200

    r = await client.get(f"/api/sessions/{session_id}/messages")
    assert r.json() == []


async def test_start_combat_rejects_statless_characters(client, world_id):
    """Characters created from AI proposals (null hp/ac) are rejected loudly
    instead of entering combat as silent 10 HP / AC 10 placeholders."""
    session_id = await _create_session(client, world_id)
    pc_id = await _create_character(client, world_id, name="Borin")
    npc_id = await _create_statless_npc(client, world_id, name="Cutter Voss")

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [pc_id, npc_id]},
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "Cutter Voss" in detail
    assert "Borin" not in detail
    assert "PATCH /api/characters/" in detail

    # No combat was created.
    r = await client.get(f"/api/sessions/{session_id}/combat")
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
    """An action from a non-combatant is a client error and must NOT pollute
    the combat log (regression: this used to return 200 and append a permanent
    actor_not_found row)."""
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
    assert r.status_code == 404
    assert "Actor" in r.json()["detail"]

    # The combat log stays clean.
    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert r.json()["combat_log"] in (None, [])


@pytest.mark.asyncio
async def test_submit_combat_action_unknown_target_is_404(client, world_id):
    """A valid actor attacking a bogus target id is rejected up front."""
    session_id = await _create_session(client, world_id)
    attacker_id = await _create_character(client, world_id, name="Attacker")

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [attacker_id]},
    )
    assert r.status_code == 201

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": attacker_id,
            "action_type": ActionType.ATTACK.value,
            "target_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert r.status_code == 404
    assert "Target" in r.json()["detail"]


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
