# NOTE: exceeds 400 LoC — single cohesive data module
"""D&D 5.5e SRD spell data — 3rd-level spells."""

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

LEVEL_3_SPELLS: list[SpellData] = [
    SpellData(
        name="Fireball",
        level=3,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=150,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A bright streak races to a point you choose and detonates in a "
            "roaring blast of flame that fills a sphere, igniting "
            "unattended flammable objects."
        ),
        material="a ball of bat guano and sulfur",
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("8d6"),
        upcast_damage_per_slot=DiceNotation("1d6"),
        area=AreaShape.SPHERE,
        area_size_ft=20,
    ),
    SpellData(
        name="Lightning Bolt",
        level=3,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A stroke of lightning blasts out from you in a 100-foot line, "
            "searing everything in its path and igniting unattended "
            "flammables."
        ),
        material="a bit of fur and a crystal rod",
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.LIGHTNING,
        damage_dice=DiceNotation("8d6"),
        upcast_damage_per_slot=DiceNotation("1d6"),
        area=AreaShape.LINE,
        area_size_ft=100,
    ),
    SpellData(
        name="Counterspell",
        level=3,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.REACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "When a creature within range casts a spell, you attempt to "
            "interrupt it: the caster must succeed on a Constitution save "
            "or its spell fails and is wasted."
        ),
        save=Ability.CONSTITUTION,
    ),
    SpellData(
        name="Dispel Magic",
        level=3,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.PALADIN,
            CharacterClass.RANGER,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "You unravel one spell affecting a creature, object, or area: "
            "spells of this slot's level or lower end automatically, and "
            "higher-level spells end on a successful ability check."
        ),
    ),
    SpellData(
        name="Fly",
        level=3,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Concentration, up to 10 minutes",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "A willing creature you touch gains a fly speed of 60 feet for "
            "the duration. Each higher slot level lets you touch one more "
            "creature."
        ),
        material="a feather",
    ),
    SpellData(
        name="Haste",
        level=3,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=30,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A willing creature doubles its speed, gains +2 AC, has "
            "advantage on Dexterity saves, and gains one extra limited "
            "action each turn; when the spell ends, it is briefly unable "
            "to act."
        ),
        material="a shaving of licorice root",
    ),
    SpellData(
        name="Slow",
        level=3,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Up to six creatures in a cube that fail a Wisdom save are "
            "mired in warped time: their speed is halved, they take a -2 "
            "penalty to AC and Dexterity saves, and they lose reactions "
            "and most of their actions."
        ),
        material="a drop of molasses",
        save=Ability.WISDOM,
        area=AreaShape.CUBE,
        area_size_ft=40,
    ),
    SpellData(
        name="Spirit Guardians",
        level=3,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Concentration, up to 10 minutes",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.CLERIC],
        description=(
            "Protective spirits whirl around you in an emanation, halving "
            "the speed of hostile creatures inside it and searing those "
            "that enter or end their turn there with radiant (or necrotic) "
            "energy."
        ),
        material="a prayer scroll",
        save=Ability.WISDOM,
        half_damage_on_save=True,
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("3d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
        area=AreaShape.EMANATION,
        area_size_ft=15,
    ),
    SpellData(
        name="Revivify",
        level=3,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.PALADIN,
            CharacterClass.RANGER,
        ],
        description=(
            "You touch a creature that died within the last minute and "
            "call it back to life with 1 hit point; the spell cannot "
            "restore missing body parts or revive a creature dead of old "
            "age."
        ),
        material="a diamond worth 300+ GP, which the spell consumes",
        revives=True,
        healing_flat=1,
    ),
    SpellData(
        name="Fear",
        level=3,
        school=SpellSchool.ILLUSION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
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
            "You project a phantasm of each creature's worst fears in a "
            "cone; a creature that fails its save drops what it is holding "
            "and is frightened, fleeing from you while the spell lasts."
        ),
        material="a white feather",
        save=Ability.WISDOM,
        conditions_applied=[Condition.FRIGHTENED],
        area=AreaShape.CONE,
        area_size_ft=30,
    ),
    SpellData(
        name="Hypnotic Pattern",
        level=3,
        school=SpellSchool.ILLUSION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A swirling pattern of shifting colors fills a cube; creatures "
            "that fail a Wisdom save are charmed, incapacitated, and rooted "
            "in place until the spell ends or they take damage."
        ),
        material="a pinch of confetti or a glowing stick of incense",
        save=Ability.WISDOM,
        conditions_applied=[Condition.CHARMED, Condition.INCAPACITATED],
        area=AreaShape.CUBE,
        area_size_ft=30,
    ),
    SpellData(
        name="Mass Healing Word",
        level=3,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.BONUS_ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.BARD, CharacterClass.CLERIC],
        description=(
            "With a single restorative word, up to six creatures you can "
            "see each regain hit points equal to 2d4 plus your "
            "spellcasting ability modifier."
        ),
        healing_dice=DiceNotation("2d4"),
        upcast_healing_per_slot=DiceNotation("1d4"),
    ),
    SpellData(
        name="Protection from Energy",
        level=3,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.RANGER,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A willing creature you touch gains resistance to one damage "
            "type you choose: acid, cold, fire, lightning, or thunder."
        ),
    ),
]
