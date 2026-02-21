"""
Tests for game_engine.core.conditions — CONDITION_EFFECTS, helpers.
"""

from __future__ import annotations

import pytest

from game_engine.core.conditions import (
    CONDITION_EFFECTS,
    ConditionEffect,
    condition_prevents_action,
    get_active_conditions,
    is_immune_to_condition,
)
from game_engine.types import (
    Ability,
    CharacterClass,
    CharacterSheet,
    Condition,
    DamageType,
    AbilityScoreSet,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_basic_char(**kwargs) -> CharacterSheet:
    return CharacterSheet(
        id="test-char",
        name="Test Character",
        level=1,
        char_class=CharacterClass.FIGHTER,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# CONDITION_EFFECTS dictionary coverage
# ---------------------------------------------------------------------------


class TestConditionEffectsDict:
    def test_all_conditions_are_keys(self):
        """Every Condition enum value must appear as a key in CONDITION_EFFECTS."""
        missing = [c for c in Condition if c not in CONDITION_EFFECTS]
        assert missing == [], f"Missing conditions in CONDITION_EFFECTS: {missing}"

    def test_all_keys_are_condition_enums(self):
        """Keys must be Condition enum instances, not raw strings."""
        for key in CONDITION_EFFECTS:
            assert isinstance(key, Condition), (
                f"Key {key!r} is not a Condition enum instance"
            )

    def test_all_values_are_condition_effect_instances(self):
        for cond, effect in CONDITION_EFFECTS.items():
            assert isinstance(effect, ConditionEffect), (
                f"Effect for {cond} is not a ConditionEffect instance"
            )

    def test_descriptions_are_non_empty(self):
        for cond, effect in CONDITION_EFFECTS.items():
            assert effect.description, f"No description for {cond}"

    # Spot-check key conditions

    def test_blinded_has_attack_disadvantage(self):
        effect = CONDITION_EFFECTS[Condition.BLINDED]
        assert effect.attack_modifier == "disadvantage"

    def test_blinded_attacks_against_have_advantage(self):
        effect = CONDITION_EFFECTS[Condition.BLINDED]
        assert effect.attack_against_modifier == "advantage"

    def test_incapacitated_cannot_act(self):
        effect = CONDITION_EFFECTS[Condition.INCAPACITATED]
        assert effect.can_act is False

    def test_paralyzed_cannot_act(self):
        effect = CONDITION_EFFECTS[Condition.PARALYZED]
        assert effect.can_act is False

    def test_paralyzed_auto_fails_str_dex_saves(self):
        effect = CONDITION_EFFECTS[Condition.PARALYZED]
        assert Ability.STRENGTH in effect.auto_fail_saves
        assert Ability.DEXTERITY in effect.auto_fail_saves

    def test_stunned_cannot_act(self):
        effect = CONDITION_EFFECTS[Condition.STUNNED]
        assert effect.can_act is False

    def test_unconscious_cannot_act(self):
        effect = CONDITION_EFFECTS[Condition.UNCONSCIOUS]
        assert effect.can_act is False

    def test_petrified_cannot_act(self):
        effect = CONDITION_EFFECTS[Condition.PETRIFIED]
        assert effect.can_act is False

    def test_grappled_speed_zero(self):
        effect = CONDITION_EFFECTS[Condition.GRAPPLED]
        assert effect.speed_zero is True

    def test_invisible_attack_advantage(self):
        effect = CONDITION_EFFECTS[Condition.INVISIBLE]
        assert effect.attack_modifier == "advantage"

    def test_invisible_attacks_against_disadvantage(self):
        effect = CONDITION_EFFECTS[Condition.INVISIBLE]
        assert effect.attack_against_modifier == "disadvantage"

    def test_poisoned_attack_disadvantage(self):
        effect = CONDITION_EFFECTS[Condition.POISONED]
        assert effect.attack_modifier == "disadvantage"

    def test_charmed_can_act(self):
        """Charmed doesn't prevent action, but restricts who you can target."""
        effect = CONDITION_EFFECTS[Condition.CHARMED]
        assert effect.can_act is True

    def test_petrified_immunity_types(self):
        effect = CONDITION_EFFECTS[Condition.PETRIFIED]
        assert DamageType.POISON in effect.immunity_types
        assert DamageType.PSYCHIC in effect.immunity_types


# ---------------------------------------------------------------------------
# Condition.prevents_action classmethod
# ---------------------------------------------------------------------------


class TestPreventsAction:
    @pytest.mark.parametrize(
        "condition,expected",
        [
            (Condition.INCAPACITATED, True),
            (Condition.PARALYZED, True),
            (Condition.PETRIFIED, True),
            (Condition.STUNNED, True),
            (Condition.UNCONSCIOUS, True),
            (Condition.BLINDED, False),
            (Condition.CHARMED, False),
            (Condition.DEAFENED, False),
            (Condition.EXHAUSTION, False),
            (Condition.FRIGHTENED, False),
            (Condition.GRAPPLED, False),
            (Condition.INVISIBLE, False),
            (Condition.POISONED, False),
            (Condition.PRONE, False),
            (Condition.RESTRAINED, False),
        ],
    )
    def test_prevents_action(self, condition: Condition, expected: bool):
        assert Condition.prevents_action(condition) is expected


# ---------------------------------------------------------------------------
# is_immune_to_condition helper
# ---------------------------------------------------------------------------


class TestIsImmuneToCondition:
    def test_immune_char_returns_true(self):
        char = make_basic_char(condition_immunities=[Condition.CHARMED])
        assert is_immune_to_condition(char, Condition.CHARMED) is True

    def test_non_immune_char_returns_false(self):
        char = make_basic_char()
        assert is_immune_to_condition(char, Condition.BLINDED) is False

    def test_string_condition_name_works(self):
        char = make_basic_char(condition_immunities=[Condition.FRIGHTENED])
        assert is_immune_to_condition(char, "frightened") is True

    def test_unknown_string_condition_returns_false(self):
        char = make_basic_char()
        assert is_immune_to_condition(char, "nonexistent_condition") is False


# ---------------------------------------------------------------------------
# get_active_conditions helper
# ---------------------------------------------------------------------------


class TestGetActiveConditions:
    def test_no_conditions(self):
        char = make_basic_char()
        assert get_active_conditions(char) == []

    def test_returns_conditions_list(self):
        char = make_basic_char(conditions=[Condition.BLINDED, Condition.PRONE])
        result = get_active_conditions(char)
        assert Condition.BLINDED in result
        assert Condition.PRONE in result
        assert len(result) == 2

    def test_returns_condition_enums(self):
        char = make_basic_char(conditions=[Condition.POISONED])
        result = get_active_conditions(char)
        assert all(isinstance(c, Condition) for c in result)


# ---------------------------------------------------------------------------
# condition_prevents_action helper
# ---------------------------------------------------------------------------


class TestConditionPreventsActionHelper:
    def test_no_conditions_can_act(self):
        char = make_basic_char()
        assert condition_prevents_action(char) is False

    def test_incapacitated_prevents_action(self):
        char = make_basic_char(conditions=[Condition.INCAPACITATED])
        assert condition_prevents_action(char) is True

    def test_paralyzed_prevents_action(self):
        char = make_basic_char(conditions=[Condition.PARALYZED])
        assert condition_prevents_action(char) is True

    def test_blinded_does_not_prevent_action(self):
        char = make_basic_char(conditions=[Condition.BLINDED])
        assert condition_prevents_action(char) is False

    def test_multiple_conditions_one_prevents(self):
        char = make_basic_char(conditions=[Condition.PRONE, Condition.STUNNED])
        assert condition_prevents_action(char) is True

    def test_dead_char_cannot_act(self):
        char = make_basic_char(hp_current=0)
        assert condition_prevents_action(char) is True
