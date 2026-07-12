"""Unit and integration tests for dm_api.api.combat_utils.

Tests cover every public function:
- advance_turn_index     — complex dead/stable/dying-skipping turn logic
- combat_summary_text    — end-of-combat text generation
- _normalize_char_class  — case-insensitive class normalisation
- missing_combat_stats   — pre-combat validation
- load_turn_states /     — TurnState serde round-trip
  dump_turn_states
- character_to_sheet     — DB Character → CharacterSheet bridge
- sync_combatants_to_db  — combat write-back to DB

build_attack_details is tested in test_build_attack_details.py.
roll_and_sort_initiatives is tested in test_roll_and_sort_initiatives.py.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from game_engine.types import CharacterClass, TurnState

from dm_api.api.combat_utils import (
    _normalize_char_class,
    advance_turn_index,
    character_to_sheet,
    combat_summary_text,
    dump_turn_states,
    load_turn_states,
    missing_combat_stats,
    sync_combatants_to_db,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_combatant(
    name: str = "Hero",
    hp_current: int = 20,
    hp_max: int = 20,
    is_dead: bool = False,
    is_stable: bool = False,
    death_successes: int = 0,
    death_failures: int = 0,
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "hp_current": hp_current,
        "hp_max": hp_max,
        "death_saves": {
            "is_dead": is_dead,
            "is_stable": is_stable,
            "successes": death_successes,
            "failures": death_failures,
        },
        "conditions": conditions or [],
        "level": 1,
        "class": "Fighter",
        "ac": 14,
        "speed": 30,
        "type": "PC",
    }


# ---------------------------------------------------------------------------
# advance_turn_index
# ---------------------------------------------------------------------------


class TestAdvanceTurnIndex:
    def test_simple_advance(self):
        combatants = [_make_combatant(), _make_combatant()]
        idx, rounds = advance_turn_index(0, 2, combatants)
        assert idx == 1
        assert rounds == 0

    def test_wraps_to_next_round(self):
        combatants = [_make_combatant(), _make_combatant()]
        idx, rounds = advance_turn_index(1, 2, combatants)
        assert idx == 0
        assert rounds == 1

    def test_skips_dead_combatant(self):
        dead = _make_combatant("Ghost", hp_current=0, hp_max=10, is_dead=True)
        alive = _make_combatant("Hero")
        # order: alive(0), dead(1), alive(2)
        combatants = [alive, dead, _make_combatant("Hero2")]
        idx, rounds = advance_turn_index(0, 3, combatants)
        # index 1 is dead → should skip to index 2
        assert idx == 2
        assert rounds == 0

    def test_skips_stable_unconscious_but_not_dying(self):
        """Stable/unconscious (0 HP, is_stable=True) are skipped.
        Dying combatants (0 HP, not stable, not dead) are NOT skipped."""
        stable = _make_combatant("Stable", hp_current=0, is_stable=True)
        dying = _make_combatant("Dying", hp_current=0, is_stable=False, is_dead=False)
        combatants = [_make_combatant("Hero"), stable, dying]
        # From idx 0: advance to 1 (stable → skip) → 2 (dying → keep)
        idx, rounds = advance_turn_index(0, 3, combatants)
        assert idx == 2
        assert rounds == 0

    def test_dying_is_not_skipped(self):
        dying = _make_combatant("Dying", hp_current=0, is_stable=False, is_dead=False)
        combatants = [_make_combatant("Hero"), dying]
        idx, rounds = advance_turn_index(0, 2, combatants)
        assert idx == 1
        assert rounds == 0

    def test_wraps_over_dead_at_end_of_order(self):
        dead = _make_combatant("Ghost", hp_current=0, is_dead=True)
        alive = _make_combatant("Hero")
        # order: dead(0), alive(1); advance from 1 wraps to 0 (dead) → skips to 1
        combatants = [dead, alive]
        idx, rounds = advance_turn_index(1, 2, combatants)
        assert idx == 1
        assert rounds == 1

    def test_all_dead_bounded(self):
        """All combatants dead: loop stays bounded and returns some index."""
        dead1 = _make_combatant("D1", hp_current=0, is_dead=True)
        dead2 = _make_combatant("D2", hp_current=0, is_dead=True)
        combatants = [dead1, dead2]
        idx, rounds = advance_turn_index(0, 2, combatants)
        # Exact result doesn't matter as long as it terminates
        assert 0 <= idx < 2


# ---------------------------------------------------------------------------
# combat_summary_text
# ---------------------------------------------------------------------------


class TestCombatSummaryText:
    def test_basic_alive(self):
        combatants = [{"name": "Hero", "hp_current": 15, "hp_max": 20, "conditions": []}]
        text = combat_summary_text(3, combatants)
        assert "3 round(s)" in text
        assert "Hero: 15/20 HP" in text

    def test_dead_combatant(self):
        combatants = [
            {
                "name": "Goblin",
                "hp_current": 0,
                "hp_max": 7,
                "death_saves": {"is_dead": True, "is_stable": False},
                "conditions": [],
            }
        ]
        text = combat_summary_text(1, combatants)
        assert "DEAD" in text
        assert "Goblin" in text

    def test_stable_unconscious(self):
        combatants = [
            {
                "name": "Elara",
                "hp_current": 0,
                "hp_max": 14,
                "death_saves": {"is_dead": False, "is_stable": True},
                "conditions": [],
            }
        ]
        text = combat_summary_text(2, combatants)
        assert "DOWN, stable" in text

    def test_dying_with_saves(self):
        combatants = [
            {
                "name": "Tank",
                "hp_current": 0,
                "hp_max": 30,
                "death_saves": {
                    "is_dead": False,
                    "is_stable": False,
                    "successes": 2,
                    "failures": 1,
                },
                "conditions": [],
            }
        ]
        text = combat_summary_text(2, combatants)
        assert "DOWN" in text
        assert "2 success" in text
        assert "1 failure" in text

    def test_conditions_appended(self):
        combatants = [
            {
                "name": "Knight",
                "hp_current": 10,
                "hp_max": 20,
                "death_saves": {},
                "conditions": ["poisoned", "prone"],
            }
        ]
        text = combat_summary_text(1, combatants)
        assert "poisoned" in text
        assert "prone" in text

    def test_multiple_combatants(self):
        combatants = [
            {"name": "A", "hp_current": 5, "hp_max": 10, "conditions": []},
            {
                "name": "B",
                "hp_current": 0,
                "hp_max": 8,
                "death_saves": {"is_dead": True},
                "conditions": [],
            },
        ]
        text = combat_summary_text(4, combatants)
        assert "- A:" in text
        assert "- B:" in text
        assert "DEAD" in text

    def test_unknown_name_fallback(self):
        combatants = [{"hp_current": 5, "hp_max": 10, "conditions": []}]
        text = combat_summary_text(1, combatants)
        assert "Unknown" in text


# ---------------------------------------------------------------------------
# _normalize_char_class
# ---------------------------------------------------------------------------


class TestNormalizeCharClass:
    def test_exact_canonical_case(self):
        assert _normalize_char_class("Fighter") == "Fighter"

    def test_all_lowercase(self):
        assert _normalize_char_class("fighter") == "Fighter"

    def test_all_uppercase(self):
        assert _normalize_char_class("WIZARD") == "Wizard"

    def test_mixed_case(self):
        assert _normalize_char_class("wIzArD") == "Wizard"

    def test_none_defaults_to_fighter(self):
        assert _normalize_char_class(None) == CharacterClass.FIGHTER.value

    def test_unknown_string_passed_through(self):
        result = _normalize_char_class("CustomClass")
        assert result == "CustomClass"

    def test_whitespace_stripped(self):
        assert _normalize_char_class("  Rogue  ") == "Rogue"


# ---------------------------------------------------------------------------
# missing_combat_stats
# ---------------------------------------------------------------------------


class TestMissingCombatStats:
    def _make_char(self, name: str, hp_max: int | None, ac: int | None):
        return SimpleNamespace(id=uuid.uuid4(), name=name, hp_max=hp_max, ac=ac)

    def test_all_complete(self):
        chars = [self._make_char("A", 10, 12), self._make_char("B", 8, 14)]
        assert missing_combat_stats(chars) == []

    def test_missing_hp_max(self):
        chars = [self._make_char("Statless", None, 12)]
        result = missing_combat_stats(chars)
        assert "Statless" in result

    def test_missing_ac(self):
        chars = [self._make_char("NoAC", 10, None)]
        result = missing_combat_stats(chars)
        assert "NoAC" in result

    def test_missing_both(self):
        chars = [self._make_char("Empty", None, None)]
        result = missing_combat_stats(chars)
        assert "Empty" in result

    def test_mixed(self):
        chars = [
            self._make_char("Full", 10, 12),
            self._make_char("Partial", None, 12),
        ]
        result = missing_combat_stats(chars)
        assert result == ["Partial"]


# ---------------------------------------------------------------------------
# build_attack_details — see test_build_attack_details.py
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# load_turn_states / dump_turn_states
# ---------------------------------------------------------------------------


class TestTurnStateSerde:
    def _make_turn_state(self) -> TurnState:
        ts = TurnState()
        ts.action_used = True
        ts.bonus_action_used = False
        ts.movement_used_ft = 15
        ts.attacks_made = 1
        ts.dodging = True
        ts.vexed_target_id = str(uuid.uuid4())
        return ts

    def test_roundtrip(self):
        char_id = str(uuid.uuid4())
        original = {char_id: self._make_turn_state()}
        dumped = dump_turn_states(original)
        loaded = load_turn_states_from_dict(dumped)
        ts = loaded[char_id]
        assert ts.action_used is True
        assert ts.movement_used_ft == 15
        assert ts.dodging is True

    def test_empty_dict(self):
        assert dump_turn_states({}) == {}
        assert load_turn_states_from_dict({}) == {}

    def test_multiple_combatants(self):
        id1, id2 = str(uuid.uuid4()), str(uuid.uuid4())
        ts1 = TurnState()
        ts1.action_used = True
        ts2 = TurnState()
        ts2.bonus_action_used = True
        dumped = dump_turn_states({id1: ts1, id2: ts2})
        loaded = load_turn_states_from_dict(dumped)
        assert loaded[id1].action_used is True
        assert loaded[id2].bonus_action_used is True
        assert loaded[id1].bonus_action_used is False


def load_turn_states_from_dict(d: dict) -> dict[str, TurnState]:
    """Thin wrapper that delegates to the module under test."""
    combat = SimpleNamespace(turn_states=d)
    return load_turn_states(combat)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# character_to_sheet
# ---------------------------------------------------------------------------


class TestCharacterToSheet:
    def _make_character(
        self,
        *,
        name: str = "Thorin",
        level: int = 3,
        char_class: str = "Fighter",
        hp_current: int = 20,
        hp_max: int = 20,
        ac: int = 14,
        speed: int = 30,
        stats: dict[str, Any] | None = None,
    ):
        from game_engine.types import CharacterType

        return SimpleNamespace(
            id=uuid.uuid4(),
            name=name,
            level=level,
            char_class=char_class,
            hp_current=hp_current,
            hp_max=hp_max,
            ac=ac,
            speed=speed,
            type=CharacterType.PC,
            stats=stats,
            spells=None,
            alignment=None,
        )

    def test_basic_fields_transferred(self):
        char = self._make_character()
        sheet = character_to_sheet(char)
        assert sheet.name == "Thorin"
        assert sheet.level == 3
        assert sheet.hp_current == 20
        assert sheet.hp_max == 20
        assert sheet.ac == 14
        assert sheet.speed == 30

    def test_null_hp_defaults_to_max(self):
        char = self._make_character(hp_current=None, hp_max=16)
        char.hp_current = None
        sheet = character_to_sheet(char)
        assert sheet.hp_current == 16

    def test_null_stats_uses_defaults(self):
        char = self._make_character(stats=None)
        sheet = character_to_sheet(char)
        assert sheet is not None
        assert sheet.ac == 14

    def test_class_normalised(self):
        char = self._make_character(char_class="wizard")
        sheet = character_to_sheet(char)
        assert sheet.char_class == CharacterClass.WIZARD

    def test_spell_slots_derived_when_absent(self):
        char = self._make_character(char_class="Wizard", level=3, stats={})
        sheet = character_to_sheet(char)
        # A level-3 Wizard has slots at levels 1 and 2
        total_slots = sum(s.maximum for s in sheet.spell_slots)
        assert total_slots > 0

    def test_hit_dice_derived_when_absent(self):
        char = self._make_character(char_class="Fighter", level=3, stats={})
        sheet = character_to_sheet(char)
        assert sheet.hit_dice is not None
        assert len(sheet.hit_dice) > 0
        assert sheet.hit_dice[0].maximum == 3

    def test_existing_spell_slots_preserved(self):
        """If stats already carry spell_slots, don't overwrite them."""
        slots = [{"slot_level": 1, "maximum": 4, "remaining": 3}]
        char = self._make_character(char_class="Wizard", level=3, stats={"spell_slots": slots})
        sheet = character_to_sheet(char)
        max_1st = next((s.maximum for s in sheet.spell_slots if s.slot_level == 1), None)
        assert max_1st == 4

    def test_ability_scores_from_stats(self):
        char = self._make_character(stats={"ability_scores": {"strength": 18, "dexterity": 14}})
        sheet = character_to_sheet(char)
        from game_engine.types import Ability

        assert sheet.ability_scores.get(Ability.STRENGTH) == 18


# ---------------------------------------------------------------------------
# sync_combatants_to_db  (needs DB session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_combatants_updates_hp(client, world_id, db_session):
    from sqlalchemy import select

    from dm_api.db.models.character import Character

    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "BattleKnight",
            "level": 3,
            "char_class": "Fighter",
            "hp_current": 20,
            "hp_max": 20,
            "ac": 14,
        },
    )
    assert r.status_code == 201
    char_id = r.json()["id"]

    combatant = {
        "id": char_id,
        "hp_current": 7,
        "conditions": [],
    }
    await sync_combatants_to_db(db_session, [combatant])
    await db_session.commit()

    result = await db_session.execute(select(Character).where(Character.id == uuid.UUID(char_id)))
    char = result.scalar_one()
    assert char.hp_current == 7


@pytest.mark.asyncio
async def test_sync_combatants_writes_state_fields(client, world_id, db_session):
    from sqlalchemy import select

    from dm_api.db.models.character import Character

    r = await client.post(
        "/api/characters/",
        json={
            "world_id": world_id,
            "type": "PC",
            "name": "Mage",
            "level": 3,
            "char_class": "Wizard",
            "hp_current": 14,
            "hp_max": 14,
            "ac": 12,
        },
    )
    char_id = r.json()["id"]

    combatant = {
        "id": char_id,
        "hp_current": 14,
        "conditions": ["poisoned"],
        "condition_durations": {"poisoned": 2},
        "exhaustion_level": 1,
    }
    await sync_combatants_to_db(db_session, [combatant])
    await db_session.commit()

    result = await db_session.execute(select(Character).where(Character.id == uuid.UUID(char_id)))
    char = result.scalar_one()
    assert char.stats["conditions"] == ["poisoned"]
    assert char.stats["exhaustion_level"] == 1


@pytest.mark.asyncio
async def test_sync_combatants_skips_unknown_id(db_session):
    """Combatants whose ID isn't in the DB are silently skipped."""
    fake_id = str(uuid.uuid4())
    combatants = [{"id": fake_id, "hp_current": 5}]
    # Must not raise
    await sync_combatants_to_db(db_session, combatants)


@pytest.mark.asyncio
async def test_sync_combatants_skips_invalid_uuid(db_session):
    """Non-UUID id strings are silently skipped."""
    combatants = [{"id": "not-a-uuid", "hp_current": 5}]
    await sync_combatants_to_db(db_session, combatants)
