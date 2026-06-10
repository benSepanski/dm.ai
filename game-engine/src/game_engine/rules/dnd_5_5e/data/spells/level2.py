"""D&D 5.5e SRD spell data — 2nd-level spells."""

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

LEVEL_2_SPELLS: list[SpellData] = [
    SpellData(
        name="Misty Step",
        level=2,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.BONUS_ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "Wreathed in silvery mist, you teleport up to 30 feet to an "
            "unoccupied space you can see."
        ),
    ),
    SpellData(
        name="Shatter",
        level=2,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A painful ringing burst of sound erupts at a point you choose, "
            "battering creatures and objects in a sphere; constructs and "
            "inorganic creatures save with disadvantage."
        ),
        material="a chip of mica",
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.THUNDER,
        damage_dice=DiceNotation("3d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
        area=AreaShape.SPHERE,
        area_size_ft=10,
    ),
    SpellData(
        name="Scorching Ray",
        level=2,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You hurl three rays of fire at one or more targets; each ray "
            "is a separate attack roll dealing 2d6 fire damage on a hit. "
            "Each higher slot level adds one more ray."
        ),
        attack_roll=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("2d6"),
        upcast_damage_per_slot=DiceNotation("2d6"),
    ),
    SpellData(
        name="Hold Person",
        level=2,
        school=SpellSchool.ENCHANTMENT,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A humanoid that fails a Wisdom save is paralyzed for the "
            "duration, repeating the save at the end of each of its turns. "
            "Each higher slot level lets you target one more humanoid."
        ),
        material="a straight piece of iron",
        save=Ability.WISDOM,
        conditions_applied=[Condition.PARALYZED],
    ),
    SpellData(
        name="Invisibility",
        level=2,
        school=SpellSchool.ILLUSION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A creature you touch becomes invisible, along with anything it "
            "wears or carries, until it attacks or casts a spell. Each "
            "higher slot level lets you touch one more creature."
        ),
        material="an eyelash in gum arabic",
        conditions_applied=[Condition.INVISIBLE],
    ),
    SpellData(
        name="Aid",
        level=2,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=30,
        duration="8 hours",
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
            "Up to three creatures gain bolstered vitality: each one's "
            "current and maximum hit points increase by 5 for the duration, "
            "plus 5 more per higher slot level."
        ),
        material="a tiny strip of white cloth",
        healing_flat=5,
        upcast_healing_flat_per_slot=5,
    ),
    SpellData(
        name="Lesser Restoration",
        level=2,
        school=SpellSchool.ABJURATION,
        casting_time=CastingTime.BONUS_ACTION,
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
            "Your touch ends one disease or one of the following conditions "
            "afflicting a creature: blinded, deafened, paralyzed, or "
            "poisoned."
        ),
    ),
    SpellData(
        name="Spiritual Weapon",
        level=2,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.BONUS_ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC],
        description=(
            "A floating spectral weapon appears and strikes a creature near "
            "it, dealing 1d8 plus your spellcasting modifier in force "
            "damage; on later turns you can move it and attack again as a "
            "bonus action."
        ),
        attack_roll=True,
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("1d8"),
        upcast_damage_per_slot=DiceNotation("1d8"),
    ),
    SpellData(
        name="Moonbeam",
        level=2,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="Concentration, up to 1 minute",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.DRUID],
        description=(
            "A silvery column of pale light shines down in a cylinder; a "
            "creature entering the beam or starting its turn there is "
            "seared by radiant energy, and you can move the beam on later "
            "turns."
        ),
        material="a moonseed leaf and a piece of opalescent feldspar",
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("2d10"),
        upcast_damage_per_slot=DiceNotation("1d10"),
        area=AreaShape.CYLINDER,
        area_size_ft=5,
    ),
    SpellData(
        name="Darkness",
        level=2,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 10 minutes",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "Magical darkness fills a sphere, spreading around corners and "
            "swallowing nonmagical light; darkvision cannot penetrate it."
        ),
        material="bat fur and a piece of coal",
        area=AreaShape.SPHERE,
        area_size_ft=15,
    ),
    SpellData(
        name="Web",
        level=2,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Thick, sticky webbing fills a cube; creatures that start their "
            "turn in the webs or enter them must save or be restrained "
            "until they break free. The webs are flammable."
        ),
        material="a bit of spiderweb",
        save=Ability.DEXTERITY,
        conditions_applied=[Condition.RESTRAINED],
        area=AreaShape.CUBE,
        area_size_ft=20,
    ),
    SpellData(
        name="Mirror Image",
        level=2,
        school=SpellSchool.ILLUSION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.SELF,
        range_ft=None,
        duration="1 minute",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "Three illusory duplicates of you appear and mimic your "
            "movements; attacks against you may strike a duplicate instead, "
            "destroying it."
        ),
    ),
    SpellData(
        name="Blindness/Deafness",
        level=2,
        school=SpellSchool.TRANSMUTATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=120,
        duration="1 minute",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A creature that fails a Constitution save is blinded or "
            "deafened (your choice) for the duration, repeating the save at "
            "the end of each of its turns. Each higher slot level adds a "
            "target."
        ),
        save=Ability.CONSTITUTION,
        conditions_applied=[Condition.BLINDED, Condition.DEAFENED],
    ),
]
