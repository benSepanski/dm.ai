"""D&D 5.5e SRD spell data — 7th-level spells."""

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

LEVEL_7_SPELLS: list[SpellData] = [
    SpellData(
        name="Forcecage",
        level=7,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=100,
        duration="Concentration, up to 1 hour",
        concentration=True,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "An immobile prison of invisible force — a barred cage or a "
            "solid box — springs up around creatures in the area; it blocks "
            "teleportation attempts unless the captive wins a Charisma "
            "save, and it is immune to dispelling."
        ),
        material="ruby dust worth 1,500+ GP, which the spell consumes",
    ),
    SpellData(
        name="Finger of Death",
        level=7,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=60,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "You unleash lethal negative energy at a creature; a humanoid "
            "slain by this spell rises on your next turn as a zombie "
            "permanently under your command."
        ),
        save=Ability.CONSTITUTION,
        half_damage_on_save=True,
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("7d8+30"),
    ),
    SpellData(
        name="Fire Storm",
        level=7,
        school=SpellSchool.EVOCATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=150,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
        classes=[CharacterClass.CLERIC, CharacterClass.DRUID, CharacterClass.SORCERER],
        description=(
            "A storm of roaring flame fills ten connected 10-foot cubes "
            "that you arrange within range; you can spare plant life in "
            "the area if you choose."
        ),
        save=Ability.DEXTERITY,
        half_damage_on_save=True,
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("7d10"),
        area=AreaShape.CUBE,
        area_size_ft=10,
    ),
    SpellData(
        name="Teleport",
        level=7,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.RANGED,
        range_ft=10,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL],
        classes=[CharacterClass.BARD, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You and up to eight willing creatures (or one object) are "
            "instantly transported to a destination you choose on the same "
            "plane; how precisely you arrive depends on your familiarity "
            "with the destination."
        ),
    ),
    SpellData(
        name="Resurrection",
        level=7,
        school=SpellSchool.NECROMANCY,
        casting_time=CastingTime.ONE_HOUR,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[CharacterClass.BARD, CharacterClass.CLERIC],
        description=(
            "You restore life and full hit points to a willing creature "
            "dead up to a century, closing mortal wounds and neutralizing "
            "poisons and diseases; both you and the revived creature are "
            "weakened for a time afterward."
        ),
        material="a diamond worth 1,000+ GP, which the spell consumes",
    ),
    SpellData(
        name="Plane Shift",
        level=7,
        school=SpellSchool.CONJURATION,
        casting_time=CastingTime.ACTION,
        range_type=SpellRangeType.TOUCH,
        range_ft=None,
        duration="Instantaneous",
        concentration=False,
        components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "You and up to eight linked, willing companions step to "
            "another plane of existence — or you banish an unwilling "
            "creature you touch to a random spot on another plane if it "
            "fails a Charisma save."
        ),
        material="a forked metal rod worth 250+ GP attuned to a plane of existence",
        save=Ability.CHARISMA,
    ),
]
