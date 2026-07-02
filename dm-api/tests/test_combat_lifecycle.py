"""Tests for combat lifecycle and initiative rolling.

Split from ``test_combat.py`` (file-length guideline); action submission,
turn advancement, and action-economy tests live in ``test_combat_actions.py``.
"""

import uuid

import pytest

from tests.combat_helpers import (
    _create_character,
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
