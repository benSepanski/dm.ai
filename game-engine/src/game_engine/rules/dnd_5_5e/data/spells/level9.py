"""D&D 5.5e SRD spell data — 9th-level spells."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.spells._base import SpellData
from game_engine.types import (
    Ability,
    AreaShape,
    CastingTime,
    CharacterClass,
    DamageType,
    DiceNotation,
    SpellComponent,
    SpellRangeType,
    SpellSchool,
)

LEVEL_9_SPELLS: list[SpellData] = [
    SpellData(
        name="Meteor Swarm",
        level=9,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=5280,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Blazing meteors plummet onto four points you can see within a "
            "mile, each detonating in a vast sphere of flame and "
            "concussive force; overlapping blasts do not stack."
        ),
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("20d6"),
        secondary_damage_type=DamageType.BLUDGEONING,
        secondary_damage_dice=DiceNotation("20d6"),
        area=AreaShape.SPHERE,
        area_size_ft=40,
    ),
    SpellData(
        name="Power Word Kill",
        level=9,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "You speak a word of absolute death: a creature you can see "
            "with 100 hit points or fewer dies instantly, with no save."
        ),
    ),
    SpellData(
        name="Wish",
        level=9,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "The mightiest of mortal spells reshapes reality: you can "
            "duplicate any spell of 8th level or lower with no "
            "requirements, or attempt a greater effect at the risk of "
            "severe strain and losing the ability to cast Wish forever."
        ),
    ),
    SpellData(
        name="Time Stop",
        level=9,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Time freezes for everyone but you: you take 1d4+1 turns in a "
            "row, and the spell ends early if you affect another creature "
            "or move too far from where you cast it."
        ),
    ),
    SpellData(
        name="Mass Heal",
        level=9,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC],
        description=(
            "A flood of healing energy restores up to 700 hit points, "
            "divided as you choose among creatures you can see, and also "
            "cures their blindness, deafness, and diseases."
        ),
        healing_flat=700,
    ),
    SpellData(
        name="True Resurrection",
        level=9,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ONE_HOUR,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.CLERIC, CharacterClass.DRUID],
        description=(
            "You restore a creature dead up to 200 years to life at full "
            "hit points, free of curses, diseases, and missing body parts; "
            "you can even provide a new body if the old one is gone."
        ),
        material="diamonds worth 25,000+ GP, which the spell consumes",
        revives=True,
        revive_full_heal=True,
    ),
]
