"""
D&D 5.5e SRD spell data.

Contains ~25 representative spells (cantrips and leveled) with typed fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import DamageType, CharacterClass


@dataclass
class SpellData:
    name: str
    level: int  # 0 = cantrip
    school: str  # abjuration, evocation, etc.
    casting_time: str
    range_ft: int | str  # int or "touch" / "self"
    duration: str
    concentration: bool
    components: list[str]  # ["V"], ["V","S"], ["V","S","M"]
    damage_type: DamageType | None
    damage_dice: str | None  # e.g. "8d6"
    save: str | None  # e.g. "dex", "con"
    classes: list[CharacterClass]
    description: str


SPELLS: list[SpellData] = [
    # ── Cantrips ──────────────────────────────────────────────────────────────
    SpellData(
        name="Fire Bolt",
        level=0,
        school="evocation",
        casting_time="1 action",
        range_ft=120,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FIRE,
        damage_dice="1d10",
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You hurl a mote of fire at a creature or object within range. "
            "Make a ranged spell attack against the target. On a hit, the "
            "target takes 1d10 fire damage. A flammable object hit by this "
            "spell ignites if it isn't being worn or carried."
        ),
    ),
    SpellData(
        name="Eldritch Blast",
        level=0,
        school="evocation",
        casting_time="1 action",
        range_ft=120,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FORCE,
        damage_dice="1d10",
        save=None,
        classes=[CharacterClass.WARLOCK],
        description=(
            "A beam of crackling energy streaks toward a creature within range. "
            "Make a ranged spell attack against the target. On a hit, the target "
            "takes 1d10 force damage. The spell creates more than one beam when "
            "you reach higher levels."
        ),
    ),
    SpellData(
        name="Sacred Flame",
        level=0,
        school="evocation",
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.RADIANT,
        damage_dice="1d8",
        save="dex",
        classes=[CharacterClass.CLERIC],
        description=(
            "Flame-like radiance descends on a creature that you can see within "
            "range. The target must succeed on a Dexterity saving throw or take "
            "1d8 radiant damage. The target gains no benefit from cover for this "
            "saving throw."
        ),
    ),
    SpellData(
        name="Toll the Dead",
        level=0,
        school="necromancy",
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.NECROTIC,
        damage_dice="1d8",
        save="wis",
        classes=[CharacterClass.CLERIC, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "You point at one creature you can see within range, and the sound "
            "of a dolorous bell fills the air around it for a moment. The target "
            "must succeed on a Wisdom saving throw or take 1d8 necrotic damage. "
            "If the target is missing any of its hit points, it instead takes 1d12 "
            "necrotic damage."
        ),
    ),
    SpellData(
        name="Chill Touch",
        level=0,
        school="necromancy",
        casting_time="1 action",
        range_ft=120,
        duration="1 round",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.NECROTIC,
        damage_dice="1d8",
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WARLOCK, CharacterClass.WIZARD],
        description=(
            "You create a ghostly, skeletal hand in the space of a creature within "
            "range. Make a ranged spell attack against the creature to assail it "
            "with the chill of the grave. On a hit, the target takes 1d8 necrotic "
            "damage, and it can't regain hit points until the start of your next turn."
        ),
    ),
    SpellData(
        name="Poison Spray",
        level=0,
        school="conjuration",
        casting_time="1 action",
        range_ft=30,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.POISON,
        damage_dice="1d12",
        save="con",
        classes=[
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "You extend your hand toward a creature you can see within range and "
            "project a puff of noxious gas. The creature must succeed on a "
            "Constitution saving throw or take 1d12 poison damage."
        ),
    ),
    SpellData(
        name="Acid Splash",
        level=0,
        school="conjuration",
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.ACID,
        damage_dice="1d6",
        save="dex",
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You hurl a bubble of acid. Choose one creature you can see within "
            "range, or choose two creatures you can see within range that are "
            "within 5 feet of each other. A target must succeed on a Dexterity "
            "saving throw or take 1d6 acid damage."
        ),
    ),
    SpellData(
        name="Ray of Frost",
        level=0,
        school="evocation",
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.COLD,
        damage_dice="1d8",
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A frigid beam of blue-white light streaks toward a creature within "
            "range. Make a ranged spell attack against the target. On a hit, it "
            "takes 1d8 cold damage, and its speed is reduced by 10 feet until the "
            "start of your next turn."
        ),
    ),
    # ── 1st Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Magic Missile",
        level=1,
        school="evocation",
        casting_time="1 action",
        range_ft=120,
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FORCE,
        damage_dice="1d4+1",
        save=None,
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You create three glowing darts of magical force. Each dart hits a "
            "creature of your choice that you can see within range. A dart deals "
            "1d4+1 force damage to its target. The darts all strike simultaneously "
            "and you can direct them to hit one creature or several."
        ),
    ),
    SpellData(
        name="Burning Hands",
        level=1,
        school="evocation",
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.FIRE,
        damage_dice="3d6",
        save="dex",
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "As you hold your hands with thumbs touching and fingers spread, a "
            "thin sheet of flames shoots forth from your outstretched fingertips. "
            "Each creature in a 15-foot cone must make a Dexterity saving throw. "
            "A creature takes 3d6 fire damage on a failed save, or half as much "
            "on a successful one."
        ),
    ),
    SpellData(
        name="Cure Wounds",
        level=1,
        school="evocation",
        casting_time="1 action",
        range_ft="touch",
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=None,
        damage_dice="1d8",
        save=None,
        classes=[
            CharacterClass.BARD,
            CharacterClass.CLERIC,
            CharacterClass.DRUID,
            CharacterClass.PALADIN,
            CharacterClass.RANGER,
        ],
        description=(
            "A creature you touch regains a number of hit points equal to "
            "1d8 + your spellcasting ability modifier. This spell has no effect "
            "on undead or constructs."
        ),
    ),
    SpellData(
        name="Shield",
        level=1,
        school="abjuration",
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
            "An invisible barrier of magical force appears and protects you. "
            "Until the start of your next turn, you have a +5 bonus to AC, "
            "including against the triggering attack, and you take no damage "
            "from Magic Missile."
        ),
    ),
    SpellData(
        name="Sleep",
        level=1,
        school="enchantment",
        casting_time="1 action",
        range_ft=90,
        duration="1 minute",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save=None,
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "This spell sends creatures into a magical slumber. Roll 5d8; the "
            "total is how many hit points of creatures this spell can affect. "
            "Creatures within 20 feet of a point you choose within range are "
            "affected in ascending order of their current hit points."
        ),
    ),
    SpellData(
        name="Thunderwave",
        level=1,
        school="evocation",
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S"],
        damage_type=DamageType.THUNDER,
        damage_dice="2d8",
        save="con",
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A wave of thunderous force sweeps out from you. Each creature in a "
            "15-foot cube originating from you must make a Constitution saving "
            "throw. On a failed save, a creature takes 2d8 thunder damage and is "
            "pushed 10 feet away from you. On a successful save, the creature "
            "takes half damage and isn't pushed."
        ),
    ),
    # ── 2nd Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Misty Step",
        level=2,
        school="conjuration",
        casting_time="1 bonus action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V"],
        damage_type=None,
        damage_dice=None,
        save=None,
        classes=[
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "Briefly surrounded by silvery mist, you teleport up to 30 feet to "
            "an unoccupied space that you can see."
        ),
    ),
    SpellData(
        name="Shatter",
        level=2,
        school="evocation",
        casting_time="1 action",
        range_ft=60,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.THUNDER,
        damage_dice="3d8",
        save="con",
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "A sudden loud ringing noise, painfully intense, erupts from a point "
            "of your choice within range. Each creature in a 10-foot-radius sphere "
            "centered on that point must make a Constitution saving throw. A "
            "creature takes 3d8 thunder damage on a failed save, or half as much "
            "on a successful one."
        ),
    ),
    # ── 3rd Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Fireball",
        level=3,
        school="evocation",
        casting_time="1 action",
        range_ft=150,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.FIRE,
        damage_dice="8d6",
        save="dex",
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A bright streak flashes from your pointing finger to a point you "
            "choose within range and then blossoms with a low roar into an "
            "explosion of flame. Each creature in a 20-foot-radius sphere centered "
            "on that point must make a Dexterity saving throw. A target takes 8d6 "
            "fire damage on a failed save, or half as much on a successful one."
        ),
    ),
    SpellData(
        name="Lightning Bolt",
        level=3,
        school="evocation",
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.LIGHTNING,
        damage_dice="8d6",
        save="dex",
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A stroke of lightning forming a line 100 feet long and 5 feet wide "
            "blasts out from you in a direction you choose. Each creature in the "
            "line must make a Dexterity saving throw. A creature takes 8d6 "
            "lightning damage on a failed save, or half as much on a successful one."
        ),
    ),
    # ── 4th Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Ice Storm",
        level=4,
        school="evocation",
        casting_time="1 action",
        range_ft=300,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.BLUDGEONING,
        damage_dice="2d8",
        save="dex",
        classes=[
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "A hail of rock-hard ice pounds to the ground in a 20-foot-radius, "
            "40-foot-high cylinder centered on a point within range. Each creature "
            "in the cylinder must make a Dexterity saving throw. A creature takes "
            "2d8 bludgeoning damage and 4d6 cold damage on a failed save, or half "
            "as much on a successful one."
        ),
    ),
    SpellData(
        name="Polymorph",
        level=4,
        school="transmutation",
        casting_time="1 action",
        range_ft=60,
        duration="1 hour",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save="wis",
        classes=[
            CharacterClass.BARD,
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "This spell transforms a creature that you can see within range into "
            "a new form. An unwilling creature must make a Wisdom saving throw to "
            "avoid the effect. The transformation lasts for the duration, or until "
            "the target drops to 0 hit points or dies."
        ),
    ),
    SpellData(
        name="Banishment",
        level=4,
        school="abjuration",
        casting_time="1 action",
        range_ft=60,
        duration="1 minute",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save="cha",
        classes=[
            CharacterClass.CLERIC,
            CharacterClass.PALADIN,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "You attempt to send one creature that you can see within range to "
            "another plane of existence. The target must succeed on a Charisma "
            "saving throw or be banished. If the target is native to a different "
            "plane of existence, the target is banished with a faint popping noise."
        ),
    ),
    # ── 5th Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Wall of Fire",
        level=4,
        school="evocation",
        casting_time="1 action",
        range_ft=120,
        duration="1 minute",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=DamageType.FIRE,
        damage_dice="5d8",
        save="dex",
        classes=[
            CharacterClass.DRUID,
            CharacterClass.SORCERER,
            CharacterClass.WIZARD,
        ],
        description=(
            "You create a wall of fire on a solid surface within range. The wall "
            "can be up to 60 feet long, 20 feet high, and 1 foot thick, or a "
            "ringed wall up to 20 feet in diameter, 20 feet high, and 1 foot thick. "
            "The wall is opaque and lasts for the duration. When the wall appears, "
            "each creature in its area must make a Dexterity saving throw."
        ),
    ),
    SpellData(
        name="Cone of Cold",
        level=5,
        school="evocation",
        casting_time="1 action",
        range_ft="self",
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.COLD,
        damage_dice="8d8",
        save="con",
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "A blast of cold air erupts from your hands. Each creature in a "
            "60-foot cone must make a Constitution saving throw. A creature takes "
            "8d8 cold damage on a failed save, or half as much on a successful one. "
            "A creature killed by this spell becomes a frozen statue until it thaws."
        ),
    ),
    SpellData(
        name="Hold Monster",
        level=5,
        school="enchantment",
        casting_time="1 action",
        range_ft=90,
        duration="1 minute",
        concentration=True,
        components=["V", "S", "M"],
        damage_type=None,
        damage_dice=None,
        save="wis",
        classes=[
            CharacterClass.BARD,
            CharacterClass.SORCERER,
            CharacterClass.WARLOCK,
            CharacterClass.WIZARD,
        ],
        description=(
            "Choose a creature that you can see within range. The target must "
            "succeed on a Wisdom saving throw or be paralyzed for the duration. "
            "This spell has no effect on undead. At the end of each of its turns, "
            "the target can make another Wisdom saving throw."
        ),
    ),
    # ── 6th Level ─────────────────────────────────────────────────────────────
    SpellData(
        name="Chain Lightning",
        level=6,
        school="evocation",
        casting_time="1 action",
        range_ft=150,
        duration="instantaneous",
        concentration=False,
        components=["V", "S", "M"],
        damage_type=DamageType.LIGHTNING,
        damage_dice="10d8",
        save="dex",
        classes=[CharacterClass.SORCERER, CharacterClass.WIZARD],
        description=(
            "You create a bolt of lightning that arcs toward a target of your "
            "choice that you can see within range. Three bolts then leap from "
            "that target to as many as three other targets, each of which must "
            "be within 30 feet of the first target. A target can be a creature "
            "or an object and can be targeted by only one of the bolts. A target "
            "must make a Dexterity saving throw. The target takes 10d8 lightning "
            "damage on a failed save, or half as much on a successful one."
        ),
    ),
    SpellData(
        name="Forcecage",
        level=7,
        school="evocation",
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
            "An immobile, invisible, cube-shaped prison composed of magical force "
            "springs into existence around an area you choose within range. The "
            "prison can be a cage or a solid box. A creature inside can't leave "
            "the prison by nonmagical means. If a creature tries to use teleportation "
            "or interplanar travel to leave, it must first make a Charisma saving throw."
        ),
    ),
]
