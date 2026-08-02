"""
Tests for DnD55eEngine.apply_damage() and 0-HP/death branching.
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
