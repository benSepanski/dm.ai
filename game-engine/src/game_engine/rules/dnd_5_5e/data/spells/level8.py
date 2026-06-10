"""D&D 5.5e SRD spell data — 8th-level spells."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.spells._base import SpellData
from game_engine.types import (
    Ability,
    AreaShape,
    CastingTime,
    CharacterClass,
    Condition,
    DamageType,
    DiceNotation,
    SpellComponent,
    SpellRangeType,
    SpellSchool,
)

LEVEL_8_SPELLS: list[SpellData] = [
    SpellData(
        name="Sunburst",
        level=8,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=150,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "Brilliant sunlight detonates in a huge sphere; creatures that "
            "fail their save are seared by radiance and blinded for a "
            "minute, and the flash dispels magical darkness in the area."
        ),
        material="a piece of sunstone",
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("12d6"),
        conditions_applied=[Condition.BLINDED],
        area=AreaShape.SPHERE,
        area_size_ft=60,
    ),
    SpellData(
        name="Power Word Stun",
        level=8,
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
            "You utter a word that overwhelms the mind of one creature with "
            "150 hit points or fewer, stunning it; the target makes a "
            "Constitution save at the end of each of its turns to shake "
            "off the effect."
        ),
        conditions_applied=[Condition.STUNNED],
    ),
    SpellData(
        name="Dominate Monster",
        level=8,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A creature that fails a Wisdom save is charmed and must obey "
            "your telepathic commands; it repeats the save whenever it "
            "takes damage. A 9th-level slot extends the duration."
        ),
        save=Ability.WISDOM,
        conditions_applied=[Condition.CHARMED],
    ),
    SpellData(
        name="Earthquake",
        level=8,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=500,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.CLERIC, CharacterClass.DRUID, CharacterClass.SORCERER],
        description=(
            "The ground heaves in a 100-foot-radius circle: the area "
            "becomes difficult terrain, concentration falters, creatures "
            "can be knocked prone or swallowed by fissures, and structures "
            "shake apart."
        ),
        material="a pinch of dirt, a piece of rock, and a lump of clay",
        save=Ability.DEXTERITY,
        conditions_applied=[Condition.PRONE],
        area=AreaShape.CYLINDER,
        area_size_ft=100,
    ),
    SpellData(
        name="Holy Aura",
        level=8,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.CLERIC],
        description=(
            "Divine radiance surrounds you in an emanation: allies inside "
            "have advantage on saving throws and impose disadvantage on "
            "attacks against them, and fiends or undead that strike them "
            "risk being blinded."
        ),
        material="a reliquary worth 1,000+ GP",
        area=AreaShape.EMANATION,
        area_size_ft=30,
    ),
    SpellData(
        name="Incendiary Cloud",
        level=8,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=150,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A swirling cloud of embers and smoke fills a sphere, heavily "
            "obscuring the area and burning creatures inside; the cloud "
            "drifts away from you at the start of each of your turns."
        ),
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("10d8"),
        area=AreaShape.SPHERE,
        area_size_ft=20,
    ),
]
