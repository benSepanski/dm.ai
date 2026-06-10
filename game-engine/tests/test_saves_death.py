"""Tests for saving throws, death saves, damage-at-zero, temp HP, healing."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    CharacterClass,
    CharacterSheet,
    Condition,
    DamageType,
    DeathSaveOutcome,
)


def _char(**kwargs) -> CharacterSheet:
    defaults = dict(
        id="c1",
        name="Hero",
        level=1,
        char_class=CharacterClass.FIGHTER,
        hp_current=20,
        hp_max=20,
    )
    defaults.update(kwargs)
    return CharacterSheet(**defaults)


@pytest.fixture
def engine() -> DnD55eEngine:
    return DnD55eEngine()


class TestSavingThrows:
    def test_proficient_save_adds_proficiency(self, engine):
        char = _char(
            level=5,
            ability_scores=AbilityScoreSet(constitution=14),
            proficient_abilities=[Ability.CONSTITUTION],
        )
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])):
            result = engine.roll_saving_throw(char, Ability.CONSTITUTION, dc=15)
        # 10 + 2 (CON) + 3 (prof) = 15
        assert result.total == 15
        assert result.success is True

    def test_unproficient_save_no_proficiency(self, engine):
        char = _char(level=5, ability_scores=AbilityScoreSet(constitution=14))
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])):
            result = engine.roll_saving_throw(char, Ability.CONSTITUTION, dc=15)
        assert result.total == 12
        assert result.success is False

    def test_paralyzed_auto_fails_str_dex(self, engine):
        char = _char(conditions=[Condition.PARALYZED])
        for ability in (Ability.STRENGTH, Ability.DEXTERITY):
            result = engine.roll_saving_throw(char, ability, dc=5)
            assert result.auto_failed is True
            assert result.success is False
        # but not mental saves
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(20, [20])):
            result = engine.roll_saving_throw(char, Ability.WISDOM, dc=5)
        assert result.auto_failed is False
        assert result.success is True

    def test_restrained_imposes_disadvantage_on_dex(self, engine):
        char = _char(conditions=[Condition.RESTRAINED])
        with patch(
            "game_engine.rules.dnd_5_5e._saves.roll_with_disadvantage",
            return_value=(3, [3, 18]),
        ) as mock_dis:
            engine.roll_saving_throw(char, Ability.DEXTERITY, dc=10)
        mock_dis.assert_called_once()

    def test_exhaustion_penalizes_saves(self, engine):
        char = _char(exhaustion_level=3)
        with patch("game_engine.rules.dnd_5_5e._saves.roll_dice", return_value=(10, [10])):
            result = engine.roll_saving_throw(char, Ability.WISDOM, dc=10)
        assert result.total == 4  # 10 - 6


class TestDamageAtZeroAndTempHp:
    def test_drop_to_zero_falls_unconscious_and_prone(self, engine):
        char = _char(hp_current=5)
        engine.apply_damage(char, 5, DamageType.SLASHING)
        assert char.hp_current == 0
        assert Condition.UNCONSCIOUS in char.conditions
        assert Condition.PRONE in char.conditions
        assert char.is_dying

    def test_massive_damage_instant_death(self, engine):
        char = _char(hp_current=5, hp_max=20)
        engine.apply_damage(char, 26, DamageType.FIRE)  # 21 excess >= 20 max
        assert char.is_dead

    def test_damage_while_dying_adds_failure(self, engine):
        char = _char(hp_current=1)
        engine.apply_damage(char, 1, DamageType.SLASHING)
        assert char.hp_current == 0
        engine.apply_damage(char, 3, DamageType.SLASHING)
        assert char.death_saves.failures == 1

    def test_temp_hp_absorbs_first_and_does_not_stack(self, engine):
        char = _char(temp_hp=0)
        engine.grant_temp_hp(char, 8)
        engine.grant_temp_hp(char, 5)
        assert char.temp_hp == 8  # larger pool wins
        engine.apply_damage(char, 10, DamageType.COLD)
        assert char.temp_hp == 0
        assert char.hp_current == 18

    def test_resistance_applies_before_temp_hp(self, engine):
        char = _char(temp_hp=4, damage_resistances=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.FIRE)  # halved to 5
        assert char.temp_hp == 0
        assert char.hp_current == 19

    def test_concentration_dc(self, engine):
        assert engine.concentration_save_dc(4) == 10
        assert engine.concentration_save_dc(44) == 22


class TestHealing:
    def test_healing_caps_at_max(self, engine):
        char = _char(hp_current=15)
        engine.apply_healing(char, 100)
        assert char.hp_current == 20

    def test_healing_wakes_dying_character(self, engine):
        char = _char(hp_current=3)
        engine.apply_damage(char, 3, DamageType.SLASHING)
        char.death_saves.failures = 2
        engine.apply_healing(char, 1)
        assert char.hp_current == 1
        assert Condition.UNCONSCIOUS not in char.conditions
        assert char.death_saves.failures == 0
        # Prone persists — standing up costs movement.
        assert Condition.PRONE in char.conditions

    def test_no_healing_for_the_dead(self, engine):
        char = _char(hp_current=1, hp_max=10)
        engine.apply_damage(char, 100, DamageType.FIRE)
        assert char.is_dead
        engine.apply_healing(char, 10)
        assert char.hp_current == 0


class TestDeathSaves:
    def _dying(self, engine) -> CharacterSheet:
        char = _char(hp_current=1)
        engine.apply_damage(char, 1, DamageType.SLASHING)
        return char

    def test_requires_dying(self, engine):
        with pytest.raises(ValueError):
            engine.roll_death_save(_char())

    def test_success_and_failure_accumulate(self, engine):
        char = self._dying(engine)
        with patch("game_engine.rules.dnd_5_5e._death.roll_dice", return_value=(12, [12])):
            result = engine.roll_death_save(char)
        assert result.outcome is DeathSaveOutcome.SUCCESS
        assert result.successes == 1
        with patch("game_engine.rules.dnd_5_5e._death.roll_dice", return_value=(4, [4])):
            result = engine.roll_death_save(char)
        assert result.outcome is DeathSaveOutcome.FAILURE
        assert result.failures == 1

    def test_three_failures_dead(self, engine):
        char = self._dying(engine)
        with patch("game_engine.rules.dnd_5_5e._death.roll_dice", return_value=(4, [4])):
            engine.roll_death_save(char)
            engine.roll_death_save(char)
            result = engine.roll_death_save(char)
        assert result.is_dead
        assert char.is_dead

    def test_natural_1_two_failures(self, engine):
        char = self._dying(engine)
        with patch("game_engine.rules.dnd_5_5e._death.roll_dice", return_value=(1, [1])):
            result = engine.roll_death_save(char)
        assert result.outcome is DeathSaveOutcome.CRITICAL_FAILURE
        assert result.failures == 2

    def test_natural_20_regains_1_hp(self, engine):
        char = self._dying(engine)
        with patch("game_engine.rules.dnd_5_5e._death.roll_dice", return_value=(20, [20])):
            result = engine.roll_death_save(char)
        assert result.regained_hp
        assert char.hp_current == 1
        assert Condition.UNCONSCIOUS not in char.conditions

    def test_three_successes_stable(self, engine):
        char = self._dying(engine)
        with patch("game_engine.rules.dnd_5_5e._death.roll_dice", return_value=(15, [15])):
            engine.roll_death_save(char)
            engine.roll_death_save(char)
            result = engine.roll_death_save(char)
        assert result.is_stable
        assert not char.is_dying

    def test_stabilize(self, engine):
        char = self._dying(engine)
        char.death_saves.failures = 2
        engine.stabilize(char)
        assert char.death_saves.is_stable
        assert char.death_saves.failures == 0
        assert char.hp_current == 0
