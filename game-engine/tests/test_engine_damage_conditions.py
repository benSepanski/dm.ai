"""
Tests for DnD55eEngine.apply_damage(), apply_condition(), remove_condition().
"""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    AbilityScoreSet,
    CharacterClass,
    CharacterSheet,
    Condition,
    DamageType,
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
    damage_resistances: list[DamageType] | None = None,
    damage_immunities: list[DamageType] | None = None,
    damage_vulnerabilities: list[DamageType] | None = None,
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
        damage_resistances=damage_resistances or [],
        damage_immunities=damage_immunities or [],
        damage_vulnerabilities=damage_vulnerabilities or [],
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
# apply_damage — basic cases
# ---------------------------------------------------------------------------


class TestApplyDamageBasic:
    def test_fire_damage_reduces_hp(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_damage(fighter, 10, DamageType.FIRE)
        assert fighter.hp_current == 34  # 44 - 10

    def test_damage_reduces_hp_correctly(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_damage(fighter, 7, DamageType.SLASHING)
        assert fighter.hp_current == 37

    def test_damage_cannot_reduce_hp_below_zero(self, engine: DnD55eEngine):
        char = make_fighter(hp_current=5)
        engine.apply_damage(char, 100, DamageType.FIRE)
        assert char.hp_current == 0

    def test_zero_damage_no_change(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_damage(fighter, 0, DamageType.COLD)
        assert fighter.hp_current == 44

    def test_returns_character_sheet(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.apply_damage(fighter, 5, DamageType.FIRE)
        assert isinstance(result, CharacterSheet)
        assert result is fighter  # modified in place and returned

    def test_modifies_in_place(self, engine: DnD55eEngine, fighter: CharacterSheet):
        original_id = id(fighter)
        engine.apply_damage(fighter, 10, DamageType.FIRE)
        assert id(fighter) == original_id
        assert fighter.hp_current == 34

    def test_string_damage_type_accepted(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_damage(fighter, 5, "fire")
        assert fighter.hp_current == 39

    def test_multiple_hits_accumulate(self, engine: DnD55eEngine, fighter: CharacterSheet):
        engine.apply_damage(fighter, 5, DamageType.FIRE)
        engine.apply_damage(fighter, 5, DamageType.COLD)
        assert fighter.hp_current == 34


# ---------------------------------------------------------------------------
# apply_damage — resistance
# ---------------------------------------------------------------------------


class TestApplyDamageResistance:
    def test_fire_resistance_halves_damage(self, engine: DnD55eEngine):
        char = make_fighter(damage_resistances=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.FIRE)
        assert char.hp_current == 39  # 44 - 5

    def test_resistance_floors_odd_damage(self, engine: DnD55eEngine):
        """Resistance halves using integer division: 7 → 3."""
        char = make_fighter(damage_resistances=[DamageType.COLD])
        engine.apply_damage(char, 7, DamageType.COLD)
        assert char.hp_current == 44 - 3  # floor(7/2) = 3

    def test_resistance_only_applies_to_matching_type(self, engine: DnD55eEngine):
        char = make_fighter(damage_resistances=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.COLD)  # no resistance to cold
        assert char.hp_current == 34

    def test_resistance_large_damage(self, engine: DnD55eEngine):
        char = make_fighter(damage_resistances=[DamageType.SLASHING])
        engine.apply_damage(char, 40, DamageType.SLASHING)
        assert char.hp_current == 44 - 20  # 40 // 2 = 20


# ---------------------------------------------------------------------------
# apply_damage — immunity
# ---------------------------------------------------------------------------


class TestApplyDamageImmunity:
    def test_immunity_prevents_all_damage(self, engine: DnD55eEngine):
        char = make_fighter(damage_immunities=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.FIRE)
        assert char.hp_current == 44

    def test_immunity_only_applies_to_matching_type(self, engine: DnD55eEngine):
        char = make_fighter(damage_immunities=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.COLD)
        assert char.hp_current == 34

    def test_immunity_takes_precedence_over_resistance(self, engine: DnD55eEngine):
        """If somehow both immunity and resistance exist, immunity wins (damage = 0)."""
        char = make_fighter(
            damage_immunities=[DamageType.FIRE],
            damage_resistances=[DamageType.FIRE],
        )
        engine.apply_damage(char, 10, DamageType.FIRE)
        assert char.hp_current == 44


# ---------------------------------------------------------------------------
# apply_damage — vulnerability
# ---------------------------------------------------------------------------


class TestApplyDamageVulnerability:
    def test_vulnerability_doubles_damage(self, engine: DnD55eEngine):
        char = make_fighter(damage_vulnerabilities=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.FIRE)
        assert char.hp_current == 44 - 20  # 10 * 2 = 20

    def test_vulnerability_only_affects_matching_type(self, engine: DnD55eEngine):
        char = make_fighter(damage_vulnerabilities=[DamageType.FIRE])
        engine.apply_damage(char, 10, DamageType.COLD)
        assert char.hp_current == 34


# ---------------------------------------------------------------------------
# apply_damage — petrified (resistance to all damage)
# ---------------------------------------------------------------------------


class TestApplyDamagePetrified:
    def test_petrified_halves_non_immune_damage(self, engine: DnD55eEngine):
        char = make_fighter(conditions=[Condition.PETRIFIED])
        engine.apply_damage(char, 10, DamageType.SLASHING)
        assert char.hp_current == 39  # 10 // 2 = 5 → 44 - 5

    def test_petrified_immune_to_poison(self, engine: DnD55eEngine):
        """Petrified condition makes creature immune to poison & psychic per CONDITION_EFFECTS."""
        char = make_fighter(
            conditions=[Condition.PETRIFIED],
            damage_immunities=[DamageType.POISON],
        )
        engine.apply_damage(char, 20, DamageType.POISON)
        assert char.hp_current == 44


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
