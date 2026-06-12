"""Tests for the DB→engine bridge in ``dm_api.api.combat_utils``.

Regression coverage for the flat-ability-scores bug: the documented character
payload (docs/running-a-game.md §1) puts the six scores flat in ``stats``,
but the sheet serde only reads a nested ``"ability_scores"`` dict — so every
combatant created per the docs silently fought with all 10s.
"""

from __future__ import annotations

import uuid

import pytest
from game_engine.types import Ability, CharacterType

from dm_api.api.combat_utils import character_to_sheet
from dm_api.db.models.character import Character

from .combat_helpers import _create_session

# ---------------------------------------------------------------------------
# Unit tests: character_to_sheet ability-score bridging
# ---------------------------------------------------------------------------


def _make_character(stats: dict | None) -> Character:
    return Character(
        id=uuid.uuid4(),
        world_id=uuid.uuid4(),
        type=CharacterType.PC,
        name="Hero",
        level=3,
        char_class="Fighter",
        hp_current=20,
        hp_max=20,
        ac=14,
        speed=30,
        stats=stats,
    )


def test_flat_ability_scores_reach_the_sheet():
    """Flat full-name ability keys in stats (the documented payload shape)."""
    character = _make_character(
        {
            "strength": 16,
            "dexterity": 14,
            "constitution": 14,
            "intelligence": 10,
            "wisdom": 12,
            "charisma": 8,
        }
    )
    sheet = character_to_sheet(character)
    assert sheet.ability_scores.strength == 16
    assert sheet.ability_scores.dexterity == 14
    assert sheet.ability_scores.charisma == 8
    assert sheet.ability_scores.modifier(Ability.STRENGTH) == 3


def test_flat_short_form_ability_scores_reach_the_sheet():
    """Short forms (``"str"``) are accepted, matching AbilityScoreSet.from_dict."""
    character = _make_character({"str": 18, "dex": 12})
    sheet = character_to_sheet(character)
    assert sheet.ability_scores.strength == 18
    assert sheet.ability_scores.dexterity == 12
    assert sheet.ability_scores.wisdom == 10  # unspecified scores default


def test_nested_ability_scores_take_precedence_over_flat_keys():
    character = _make_character(
        {
            "strength": 8,
            "ability_scores": {"strength": 16},
        }
    )
    sheet = character_to_sheet(character)
    assert sheet.ability_scores.strength == 16


def test_non_numeric_flat_ability_score_is_ignored():
    character = _make_character({"strength": "mighty", "dexterity": 14})
    sheet = character_to_sheet(character)
    assert sheet.ability_scores.strength == 10
    assert sheet.ability_scores.dexterity == 14


def test_no_ability_scores_at_all_defaults_to_tens():
    sheet = character_to_sheet(_make_character(None))
    assert sheet.ability_scores.strength == 10


# ---------------------------------------------------------------------------
# Integration: flat stats survive into the combat state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_combat_with_flat_stats_carries_ability_scores(client, world_id):
    """A character created with the documented flat-stats payload enters
    combat with its real ability scores, not all 10s."""
    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Doc Payload",
            "level": 3,
            "char_class": "Fighter",
            "hp_current": 20,
            "hp_max": 20,
            "ac": 14,
            "stats": {"strength": 16, "dexterity": 14, "constitution": 14},
        },
    )
    assert r.status_code == 201
    char_id = r.json()["id"]
    session_id = await _create_session(client, world_id)

    r = await client.post(
        f"/api/sessions/{session_id}/combat",
        json={"character_ids": [char_id]},
    )
    assert r.status_code == 201, r.text
    combatant = r.json()["combatants"][0]
    assert combatant["ability_scores"]["strength"] == 16
    assert combatant["ability_scores"]["dexterity"] == 14
