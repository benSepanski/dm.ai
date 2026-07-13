"""
Tests for game_engine.core.conditions — CONDITION_EFFECTS, helpers.
"""

from __future__ import annotations

import pytest

from game_engine.core.conditions import (
    CONDITION_EFFECTS,
    ConditionEffect,
    is_immune_to_condition,
)
from game_engine.types import (
    Ability,
    AdvantageType,
    CharacterClass,
    CharacterSheet,
    Condition,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_basic_char(**kwargs: object) -> CharacterSheet:
    return CharacterSheet(
        id="test-char",
        name="Test Character",
        level=1,
        char_class=CharacterClass.FIGHTER,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# CONDITION_EFFECTS dictionary coverage
# ---------------------------------------------------------------------------


class TestConditionEffectsDict:
    def test_all_conditions_are_keys(self) -> None:
        """Every Condition enum value must appear as a key in CONDITION_EFFECTS."""
        missing = [c for c in Condition if c not in CONDITION_EFFECTS]
        assert missing == [], f"Missing conditions in CONDITION_EFFECTS: {missing}"

    def test_all_keys_are_condition_enums(self) -> None:
        """Keys must be Condition enum instances, not raw strings."""
        for key in CONDITION_EFFECTS:
            assert isinstance(key, Condition), f"Key {key!r} is not a Condition enum instance"

    def test_all_values_are_condition_effect_instances(self) -> None:
        for cond, effect in CONDITION_EFFECTS.items():
            assert isinstance(
                effect, ConditionEffect
            ), f"Effect for {cond} is not a ConditionEffect instance"

    def test_descriptions_are_non_empty(self) -> None:
        for cond, effect in CONDITION_EFFECTS.items():
            assert effect.description, f"No description for {cond}"

    # Spot-check key conditions

    def test_blinded_has_attack_disadvantage(self) -> None:
        effect = CONDITION_EFFECTS[Condition.BLINDED]
        assert effect.attack_modifier == AdvantageType.DISADVANTAGE

    def test_blinded_attacks_against_have_advantage(self) -> None:
        effect = CONDITION_EFFECTS[Condition.BLINDED]
        assert effect.attack_against_modifier == AdvantageType.ADVANTAGE

    def test_paralyzed_auto_fails_str_dex_saves(self) -> None:
        effect = CONDITION_EFFECTS[Condition.PARALYZED]
        assert Ability.STRENGTH in effect.auto_fail_saves
        assert Ability.DEXTERITY in effect.auto_fail_saves

    def test_invisible_attack_advantage(self) -> None:
        effect = CONDITION_EFFECTS[Condition.INVISIBLE]
        assert effect.attack_modifier == AdvantageType.ADVANTAGE

    def test_invisible_attacks_against_disadvantage(self) -> None:
        effect = CONDITION_EFFECTS[Condition.INVISIBLE]
        assert effect.attack_against_modifier == AdvantageType.DISADVANTAGE

    def test_poisoned_attack_disadvantage(self) -> None:
        effect = CONDITION_EFFECTS[Condition.POISONED]
        assert effect.attack_modifier == AdvantageType.DISADVANTAGE

    def test_petrified_no_poison_or_psychic_damage_immunity(self) -> None:
        """SRD 5.2: Petrified resists (does not negate) poison/psychic damage
        via damage_resistances_all — it grants no damage-type immunity_types
        entries at all; the 2014 poison/psychic damage immunity was wrong
        (EFF-05)."""
        effect = CONDITION_EFFECTS[Condition.PETRIFIED]
        assert effect.immunity_types == []

    def test_petrified_grants_poisoned_condition_immunity(self) -> None:
        """SRD 5.2: 'Poison Immunity. You have Immunity to the Poisoned
        condition' while Petrified (EFF-05)."""
        effect = CONDITION_EFFECTS[Condition.PETRIFIED]
        assert effect.grants_condition_immunities == [Condition.POISONED]

    def test_petrified_damage_resistances_all(self) -> None:
        """PETRIFIED grants resistance to all damage types via damage_resistances_all."""
        effect = CONDITION_EFFECTS[Condition.PETRIFIED]
        assert effect.damage_resistances_all is True

    def test_no_other_condition_has_damage_resistances_all(self) -> None:
        """Only PETRIFIED should have damage_resistances_all=True in the base set."""
        conditions_with_all_resistance = [
            c for c, e in CONDITION_EFFECTS.items() if e.damage_resistances_all
        ]
        assert conditions_with_all_resistance == [Condition.PETRIFIED]

    def test_prone_attack_against_modifier_is_none(self) -> None:
        """PRONE's attack_against_modifier is None because _attacks.py handles the
        range-dependent rule (advantage melee, disadvantage ranged) via its own
        short-circuit before reaching the generic condition-effect loop."""
        effect = CONDITION_EFFECTS[Condition.PRONE]
        assert effect.attack_against_modifier is None


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
    def test_prevents_action(self, condition: Condition, expected: bool) -> None:
        assert Condition.prevents_action(condition) is expected


# ---------------------------------------------------------------------------
# Condition.sets_speed_to_zero classmethod
# ---------------------------------------------------------------------------


class TestSetsSpeedToZero:
    @pytest.mark.parametrize(
        "condition,expected",
        [
            (Condition.GRAPPLED, True),
            (Condition.PARALYZED, True),
            (Condition.PETRIFIED, True),
            (Condition.RESTRAINED, True),
            (Condition.UNCONSCIOUS, True),
            # 2024 Stunned deliberately omits the Speed-0 clause the 2014
            # version had — regression coverage for EFF-06.
            (Condition.STUNNED, False),
            (Condition.BLINDED, False),
            (Condition.CHARMED, False),
            (Condition.DEAFENED, False),
            (Condition.EXHAUSTION, False),
            (Condition.FRIGHTENED, False),
            (Condition.INCAPACITATED, False),
            (Condition.INVISIBLE, False),
            (Condition.POISONED, False),
            (Condition.PRONE, False),
        ],
    )
    def test_sets_speed_to_zero(self, condition: Condition, expected: bool) -> None:
        assert Condition.sets_speed_to_zero(condition) is expected


# ---------------------------------------------------------------------------
# is_immune_to_condition helper
# ---------------------------------------------------------------------------


class TestIsImmuneToCondition:
    def test_immune_char_returns_true(self) -> None:
        char = make_basic_char(condition_immunities=[Condition.CHARMED])
        assert is_immune_to_condition(char, Condition.CHARMED) is True

    def test_non_immune_char_returns_false(self) -> None:
        char = make_basic_char()
        assert is_immune_to_condition(char, Condition.BLINDED) is False

    def test_petrified_grants_poisoned_immunity(self) -> None:
        """A currently-Petrified character is immune to the Poisoned
        condition even without declaring it in condition_immunities
        (EFF-05)."""
        char = make_basic_char(conditions=[Condition.PETRIFIED])
        assert is_immune_to_condition(char, Condition.POISONED) is True

    def test_petrified_does_not_grant_other_condition_immunity(self) -> None:
        char = make_basic_char(conditions=[Condition.PETRIFIED])
        assert is_immune_to_condition(char, Condition.CHARMED) is False

    def test_no_longer_petrified_loses_poisoned_immunity(self) -> None:
        char = make_basic_char(conditions=[])
        assert is_immune_to_condition(char, Condition.POISONED) is False


# ---------------------------------------------------------------------------
# CharacterSheet.conditions / .can_act property coverage
# ---------------------------------------------------------------------------


class TestGetActiveConditions:
    def test_no_conditions(self) -> None:
        char = make_basic_char()
        assert list(char.conditions) == []

    def test_returns_conditions_list(self) -> None:
        char = make_basic_char(conditions=[Condition.BLINDED, Condition.PRONE])
        result = list(char.conditions)
        assert Condition.BLINDED in result
        assert Condition.PRONE in result
        assert len(result) == 2

    def test_returns_condition_enums(self) -> None:
        char = make_basic_char(conditions=[Condition.POISONED])
        result = list(char.conditions)
        assert all(isinstance(c, Condition) for c in result)


class TestConditionPreventsActionHelper:
    def test_no_conditions_can_act(self) -> None:
        char = make_basic_char()
        assert char.can_act is True

    def test_incapacitated_prevents_action(self) -> None:
        char = make_basic_char(conditions=[Condition.INCAPACITATED])
        assert char.can_act is False

    def test_paralyzed_prevents_action(self) -> None:
        char = make_basic_char(conditions=[Condition.PARALYZED])
        assert char.can_act is False

    def test_blinded_does_not_prevent_action(self) -> None:
        char = make_basic_char(conditions=[Condition.BLINDED])
        assert char.can_act is True

    def test_multiple_conditions_one_prevents(self) -> None:
        char = make_basic_char(conditions=[Condition.PRONE, Condition.STUNNED])
        assert char.can_act is False

    def test_dead_char_cannot_act(self) -> None:
        char = make_basic_char(hp_current=0)
        assert char.can_act is False
