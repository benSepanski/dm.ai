# NOTE: exceeds 400 LoC — single cohesive data module
"""D&D 5.5e SRD spell data — 1st-level spells."""

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

LEVEL_1_SPELLS: list[SpellData] = [
    SpellData(
        name="Magic Missile",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Three glowing darts of force streak unerringly to creatures of "
            "your choice in range, each striking automatically for 1d4+1 "
            "force damage."
        ),
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("3d4+3"),
        upcast_damage_per_slot=DiceNotation("1d4+1"),
    ),
    SpellData(
        name="Burning Hands",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A fan of flame erupts from your outstretched fingers, scorching "
            "everything in a cone and igniting unattended flammables."
        ),
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("3d6"),
        upcast_damage_per_slot=DiceNotation("1d6"),
        area=AreaShape.CONE,
        area_size_ft=15,
    ),
    SpellData(
        name="Cure Wounds",
        level=1,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.PALADIN,
            CharacterClass.RANGER,
        ],
        description=(
            "Healing energy flows through your touch, restoring hit points "
            "equal to 2d8 plus your spellcasting ability modifier."
        ),
        healing_dice=DiceNotation("2d8"),
        upcast_healing_per_slot=DiceNotation("2d8"),
    ),
    SpellData(
        name="Healing Word",
        level=1,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.BONUS_ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.BARD, CharacterClass.CLERIC, CharacterClass.DRUID],
        description=(
            "With a word of restoration, a creature you can see regains hit "
            "points equal to 2d4 plus your spellcasting ability modifier."
        ),
        healing_dice=DiceNotation("2d4"),
        upcast_healing_per_slot=DiceNotation("2d4"),
    ),
    SpellData(
        name="Shield",
        level=1,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.REACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="1 round",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "An invisible barrier snaps into place when you are hit or "
            "targeted by Magic Missile, granting +5 AC until your next turn "
            "and negating Magic Missile entirely."
        ),
    ),
    SpellData(
        name="Sleep",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Drowsy magic washes over creatures in a small sphere; on a "
            "failed save a creature becomes incapacitated, and if it fails "
            "again at the end of its next turn it falls unconscious for the "
            "duration."
        ),
        material="a pinch of sand or rose petals",
        save=Ability.WISDOM,
        conditions_applied=[Condition.INCAPACITATED, Condition.UNCONSCIOUS],
        area=AreaShape.SPHERE,
        area_size_ft=5,
    ),
    SpellData(
        name="Thunderwave",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A booming wave of thunderous force sweeps out from you, "
            "battering creatures in a cube and pushing those that fail "
            "their save 10 feet away."
        ),
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.THUNDER,
        damage_dice=DiceNotation("2d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
        area=AreaShape.CUBE,
        area_size_ft=15,
    ),
    SpellData(
        name="Bless",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=30,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.CLERIC, CharacterClass.PALADIN],
        description=(
            "You bless up to three creatures, each of which can add 1d4 to "
            "its attack rolls and saving throws while the spell lasts."
        ),
        material="a Holy Water sprinkle",
    ),
    SpellData(
        name="Bane",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=30,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.CLERIC, CharacterClass.WARLOCK],
        description=(
            "Up to three creatures that fail a Charisma save must subtract "
            "1d4 from their attack rolls and saving throws while the spell "
            "lasts."
        ),
        material="a drop of blood",
        save=Ability.CHARISMA,
    ),
    SpellData(
        name="Guiding Bolt",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="1 round",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC],
        description=(
            "A bolt of holy light streaks toward a creature; on a hit it "
            "deals radiant damage and limns the target so the next attack "
            "roll against it has advantage."
        ),
        attack_roll=True,
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("4d6"),
        upcast_damage_per_slot=DiceNotation("1d6"),
    ),
    SpellData(
        name="Inflict Wounds",
        level=1,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC],
        description=(
            "Necrotic energy floods from your hand into a creature you "
            "touch, which takes full damage on a failed Constitution save "
            "or half on a success."
        ),
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("2d10"),
        upcast_damage_per_slot=DiceNotation("1d10"),
    ),
    SpellData(
        name="Mage Armor",
        level=1,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="8 hours",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Protective magical force wraps an unarmored willing creature, "
            "setting its base AC to 13 plus its Dexterity modifier for the "
            "duration."
        ),
        material="a piece of cured leather",
    ),
    SpellData(
        name="Faerie Fire",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.BARD, CharacterClass.DRUID],
        description=(
            "Objects and creatures in a cube are outlined in shimmering "
            "light; affected creatures that fail a Dexterity save cannot "
            "benefit from invisibility, and attacks against them have "
            "advantage."
        ),
        save=Ability.DEXTERITY,
        area=AreaShape.CUBE,
        area_size_ft=20,
    ),
    SpellData(
        name="Hex",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.BONUS_ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=90,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.WARLOCK],
        description=(
            "You curse a creature: your attacks deal an extra 1d6 necrotic "
            "damage to it, and it has disadvantage on checks with an "
            "ability you choose. Higher-level slots extend the duration."
        ),
        material="the petrified eye of a newt",
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("1d6"),
    ),
    SpellData(
        name="Hunter's Mark",
        level=1,
        school=SpellSchool.DIVINATION,
        casting_time=CastingTime.BONUS_ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=90,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.RANGER],
        description=(
            "You magically mark your quarry: your attacks deal an extra 1d6 "
            "force damage to it, and you have advantage on checks to track "
            "or find it. Higher-level slots extend the duration."
        ),
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("1d6"),
    ),
    SpellData(
        name="Detect Magic",
        level=1,
        school=SpellSchool.DIVINATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Concentration, up to 10 minutes",
        concentration=True,
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
            "For the duration you sense magic within 30 feet of you and can "
            "use an action to see faint auras around visible magical "
            "creatures and objects, learning their schools of magic."
        ),
        ritual=True,
    ),
    SpellData(
        name="Charm Person",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=30,
        duration="1 hour",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A humanoid that fails a Wisdom save regards you as a friendly "
            "acquaintance until the spell ends or you harm it; it knows it "
            "was charmed once the spell ends."
        ),
        save=Ability.WISDOM,
        conditions_applied=[Condition.CHARMED],
    ),
    SpellData(
        name="Feather Fall",
        level=1,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.REACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="1 minute",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Up to five falling creatures drift downward at 60 feet per "
            "round and land without taking falling damage."
        ),
        material="a small feather or piece of down",
    ),
]
