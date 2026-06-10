# NOTE: exceeds 400 LoC — single cohesive data module
"""
D&D 5.5e class definitions (2024 PHB chapter 3, plus Tasha's Artificer).

Static identity data for all 13 classes: hit die, saves, proficiencies,
and skill choices. Per-level features live in
:mod:`game_engine.rules.dnd_5_5e.data.class_features`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, ArmorCategory, CharacterClass, Skill, WeaponCategory


@dataclass(frozen=True)
class ClassData:
    """Static data describing a D&D 5.5e character class."""

    character_class: CharacterClass
    hit_die: int
    primary_abilities: list[Ability]
    saving_throw_proficiencies: list[Ability]
    armor_training: list[ArmorCategory]
    weapon_category_training: list[WeaponCategory]
    skill_choices: list[Skill]
    num_skill_choices: int
    spellcasting: bool
    # Qualified weapon training that a category can't express
    # (e.g. "Martial weapons that have the Light property").
    weapon_training_notes: list[str] = field(default_factory=list)
    subclass_level: int = 3


CLASSES: dict[CharacterClass, ClassData] = {
    CharacterClass.ARTIFICER: ClassData(
        character_class=CharacterClass.ARTIFICER,
        hit_die=8,
        primary_abilities=[Ability.INTELLIGENCE],
        saving_throw_proficiencies=[Ability.CONSTITUTION, Ability.INTELLIGENCE],
        armor_training=[ArmorCategory.LIGHT, ArmorCategory.MEDIUM, ArmorCategory.SHIELD],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=[
            Skill.ARCANA,
            Skill.HISTORY,
            Skill.INVESTIGATION,
            Skill.MEDICINE,
            Skill.NATURE,
            Skill.PERCEPTION,
            Skill.SLEIGHT_OF_HAND,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
    CharacterClass.BARBARIAN: ClassData(
        character_class=CharacterClass.BARBARIAN,
        hit_die=12,
        primary_abilities=[Ability.STRENGTH],
        saving_throw_proficiencies=[Ability.STRENGTH, Ability.CONSTITUTION],
        armor_training=[ArmorCategory.LIGHT, ArmorCategory.MEDIUM, ArmorCategory.SHIELD],
        weapon_category_training=[WeaponCategory.SIMPLE, WeaponCategory.MARTIAL],
        skill_choices=[
            Skill.ANIMAL_HANDLING,
            Skill.ATHLETICS,
            Skill.INTIMIDATION,
            Skill.NATURE,
            Skill.PERCEPTION,
            Skill.SURVIVAL,
        ],
        num_skill_choices=2,
        spellcasting=False,
    ),
    CharacterClass.BARD: ClassData(
        character_class=CharacterClass.BARD,
        hit_die=8,
        primary_abilities=[Ability.CHARISMA],
        saving_throw_proficiencies=[Ability.DEXTERITY, Ability.CHARISMA],
        armor_training=[ArmorCategory.LIGHT],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=list(Skill),
        num_skill_choices=3,
        spellcasting=True,
    ),
    CharacterClass.CLERIC: ClassData(
        character_class=CharacterClass.CLERIC,
        hit_die=8,
        primary_abilities=[Ability.WISDOM],
        saving_throw_proficiencies=[Ability.WISDOM, Ability.CHARISMA],
        armor_training=[ArmorCategory.LIGHT, ArmorCategory.MEDIUM, ArmorCategory.SHIELD],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=[
            Skill.HISTORY,
            Skill.INSIGHT,
            Skill.MEDICINE,
            Skill.PERSUASION,
            Skill.RELIGION,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
    CharacterClass.DRUID: ClassData(
        character_class=CharacterClass.DRUID,
        hit_die=8,
        primary_abilities=[Ability.WISDOM],
        saving_throw_proficiencies=[Ability.INTELLIGENCE, Ability.WISDOM],
        armor_training=[ArmorCategory.LIGHT, ArmorCategory.SHIELD],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=[
            Skill.ARCANA,
            Skill.ANIMAL_HANDLING,
            Skill.INSIGHT,
            Skill.MEDICINE,
            Skill.NATURE,
            Skill.PERCEPTION,
            Skill.RELIGION,
            Skill.SURVIVAL,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
    CharacterClass.FIGHTER: ClassData(
        character_class=CharacterClass.FIGHTER,
        hit_die=10,
        primary_abilities=[Ability.STRENGTH, Ability.DEXTERITY],
        saving_throw_proficiencies=[Ability.STRENGTH, Ability.CONSTITUTION],
        armor_training=[
            ArmorCategory.LIGHT,
            ArmorCategory.MEDIUM,
            ArmorCategory.HEAVY,
            ArmorCategory.SHIELD,
        ],
        weapon_category_training=[WeaponCategory.SIMPLE, WeaponCategory.MARTIAL],
        skill_choices=[
            Skill.ACROBATICS,
            Skill.ANIMAL_HANDLING,
            Skill.ATHLETICS,
            Skill.HISTORY,
            Skill.INSIGHT,
            Skill.INTIMIDATION,
            Skill.PERCEPTION,
            Skill.PERSUASION,
            Skill.SURVIVAL,
        ],
        num_skill_choices=2,
        spellcasting=False,
    ),
    CharacterClass.MONK: ClassData(
        character_class=CharacterClass.MONK,
        hit_die=8,
        primary_abilities=[Ability.DEXTERITY, Ability.WISDOM],
        saving_throw_proficiencies=[Ability.STRENGTH, Ability.DEXTERITY],
        armor_training=[],
        weapon_category_training=[WeaponCategory.SIMPLE],
        weapon_training_notes=["Martial weapons that have the Light property"],
        skill_choices=[
            Skill.ACROBATICS,
            Skill.ATHLETICS,
            Skill.HISTORY,
            Skill.INSIGHT,
            Skill.RELIGION,
            Skill.STEALTH,
        ],
        num_skill_choices=2,
        spellcasting=False,
    ),
    CharacterClass.PALADIN: ClassData(
        character_class=CharacterClass.PALADIN,
        hit_die=10,
        primary_abilities=[Ability.STRENGTH, Ability.CHARISMA],
        saving_throw_proficiencies=[Ability.WISDOM, Ability.CHARISMA],
        armor_training=[
            ArmorCategory.LIGHT,
            ArmorCategory.MEDIUM,
            ArmorCategory.HEAVY,
            ArmorCategory.SHIELD,
        ],
        weapon_category_training=[WeaponCategory.SIMPLE, WeaponCategory.MARTIAL],
        skill_choices=[
            Skill.ATHLETICS,
            Skill.INSIGHT,
            Skill.INTIMIDATION,
            Skill.MEDICINE,
            Skill.PERSUASION,
            Skill.RELIGION,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
    CharacterClass.RANGER: ClassData(
        character_class=CharacterClass.RANGER,
        hit_die=10,
        primary_abilities=[Ability.DEXTERITY, Ability.WISDOM],
        saving_throw_proficiencies=[Ability.STRENGTH, Ability.DEXTERITY],
        armor_training=[ArmorCategory.LIGHT, ArmorCategory.MEDIUM, ArmorCategory.SHIELD],
        weapon_category_training=[WeaponCategory.SIMPLE, WeaponCategory.MARTIAL],
        skill_choices=[
            Skill.ANIMAL_HANDLING,
            Skill.ATHLETICS,
            Skill.INSIGHT,
            Skill.INVESTIGATION,
            Skill.NATURE,
            Skill.PERCEPTION,
            Skill.STEALTH,
            Skill.SURVIVAL,
        ],
        num_skill_choices=3,
        spellcasting=True,
    ),
    CharacterClass.ROGUE: ClassData(
        character_class=CharacterClass.ROGUE,
        hit_die=8,
        primary_abilities=[Ability.DEXTERITY],
        saving_throw_proficiencies=[Ability.DEXTERITY, Ability.INTELLIGENCE],
        armor_training=[ArmorCategory.LIGHT],
        weapon_category_training=[WeaponCategory.SIMPLE],
        weapon_training_notes=["Martial weapons that have the Finesse or Light property"],
        skill_choices=[
            Skill.ACROBATICS,
            Skill.ATHLETICS,
            Skill.DECEPTION,
            Skill.INSIGHT,
            Skill.INTIMIDATION,
            Skill.INVESTIGATION,
            Skill.PERCEPTION,
            Skill.PERSUASION,
            Skill.SLEIGHT_OF_HAND,
            Skill.STEALTH,
        ],
        num_skill_choices=4,
        spellcasting=False,
    ),
    CharacterClass.SORCERER: ClassData(
        character_class=CharacterClass.SORCERER,
        hit_die=6,
        primary_abilities=[Ability.CHARISMA],
        saving_throw_proficiencies=[Ability.CONSTITUTION, Ability.CHARISMA],
        armor_training=[],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=[
            Skill.ARCANA,
            Skill.DECEPTION,
            Skill.INSIGHT,
            Skill.INTIMIDATION,
            Skill.PERSUASION,
            Skill.RELIGION,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
    CharacterClass.WARLOCK: ClassData(
        character_class=CharacterClass.WARLOCK,
        hit_die=8,
        primary_abilities=[Ability.CHARISMA],
        saving_throw_proficiencies=[Ability.WISDOM, Ability.CHARISMA],
        armor_training=[ArmorCategory.LIGHT],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=[
            Skill.ARCANA,
            Skill.DECEPTION,
            Skill.HISTORY,
            Skill.INTIMIDATION,
            Skill.INVESTIGATION,
            Skill.NATURE,
            Skill.RELIGION,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
    CharacterClass.WIZARD: ClassData(
        character_class=CharacterClass.WIZARD,
        hit_die=6,
        primary_abilities=[Ability.INTELLIGENCE],
        saving_throw_proficiencies=[Ability.INTELLIGENCE, Ability.WISDOM],
        armor_training=[],
        weapon_category_training=[WeaponCategory.SIMPLE],
        skill_choices=[
            Skill.ARCANA,
            Skill.HISTORY,
            Skill.INSIGHT,
            Skill.INVESTIGATION,
            Skill.MEDICINE,
            Skill.NATURE,
            Skill.RELIGION,
        ],
        num_skill_choices=2,
        spellcasting=True,
    ),
}
