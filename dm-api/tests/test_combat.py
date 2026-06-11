"""Tests for the combat API endpoints: lifecycle, initiative, actions, turns."""

import uuid

import pytest
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import ActionType

from tests.combat_helpers import (
    _create_character,
    _create_dead_monster,
    _create_downed_character,
    _create_session,
    _create_statless_npc,
)

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


# ---------------------------------------------------------------------------
# Action economy — enforced across requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_second_action_same_turn_is_409(client, world_id):
    """The action economy persists between requests: one action per turn."""
    attacker_id = await _create_character(client, world_id, name="Attacker")
    defender_id = await _create_character(client, world_id, name="Defender")
    session_id = await _create_session(client, world_id)
    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [attacker_id, defender_id]},
    )

    attack = {
        "actor_id": attacker_id,
        "action_type": ActionType.ATTACK.value,
        "target_id": defender_id,
    }
    r = await client.post(f"/api/sessions/{session_id}/combat/action", json=attack)
    assert r.status_code == 200
    log_len = len(r.json()["combat_log"])

    r = await client.post(f"/api/sessions/{session_id}/combat/action", json=attack)
    assert r.status_code == 409
    assert "Action already used" in r.json()["detail"]

    # The rejected action never reaches the combat log.
    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert len(r.json()["combat_log"]) == log_len


@pytest.mark.asyncio
async def test_action_economy_resets_when_turn_comes_around(client, world_id):
    attacker_id = await _create_character(client, world_id, name="Attacker")
    defender_id = await _create_character(client, world_id, name="Defender")
    session_id = await _create_session(client, world_id)
    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [attacker_id, defender_id]},
    )

    attack = {
        "actor_id": attacker_id,
        "action_type": ActionType.ATTACK.value,
        "target_id": defender_id,
    }
    r = await client.post(f"/api/sessions/{session_id}/combat/action", json=attack)
    assert r.status_code == 200
    r = await client.post(f"/api/sessions/{session_id}/combat/action", json=attack)
    assert r.status_code == 409

    # Advance a full round so the attacker's turn begins again.
    await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    await client.post(f"/api/sessions/{session_id}/combat/next-turn")

    r = await client.post(f"/api/sessions/{session_id}/combat/action", json=attack)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_incapacitated_actor_is_409_and_keeps_log_clean(client, world_id):
    """An unconscious actor can't act; the rejection never pollutes the log."""
    downed_id = await _create_downed_character(client, world_id)
    target_id = await _create_character(client, world_id, name="Target")
    session_id = await _create_session(client, world_id)
    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [downed_id, target_id]},
    )

    r = await client.post(
        f"/api/sessions/{session_id}/combat/action",
        json={
            "actor_id": downed_id,
            "action_type": ActionType.ATTACK.value,
            "target_id": target_id,
        },
    )
    assert r.status_code == 409

    r = await client.get(f"/api/sessions/{session_id}/combat")
    assert r.json()["combat_log"] in (None, [])


# ---------------------------------------------------------------------------
# next-turn skips the dead; initiative ties break on Dexterity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_turn_skips_dead_combatant(client, world_id, monkeypatch):
    """A dead monster between two living combatants never gets a turn."""
    initiative = {"Alive A": 20, "Slain Goblin": 15, "Alive B": 10}
    monkeypatch.setattr(
        DnD55eEngine, "roll_initiative", lambda self, sheet: initiative[sheet.name]
    )
    a_id = await _create_character(client, world_id, name="Alive A")
    dead_id = await _create_dead_monster(client, world_id, name="Slain Goblin")
    b_id = await _create_character(client, world_id, name="Alive B")
    session_id = await _create_session(client, world_id)
    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [a_id, dead_id, b_id]},
    )
    assert r.status_code == 201
    assert [e["name"] for e in r.json()["initiative_order"]] == [
        "Alive A",
        "Slain Goblin",
        "Alive B",
    ]

    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    data = r.json()
    assert data["current_turn_index"] == 2  # skipped the dead goblin at index 1
    assert data["round_number"] == 1

    # Wrapping also skips: B → (skip goblin going through wrap) → A, round 2.
    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    data = r.json()
    assert data["current_turn_index"] == 0
    assert data["round_number"] == 2


@pytest.mark.asyncio
async def test_next_turn_does_not_skip_dying_combatant(client, world_id, monkeypatch):
    """Dying (not stable, not dead) combatants keep their turn — that's when
    their death save rolls."""
    initiative = {"Alive A": 20, "Sylvara": 10}
    monkeypatch.setattr(
        DnD55eEngine, "roll_initiative", lambda self, sheet: initiative[sheet.name]
    )
    a_id = await _create_character(client, world_id, name="Alive A")
    dying_id = await _create_downed_character(client, world_id, name="Sylvara")
    session_id = await _create_session(client, world_id)
    await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [a_id, dying_id]},
    )

    r = await client.post(f"/api/sessions/{session_id}/combat/next-turn")
    assert r.status_code == 200
    data = r.json()
    assert data["current_turn_index"] == 1
    assert data["combat_log"][-1]["event"] == "death_save"


@pytest.mark.asyncio
async def test_initiative_tie_broken_by_dexterity(client, world_id, monkeypatch):
    monkeypatch.setattr(DnD55eEngine, "roll_initiative", lambda self, sheet: 12)

    async def create(name, dex):
        r = await client.post(
            "/api/characters/",
            json={
                "world_id": world_id,
                "type": "PC",
                "name": name,
                "level": 1,
                "char_class": "Fighter",
                "hp_current": 10,
                "hp_max": 10,
                "ac": 14,
                "stats": {"ability_scores": {"dexterity": dex}},
            },
        )
        assert r.status_code == 201
        return r.json()["id"]

    slow_id = await create("Slowfoot", 8)
    swift_id = await create("Swift", 18)
    session_id = await _create_session(client, world_id)
    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [slow_id, swift_id]},
    )
    assert r.status_code == 201
    order = r.json()["initiative_order"]
    assert [e["name"] for e in order] == ["Swift", "Slowfoot"]
    assert order[0]["initiative"] == order[1]["initiative"] == 12
