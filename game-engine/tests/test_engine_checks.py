"""
Tests for DnD55eEngine.roll_check(), roll_initiative(), and proficiency bonus.
"""

from __future__ import annotations

import random

import pytest

from game_engine.interface import CheckResult
from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import (
    Ability,
    CharacterClass,
    CharacterSheet,
    Skill,
    AbilityScoreSet,
)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def make_fighter(
    level: int = 5,
    strength: int = 18,
    dexterity: int = 14,
    constitution: int = 16,
    intelligence: int = 10,
    wisdom: int = 12,
    charisma: int = 8,
    proficient_skills: list[Skill] | None = None,
    proficient_abilities: list[Ability] | None = None,
) -> CharacterSheet:
    """Return a CharacterSheet for a Fighter with sensible defaults."""
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
        hp_current=44,
        hp_max=44,
        ac=17,
        speed=30,
        proficient_skills=proficient_skills or [Skill.ATHLETICS, Skill.INTIMIDATION],
        proficient_abilities=proficient_abilities or [],
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
# CheckResult attributes
# ---------------------------------------------------------------------------


class TestCheckResultAttributes:
    def test_result_has_success_attribute(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, Skill.ATHLETICS, dc=10)
        assert hasattr(result, "success")
        assert isinstance(result.success, bool)

    def test_result_has_roll_attribute(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, Skill.ATHLETICS, dc=10)
        assert hasattr(result, "roll")
        assert 1 <= result.roll <= 20

    def test_result_has_total_attribute(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, Skill.ATHLETICS, dc=10)
        assert hasattr(result, "total")

    def test_result_has_dc_attribute(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, Skill.ATHLETICS, dc=15)
        assert result.dc == 15

    def test_result_has_margin_attribute(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, Skill.ATHLETICS, dc=10)
        assert hasattr(result, "margin")
        assert result.margin == result.total - result.dc

    def test_result_is_check_result_instance(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, Skill.ATHLETICS, dc=10)
        assert isinstance(result, CheckResult)


# ---------------------------------------------------------------------------
# Success / failure based on DC
# ---------------------------------------------------------------------------


class TestCheckSuccessFailure:
    def test_low_dc_str_20_usually_passes(self, engine: DnD55eEngine):
        """STR 20 (+5) + proficiency for Athletics (level 5 = +3) → +8 total.
        DC 10 should pass on nearly every roll (need at least 2 on d20)."""
        char = make_fighter(strength=20, level=5,
                            proficient_skills=[Skill.ATHLETICS])
        results = [engine.roll_check(char, Skill.ATHLETICS, dc=10) for _ in range(30)]
        passes = sum(1 for r in results if r.success)
        # With +8 mod, need roll >= 2 to hit DC 10; P(pass) ≈ 95%
        assert passes >= 25

    def test_high_dc_low_stat_usually_fails(self, engine: DnD55eEngine):
        """INT 8 (−1) with no proficiency vs DC 25 should almost always fail."""
        char = make_fighter(intelligence=8)
        results = [engine.roll_check(char, Ability.INTELLIGENCE, dc=25) for _ in range(30)]
        fails = sum(1 for r in results if not r.success)
        # Need roll >= 26 which is impossible; always fails.
        assert fails == 30

    def test_success_flag_matches_total_vs_dc(self, engine: DnD55eEngine, fighter: CharacterSheet):
        """success should be True iff total >= dc."""
        for _ in range(40):
            result = engine.roll_check(fighter, Skill.ATHLETICS, dc=12)
            if result.total >= result.dc:
                assert result.success is True
            else:
                assert result.success is False


# ---------------------------------------------------------------------------
# Proficiency bonus interaction
# ---------------------------------------------------------------------------


class TestProficiencyBonus:
    def test_proficient_total_higher_than_nonproficient(self, engine: DnD55eEngine):
        """Proficient character should have a higher average total."""
        proficient = make_fighter(
            strength=10, level=5, proficient_skills=[Skill.ATHLETICS]
        )
        non_proficient = make_fighter(
            strength=10, level=5, proficient_skills=[]
        )

        # Run many trials and compare means
        random.seed(0)
        prof_totals = [
            engine.roll_check(proficient, Skill.ATHLETICS, dc=1).total
            for _ in range(100)
        ]
        random.seed(0)
        non_prof_totals = [
            engine.roll_check(non_proficient, Skill.ATHLETICS, dc=1).total
            for _ in range(100)
        ]

        assert sum(prof_totals) > sum(non_prof_totals)

    def test_prof_bonus_added_for_proficient_skill(self, engine: DnD55eEngine):
        """With a fixed seed, verify the bonus is exactly prof_bonus more."""
        char = make_fighter(
            strength=10,  # modifier = 0 for clean arithmetic
            level=5,      # proficiency bonus = +3
            proficient_skills=[Skill.ATHLETICS],
        )
        non_prof_char = make_fighter(
            strength=10, level=5, proficient_skills=[]
        )

        # Force same dice rolls
        random.seed(7)
        result_prof = engine.roll_check(char, Skill.ATHLETICS, dc=1)
        random.seed(7)
        result_non_prof = engine.roll_check(non_prof_char, Skill.ATHLETICS, dc=1)

        # Same roll, same ability mod; prof should have total 3 higher (level-5 bonus)
        assert result_prof.total == result_non_prof.total + 3

    def test_no_proficiency_bonus_for_non_proficient(self, engine: DnD55eEngine):
        char = make_fighter(
            strength=10,  # modifier = 0
            level=5,      # prof bonus = +3
            proficient_skills=[],
        )
        # Without proficiency, total = roll + ability_mod only
        random.seed(42)
        result = engine.roll_check(char, Skill.ATHLETICS, dc=1)
        random.seed(42)
        raw_roll, _ = __import__("game_engine.core.dice", fromlist=["roll_dice"]).roll_dice(1, 20)
        expected_total = raw_roll + 4  # STR default=18, modifier=+4

        # Make char with str=10 so mod=0
        assert result.total == raw_roll + 0  # 0 ability mod, no proficiency

    def test_proficiency_bonus_for_proficient_ability(self, engine: DnD55eEngine):
        """Proficiency in Ability.STRENGTH adds prof bonus to STR checks."""
        char = make_fighter(
            strength=10, level=1,  # prof = +2
            proficient_abilities=[Ability.STRENGTH],
            proficient_skills=[],
        )
        non_prof_char = make_fighter(
            strength=10, level=1, proficient_skills=[], proficient_abilities=[]
        )
        random.seed(15)
        result_prof = engine.roll_check(char, Ability.STRENGTH, dc=1)
        random.seed(15)
        result_non_prof = engine.roll_check(non_prof_char, Ability.STRENGTH, dc=1)
        assert result_prof.total == result_non_prof.total + 2


# ---------------------------------------------------------------------------
# String-based skill lookup
# ---------------------------------------------------------------------------


class TestStringSkillLookup:
    def test_skill_by_string_name(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, "athletics", dc=10)
        assert isinstance(result, CheckResult)

    def test_ability_by_string_name(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_check(fighter, "strength", dc=10)
        assert isinstance(result, CheckResult)

    def test_unknown_skill_raises_value_error(self, engine: DnD55eEngine, fighter: CharacterSheet):
        with pytest.raises(ValueError):
            engine.roll_check(fighter, "flying", dc=10)


# ---------------------------------------------------------------------------
# Advantage / disadvantage
# ---------------------------------------------------------------------------


class TestAdvantageDisadvantage:
    def test_advantage_tends_higher_total(self, engine: DnD55eEngine):
        char = make_fighter(strength=10, proficient_skills=[])
        random.seed(0)
        normal_totals = [
            engine.roll_check(char, Skill.ATHLETICS, dc=1).total
            for _ in range(100)
        ]
        random.seed(0)
        adv_totals = [
            engine.roll_check(char, Skill.ATHLETICS, dc=1, advantage=True).total
            for _ in range(100)
        ]
        assert sum(adv_totals) >= sum(normal_totals)

    def test_disadvantage_tends_lower_total(self, engine: DnD55eEngine):
        char = make_fighter(strength=10, proficient_skills=[])
        random.seed(0)
        normal_totals = [
            engine.roll_check(char, Skill.ATHLETICS, dc=1).total
            for _ in range(100)
        ]
        random.seed(0)
        dis_totals = [
            engine.roll_check(char, Skill.ATHLETICS, dc=1, disadvantage=True).total
            for _ in range(100)
        ]
        assert sum(dis_totals) <= sum(normal_totals)


# ---------------------------------------------------------------------------
# roll_initiative
# ---------------------------------------------------------------------------


class TestRollInitiative:
    def test_returns_integer(self, engine: DnD55eEngine, fighter: CharacterSheet):
        result = engine.roll_initiative(fighter)
        assert isinstance(result, int)

    def test_result_in_expected_range(self, engine: DnD55eEngine):
        """DEX 14 → modifier +2; total range = [3, 22]."""
        char = make_fighter(dexterity=14)
        for _ in range(50):
            total = engine.roll_initiative(char)
            assert 3 <= total <= 22

    def test_higher_dex_produces_higher_average(self, engine: DnD55eEngine):
        high_dex_char = make_fighter(dexterity=20)  # +5 modifier
        low_dex_char = make_fighter(dexterity=8)    # -1 modifier

        random.seed(123)
        high_totals = [engine.roll_initiative(high_dex_char) for _ in range(100)]
        random.seed(123)
        low_totals = [engine.roll_initiative(low_dex_char) for _ in range(100)]

        assert sum(high_totals) > sum(low_totals)


# ---------------------------------------------------------------------------
# calculate_proficiency_bonus
# ---------------------------------------------------------------------------


class TestCalculateProficiencyBonus:
    @pytest.mark.parametrize(
        "level,expected",
        [
            (1, 2), (4, 2),
            (5, 3), (8, 3),
            (9, 4), (12, 4),
            (13, 5), (16, 5),
            (17, 6), (20, 6),
        ],
    )
    def test_proficiency_bonus(self, engine: DnD55eEngine, level: int, expected: int):
        assert engine.calculate_proficiency_bonus(level) == expected

    def test_level_0_raises(self, engine: DnD55eEngine):
        with pytest.raises(ValueError):
            engine.calculate_proficiency_bonus(0)

    def test_level_21_raises(self, engine: DnD55eEngine):
        with pytest.raises(ValueError):
            engine.calculate_proficiency_bonus(21)
