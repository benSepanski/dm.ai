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
    CharacterType,
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
# apply_damage — effective (post-mitigation) amount returned, for
# concentration-check callers (Workstream F.1 / EFF-07)
# ---------------------------------------------------------------------------


class TestApplyDamageEffectiveAmount:
    """_apply_damage_effective returns the post-immunity/resistance/
    vulnerability damage, which callers (weapon attacks, spell damage) use
    to decide whether — and at what DC — a concentration save is rolled."""

    def test_normal_damage_returns_full_amount(self):
        from game_engine.rules.dnd_5_5e._damage import _apply_damage_effective

        char = make_fighter()
        effective = _apply_damage_effective(char, 10, DamageType.SLASHING)
        assert effective == 10

    def test_immune_target_returns_zero(self):
        """EFF-07: an immune target takes 0 effective damage, so no
        concentration save should ever be rolled for this hit."""
        from game_engine.rules.dnd_5_5e._damage import _apply_damage_effective

        char = make_fighter(damage_immunities=[DamageType.FIRE])
        effective = _apply_damage_effective(char, 40, DamageType.FIRE)
        assert effective == 0
        assert char.hp_current == 44  # unchanged

    def test_resistant_target_returns_halved_amount(self):
        from game_engine.rules.dnd_5_5e._damage import _apply_damage_effective

        char = make_fighter(damage_resistances=[DamageType.FIRE])
        effective = _apply_damage_effective(char, 11, DamageType.FIRE)
        assert effective == 5  # floor(11 / 2)

    def test_temp_hp_fully_absorbing_still_reports_effective_damage(self):
        """Effective damage is the post-immunity/resistance figure, not what
        was left over after temp HP absorption — concentration DC is based
        on the damage taken, not the HP actually lost."""
        from game_engine.rules.dnd_5_5e._damage import _apply_damage_effective

        char = make_fighter()
        char.temp_hp = 100
        effective = _apply_damage_effective(char, 12, DamageType.SLASHING)
        assert effective == 12
        assert char.hp_current == 44  # fully absorbed by temp HP


# ---------------------------------------------------------------------------
# apply_damage — petrified (resistance to all damage)
# ---------------------------------------------------------------------------


class TestApplyDamagePetrified:
    def test_petrified_halves_non_immune_damage(self, engine: DnD55eEngine):
        char = make_fighter(conditions=[Condition.PETRIFIED])
        engine.apply_damage(char, 10, DamageType.SLASHING)
        assert char.hp_current == 39  # 10 // 2 = 5 → 44 - 5

    def test_petrified_resists_but_does_not_negate_poison_damage(self, engine: DnD55eEngine):
        """SRD 5.2: Petrified has Resistance to all damage (not immunity) to
        poison/psychic — only the Poisoned *condition* is immune (EFF-05)."""
        char = make_fighter(conditions=[Condition.PETRIFIED])
        engine.apply_damage(char, 20, DamageType.POISON)
        assert char.hp_current == 34  # 20 // 2 = 10 resisted, not negated

    def test_petrified_resists_but_does_not_negate_psychic_damage(self, engine: DnD55eEngine):
        char = make_fighter(conditions=[Condition.PETRIFIED])
        engine.apply_damage(char, 20, DamageType.PSYCHIC)
        assert char.hp_current == 34  # 20 // 2 = 10 resisted, not negated

    def test_petrified_immune_to_poisoned_condition(self, engine: DnD55eEngine):
        """SRD 5.2: 'Poison Immunity. You have Immunity to the Poisoned
        condition' while Petrified."""
        char = make_fighter(conditions=[Condition.PETRIFIED])
        engine.apply_condition(char, Condition.POISONED)
        assert Condition.POISONED not in char.conditions

    def test_petrified_immune_to_poison_explicit_immunities_still_work(self, engine: DnD55eEngine):
        """Explicit damage_immunities stack correctly with petrified condition."""
        char = make_fighter(
            conditions=[Condition.PETRIFIED],
            damage_immunities=[DamageType.POISON],
        )
        engine.apply_damage(char, 20, DamageType.POISON)
        assert char.hp_current == 44

    def test_petrified_resistance_via_condition_effect_not_hardcode(self, engine: DnD55eEngine):
        """PETRIFIED all-damage resistance comes from ConditionEffect.damage_resistances_all,
        not a hardcoded isinstance check — so any future condition with the same flag works."""
        from game_engine.core.conditions import CONDITION_EFFECTS

        # Verify the data model: PETRIFIED carries damage_resistances_all=True.
        petrified_effect = CONDITION_EFFECTS[Condition.PETRIFIED]
        assert petrified_effect.damage_resistances_all is True

        # The engine halves non-immune damage through the generic mechanism.
        char = make_fighter(conditions=[Condition.PETRIFIED])
        engine.apply_damage(char, 20, DamageType.FIRE)
        assert char.hp_current == 44 - 10  # 20 // 2 = 10


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


# ---------------------------------------------------------------------------
# Monsters at 0 HP die outright (2024 PHB — death saves are for PCs/NPCs)
# ---------------------------------------------------------------------------


def make_monster(hp_current: int = 10, hp_max: int = 10) -> CharacterSheet:
    return CharacterSheet(
        id="monster-1",
        name="Goblin",
        level=1,
        char_class=CharacterClass.FIGHTER,
        hp_current=hp_current,
        hp_max=hp_max,
        ac=13,
        char_type=CharacterType.MONSTER,
    )


class TestMonsterDeath:
    def test_monster_dies_at_zero_hp(self, engine: DnD55eEngine):
        monster = make_monster(hp_current=5)
        engine.apply_damage(monster, 5, DamageType.SLASHING)
        assert monster.hp_current == 0
        assert monster.is_dead
        assert Condition.UNCONSCIOUS not in monster.conditions
        assert monster.death_saves.failures == 0

    def test_monster_at_zero_hp_dies_from_further_damage(self, engine: DnD55eEngine):
        monster = make_monster(hp_current=0)
        engine.apply_damage(monster, 1, DamageType.PIERCING)
        assert monster.is_dead

    def test_monster_death_ends_concentration(self, engine: DnD55eEngine):
        monster = make_monster(hp_current=3)
        monster.concentrating_on = "Hold Person"
        engine.apply_damage(monster, 3, DamageType.FIRE)
        assert monster.concentrating_on is None

    def test_pc_at_zero_hp_still_falls_unconscious(self, engine: DnD55eEngine):
        pc = make_fighter(hp_current=5, hp_max=44)
        engine.apply_damage(pc, 5, DamageType.SLASHING)
        assert pc.hp_current == 0
        assert not pc.is_dead
        assert pc.is_dying
        assert Condition.UNCONSCIOUS in pc.conditions

    def test_dead_monster_is_not_dying(self, engine: DnD55eEngine):
        monster = make_monster(hp_current=1)
        engine.apply_damage(monster, 1, DamageType.BLUDGEONING)
        assert not monster.is_dying
