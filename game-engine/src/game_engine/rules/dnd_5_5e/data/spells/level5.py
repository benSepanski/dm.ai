"""D&D 5.5e SRD spell data — 5th-level spells."""

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

LEVEL_5_SPELLS: list[SpellData] = [
    SpellData(
        name="Cone of Cold",
        level=5,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A blast of freezing air erupts from your hands in a huge cone, "
            "chilling everything within; creatures killed by the cold "
            "become frozen statues until they thaw."
        ),
        material="a small crystal or glass cone",
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.COLD,
        damage_dice=DiceNotation("8d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
        area=AreaShape.CONE,
        area_size_ft=60,
    ),
    SpellData(
        name="Hold Monster",
        level=5,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=90,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A creature that fails a Wisdom save is paralyzed for the "
            "duration, repeating the save at the end of each of its turns. "
            "Each higher slot level lets you target one more creature."
        ),
        material="a straight piece of iron",
        save=Ability.WISDOM,
        conditions_applied=[Condition.PARALYZED],
    ),
    SpellData(
        name="Cloudkill",
        level=5,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 10 minutes",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A sickly yellow-green fog fills a sphere and creeps away from "
            "you each round, heavily obscuring the area and poisoning "
            "creatures that start their turn inside it."
        ),
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.POISON,
        damage_dice=DiceNotation("5d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
        area=AreaShape.SPHERE,
        area_size_ft=20,
    ),
    SpellData(
        name="Flame Strike",
        level=5,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.CLERIC],
        description=(
            "A column of divine fire roars down from above, scouring a "
            "cylinder with equal parts mundane flame and searing radiance."
        ),
        material="a pinch of sulfur",
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("5d6"),
        secondary_damage_type=DamageType.RADIANT,
        secondary_damage_dice=DiceNotation("5d6"),
        upcast_damage_per_slot=DiceNotation("1d6"),
        area=AreaShape.CYLINDER,
        area_size_ft=10,
    ),
    SpellData(
        name="Greater Restoration",
        level=5,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.PALADIN,
            CharacterClass.RANGER,
        ],
        description=(
            "Potent restorative magic ends one debilitating effect on the "
            "creature you touch, such as a charm, petrification, a curse, "
            "exhaustion, or a reduction to its ability scores or hit point "
            "maximum."
        ),
        material="diamond dust worth 100+ GP, which the spell consumes",
    ),
    SpellData(
        name="Mass Cure Wounds",
        level=5,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.BARD, CharacterClass.CLERIC, CharacterClass.DRUID],
        description=(
            "A wave of healing energy washes over up to six creatures in a "
            "sphere, restoring hit points equal to 5d8 plus your "
            "spellcasting ability modifier to each."
        ),
        healing_dice=DiceNotation("5d8"),
        upcast_healing_per_slot=DiceNotation("1d8"),
        area=AreaShape.SPHERE,
        area_size_ft=30,
    ),
    SpellData(
        name="Raise Dead",
        level=5,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ONE_HOUR,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.CLERIC, CharacterClass.PALADIN],
        description=(
            "You return a creature dead no longer than 10 days to life with "
            "1 hit point, provided its soul is free and willing; the "
            "revived creature suffers a lingering penalty that fades over "
            "several long rests."
        ),
        material="a diamond worth 500+ GP, which the spell consumes",
        revives=True,
        healing_flat=1,
    ),
    SpellData(
        name="Wall of Stone",
        level=5,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 10 minutes",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A wall of solid stone composed of ten connected panels rises "
            "from a surface you choose; if you concentrate for the full "
            "duration, the wall becomes permanent."
        ),
        material="a small block of granite",
    ),
    SpellData(
        name="Dominate Person",
        level=5,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A humanoid that fails a Wisdom save is charmed and obeys your "
            "telepathic commands; it repeats the save each time it takes "
            "damage. Higher-level slots extend the duration."
        ),
        save=Ability.WISDOM,
        conditions_applied=[Condition.CHARMED],
    ),
    SpellData(
        name="Telekinesis",
        level=5,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 10 minutes",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You move creatures or objects of up to 1,000 pounds with your "
            "mind, shifting them up to 30 feet each round; an unwilling "
            "creature can resist with a contested Strength check."
        ),
    ),
]
