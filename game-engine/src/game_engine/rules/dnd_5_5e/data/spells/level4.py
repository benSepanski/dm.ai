"""D&D 5.5e SRD spell data — 4th-level spells."""

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

LEVEL_4_SPELLS: list[SpellData] = [
    SpellData(
        name="Ice Storm",
        level=4,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=300,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Hailstones pound a cylindrical area, bludgeoning and freezing "
            "creatures within and turning the ground to difficult terrain "
            "until the end of your next turn."
        ),
        material="a pinch of dust and a few drops of water",
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.BLUDGEONING,
        # 2024 PHB: 2d10 bludgeoning (was 2d8 in 2014); the bludgeoning
        # damage increases by 1d10 per slot level above 4 — the cold pool
        # does not upcast (SPL-19).
        damage_dice=DiceNotation("2d10"),
        secondary_damage_type=DamageType.COLD,
        secondary_damage_dice=DiceNotation("4d6"),
        upcast_damage_per_slot=DiceNotation("1d10"),
        area=AreaShape.CYLINDER,
        area_size_ft=20,
    ),
    SpellData(
        name="Polymorph",
        level=4,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A creature that fails a Wisdom save is transformed into a "
            "beast whose challenge rating does not exceed its own (or its "
            "level), adopting that form's statistics until the spell ends "
            "or it drops to 0 hit points."
        ),
        material="a caterpillar cocoon",
        save=Ability.WISDOM,
    ),
    SpellData(
        name="Banishment",
        level=4,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.PALADIN,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A creature that fails a Charisma save is hurled to another "
            "plane of existence; if it is native to another plane and the "
            "spell lasts its full duration, it does not return."
        ),
        material="a pentacle",
        save=Ability.CHARISMA,
    ),
    SpellData(
        name="Wall of Fire",
        level=4,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A curtain of roaring flame up to 60 feet long springs into "
            "being, burning creatures caught in it when it appears and "
            "scorching anyone who ends its turn close to its hot side."
        ),
        material="a piece of charcoal",
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("5d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
        area=AreaShape.LINE,
        area_size_ft=60,
    ),
    SpellData(
        name="Dimension Door",
        level=4,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=500,
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
            "You teleport to any spot within range that you can see or "
            "describe, optionally bringing one willing creature along; "
            "arriving in an occupied space deals force damage to both of "
            "you."
        ),
    ),
    SpellData(
        name="Greater Invisibility",
        level=4,
        school=SpellSchool.ILLUSION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.BARD, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A creature you touch becomes invisible for the duration, even "
            "while attacking or casting spells."
        ),
        conditions_applied=[Condition.INVISIBLE],
    ),
    SpellData(
        name="Blight",
        level=4,
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
            "Withering necromantic energy drains moisture and vitality from "
            "a creature; plant creatures save with disadvantage and take "
            "maximum damage, while undead and constructs are unaffected."
        ),
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("8d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
    ),
    SpellData(
        name="Stoneskin",
        level=4,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.DRUID,
            CharacterClass.RANGER,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "The flesh of a willing creature you touch hardens like stone, "
            "granting it resistance to bludgeoning, piercing, and slashing "
            "damage for the duration."
        ),
        material="diamond dust worth 100+ GP, which the spell consumes",
    ),
    SpellData(
        name="Confusion",
        level=4,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=90,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "Creatures in a sphere that fail a Wisdom save lose control of "
            "their actions, wandering randomly or lashing out at whoever is "
            "nearby; each repeats the save at the end of its turns."
        ),
        material="three nut shells",
        save=Ability.WISDOM,
        area=AreaShape.SPHERE,
        area_size_ft=10,
    ),
    SpellData(
        name="Phantasmal Killer",
        level=4,
        school=SpellSchool.ILLUSION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.BARD, CharacterClass.WIZARD],
        description=(
            "You conjure a phantasm of a creature's deepest dread, visible "
            "only to it; on a failed Wisdom save it takes psychic damage "
            "and is frightened, suffering the damage again each turn it "
            "keeps failing."
        ),
        save=Ability.WISDOM,
        damage_type=DamageType.PSYCHIC,
        damage_dice=DiceNotation("4d10"),
        upcast_damage_per_slot=DiceNotation("1d10"),
        conditions_applied=[Condition.FRIGHTENED],
    ),
]
