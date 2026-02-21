"""
Tests for game_engine.types — enums, AbilityScoreSet, CharacterSheet.
"""

from __future__ import annotations

import pytest

from game_engine.types import (
    Ability,
    AbilityScoreSet,
    AttackDetails,
    CharacterClass,
    CharacterSheet,
    CharacterType,
    CombatStateData,
    Condition,
    DamageType,
    Skill,
)

# ---------------------------------------------------------------------------
# AbilityScoreSet
# ---------------------------------------------------------------------------


class TestAbilityScoreSet:
    def test_default_scores_are_10(self):
        scores = AbilityScoreSet()
        for ability in Ability:
            assert scores.get(ability) == 10

    def test_custom_construction(self):
        scores = AbilityScoreSet(
            strength=18, dexterity=14, constitution=16, intelligence=10, wisdom=12, charisma=8
        )
        assert scores.get(Ability.STRENGTH) == 18
        assert scores.get(Ability.DEXTERITY) == 14

    def test_modifier_score_10_returns_0(self):
        scores = AbilityScoreSet(strength=10)
        assert scores.modifier(Ability.STRENGTH) == 0

    def test_modifier_score_8_returns_minus_1(self):
        scores = AbilityScoreSet(strength=8)
        assert scores.modifier(Ability.STRENGTH) == -1

    def test_modifier_score_18_returns_plus_4(self):
        scores = AbilityScoreSet(strength=18)
        assert scores.modifier(Ability.STRENGTH) == 4

    def test_modifier_score_20_returns_plus_5(self):
        scores = AbilityScoreSet(strength=20)
        assert scores.modifier(Ability.STRENGTH) == 5

    def test_modifier_score_1_returns_minus_5(self):
        scores = AbilityScoreSet(dexterity=1)
        assert scores.modifier(Ability.DEXTERITY) == -5

    def test_modifier_score_30_returns_plus_10(self):
        scores = AbilityScoreSet(strength=30)
        assert scores.modifier(Ability.STRENGTH) == 10

    def test_to_dict_returns_all_six_keys(self):
        scores = AbilityScoreSet()
        d = scores.to_dict()
        for ability in Ability:
            assert ability.value in d

    def test_to_dict_values_are_correct(self):
        scores = AbilityScoreSet(
            strength=18, dexterity=14, constitution=16, intelligence=10, wisdom=12, charisma=8
        )
        d = scores.to_dict()
        assert d["strength"] == 18
        assert d["dexterity"] == 14
        assert d["constitution"] == 16
        assert d["intelligence"] == 10
        assert d["wisdom"] == 12
        assert d["charisma"] == 8

    def test_from_dict_round_trip(self):
        original = AbilityScoreSet(
            strength=15, dexterity=13, constitution=11, intelligence=9, wisdom=7, charisma=5
        )
        d = original.to_dict()
        restored = AbilityScoreSet.from_dict(d)
        for ability in Ability:
            assert restored.get(ability) == original.get(ability)

    def test_from_dict_defaults_missing_to_10(self):
        scores = AbilityScoreSet.from_dict({})
        for ability in Ability:
            assert scores.get(ability) == 10

    def test_from_dict_short_form_keys(self):
        """from_dict should accept three-letter ability abbreviations."""
        scores = AbilityScoreSet.from_dict({"str": 16, "dex": 14})
        assert scores.get(Ability.STRENGTH) == 16
        assert scores.get(Ability.DEXTERITY) == 14


# ---------------------------------------------------------------------------
# Ability enum
# ---------------------------------------------------------------------------


class TestAbilityEnum:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (10, 0),
            (8, -1),
            (18, 4),
            (20, 5),
            (1, -5),
            (30, 10),
            (11, 0),
            (12, 1),
            (13, 1),
            (15, 2),
        ],
    )
    def test_modifier_math(self, score: int, expected: int):
        assert Ability.STRENGTH.modifier(score) == expected

    def test_short_property(self):
        assert Ability.STRENGTH.short == "str"
        assert Ability.DEXTERITY.short == "dex"
        assert Ability.CONSTITUTION.short == "con"
        assert Ability.INTELLIGENCE.short == "int"
        assert Ability.WISDOM.short == "wis"
        assert Ability.CHARISMA.short == "cha"

    def test_is_str_enum(self):
        assert isinstance(Ability.STRENGTH, str)
        assert Ability.STRENGTH == "strength"


# ---------------------------------------------------------------------------
# Skill enum
# ---------------------------------------------------------------------------


class TestSkillEnum:
    @pytest.mark.parametrize(
        "skill,expected_ability",
        [
            (Skill.ATHLETICS, Ability.STRENGTH),
            (Skill.ACROBATICS, Ability.DEXTERITY),
            (Skill.STEALTH, Ability.DEXTERITY),
            (Skill.SLEIGHT_OF_HAND, Ability.DEXTERITY),
            (Skill.ARCANA, Ability.INTELLIGENCE),
            (Skill.HISTORY, Ability.INTELLIGENCE),
            (Skill.INVESTIGATION, Ability.INTELLIGENCE),
            (Skill.NATURE, Ability.INTELLIGENCE),
            (Skill.RELIGION, Ability.INTELLIGENCE),
            (Skill.ANIMAL_HANDLING, Ability.WISDOM),
            (Skill.INSIGHT, Ability.WISDOM),
            (Skill.MEDICINE, Ability.WISDOM),
            (Skill.PERCEPTION, Ability.WISDOM),
            (Skill.SURVIVAL, Ability.WISDOM),
            (Skill.DECEPTION, Ability.CHARISMA),
            (Skill.INTIMIDATION, Ability.CHARISMA),
            (Skill.PERFORMANCE, Ability.CHARISMA),
            (Skill.PERSUASION, Ability.CHARISMA),
        ],
    )
    def test_governing_ability(self, skill: Skill, expected_ability: Ability):
        assert skill.governing_ability == expected_ability

    def test_all_skills_have_governing_ability(self):
        for skill in Skill:
            assert isinstance(skill.governing_ability, Ability)


# ---------------------------------------------------------------------------
# CharacterClass enum
# ---------------------------------------------------------------------------


class TestCharacterClassEnum:
    def test_all_returns_13_classes(self):
        classes = CharacterClass.all()
        assert len(classes) == 13

    def test_str_representation(self):
        # In Python 3.12, str(StrEnum) returns the qualified name.
        # The wire-compatible string value is accessed via .value
        assert CharacterClass.FIGHTER.value == "Fighter"
        assert CharacterClass.WIZARD.value == "Wizard"
        assert CharacterClass.ROGUE.value == "Rogue"

    def test_constructable_from_value(self):
        assert CharacterClass("Fighter") == CharacterClass.FIGHTER
        assert CharacterClass("Wizard") == CharacterClass.WIZARD

    def test_is_str_enum(self):
        assert isinstance(CharacterClass.FIGHTER, str)
        assert CharacterClass.FIGHTER == "Fighter"

    def test_all_expected_classes_present(self):
        expected = {
            "Artificer",
            "Barbarian",
            "Bard",
            "Cleric",
            "Druid",
            "Fighter",
            "Monk",
            "Paladin",
            "Ranger",
            "Rogue",
            "Sorcerer",
            "Warlock",
            "Wizard",
        }
        actual = {cls.value for cls in CharacterClass}
        assert actual == expected


# ---------------------------------------------------------------------------
# CharacterSheet
# ---------------------------------------------------------------------------


class TestCharacterSheet:
    def test_minimal_construction(self):
        sheet = CharacterSheet(
            id="hero-1",
            name="Aria",
            level=1,
            char_class=CharacterClass.FIGHTER,
        )
        assert sheet.id == "hero-1"
        assert sheet.name == "Aria"
        assert sheet.level == 1
        assert sheet.char_class == CharacterClass.FIGHTER

    def test_default_ability_scores(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        for ability in Ability:
            assert sheet.ability_scores.get(ability) == 10

    def test_default_hp(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        assert sheet.hp_current == 10
        assert sheet.hp_max == 10

    def test_default_ac(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        assert sheet.ac == 10

    def test_default_speed(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        assert sheet.speed == 30

    def test_default_conditions_empty(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        assert sheet.conditions == []

    def test_is_alive_when_hp_positive(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER, hp_current=5
        )
        assert sheet.is_alive is True

    def test_is_not_alive_when_hp_zero(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER, hp_current=0
        )
        assert sheet.is_alive is False

    def test_can_act_when_healthy(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER, hp_current=10
        )
        assert sheet.can_act is True

    def test_cannot_act_when_dead(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER, hp_current=0
        )
        assert sheet.can_act is False

    def test_cannot_act_when_paralyzed(self):
        sheet = CharacterSheet(
            id="hero-1",
            name="Hero",
            level=1,
            char_class=CharacterClass.FIGHTER,
            conditions=[Condition.PARALYZED],
        )
        assert sheet.can_act is False

    def test_is_proficient_in_listed_skill(self):
        sheet = CharacterSheet(
            id="hero-1",
            name="Hero",
            level=1,
            char_class=CharacterClass.FIGHTER,
            proficient_skills=[Skill.ATHLETICS],
        )
        assert sheet.is_proficient(Skill.ATHLETICS) is True

    def test_is_not_proficient_in_unlisted_skill(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        assert sheet.is_proficient(Skill.ARCANA) is False

    def test_is_proficient_in_listed_ability(self):
        sheet = CharacterSheet(
            id="hero-1",
            name="Hero",
            level=1,
            char_class=CharacterClass.FIGHTER,
            proficient_abilities=[Ability.STRENGTH],
        )
        assert sheet.is_proficient(Ability.STRENGTH) is True

    def test_to_dict_round_trip(self):
        original = CharacterSheet(
            id="hero-1",
            name="Aria",
            level=5,
            char_class=CharacterClass.FIGHTER,
            ability_scores=AbilityScoreSet(
                strength=18, dexterity=14, constitution=16, intelligence=10, wisdom=12, charisma=8
            ),
            hp_current=40,
            hp_max=44,
            ac=16,
            speed=30,
            proficient_skills=[Skill.ATHLETICS, Skill.INTIMIDATION],
            conditions=[Condition.PRONE],
            damage_resistances=[DamageType.FIRE],
        )
        d = original.to_dict()
        restored = CharacterSheet.from_dict(d)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.level == original.level
        assert restored.char_class == original.char_class
        assert restored.hp_current == original.hp_current
        assert restored.hp_max == original.hp_max
        assert restored.ac == original.ac

    def test_char_type_default_pc(self):
        sheet = CharacterSheet(
            id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER
        )
        assert sheet.char_type == CharacterType.PC


# ---------------------------------------------------------------------------
# CombatStateData
# ---------------------------------------------------------------------------


class TestCombatStateData:
    def test_default_construction(self):
        state = CombatStateData()
        assert state.combatants == []
        assert state.round_number == 1
        assert state.current_turn_index == 0

    def test_get_combatant_found(self):
        char = CharacterSheet(id="hero-1", name="Hero", level=1, char_class=CharacterClass.FIGHTER)
        state = CombatStateData(combatants=[char])
        found = state.get_combatant("hero-1")
        assert found is char

    def test_get_combatant_not_found(self):
        state = CombatStateData()
        assert state.get_combatant("nonexistent") is None


# ---------------------------------------------------------------------------
# AttackDetails
# ---------------------------------------------------------------------------


class TestAttackDetails:
    def test_defaults(self):
        details = AttackDetails()
        assert details.weapon_name == "Unarmed Strike"
        assert details.damage_dice == "1d4"
        assert details.damage_type == DamageType.BLUDGEONING
        assert details.attack_ability == Ability.STRENGTH
        assert details.is_ranged is False

    def test_custom_construction(self):
        details = AttackDetails(
            weapon_name="Longsword",
            damage_dice="1d8",
            damage_type=DamageType.SLASHING,
            attack_ability=Ability.STRENGTH,
            is_ranged=False,
        )
        assert details.weapon_name == "Longsword"
        assert details.damage_type == DamageType.SLASHING
