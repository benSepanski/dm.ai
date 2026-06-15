"""Tests for dm_api.api.character_combat — combat write-through helpers.

Covers:
- _patched_combatant     — pure function: applies PATCH fields onto a snapshot
- write_through_character_update — mirrors patches into active combats in DB
- active_combats_with_character  — query helper
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from dm_api.api.character_combat import (
    _patched_combatant,
    active_combats_with_character,
    write_through_character_update,
)

# ---------------------------------------------------------------------------
# _patched_combatant  (pure unit tests — no DB)
# ---------------------------------------------------------------------------


class TestPatchedCombatant:
    def _base(self) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "name": "Hero",
            "level": 3,
            "hp_current": 20,
            "hp_max": 20,
            "ac": 14,
            "speed": 30,
            "conditions": [],
        }

    def test_hp_current_updated(self):
        base = self._base()
        result = _patched_combatant(base, {"hp_current": 10}, {})
        assert result["hp_current"] == 10

    def test_name_updated(self):
        base = self._base()
        result = _patched_combatant(base, {"name": "Legend"}, {})
        assert result["name"] == "Legend"

    def test_none_values_not_applied(self):
        """Patch values of None must not overwrite existing data."""
        base = self._base()
        result = _patched_combatant(base, {"hp_current": None}, {})
        assert result["hp_current"] == 20

    def test_stats_updates_applied(self):
        base = self._base()
        result = _patched_combatant(base, {}, {"ability_scores": {"strength": 18}})
        assert result["ability_scores"]["strength"] == 18

    def test_unpatched_fields_preserved(self):
        base = self._base()
        result = _patched_combatant(base, {"hp_current": 5}, {})
        assert result["ac"] == 14
        assert result["name"] == "Hero"

    def test_original_not_mutated(self):
        base = self._base()
        original_hp = base["hp_current"]
        _patched_combatant(base, {"hp_current": 1}, {})
        assert base["hp_current"] == original_hp

    def test_stats_none_value_not_applied(self):
        """None values in stats_updates should not overwrite existing data."""
        base = {**self._base(), "conditions": ["poisoned"]}
        result = _patched_combatant(base, {}, {"conditions": None})
        assert result["conditions"] == ["poisoned"]

    def test_multiple_columns_patched(self):
        base = self._base()
        result = _patched_combatant(
            base,
            {"hp_current": 5, "ac": 18, "level": 5},
            {},
        )
        assert result["hp_current"] == 5
        assert result["ac"] == 18
        assert result["level"] == 5


# ---------------------------------------------------------------------------
# active_combats_with_character + write_through_character_update (DB tests)
# ---------------------------------------------------------------------------


async def _create_world_and_session(client) -> tuple[str, str]:
    r = await client.post(
        "/api/worlds/",
        json={"name": "WriteThrough World", "setting_description": "Testing"},
    )
    assert r.status_code == 201
    world_id = r.json()["id"]

    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "WriteThrough Session"},
    )
    assert r.status_code == 201
    return world_id, r.json()["id"]


async def _create_character(client, world_id: str, name: str = "Warrior") -> str:
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": name,
            "level": 3,
            "char_class": "Fighter",
            "hp_current": 20,
            "hp_max": 20,
            "ac": 14,
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


@pytest.mark.asyncio
async def test_active_combats_with_character_no_combat(client, db_session, world_id):
    char_id_str = await _create_character(client, world_id)
    result = await active_combats_with_character(db_session, uuid.UUID(char_id_str))
    assert result == []


@pytest.mark.asyncio
async def test_active_combats_with_character_enrolled(client, db_session, world_id):
    char_id_str = await _create_character(client, world_id)

    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Enrolled Session"},
    )
    session_id = r.json()["id"]

    # Start combat with the character enrolled from the beginning
    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id_str]},
    )
    assert r.status_code == 201

    result = await active_combats_with_character(db_session, uuid.UUID(char_id_str))
    assert len(result) == 1


@pytest.mark.asyncio
async def test_write_through_no_active_combat(client, db_session, world_id):
    """write_through with no combat returns an empty list — nothing to update."""
    from sqlalchemy import select

    from dm_api.db.models.character import Character

    char_id_str = await _create_character(client, world_id)
    result_q = await db_session.execute(
        select(Character).where(Character.id == uuid.UUID(char_id_str))
    )
    character = result_q.scalar_one()

    updated = await write_through_character_update(
        db_session,
        character,
        {"hp_current": 10},
        {},
    )
    assert updated == []


@pytest.mark.asyncio
async def test_write_through_patches_combatant_in_active_combat(client, db_session, world_id):
    """Patching a character while in combat should mirror the update into the snapshot."""
    from sqlalchemy import select

    from dm_api.db.models.character import Character

    char_id_str = await _create_character(client, world_id, "Mirrored")

    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Mirror Session"},
    )
    session_id = r.json()["id"]

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id_str]},
    )
    assert r.status_code == 201

    result_q = await db_session.execute(
        select(Character).where(Character.id == uuid.UUID(char_id_str))
    )
    character = result_q.scalar_one()

    updated_combats = await write_through_character_update(
        db_session,
        character,
        {"hp_current": 5},
        {},
    )
    assert len(updated_combats) == 1
    combat = updated_combats[0]
    patched = next(
        (c for c in (combat.combatants or []) if c.get("id") == char_id_str),
        None,
    )
    assert patched is not None
    assert patched["hp_current"] == 5


@pytest.mark.asyncio
async def test_write_through_preserves_other_combatants(client, db_session, world_id):
    """Only the patched character's snapshot is modified; others stay intact."""
    from sqlalchemy import select

    from dm_api.db.models.character import Character

    char1_id = await _create_character(client, world_id, "Alice")
    char2_id = await _create_character(client, world_id, "Bob")

    r = await client.post(
        "/api/sessions/",
        json={"world_id": world_id, "name": "Multi Session"},
    )
    session_id = r.json()["id"]

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char1_id, char2_id]},
    )
    assert r.status_code == 201

    result_q = await db_session.execute(
        select(Character).where(Character.id == uuid.UUID(char1_id))
    )
    character = result_q.scalar_one()

    updated_combats = await write_through_character_update(
        db_session,
        character,
        {"hp_current": 1},
        {},
    )
    assert len(updated_combats) == 1
    combat = updated_combats[0]

    alice_snap = next(c for c in (combat.combatants or []) if c.get("id") == char1_id)
    bob_snap = next(c for c in (combat.combatants or []) if c.get("id") == char2_id)
    assert alice_snap["hp_current"] == 1
    assert bob_snap["hp_current"] == 20  # unchanged
