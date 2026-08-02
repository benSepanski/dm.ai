"""
Tests for DnD55eEngine.apply_condition(), remove_condition(), tick_condition_durations().
"""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    AbilityScoreSet,
    CharacterClass,
    CharacterSheet,
    Condition,
)

# ---------------------------------------------------------------------------
# Shared helper (same as engine_checks to keep test files self-contained)
# ---------------------------------------------------------------------------


def make_fighter(
    level: int = 5,
    strength: int = 18,
    dexterity: int = 14,
    constitution: int = 16,
    intelligence: int = 10,
    wisdom: int = 12,
    charisma: int = 8,
    hp_current: int = 44,
    hp_max: int = 44,
    conditions: list[Condition] | None = None,
    condition_immunities: list[Condition] | None = None,
) -> CharacterSheet:
    return CharacterSheet(
        id="fighter-1",
        name="Thorin",
        level=level,
        char_class=CharacterClass.FIGHTER,
        ability_scores=AbilityScoreSet(
            strength=strength,
            dexterity=dexterity,
            constitution=constitution,
            intelligence=intelligence,
            wisdom=wisdom,
            charisma=charisma,
        ),
        hp_current=hp_current,
        hp_max=hp_max,
        ac=17,
        speed=30,
        conditions=conditions or [],
        condition_immunities=condition_immunities or [],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine() -> DnD55eEngine:
    return DnD55eEngine()


@pytest.fixture
def fighter() -> CharacterSheet:
    return make_fighter()


# ---------------------------------------------------------------------------
# apply_condition
# ---------------------------------------------------------------------------


class TestApplyCondition:
    def test_adds_condition_to_char(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        assert Condition.BLINDED in fighter.conditions

    def test_condition_not_duplicated(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        engine.apply_condition(fighter, Condition.BLINDED)
        count = fighter.conditions.count(Condition.BLINDED)
        assert count == 1

    def test_multiple_conditions_applied(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        engine.apply_condition(fighter, Condition.PRONE)
        assert Condition.BLINDED in fighter.conditions
        assert Condition.PRONE in fighter.conditions

    def test_returns_character_sheet(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.apply_condition(fighter, Condition.BLINDED)
        assert result is fighter

    def test_immune_condition_not_applied(self, engine: DnD55eEngine):
        char = make_fighter(condition_immunities=[Condition.CHARMED])
        engine.apply_condition(char, Condition.CHARMED)
        assert Condition.CHARMED not in char.conditions

    def test_string_condition_name_accepted(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, "blinded")
        assert Condition.BLINDED in fighter.conditions

    def test_duration_stored(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.FRIGHTENED, duration_rounds=3)
        assert fighter.condition_durations.get(Condition.FRIGHTENED) == 3

    def test_no_duration_no_entry(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        assert Condition.BLINDED not in fighter.condition_durations

    def test_unknown_string_condition_is_noop(self, engine: DnD55eEngine, fighter: CharacterSheet):
        """Applying an unknown string condition should not raise; it's a no-op."""
        original_count = len(fighter.conditions)
        engine.apply_condition(fighter, "nonexistent_condition")
        assert len(fighter.conditions) == original_count

    def test_incapacitating_condition_affects_can_act(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        assert fighter.can_act is True
        engine.apply_condition(fighter, Condition.PARALYZED)
        assert fighter.can_act is False

    def test_unconscious_applies_prone_too(self, engine: DnD55eEngine, fighter: CharacterSheet):
        """SRD 5.2 Unconscious: 'You have the Incapacitated and Prone
        conditions ... and you fall Prone' (EFF-14)."""
        engine.apply_condition(fighter, Condition.UNCONSCIOUS)
        assert Condition.UNCONSCIOUS in fighter.conditions
        assert Condition.PRONE in fighter.conditions

    def test_stunned_does_not_zero_speed(self, engine: DnD55eEngine, fighter: CharacterSheet):
        """2024 Stunned omits the Speed-0 clause present in Paralyzed/
        Petrified/Unconscious (EFF-06)."""
        assert fighter.effective_speed == 30
        engine.apply_condition(fighter, Condition.STUNNED)
        assert fighter.can_act is False
        assert fighter.effective_speed == 30

    def test_incapacitating_condition_breaks_concentration(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        """EFF-01: 'You lose concentration on a spell if you are
        incapacitated.' Stunning a concentrating caster ends their spell."""
        fighter.concentrating_on = "Bless"
        engine.apply_condition(fighter, Condition.STUNNED)
        assert fighter.concentrating_on is None

    def test_non_incapacitating_condition_does_not_break_concentration(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        fighter.concentrating_on = "Bless"
        engine.apply_condition(fighter, Condition.FRIGHTENED)
        assert fighter.concentrating_on == "Bless"

    def test_exhaustion_increments_level_instead_of_tagging_only(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        """EFF-03: apply_condition(EXHAUSTION) must not be a cosmetic no-op —
        it drives exhaustion_level, the field every derived effect reads."""
        assert fighter.exhaustion_level == 0
        engine.apply_condition(fighter, Condition.EXHAUSTION)
        assert fighter.exhaustion_level == 1
        assert Condition.EXHAUSTION in fighter.conditions

    def test_exhaustion_stacks_cumulatively(self, engine: DnD55eEngine, fighter: CharacterSheet):
        for _ in range(3):
            engine.apply_condition(fighter, Condition.EXHAUSTION)
        assert fighter.exhaustion_level == 3
        # The bare tag is a single membership flag, not one per level.
        assert fighter.conditions.count(Condition.EXHAUSTION) == 1

    def test_exhaustion_has_derived_mechanical_effects(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        engine.apply_condition(fighter, Condition.EXHAUSTION)
        engine.apply_condition(fighter, Condition.EXHAUSTION)
        assert fighter.d20_modifier == -4
        assert fighter.effective_speed == 20

    def test_exhaustion_level_six_is_death(self, engine: DnD55eEngine, fighter: CharacterSheet):
        for _ in range(6):
            engine.apply_condition(fighter, Condition.EXHAUSTION)
        assert fighter.is_dead is True

    def test_immune_creature_gains_no_exhaustion(self, engine: DnD55eEngine):
        char = make_fighter(condition_immunities=[Condition.EXHAUSTION])
        engine.apply_condition(char, Condition.EXHAUSTION)
        assert char.exhaustion_level == 0
        assert Condition.EXHAUSTION not in char.conditions

    def test_gain_exhaustion_helper_accepts_multiple_levels(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        from game_engine.rules.dnd_5_5e import gain_exhaustion

        gain_exhaustion(fighter, levels=2)
        assert fighter.exhaustion_level == 2


# ---------------------------------------------------------------------------
# remove_condition
# ---------------------------------------------------------------------------


class TestRemoveCondition:
    def test_removes_existing_condition(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        engine.remove_condition(fighter, Condition.BLINDED)
        assert Condition.BLINDED not in fighter.conditions

    def test_remove_nonexistent_condition_no_error(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        """Should not raise if the condition is not present."""
        engine.remove_condition(fighter, Condition.BLINDED)  # not applied
        assert Condition.BLINDED not in fighter.conditions

    def test_returns_character_sheet(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.PRONE)
        result = engine.remove_condition(fighter, Condition.PRONE)
        assert result is fighter

    def test_only_target_condition_removed(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        engine.apply_condition(fighter, Condition.PRONE)
        engine.remove_condition(fighter, Condition.BLINDED)
        assert Condition.BLINDED not in fighter.conditions
        assert Condition.PRONE in fighter.conditions

    def test_duration_cleared_on_remove(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.FRIGHTENED, duration_rounds=3)
        engine.remove_condition(fighter, Condition.FRIGHTENED)
        assert Condition.FRIGHTENED not in fighter.condition_durations

    def test_string_condition_name_accepted(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED)
        engine.remove_condition(fighter, "blinded")
        assert Condition.BLINDED not in fighter.conditions

    def test_removing_incapacitating_condition_restores_can_act(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        engine.apply_condition(fighter, Condition.STUNNED)
        assert fighter.can_act is False
        engine.remove_condition(fighter, Condition.STUNNED)
        assert fighter.can_act is True

    def test_remove_condition_from_empty_conditions_no_error(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        assert fighter.conditions == []
        engine.remove_condition(fighter, Condition.PRONE)
        assert fighter.conditions == []

    def test_removing_exhaustion_zeroes_the_level(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        """Keeps Condition.EXHAUSTION and exhaustion_level consistent even
        via the generic remove path (e.g. a full Greater Restoration cure)."""
        engine.apply_condition(fighter, Condition.EXHAUSTION)
        engine.apply_condition(fighter, Condition.EXHAUSTION)
        assert fighter.exhaustion_level == 2
        engine.remove_condition(fighter, Condition.EXHAUSTION)
        assert fighter.exhaustion_level == 0
        assert Condition.EXHAUSTION not in fighter.conditions


# ---------------------------------------------------------------------------
# tick_condition_durations
# ---------------------------------------------------------------------------


class TestTickConditionDurations:
    def test_decrements_timed_condition(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.FRIGHTENED, duration_rounds=3)
        engine.tick_condition_durations(fighter)
        assert fighter.condition_durations[Condition.FRIGHTENED] == 2

    def test_expires_condition_with_duration_one(
        self, engine: DnD55eEngine, fighter: CharacterSheet
    ):
        engine.apply_condition(fighter, Condition.BLINDED, duration_rounds=1)
        engine.tick_condition_durations(fighter)
        assert Condition.BLINDED not in fighter.conditions
        assert Condition.BLINDED not in fighter.condition_durations

    def test_indefinite_condition_not_removed(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.POISONED)  # no duration
        engine.tick_condition_durations(fighter)
        assert Condition.POISONED in fighter.conditions
        assert Condition.POISONED not in fighter.condition_durations

    def test_only_expired_condition_removed(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED, duration_rounds=1)
        engine.apply_condition(fighter, Condition.PRONE, duration_rounds=3)
        engine.tick_condition_durations(fighter)
        assert Condition.BLINDED not in fighter.conditions
        assert Condition.PRONE in fighter.conditions
        assert fighter.condition_durations[Condition.PRONE] == 2

    def test_returns_character_sheet(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.tick_condition_durations(fighter)
        assert result is fighter

    def test_noop_when_no_timed_conditions(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.CHARMED)  # indefinite
        engine.tick_condition_durations(fighter)
        assert Condition.CHARMED in fighter.conditions

    def test_multiple_expirations_in_one_tick(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_condition(fighter, Condition.BLINDED, duration_rounds=1)
        engine.apply_condition(fighter, Condition.PRONE, duration_rounds=1)
        engine.tick_condition_durations(fighter)
        assert Condition.BLINDED not in fighter.conditions
        assert Condition.PRONE not in fighter.conditions
        assert fighter.condition_durations == {}

    def test_zero_duration_condition_removed(self, engine: DnD55eEngine, fighter: CharacterSheet):
        """A duration of 0 is treated as already expired — removed immediately."""
        engine.apply_condition(fighter, Condition.STUNNED, duration_rounds=1)
        fighter.condition_durations[Condition.STUNNED] = 0
        engine.tick_condition_durations(fighter)
        assert Condition.STUNNED not in fighter.conditions
