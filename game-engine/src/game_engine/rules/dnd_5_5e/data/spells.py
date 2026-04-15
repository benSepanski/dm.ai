# NOTE: exceeds 400 LoC — single cohesive data module
"""D&D 5.5e SRD spell data — ~25 representative spells (cantrips + leveled)."""

from __future__ import annotations

from dataclasses import dataclass

from game_engine.types import Ability, CharacterClass, DamageType, DiceNotation, SpellSchool


@dataclass
class SpellData:
    name: str
    level: int  # 0 = cantrip
    school: SpellSchool  # abjuration, evocation, etc.
    casting_time: str
    range_ft: int | str  # int or "touch" / "self"
    duration: str
    concentration: bool
    components: list[str]  # ["V"], ["V","S"], ["V","S","M"]
    damage_type: DamageType | None
    damage_dice: DiceNotation | None  # e.g. DiceNotation("8d6")
    save: Ability | None  # e.g. Ability.DEXTERITY, Ability.CONSTITUTION
    classes: list[CharacterClass]
    description: str


SPELLS: list[SpellData] = [
    # ── Cantrips ──────────────────────────────────────────────────────────────
    SpellData(
        name="Fire Bolt",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=120,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("1d10"),
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Make a ranged spell attack against the target. On a hit, the target "
            "takes 1d10 fire damage. A flammable object hit ignites if not worn/carried."
        ),
    ),
    SpellData(
        name="Eldritch Blast",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=120,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("1d10"),
        save=None,
        classes=[CharacterClass.WARLOCK],
        description=(
            "A beam of crackling energy streaks toward a creature within range. "
            "Make a ranged spell attack. On a hit, the target takes 1d10 force damage."
        ),
    ),
    SpellData(
        name="Sacred Flame",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.RADIANT,
        damage_dice=DiceNotation("1d8"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.CLERIC],
        description=(
            "Flame-like radiance descends on a creature you can see within range. "
            "Target must succeed on a Dexterity save or take 1d8 radiant damage. "
            "Target gains no benefit from cover for this save."
        ),
    ),
    SpellData(
        name="Toll the Dead",
        level=0,
        school=SpellSchool.NECROMANCY,
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("1d8"),
        save=Ability.WISDOM,
        classes=[CharacterClass.CLERIC, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "Target must succeed on a Wisdom save or take 1d8 necrotic damage. "
            "If the target is missing any hit points, it takes 1d12 necrotic damage instead."
        ),
    ),
    SpellData(
        name="Chill Touch",
        level=0,
        school=SpellSchool.NECROMANCY,
        casting_time="1 action",
        range_ft=120,
        duration="1 round",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.NECROTIC,
        damage_dice=DiceNotation("1d8"),
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "Make a ranged spell attack. On a hit, target takes 1d8 necrotic damage "
            "and cannot regain hit points until the start of your next turn."
        ),
    ),
    SpellData(
        name="Poison Spray",
        level=0,
        school=SpellSchool.CONJURATION,
        casting_time="1 action",
        range_ft=30,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.POISON,
        damage_dice=DiceNotation("1d12"),
        save=Ability.CONSTITUTION,
        classes=[
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "Project a puff of noxious gas at a creature within range. The creature "
            "must succeed on a Constitution save or take 1d12 poison damage."
        ),
    ),
    SpellData(
        name="Acid Splash",
        level=0,
        school=SpellSchool.CONJURATION,
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.ACID,
        damage_dice=DiceNotation("1d6"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Hurl a bubble of acid at one creature or two creatures within 5 ft of "
            "each other. Each target must succeed on a Dexterity save or take 1d6 acid damage."
        ),
    ),
    SpellData(
        name="Ray of Frost",
        level=0,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.COLD,
        damage_dice=DiceNotation("1d8"),
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Make a ranged spell attack. On a hit, target takes 1d8 cold damage "
            "and its speed is reduced by 10 feet until the start of your next turn."
        ),
    ),
    # ── 1st Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Magic Missile",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=120,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FORCE,
        damage_dice=DiceNotation("1d4+1"),
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Create three glowing darts of magical force, each dealing 1d4+1 force "
            "damage. Darts strike simultaneously and can target one or multiple creatures."
        ),
    ),
    SpellData(
        name="Burning Hands",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("3d6"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A thin sheet of flames shoots from your fingertips in a 15-foot cone. "
            "Each creature in the cone must make a Dexterity save, taking 3d6 fire "
            "damage on a failure or half on a success."
        ),
    ),
    SpellData(
        name="Cure Wounds",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft="touch",
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=None,
        damage_dice=DiceNotation("1d8"),
        save=None,
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.PALADIN,
            CharacterClass.RANGER,
        ],
        description=(
            "A creature you touch regains 1d8 + spellcasting modifier hit points. "
            "No effect on undead or constructs."
        ),
    ),
    SpellData(
        name="Shield",
        level=1,
        school=SpellSchool.ABJURATION,
        casting_time="1 reaction",
        range_ft="self",
        duration="1 round",
        concentration=False,
        components=["V", "S"],
        damage_type=None,
        damage_dice=None,
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "An invisible barrier of magical force appears. Until the start of your "
            "next turn you gain +5 AC (including vs. the triggering attack) and take "
            "no damage from Magic Missile."
        ),
    ),
    SpellData(
        name="Sleep",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time="1 action",
        range_ft=90,
        duration="1 minute",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save=None,
        classes=[CharacterClass.BARD, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Roll 5d8; total = hit points of creatures this spell can affect. "
            "Creatures within a 20-ft-radius sphere are affected in ascending HP order."
        ),
    ),
    SpellData(
        name="Thunderwave",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.THUNDER,
        damage_dice=DiceNotation("2d8"),
        save=Ability.CONSTITUTION,
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A 15-foot cube of thunderous force erupts from you. Each creature "
            "in the area makes a Constitution save, taking 2d8 thunder damage and "
            "being pushed 10 ft on a failure, or half damage on a success."
        ),
    ),
    # ── 2nd Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Misty Step",
        level=2,
        school=SpellSchool.CONJURATION,
        casting_time="1 bonus action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V"],
        damage_type=None,
        damage_dice=None,
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description="Briefly surrounded by silvery mist, you teleport up to 30 feet to an unoccupied space you can see.",
    ),
    SpellData(
        name="Shatter",
        level=2,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.THUNDER,
        damage_dice=DiceNotation("3d8"),
        save=Ability.CONSTITUTION,
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A sudden ringing noise erupts from a point within range. Each creature "
            "in a 10-ft-radius sphere makes a Constitution save, taking 3d8 thunder "
            "damage on failure or half on success."
        ),
    ),
    # ── 3rd Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Fireball",
        level=3,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=150,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("8d6"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A bright streak explodes into a 20-ft-radius sphere of fire. Each "
            "creature in the area makes a Dexterity save, taking 8d6 fire damage "
            "on failure or half on success."
        ),
    ),
    SpellData(
        name="Lightning Bolt",
        level=3,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.LIGHTNING,
        damage_dice=DiceNotation("8d6"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A 100-ft-long, 5-ft-wide bolt of lightning blasts from you. Each "
            "creature in the line makes a Dexterity save, taking 8d6 lightning "
            "damage on failure or half on success."
        ),
    ),
    # ── 4th Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Ice Storm",
        level=4,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=300,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.BLUDGEONING,
        damage_dice=DiceNotation("2d8"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Hail pounds a 20-ft-radius, 40-ft-high cylinder. Creatures in the "
            "area make a Dexterity save, taking 2d8 bludgeoning + 4d6 cold on "
            "failure or half on success."
        ),
    ),
    SpellData(
        name="Polymorph",
        level=4,
        school=SpellSchool.TRANSMUTATION,
        casting_time="1 action",
        range_ft=60,
        duration="1 hour",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save=Ability.WISDOM,
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "Transform a creature within range into a new form. An unwilling target "
            "makes a Wisdom save. Lasts up to 1 hour, until target reaches 0 HP, or dies."
        ),
    ),
    SpellData(
        name="Banishment",
        level=4,
        school=SpellSchool.ABJURATION,
        casting_time="1 action",
        range_ft=60,
        duration="1 minute",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save=Ability.CHARISMA,
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.PALADIN,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "Target one creature within range; it must succeed on a Charisma save "
            "or be banished. If native to another plane it is permanently sent there "
            "when concentration ends."
        ),
    ),
    SpellData(
        name="Wall of Fire",
        level=4,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=120,
        duration="1 minute",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=DamageType.FIRE,
        damage_dice=DiceNotation("5d8"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.DRUID, CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "Create a 60-ft-long, 20-ft-high wall of fire on a solid surface. "
            "Creatures entering or starting their turn inside make a Dexterity save, "
            "taking 5d8 fire damage on failure or half on success."
        ),
    ),
    # ── 5th Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Cone of Cold",
        level=5,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.COLD,
        damage_dice=DiceNotation("8d8"),
        save=Ability.CONSTITUTION,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A blast of cold erupts in a 60-foot cone. Each creature makes a "
            "Constitution save, taking 8d8 cold damage on failure or half on success. "
            "Creatures killed become frozen statues."
        ),
    ),
    SpellData(
        name="Hold Monster",
        level=5,
        school=SpellSchool.ENCHANTMENT,
        casting_time="1 action",
        range_ft=90,
        duration="1 minute",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save=Ability.WISDOM,
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "Target a creature within range; it must succeed on a Wisdom save or be "
            "paralyzed. No effect on undead. Target may repeat the save each turn."
        ),
    ),
    # ── 6th-7th Level ────────────────────────────────────────────────────────
    SpellData(
        name="Chain Lightning",
        level=6,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=150,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.LIGHTNING,
        damage_dice=DiceNotation("10d8"),
        save=Ability.DEXTERITY,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A bolt of lightning arcs to a primary target, then leaps to up to "
            "three other targets within 30 ft of the first. Each target makes a "
            "Dexterity save, taking 10d8 lightning damage on failure or half on success."
        ),
    ),
    SpellData(
        name="Forcecage",
        level=7,
        school=SpellSchool.EVOCATION,
        casting_time="1 action",
        range_ft=100,
        duration="1 hour",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save=None,
        classes=[CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "An immobile, invisible cube-shaped prison of magical force springs into "
            "existence. Creatures inside cannot escape by nonmagical means and must "
            "make a Charisma save to use teleportation or interplanar travel."
        ),
    ),
]
