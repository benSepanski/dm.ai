"""Tests for XP progression, leveling, multiclassing, and character creation."""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e.character_builder import (
    POINT_BUY_BUDGET,
    STANDARD_ARRAY,
    build_character,
    is_legal_ability_scores,
    is_standard_array,
    is_valid_manual_scores,
    is_valid_point_buy,
    point_buy_cost,
)
from game_engine.rules.dnd_5_5e.progression import (
    XP_THRESHOLDS,
    can_multiclass,
    level_for_xp,
    level_up,
    xp_for_level,
)
from game_engine.types import (
    Ability,
    AbilityScoreSet,
    Background,
    CharacterClass,
    CharacterSheet,
    ClassLevelEntry,
    HitDicePool,
    Skill,
    Species,
    Subclass,
)


def _scores(**kwargs) -> AbilityScoreSet:
    return AbilityScoreSet(**kwargs)


class TestXp:
    def test_thresholds_cover_all_levels(self):
        assert set(XP_THRESHOLDS) == set(range(1, 21))
        assert XP_THRESHOLDS[20] == 355_000

    def test_level_for_xp(self):
        assert level_for_xp(0) == 1
        assert level_for_xp(299) == 1
        assert level_for_xp(300) == 2
        assert level_for_xp(6_500) == 5
        assert level_for_xp(999_999) == 20

    def test_xp_for_level_bounds(self):
        assert xp_for_level(5) == 6_500
        with pytest.raises(ValueError):
            xp_for_level(21)


class TestLevelUp:
    def _fighter(self) -> CharacterSheet:
        return CharacterSheet(
            id="f",
            name="Fighter",
            level=1,
            char_class=CharacterClass.FIGHTER,
            ability_scores=_scores(strength=16, constitution=14),
            hp_current=12,
            hp_max=12,
            class_levels=[ClassLevelEntry(CharacterClass.FIGHTER, 1)],
            hit_dice=[HitDicePool(die_size=10, maximum=1, remaining=1)],
        )

    def test_average_hp_gain(self):
        sheet = self._fighter()
        level_up(sheet)
        # d10 average 6 + CON 2 = 8
        assert sheet.level == 2
        assert sheet.hp_max == 20
        assert sheet.class_levels[0].level == 2

    def test_rolled_hp_gain(self):
        sheet = self._fighter()
        level_up(sheet, rolled_hp=10)
        assert sheet.hp_max == 24  # 12 + 10 + 2

    def test_hit_dice_pool_grows(self):
        sheet = self._fighter()
        level_up(sheet)
        assert sheet.hit_dice[0].die_size == 10
        assert sheet.hit_dice[0].maximum == 2

    def test_subclass_recorded(self):
        sheet = self._fighter()
        level_up(sheet)
        level_up(sheet, subclass=Subclass.CHAMPION)
        assert sheet.subclass is Subclass.CHAMPION
        assert sheet.class_levels[0].subclass is Subclass.CHAMPION

    def test_multiclass_into_wizard_requires_int_13(self):
        sheet = self._fighter()  # INT 10
        check = can_multiclass(sheet, CharacterClass.WIZARD)
        assert not check.allowed
        with pytest.raises(ValueError):
            level_up(sheet, CharacterClass.WIZARD)

    def test_multiclass_grants_slots(self):
        sheet = self._fighter()
        sheet.ability_scores.set(Ability.INTELLIGENCE, 14)
        level_up(sheet, CharacterClass.WIZARD)
        assert sheet.class_level(CharacterClass.WIZARD) == 1
        assert sheet.level == 2
        assert [(s.slot_level, s.maximum) for s in sheet.spell_slots] == [(1, 2)]
        # A d6 hit dice pool appears alongside the d10.
        assert {p.die_size for p in sheet.hit_dice} == {10, 6}

    def test_cannot_exceed_level_20(self):
        sheet = self._fighter()
        sheet.level = 20
        with pytest.raises(ValueError):
            level_up(sheet)


class TestAbilityGeneration:
    def test_standard_array(self):
        assert sorted(STANDARD_ARRAY) == [8, 10, 12, 13, 14, 15]
        scores = _scores(
            strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8
        )
        assert is_standard_array(scores)
        assert not is_standard_array(_scores())

    def test_point_buy(self):
        scores = _scores(
            strength=15, dexterity=15, constitution=15, intelligence=8, wisdom=8, charisma=8
        )
        assert point_buy_cost(scores) == 27 == POINT_BUY_BUDGET
        assert is_valid_point_buy(scores)
        too_expensive = _scores(
            strength=15, dexterity=15, constitution=15, intelligence=9, wisdom=8, charisma=8
        )
        assert not is_valid_point_buy(too_expensive)
        with pytest.raises(ValueError):
            point_buy_cost(_scores(strength=18))

    def test_manual_range(self):
        assert is_valid_manual_scores(_scores(strength=18, charisma=3))
        assert not is_valid_manual_scores(_scores(strength=19))

    def test_legal_ability_scores_accepts_any_supported_method(self):
        standard = _scores(
            strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8
        )
        point_buy = _scores(
            strength=15, dexterity=15, constitution=15, intelligence=8, wisdom=8, charisma=8
        )
        rolled = _scores(
            strength=18, dexterity=16, constitution=14, intelligence=12, wisdom=9, charisma=3
        )
        assert is_legal_ability_scores(standard)
        assert is_legal_ability_scores(point_buy)
        assert is_legal_ability_scores(rolled)

    def test_legal_ability_scores_rejects_impossible_scores(self):
        assert not is_legal_ability_scores(_scores(strength=20))
        all_twenties = _scores(
            strength=20, dexterity=20, constitution=20, intelligence=20, wisdom=20, charisma=20
        )
        assert not is_legal_ability_scores(all_twenties)


class TestBuildCharacter:
    def _build(self, **overrides):
        params = dict(
            char_id="pc1",
            name="Aria",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(
                strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8
            ),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
            armor_name="Chain Mail",
        )
        params.update(overrides)
        return build_character(**params)

    def test_background_increases_applied(self):
        result = self._build()
        # Soldier: STR/DEX/CON; default +2 STR, +1 DEX
        assert result.sheet.ability_scores.get(Ability.STRENGTH) == 17
        assert result.sheet.ability_scores.get(Ability.DEXTERITY) == 15

    def test_hp_ac_and_saves(self):
        result = self._build()
        sheet = result.sheet
        assert sheet.hp_max == 11  # d10 + CON 1
        assert sheet.ac == 16  # chain mail
        assert Ability.STRENGTH in sheet.proficient_abilities
        assert Ability.CONSTITUTION in sheet.proficient_abilities

    def test_background_skills_and_feat(self):
        result = self._build()
        sheet = result.sheet
        assert Skill.ATHLETICS in sheet.proficient_skills
        assert Skill.INTIMIDATION in sheet.proficient_skills  # Soldier
        assert len(sheet.feats) == 1  # Savage Attacker origin feat

    def test_wizard_gets_slots(self):
        result = self._build(
            character_class=CharacterClass.WIZARD,
            background=Background.SAGE,
            skill_choices=[Skill.ARCANA, Skill.INVESTIGATION],
            armor_name=None,
        )
        assert [(s.slot_level, s.maximum) for s in result.sheet.spell_slots] == [(1, 2)]

    def test_barbarian_unarmored_defense(self):
        result = self._build(
            character_class=CharacterClass.BARBARIAN,
            background=Background.FARMER,
            skill_choices=[Skill.ATHLETICS, Skill.SURVIVAL],
            armor_name=None,
            ability_scores=_scores(strength=15, dexterity=14, constitution=14),
        )
        # 10 + DEX 2 + CON 3 (farmer +1 CON? default +2 STR +1 CON)
        sheet = result.sheet
        dex = sheet.ability_scores.modifier(Ability.DEXTERITY)
        con = sheet.ability_scores.modifier(Ability.CONSTITUTION)
        assert sheet.ac == 10 + dex + con

    def test_dwarf_toughness_and_darkvision(self):
        result = self._build(species=Species.DWARF)
        assert result.sheet.hp_max == 12  # 11 + 1 dwarven toughness
        assert result.sheet.darkvision_ft == 120
        from game_engine.types import DamageType

        assert DamageType.POISON in result.sheet.damage_resistances

    def test_goliath_speed(self):
        result = self._build(species=Species.GOLIATH)
        assert result.sheet.speed == 35

    def test_invalid_skill_choice_warns(self):
        result = self._build(skill_choices=[Skill.ARCANA, Skill.PERCEPTION])
        assert any("not a Fighter skill" in w for w in result.warnings)

    def test_untrained_armor_warns(self):
        result = self._build(
            character_class=CharacterClass.WIZARD,
            background=Background.SAGE,
            skill_choices=[Skill.ARCANA, Skill.HISTORY],
            armor_name="Plate Armor",
        )
        assert any("armor training" in w for w in result.warnings)

    def test_impossible_ability_scores_rejected(self):
        # All-20s isn't reachable by Standard Array, Point Buy, or Manual/Rolled
        # (max 18) generation — must be rejected, not silently accepted (PT-26).
        with pytest.raises(ValueError):
            self._build(
                ability_scores=_scores(
                    strength=20,
                    dexterity=20,
                    constitution=20,
                    intelligence=20,
                    wisdom=20,
                    charisma=20,
                )
            )


class TestBuildCharacterVersatileFeat:
    """PT-30: Human's Versatile trait grants an extra Origin feat of choice,
    on top of the background's origin feat."""

    def _build(self, **overrides):
        params = dict(
            char_id="pc1",
            name="Aria",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(
                strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8
            ),
            skill_choices=[Skill.ATHLETICS, Skill.PERCEPTION],
            armor_name="Chain Mail",
        )
        params.update(overrides)
        return build_character(**params)

    def test_versatile_feat_added_alongside_background_feat(self):
        from game_engine.types import Feat

        result = self._build(species_trait_choices={"Versatile": "Alert"})
        assert result.sheet.feats == [Feat.SAVAGE_ATTACKER, Feat.ALERT]
        assert not any("Versatile" in w for w in result.warnings)

    def test_missing_versatile_choice_warns_not_errors(self):
        from game_engine.types import Feat

        result = self._build()
        assert any("Versatile requires a choice" in w for w in result.warnings)
        assert result.sheet.feats == [Feat.SAVAGE_ATTACKER]

    def test_illegal_versatile_choice_rejected(self):
        with pytest.raises(ValueError, match="Versatile"):
            self._build(species_trait_choices={"Versatile": "Not A Feat"})

    def test_non_origin_feat_rejected(self):
        # Ability Score Improvement is a General feat, not in Versatile's
        # closed Origin-feat option set.
        with pytest.raises(ValueError, match="Versatile"):
            self._build(species_trait_choices={"Versatile": "Ability Score Improvement"})

    def test_versatile_duplicating_background_feat_warns_and_is_not_added_twice(self):
        from game_engine.types import Feat

        result = self._build(species_trait_choices={"Versatile": "Savage Attacker"})
        assert result.sheet.feats == [Feat.SAVAGE_ATTACKER]
        assert any("duplicates the background's origin feat" in w for w in result.warnings)

    def test_versatile_tough_grants_hp_bonus(self):
        result = self._build(
            background=Background.FARMER,
            skill_choices=[Skill.ATHLETICS, Skill.SURVIVAL],
            species_trait_choices={"Versatile": "Alert"},
        )
        # d10 + CON 2 + Farmer's own Tough (+2) = 14
        assert result.sheet.hp_max == 14

    def test_versatile_duplicating_tough_background_feat_grants_hp_once(self):
        result = self._build(
            background=Background.FARMER,
            skill_choices=[Skill.ATHLETICS, Skill.SURVIVAL],
            species_trait_choices={"Versatile": "Tough"},
        )
        # Duplicate pick is dropped, not stacked: d10 + CON 2 + Tough once (+2) = 14
        assert result.sheet.hp_max == 14
        assert any("duplicates the background's origin feat" in w for w in result.warnings)


class TestBuildCharacterSpeciesAndSpellChoices:
    """PT-19: species sub-choices (Elf) and starting cantrips/spells."""

    def _build(self, **overrides):
        params = dict(
            char_id="pc1",
            name="Maret",
            character_class=CharacterClass.WIZARD,
            species=Species.ELF,
            background=Background.SAGE,
            ability_scores=_scores(
                strength=8, dexterity=14, constitution=13, intelligence=15, wisdom=12, charisma=10
            ),
            skill_choices=[Skill.ARCANA, Skill.INVESTIGATION],
        )
        params.update(overrides)
        return build_character(**params)

    def test_elf_wizard_persists_lineage_keen_senses_and_spells(self):
        from game_engine.types import SpeciesLineage

        result = self._build(
            species_trait_choices={"Elven Lineage": "Drow", "Keen Senses": "perception"},
            starting_cantrips=["Fire Bolt", "Light", "Acid Splash"],
            starting_spells=["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
        )
        sheet = result.sheet
        assert sheet.species_lineage is SpeciesLineage.DROW
        assert Skill.PERCEPTION in sheet.proficient_skills
        assert sheet.known_spells == ["Fire Bolt", "Light", "Acid Splash"]
        assert sheet.prepared_spells == [
            "Magic Missile",
            "Shield",
            "Mage Armor",
            "Detect Magic",
        ]
        assert not result.warnings

    def test_missing_species_trait_choices_warns_not_errors(self):
        result = self._build(
            starting_cantrips=["Fire Bolt", "Light", "Acid Splash"],
            starting_spells=["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
        )
        assert any("Elven Lineage requires a choice" in w for w in result.warnings)
        assert any("Keen Senses requires a choice" in w for w in result.warnings)
        assert result.sheet.species_lineage is None

    def test_missing_starting_spells_warns_not_errors(self):
        result = self._build(
            species_trait_choices={"Elven Lineage": "Drow", "Keen Senses": "perception"},
        )
        assert any("starting cantrip" in w for w in result.warnings)
        assert any("starting spell" in w for w in result.warnings)
        assert result.sheet.known_spells == []
        assert result.sheet.prepared_spells == []

    def test_illegal_lineage_choice_rejected(self):
        with pytest.raises(ValueError, match="Elven Lineage"):
            self._build(
                species_trait_choices={"Elven Lineage": "Sun Elf", "Keen Senses": "perception"},
                starting_cantrips=["Fire Bolt", "Light", "Acid Splash"],
                starting_spells=["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
            )

    def test_illegal_keen_senses_choice_rejected(self):
        with pytest.raises(ValueError, match="Keen Senses"):
            self._build(
                species_trait_choices={"Elven Lineage": "Drow", "Keen Senses": "athletics"},
                starting_cantrips=["Fire Bolt", "Light", "Acid Splash"],
                starting_spells=["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
            )

    def test_illegal_cantrip_for_class_rejected(self):
        with pytest.raises(ValueError, match="Guidance"):
            self._build(
                species_trait_choices={"Elven Lineage": "Drow", "Keen Senses": "perception"},
                starting_cantrips=["Guidance", "Light", "Acid Splash"],
                starting_spells=["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
            )

    def test_illegal_spell_for_class_rejected(self):
        with pytest.raises(ValueError, match="Cure Wounds"):
            self._build(
                species_trait_choices={"Elven Lineage": "Drow", "Keen Senses": "perception"},
                starting_cantrips=["Fire Bolt", "Light", "Acid Splash"],
                starting_spells=["Cure Wounds", "Shield", "Mage Armor", "Detect Magic"],
            )

    def test_wrong_cantrip_count_warns(self):
        result = self._build(
            species_trait_choices={"Elven Lineage": "Drow", "Keen Senses": "perception"},
            starting_cantrips=["Fire Bolt", "Light"],
            starting_spells=["Magic Missile", "Shield", "Mage Armor", "Detect Magic"],
        )
        assert any("expects 3 starting cantrip" in w for w in result.warnings)

    def test_non_wizard_caster_uses_known_spells(self):
        result = self._build(
            character_class=CharacterClass.SORCERER,
            species=Species.HUMAN,
            background=Background.NOBLE,
            skill_choices=[Skill.PERSUASION, Skill.INTIMIDATION],
            starting_cantrips=["Fire Bolt", "Light", "Acid Splash", "Ray of Frost"],
            starting_spells=["Magic Missile", "Shield"],
        )
        sheet = result.sheet
        # Sorcerer is a known-spell caster: level-1 spells land in known_spells,
        # not prepared_spells (Wizard-only).
        assert "Magic Missile" in sheet.known_spells
        assert "Shield" in sheet.known_spells
        assert sheet.prepared_spells == []


class TestBuildCharacterHumanSkillful:
    """PT-31: Human's Skillful trait grants an extra skill proficiency of
    choice, on top of class/background skills (mirrors Elf's Keen Senses)."""

    def _build(self, **overrides):
        params = dict(
            char_id="pc1",
            name="Roderick",
            character_class=CharacterClass.FIGHTER,
            species=Species.HUMAN,
            background=Background.SOLDIER,
            ability_scores=_scores(
                strength=15, dexterity=14, constitution=13, intelligence=12, wisdom=10, charisma=8
            ),
            skill_choices=[Skill.ATHLETICS, Skill.ACROBATICS],
            armor_name="Chain Mail",
        )
        params.update(overrides)
        return build_character(**params)

    def test_skillful_skill_added_alongside_class_and_background_skills(self):
        result = self._build(species_trait_choices={"Skillful": "stealth"})
        sheet = result.sheet
        assert Skill.STEALTH in sheet.proficient_skills
        assert Skill.ATHLETICS in sheet.proficient_skills  # class choice
        assert Skill.INTIMIDATION in sheet.proficient_skills  # Soldier background
        assert not any("Skillful" in w for w in result.warnings)

    def test_skillful_duplicating_existing_skill_is_not_added_twice(self):
        # Athletics is already a class skill choice; picking it again for
        # Skillful must not produce a duplicate entry.
        result = self._build(species_trait_choices={"Skillful": "athletics"})
        assert result.sheet.proficient_skills.count(Skill.ATHLETICS) == 1

    def test_missing_skillful_choice_warns_not_errors(self):
        result = self._build()
        assert any("Skillful requires a choice" in w for w in result.warnings)
        assert Skill.STEALTH not in result.sheet.proficient_skills

    def test_illegal_skillful_choice_rejected(self):
        with pytest.raises(ValueError, match="Skillful"):
            self._build(species_trait_choices={"Skillful": "not-a-skill"})
