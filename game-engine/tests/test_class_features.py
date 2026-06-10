"""Structural tests for the 2024 PHB class progression tables."""

from __future__ import annotations

import pytest

from game_engine.rules.dnd_5_5e.data.class_features import (
    CLASS_PROGRESSIONS,
    ClassProgression,
    get_progression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

DESIGNATED_SUBCLASS: dict[CharacterClass, Subclass] = {
    CharacterClass.ARTIFICER: Subclass.BATTLE_SMITH,
    CharacterClass.BARBARIAN: Subclass.PATH_OF_THE_BERSERKER,
    CharacterClass.BARD: Subclass.COLLEGE_OF_LORE,
    CharacterClass.CLERIC: Subclass.LIFE_DOMAIN,
    CharacterClass.DRUID: Subclass.CIRCLE_OF_THE_LAND,
    CharacterClass.FIGHTER: Subclass.CHAMPION,
    CharacterClass.MONK: Subclass.WARRIOR_OF_THE_OPEN_HAND,
    CharacterClass.PALADIN: Subclass.OATH_OF_DEVOTION,
    CharacterClass.RANGER: Subclass.HUNTER,
    CharacterClass.ROGUE: Subclass.THIEF,
    CharacterClass.SORCERER: Subclass.DRACONIC_SORCERY,
    CharacterClass.WARLOCK: Subclass.FIEND_PATRON,
    CharacterClass.WIZARD: Subclass.EVOKER,
}

FULL_CASTERS = [
    CharacterClass.BARD,
    CharacterClass.CLERIC,
    CharacterClass.DRUID,
    CharacterClass.SORCERER,
    CharacterClass.WIZARD,
]

ALL_CLASSES = list(CharacterClass)


def _progression(character_class: CharacterClass) -> ClassProgression:
    return CLASS_PROGRESSIONS[character_class]


def test_all_thirteen_classes_present() -> None:
    assert set(CLASS_PROGRESSIONS) == set(CharacterClass)
    assert len(CLASS_PROGRESSIONS) == 13


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_get_progression_matches_class(character_class: CharacterClass) -> None:
    progression = get_progression(character_class)
    assert progression.character_class == character_class


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_has_level_one_feature(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    assert len(progression.features_at_level(1)) >= 1


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_epic_boon_at_nineteen(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    boons = [f for f in progression.features_at_level(19) if f.name == "Epic Boon"]
    assert len(boons) == 1
    assert boons[0].subclass is None


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_feature_levels_in_range(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    assert all(1 <= f.level <= 20 for f in progression.features)


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_resource_tables_have_twenty_entries(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    for resource, table in progression.resources.items():
        assert len(table) == 20, f"{character_class}: {resource} table must span levels 1-20"


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_subclass_choice_feature_at_level_three(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    choices = [
        f for f in progression.features_at_level(3) if f.subclass is None and "Subclass" in f.name
    ]
    assert len(choices) == 1


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_subclass_features_only_for_designated_subclass(
    character_class: CharacterClass,
) -> None:
    progression = _progression(character_class)
    designated = DESIGNATED_SUBCLASS[character_class]
    subclass_features = [f for f in progression.features if f.subclass is not None]
    assert subclass_features, f"{character_class} must have subclass features"
    assert all(f.subclass == designated for f in subclass_features)


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_subclass_features_first_appear_at_level_three(
    character_class: CharacterClass,
) -> None:
    progression = _progression(character_class)
    levels = sorted(f.level for f in progression.features if f.subclass is not None)
    assert levels[0] == 3


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_subclass_features_excluded_without_subclass(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    assert all(f.subclass is None for f in progression.features_through_level(20))


def test_ability_score_improvement_levels() -> None:
    for character_class in ALL_CLASSES:
        expected = {4, 8, 12, 16}
        if character_class == CharacterClass.FIGHTER:
            expected |= {6, 14}
        if character_class == CharacterClass.ROGUE:
            expected |= {10}
        progression = _progression(character_class)
        asi_levels = sorted(
            f.level for f in progression.features if f.name == "Ability Score Improvement"
        )
        assert asi_levels == sorted(expected), f"{character_class} ASI levels wrong"
        assert len(asi_levels) == len(set(asi_levels)), f"{character_class} duplicate ASI"


def test_rogue_sneak_attack_dice() -> None:
    rogue = _progression(CharacterClass.ROGUE)
    assert rogue.resource_at_level(ClassResource.SNEAK_ATTACK_DICE, 1) == 1
    assert rogue.resource_at_level(ClassResource.SNEAK_ATTACK_DICE, 11) == 6
    assert rogue.resource_at_level(ClassResource.SNEAK_ATTACK_DICE, 20) == 10


def test_barbarian_rage_table() -> None:
    barbarian = _progression(CharacterClass.BARBARIAN)
    assert barbarian.resource_at_level(ClassResource.RAGE, 1) == 2
    assert barbarian.resource_at_level(ClassResource.RAGE, 20) == 6
    assert barbarian.resource_at_level(ClassResource.RAGE_DAMAGE, 9) == 3
    assert barbarian.resource_at_level(ClassResource.RAGE_DAMAGE, 16) == 4


def test_monk_martial_arts_die_and_focus() -> None:
    monk = _progression(CharacterClass.MONK)
    assert monk.resource_at_level(ClassResource.MARTIAL_ARTS_DIE, 1) == 6
    assert monk.resource_at_level(ClassResource.MARTIAL_ARTS_DIE, 5) == 8
    assert monk.resource_at_level(ClassResource.MARTIAL_ARTS_DIE, 11) == 10
    assert monk.resource_at_level(ClassResource.MARTIAL_ARTS_DIE, 17) == 12
    assert monk.resource_at_level(ClassResource.FOCUS_POINT, 1) == 0
    assert monk.resource_at_level(ClassResource.FOCUS_POINT, 2) == 2
    assert monk.resource_at_level(ClassResource.FOCUS_POINT, 20) == 20


def test_fighter_extra_attack_family() -> None:
    fighter = _progression(CharacterClass.FIGHTER)
    base_features = fighter.features_through_level(20)
    attack_family = [f for f in base_features if "Attack" in f.name]
    assert len(attack_family) == 4
    names = {f.name for f in attack_family}
    assert {"Extra Attack", "Two Extra Attacks", "Three Extra Attacks"} <= names


def test_fighter_resource_tables() -> None:
    fighter = _progression(CharacterClass.FIGHTER)
    assert fighter.resource_at_level(ClassResource.SECOND_WIND, 1) == 2
    assert fighter.resource_at_level(ClassResource.SECOND_WIND, 10) == 4
    assert fighter.resource_at_level(ClassResource.ACTION_SURGE, 1) == 0
    assert fighter.resource_at_level(ClassResource.ACTION_SURGE, 17) == 2
    assert fighter.resource_at_level(ClassResource.INDOMITABLE, 8) == 0
    assert fighter.resource_at_level(ClassResource.INDOMITABLE, 9) == 1
    assert fighter.resource_at_level(ClassResource.INDOMITABLE, 17) == 3
    assert fighter.resource_at_level(ClassResource.WEAPON_MASTERY, 16) == 6


def test_paladin_lay_on_hands_pool() -> None:
    paladin = _progression(CharacterClass.PALADIN)
    assert paladin.resource_at_level(ClassResource.LAY_ON_HANDS, 1) == 5
    assert paladin.resource_at_level(ClassResource.LAY_ON_HANDS, 20) == 100
    assert paladin.resource_at_level(ClassResource.CHANNEL_DIVINITY, 2) == 0
    assert paladin.resource_at_level(ClassResource.CHANNEL_DIVINITY, 3) == 2
    assert paladin.resource_at_level(ClassResource.CHANNEL_DIVINITY, 11) == 3


def test_cleric_and_druid_resource_tables() -> None:
    cleric = _progression(CharacterClass.CLERIC)
    assert cleric.resource_at_level(ClassResource.CHANNEL_DIVINITY, 1) == 0
    assert cleric.resource_at_level(ClassResource.CHANNEL_DIVINITY, 6) == 3
    assert cleric.resource_at_level(ClassResource.CHANNEL_DIVINITY, 18) == 4
    druid = _progression(CharacterClass.DRUID)
    assert druid.resource_at_level(ClassResource.WILD_SHAPE, 1) == 0
    assert druid.resource_at_level(ClassResource.WILD_SHAPE, 6) == 3
    assert druid.resource_at_level(ClassResource.WILD_SHAPE, 17) == 4


def test_sorcerer_and_warlock_resource_tables() -> None:
    sorcerer = _progression(CharacterClass.SORCERER)
    assert sorcerer.resource_at_level(ClassResource.SORCERY_POINT, 1) == 0
    assert sorcerer.resource_at_level(ClassResource.SORCERY_POINT, 2) == 2
    assert sorcerer.resource_at_level(ClassResource.SORCERY_POINT, 20) == 20
    warlock = _progression(CharacterClass.WARLOCK)
    assert warlock.resource_at_level(ClassResource.ELDRITCH_INVOCATION, 1) == 1
    assert warlock.resource_at_level(ClassResource.ELDRITCH_INVOCATION, 2) == 3
    assert warlock.resource_at_level(ClassResource.ELDRITCH_INVOCATION, 5) == 5
    assert warlock.resource_at_level(ClassResource.ELDRITCH_INVOCATION, 11) == 7
    assert warlock.resource_at_level(ClassResource.ELDRITCH_INVOCATION, 18) == 10


def test_bard_prepared_spells_and_inspiration() -> None:
    bard = _progression(CharacterClass.BARD)
    assert bard.prepared_spells is not None
    assert bard.prepared_spells[19] == 22
    # 2024 rule: Bardic Inspiration uses equal the Charisma modifier, so no table.
    assert ClassResource.BARDIC_INSPIRATION not in bard.resources


@pytest.mark.parametrize("character_class", FULL_CASTERS)
def test_full_casters_have_complete_spell_columns(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    assert progression.spellcaster_type == SpellcasterType.FULL
    assert progression.spellcasting_ability is not None
    assert progression.cantrips_known is not None
    assert progression.prepared_spells is not None
    assert len(progression.cantrips_known) == 20
    assert len(progression.prepared_spells) == 20


def test_half_and_pact_caster_metadata() -> None:
    expected: dict[CharacterClass, tuple[SpellcasterType, Ability]] = {
        CharacterClass.PALADIN: (SpellcasterType.HALF, Ability.CHARISMA),
        CharacterClass.RANGER: (SpellcasterType.HALF, Ability.WISDOM),
        CharacterClass.ARTIFICER: (SpellcasterType.HALF, Ability.INTELLIGENCE),
        CharacterClass.WARLOCK: (SpellcasterType.PACT, Ability.CHARISMA),
    }
    for character_class, (caster_type, ability) in expected.items():
        progression = _progression(character_class)
        assert progression.spellcaster_type == caster_type
        assert progression.spellcasting_ability == ability


def test_non_casters_have_no_spell_metadata() -> None:
    for character_class in [
        CharacterClass.BARBARIAN,
        CharacterClass.FIGHTER,
        CharacterClass.MONK,
        CharacterClass.ROGUE,
    ]:
        progression = _progression(character_class)
        assert progression.spellcaster_type == SpellcasterType.NONE
        assert progression.spellcasting_ability is None
        assert progression.cantrips_known is None
        assert progression.prepared_spells is None


def test_paladin_and_ranger_have_no_cantrips() -> None:
    assert _progression(CharacterClass.PALADIN).cantrips_known is None
    assert _progression(CharacterClass.RANGER).cantrips_known is None


def test_artificer_prepared_spells_formula_based() -> None:
    artificer = _progression(CharacterClass.ARTIFICER)
    assert artificer.prepared_spells is None
    assert artificer.cantrips_known is not None
    assert artificer.cantrips_known[0] == 2
    assert artificer.cantrips_known[19] == 4


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_features_at_level_three_include_subclass_choice_and_grants(
    character_class: CharacterClass,
) -> None:
    progression = _progression(character_class)
    designated = DESIGNATED_SUBCLASS[character_class]
    with_subclass = progression.features_at_level(3, subclass=designated)
    assert any(f.subclass == designated for f in with_subclass)
    assert any(f.subclass is None and "Subclass" in f.name for f in with_subclass)


@pytest.mark.parametrize("character_class", ALL_CLASSES)
def test_feature_descriptions_are_meaningful(character_class: CharacterClass) -> None:
    progression = _progression(character_class)
    for feature in progression.features:
        assert feature.name.strip()
        assert len(feature.description.strip()) >= 20, f"{feature.name} description too short"
