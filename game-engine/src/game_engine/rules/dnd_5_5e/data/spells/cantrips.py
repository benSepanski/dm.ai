"""D&D 5.5e SRD spell data — Cantrips (level 0)."""

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

CANTRIPS: list[SpellData] = [
    SpellData(
        name="Fire Bolt",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You fling a streak of flame at a creature or object in range. "
            "Unattended flammable objects catch fire on a hit."
        ),
        attack_roll=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("1d10"),
    ),
    SpellData(
        name="Eldritch Blast",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.WARLOCK],
        description=(
            "A crackling beam of eldritch energy lances toward a target. "
            "At higher character levels the spell produces additional beams, "
            "each requiring its own attack roll."
        ),
        attack_roll=True,
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("1d10"),
    ),
    SpellData(
        name="Sacred Flame",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC],
        description=(
            "Radiant fire descends on a creature you can see, which gains "
            "no benefit from cover against the saving throw."
        ),
        save=Ability.DEXTERITY,
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("1d8"),
    ),
    SpellData(
        name="Toll the Dead",
        level=0,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "A dolorous bell tolls around one creature in range; the damage "
            "die becomes a d12 if the target is missing any hit points."
        ),
        save=Ability.WISDOM,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("1d8"),
    ),
    SpellData(
        name="Chill Touch",
        level=0,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "Grave-cold necrotic energy flows from your hand into a creature "
            "you touch, which then cannot regain hit points until the start "
            "of your next turn."
        ),
        attack_roll=True,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("1d10"),
    ),
    SpellData(
        name="Poison Spray",
        level=0,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=30,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "You spray a puff of toxic mist at a creature in range, making a "
            "ranged spell attack against it."
        ),
        attack_roll=True,
        damage_type=DamageType.POISON,
        damage_dice=DiceNotation("1d12"),
    ),
    SpellData(
        name="Acid Splash",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "An acidic bubble bursts at a point in range, dousing every "
            "creature in a small sphere centered there."
        ),
        save=Ability.DEXTERITY,
        damage_type=DamageType.ACID,
        damage_dice=DiceNotation("1d6"),
        area=AreaShape.SPHERE,
        area_size_ft=5,
    ),
    SpellData(
        name="Ray of Frost",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A frigid beam of blue-white light chills a creature, reducing "
            "its speed by 10 feet until the start of your next turn."
        ),
        attack_roll=True,
        damage_type=DamageType.COLD,
        damage_dice=DiceNotation("1d8"),
    ),
    SpellData(
        name="Shocking Grasp",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Lightning leaps from your hand into a creature you touch; the "
            "jolt also stops the target from making opportunity attacks "
            "until the start of its next turn."
        ),
        attack_roll=True,
        damage_type=DamageType.LIGHTNING,
        damage_dice=DiceNotation("1d8"),
    ),
    SpellData(
        name="Mind Sliver",
        level=0,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "You drive a disorienting spike of psychic energy into a "
            "creature's mind; on a failed save it also subtracts 1d4 from "
            "its next saving throw before the end of your next turn."
        ),
        save=Ability.INTELLIGENCE,
        damage_type=DamageType.PSYCHIC,
        damage_dice=DiceNotation("1d6"),
    ),
    SpellData(
        name="Guidance",
        level=0,
        school=SpellSchool.DIVINATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC, CharacterClass.DRUID],
        description=(
            "You touch a willing creature and grant it a flicker of divine "
            "insight, letting it add 1d4 to one ability check before the "
            "spell ends."
        ),
    ),
    SpellData(
        name="Light",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="1 hour",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "An object you touch sheds bright light in a 20-foot radius and "
            "dim light for another 20 feet until the spell ends."
        ),
        material="a firefly or phosphorescent moss",
    ),
]
