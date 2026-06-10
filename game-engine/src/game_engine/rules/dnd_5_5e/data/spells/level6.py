"""D&D 5.5e SRD spell data — 6th-level spells."""

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

LEVEL_6_SPELLS: list[SpellData] = [
    SpellData(
        name="Chain Lightning",
        level=6,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=150,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A bolt of lightning strikes one target and then arcs to as "
            "many as three more creatures or objects nearby, each making "
            "its own save. Each higher slot level adds another arc."
        ),
        material="a bit of fur, a piece of amber, and three silver pins",
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.LIGHTNING,
        damage_dice=DiceNotation("10d8"),
    ),
    SpellData(
        name="Disintegrate",
        level=6,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A thin green ray unravels matter itself; a creature that fails "
            "its Dexterity save takes massive force damage, and one reduced "
            "to 0 hit points crumbles to fine gray dust along with its "
            "nonmagical gear."
        ),
        material="a lodestone and dust",
        save=Ability.DEXTERITY,
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("10d6+40"),
        upcast_damage_per_slot=DiceNotation("3d6"),
    ),
    SpellData(
        name="Heal",
        level=6,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC, CharacterClass.DRUID],
        description=(
            "A surge of positive energy restores 70 hit points to a "
            "creature you can see and also ends any blindness and deafness "
            "afflicting it. Each higher slot level restores 10 more hit "
            "points."
        ),
        healing_flat=70,
        upcast_healing_flat_per_slot=10,
    ),
    SpellData(
        name="Harm",
        level=6,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC],
        description=(
            "Virulent magic ravages a creature with necrotic agony; on a "
            "failed Constitution save its hit point maximum is also "
            "reduced by the damage dealt, though the spell cannot kill "
            "outright."
        ),
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("14d6"),
    ),
    SpellData(
        name="Sunbeam",
        level=6,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A beam of brilliant sunlight flashes from your hand in a line; "
            "creatures that fail their save are seared by radiance and "
            "blinded until your next turn, and you can fire the beam again "
            "each round."
        ),
        material="a magnifying glass",
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("6d8"),
        conditions_applied=[Condition.BLINDED],
        area=AreaShape.LINE,
        area_size_ft=60,
    ),
    SpellData(
        name="True Seeing",
        level=6,
        school=SpellSchool.DIVINATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="1 hour",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A willing creature you touch gains truesight to 120 feet, "
            "piercing illusions, invisibility, shapeshifting, and magical "
            "darkness, and perceiving the Ethereal Plane."
        ),
        material="mushroom-powder ointment worth 25+ GP, which the spell consumes",
    ),
    SpellData(
        name="Circle of Death",
        level=6,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=150,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "A wave of life-draining energy ripples out from a point you "
            "choose, withering every creature in an enormous sphere."
        ),
        material="the powder of a crushed black pearl worth 500+ GP",
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("8d8"),
        upcast_damage_per_slot=DiceNotation("2d8"),
        area=AreaShape.SPHERE,
        area_size_ft=60,
    ),
    SpellData(
        name="Globe of Invulnerability",
        level=6,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A shimmering barrier surrounds you in an emanation; spells of "
            "5th level or lower cast from outside cannot affect anything "
            "within it. Each higher slot level raises the blocked spell "
            "level by one."
        ),
        material="a glass bead",
        area=AreaShape.EMANATION,
        area_size_ft=10,
    ),
]
