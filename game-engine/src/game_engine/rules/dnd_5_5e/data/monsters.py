# NOTE: exceeds 400 LoC — single cohesive data module
"""D&D 5.5e SRD monster data — ~20 representative monsters."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import DamageType, Condition, Ability


@dataclass
class MonsterAction:
    name: str
    attack_bonus: int | None
    damage_dice: str
    damage_type: DamageType
    reach_ft: int
    description: str


@dataclass
class MonsterData:
    name: str
    cr: float           # Challenge Rating (0.125, 0.25, 0.5, 1, 2, … 21)
    size: str           # Tiny/Small/Medium/Large/Huge/Gargantuan
    type: str           # beast, humanoid, undead, etc.
    hp_dice: str        # e.g. "2d8+2"
    hp_avg: int
    ac: int
    speed_ft: int
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    damage_immunities: list[DamageType]
    damage_resistances: list[DamageType]
    condition_immunities: list[Condition]
    saving_throw_proficiencies: list[Ability]
    actions: list[MonsterAction]
    special_traits: list[str]
    legendary_actions: list[str]


MONSTERS: list[MonsterData] = [
    # CR 1/8
    MonsterData(
        name="Kobold", cr=0.125, size="Small", type="humanoid",
        hp_dice="2d6", hp_avg=7, ac=12, speed_ft=30,
        strength=7, dexterity=15, constitution=9, intelligence=8, wisdom=7, charisma=8,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Dagger", 4, "1d4+2", DamageType.PIERCING, 5,
                          "Melee or ranged weapon attack."),
            MonsterAction("Sling", 4, "1d4+2", DamageType.BLUDGEONING, 5,
                          "Ranged weapon attack, range 30/120 ft."),
        ],
        special_traits=["Sunlight Sensitivity: Disadvantage on attack rolls and Perception checks in sunlight.",
                        "Pack Tactics: Advantage on attack rolls when an ally is adjacent to the target."],
        legendary_actions=[],
    ),
    # CR 1/4 ──────────────────────────────────────────────────────────────────
    MonsterData(
        name="Goblin", cr=0.25, size="Small", type="humanoid",
        hp_dice="2d6", hp_avg=7, ac=15, speed_ft=30,
        strength=8, dexterity=14, constitution=10, intelligence=10, wisdom=8, charisma=8,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Scimitar", 4, "1d6+2", DamageType.SLASHING, 5,
                          "Melee weapon attack."),
            MonsterAction("Shortbow", 4, "1d6+2", DamageType.PIERCING, 5,
                          "Ranged weapon attack, range 80/320 ft."),
        ],
        special_traits=["Nimble Escape: Can take Disengage or Hide as a bonus action each turn."],
        legendary_actions=[],
    ),
    MonsterData(
        name="Skeleton", cr=0.25, size="Medium", type="undead",
        hp_dice="2d8+4", hp_avg=13, ac=13, speed_ft=30,
        strength=10, dexterity=14, constitution=15, intelligence=6, wisdom=8, charisma=5,
        damage_immunities=[DamageType.POISON],
        damage_resistances=[],
        condition_immunities=[Condition.EXHAUSTION, Condition.POISONED],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Shortsword", 4, "1d6+2", DamageType.PIERCING, 5,
                          "Melee weapon attack."),
            MonsterAction("Shortbow", 4, "1d6+2", DamageType.PIERCING, 5,
                          "Ranged weapon attack, range 80/320 ft."),
        ],
        special_traits=[],
        legendary_actions=[],
    ),
    MonsterData(
        name="Zombie", cr=0.25, size="Medium", type="undead",
        hp_dice="3d8+9", hp_avg=22, ac=8, speed_ft=20,
        strength=13, dexterity=6, constitution=16, intelligence=3, wisdom=6, charisma=5,
        damage_immunities=[DamageType.POISON],
        damage_resistances=[],
        condition_immunities=[Condition.POISONED],
        saving_throw_proficiencies=[Ability.WISDOM],
        actions=[
            MonsterAction("Slam", 3, "1d6+1", DamageType.BLUDGEONING, 5,
                          "Melee weapon attack."),
        ],
        special_traits=["Undead Fortitude: On being reduced to 0 HP, makes a Constitution save (DC = 5 + damage taken). On success it drops to 1 HP instead."],
        legendary_actions=[],
    ),
    MonsterData(
        name="Wolf", cr=0.25, size="Medium", type="beast",
        hp_dice="2d8+2", hp_avg=11, ac=13, speed_ft=40,
        strength=12, dexterity=15, constitution=12, intelligence=3, wisdom=12, charisma=6,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Bite", 4, "2d4+2", DamageType.PIERCING, 5,
                          "Melee weapon attack. Target must make DC 11 Strength save or be knocked prone."),
        ],
        special_traits=["Keen Hearing and Smell: Advantage on Perception checks relying on hearing or smell.",
                        "Pack Tactics: Advantage on attack rolls when an ally is adjacent to the target."],
        legendary_actions=[],
    ),
    # CR 1/2
    MonsterData(
        name="Orc", cr=0.5, size="Medium", type="humanoid",
        hp_dice="2d8+6", hp_avg=15, ac=13, speed_ft=30,
        strength=16, dexterity=12, constitution=16, intelligence=7, wisdom=11, charisma=10,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Greataxe", 5, "1d12+3", DamageType.SLASHING, 5,
                          "Melee weapon attack."),
            MonsterAction("Javelin", 5, "1d6+3", DamageType.PIERCING, 5,
                          "Melee or ranged weapon attack, range 30/120 ft."),
        ],
        special_traits=["Aggressive: As a bonus action, move up to speed toward a hostile creature."],
        legendary_actions=[],
    ),
    # CR 1 ────────────────────────────────────────────────────────────────────
    MonsterData(
        name="Giant Spider", cr=1.0, size="Large", type="beast",
        hp_dice="4d10+4", hp_avg=26, ac=14, speed_ft=30,
        strength=14, dexterity=16, constitution=12, intelligence=2, wisdom=11, charisma=4,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Bite", 5, "1d8+3", DamageType.PIERCING, 5,
                          "Target must make DC 11 Constitution save or take 2d8 poison damage."),
            MonsterAction("Web", None, "0", DamageType.BLUDGEONING, 5,
                          "Ranged attack, range 30/60 ft. Target is restrained (DC 12 Strength to escape)."),
        ],
        special_traits=["Spider Climb: Can climb difficult surfaces, including upside down.",
                        "Web Sense: Knows location of anything touching its web.",
                        "Web Walker: Ignores movement restrictions caused by webbing."],
        legendary_actions=[],
    ),
    MonsterData(
        name="Bugbear", cr=1.0, size="Medium", type="humanoid",
        hp_dice="5d8+5", hp_avg=27, ac=16, speed_ft=30,
        strength=15, dexterity=14, constitution=13, intelligence=8, wisdom=11, charisma=9,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Morningstar", 4, "2d8+2", DamageType.PIERCING, 5,
                          "Melee weapon attack."),
            MonsterAction("Javelin", 4, "2d6+2", DamageType.PIERCING, 5,
                          "Melee or ranged attack, range 30/120 ft."),
        ],
        special_traits=["Brute: A melee weapon hit deals one extra die of damage (included above).",
                        "Surprise Attack: +2d6 damage on first hit if target hasn't taken a turn yet."],
        legendary_actions=[],
    ),
    # CR 2 ────────────────────────────────────────────────────────────────────
    MonsterData(
        name="Ghoul", cr=2.0, size="Medium", type="undead",
        hp_dice="5d8+5", hp_avg=22, ac=12, speed_ft=30,
        strength=13, dexterity=15, constitution=10, intelligence=7, wisdom=10, charisma=6,
        damage_immunities=[DamageType.POISON],
        damage_resistances=[],
        condition_immunities=[Condition.CHARMED, Condition.EXHAUSTION, Condition.POISONED],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Bite", 2, "2d6+2", DamageType.PIERCING, 5,
                          "Melee weapon attack. Not usable against undead or constructs."),
            MonsterAction("Claws", 4, "2d4+2", DamageType.SLASHING, 5,
                          "Target (not elf/undead) makes DC 10 Constitution save or is paralyzed until end of its next turn."),
        ],
        special_traits=[],
        legendary_actions=[],
    ),
    MonsterData(
        name="Ogre", cr=2.0, size="Large", type="giant",
        hp_dice="7d10+21", hp_avg=59, ac=11, speed_ft=40,
        strength=19, dexterity=8, constitution=16, intelligence=5, wisdom=7, charisma=7,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Greatclub", 6, "2d8+4", DamageType.BLUDGEONING, 5,
                          "Melee weapon attack."),
            MonsterAction("Javelin", 6, "2d6+4", DamageType.PIERCING, 5,
                          "Melee or ranged weapon attack, range 30/120 ft."),
        ],
        special_traits=[],
        legendary_actions=[],
    ),
    # CR 3 ────────────────────────────────────────────────────────────────────
    MonsterData(
        name="Manticore", cr=3.0, size="Large", type="monstrosity",
        hp_dice="8d10+24", hp_avg=68, ac=14, speed_ft=30,
        strength=17, dexterity=16, constitution=17, intelligence=7, wisdom=12, charisma=8,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Bite", 5, "1d8+3", DamageType.PIERCING, 5, "Melee weapon attack."),
            MonsterAction("Claw", 5, "2d6+3", DamageType.SLASHING, 5, "Melee weapon attack."),
            MonsterAction("Tail Spike", 5, "2d8+3", DamageType.PIERCING, 5,
                          "Ranged weapon attack, range 100/200 ft. Can make up to 3 per turn (24 total)."),
        ],
        special_traits=["Tail Spike Regrowth: Has 24 tail spikes; used spikes regrow when it finishes a long rest."],
        legendary_actions=[],
    ),
    MonsterData(
        name="Basilisk", cr=3.0, size="Medium", type="monstrosity",
        hp_dice="8d8+16", hp_avg=52, ac=15, speed_ft=20,
        strength=16, dexterity=8, constitution=15, intelligence=2, wisdom=8, charisma=7,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Bite", 5, "2d6+3", DamageType.PIERCING, 5,
                          "Melee weapon attack; additionally deals 2d6 poison damage."),
        ],
        special_traits=["Petrifying Gaze: Creatures that start their turn within 30 ft and can see the basilisk's eyes must make a DC 12 Constitution save or begin petrifying (petrified on second failure)."],
        legendary_actions=[],
    ),
    MonsterData(
        name="Owlbear", cr=3.0, size="Large", type="monstrosity",
        hp_dice="7d10+21", hp_avg=59, ac=13, speed_ft=40,
        strength=20, dexterity=12, constitution=17, intelligence=3, wisdom=12, charisma=7,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Multiattack", None, "0", DamageType.SLASHING, 5,
                          "Makes two attacks: one with its beak and one with its claws."),
            MonsterAction("Beak", 7, "1d10+5", DamageType.PIERCING, 5, "Melee weapon attack."),
            MonsterAction("Claws", 7, "2d8+5", DamageType.SLASHING, 5, "Melee weapon attack."),
        ],
        special_traits=["Keen Sight and Smell: Advantage on Perception checks relying on sight or smell."],
        legendary_actions=[],
    ),
    # CR 4 ────────────────────────────────────────────────────────────────────
    MonsterData(
        name="Banshee", cr=4.0, size="Medium", type="undead",
        hp_dice="13d8", hp_avg=58, ac=12, speed_ft=40,
        strength=1, dexterity=14, constitution=10, intelligence=12, wisdom=11, charisma=17,
        damage_immunities=[DamageType.COLD, DamageType.NECROTIC, DamageType.POISON],
        damage_resistances=[
            DamageType.ACID, DamageType.FIRE, DamageType.LIGHTNING, DamageType.THUNDER,
            DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING,
        ],
        condition_immunities=[
            Condition.CHARMED, Condition.EXHAUSTION, Condition.FRIGHTENED,
            Condition.GRAPPLED, Condition.PARALYZED, Condition.PETRIFIED,
            Condition.POISONED, Condition.PRONE, Condition.RESTRAINED,
        ],
        saving_throw_proficiencies=[Ability.WISDOM, Ability.CHARISMA],
        actions=[
            MonsterAction("Corrupting Touch", 4, "3d6", DamageType.NECROTIC, 5,
                          "Melee spell attack."),
            MonsterAction("Horrifying Visage", None, "0", DamageType.PSYCHIC, 30,
                          "Each non-undead within 60 ft that can see the banshee makes DC 13 Wisdom save or is frightened for 1 minute."),
            MonsterAction("Wail", None, "0", DamageType.PSYCHIC, 30,
                          "Each non-undead creature within 30 ft that can hear the wail makes DC 13 Constitution save or drops to 0 HP."),
        ],
        special_traits=["Detect Life: Can sense the life force of creatures within 5 miles.",
                        "Incorporeal Movement: Can move through creatures and objects."],
        legendary_actions=[],
    ),
    # CR 5 ────────────────────────────────────────────────────────────────────
    MonsterData(
        name="Troll", cr=5.0, size="Large", type="giant",
        hp_dice="8d10+40", hp_avg=84, ac=15, speed_ft=30,
        strength=18, dexterity=13, constitution=20, intelligence=7, wisdom=9, charisma=7,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Multiattack", None, "0", DamageType.SLASHING, 5,
                          "Makes three attacks: one with its bite and two with its claws."),
            MonsterAction("Bite", 7, "1d6+4", DamageType.PIERCING, 5, "Melee weapon attack."),
            MonsterAction("Claw", 7, "2d6+4", DamageType.SLASHING, 5, "Melee weapon attack."),
        ],
        special_traits=["Keen Smell: Advantage on Perception checks relying on smell.",
                        "Regeneration: Regains 10 HP at the start of its turn unless it took acid or fire damage since its last turn."],
        legendary_actions=[],
    ),
    # CR 6 ────────────────────────────────────────────────────────────────────
    MonsterData(
        name="Wyvern", cr=6.0, size="Large", type="dragon",
        hp_dice="13d10+39", hp_avg=110, ac=13, speed_ft=20,
        strength=19, dexterity=10, constitution=16, intelligence=5, wisdom=12, charisma=6,
        damage_immunities=[], damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[],
        actions=[
            MonsterAction("Multiattack", None, "0", DamageType.PIERCING, 5,
                          "Makes two attacks: one with its bite and one with its stinger. While flying, may substitute a claw attack."),
            MonsterAction("Bite", 7, "2d6+4", DamageType.PIERCING, 10, "Melee weapon attack."),
            MonsterAction("Claw", 7, "2d8+4", DamageType.SLASHING, 5, "Melee weapon attack."),
            MonsterAction("Stinger", 7, "2d6+4", DamageType.PIERCING, 10,
                          "Melee weapon attack. Target makes DC 15 Constitution save or takes 7d6 poison damage (half on success)."),
        ],
        special_traits=[],
        legendary_actions=[],
    ),
    # CR 13 ───────────────────────────────────────────────────────────────────
    MonsterData(
        name="Young Red Dragon", cr=13.0, size="Large", type="dragon",
        hp_dice="17d10+85", hp_avg=178, ac=18, speed_ft=40,
        strength=23, dexterity=10, constitution=21, intelligence=14, wisdom=11, charisma=19,
        damage_immunities=[DamageType.FIRE],
        damage_resistances=[],
        condition_immunities=[],
        saving_throw_proficiencies=[
            Ability.DEXTERITY, Ability.CONSTITUTION, Ability.WISDOM, Ability.CHARISMA,
        ],
        actions=[
            MonsterAction("Multiattack", None, "0", DamageType.PIERCING, 10,
                          "Makes three attacks: one with its bite and two with its claws."),
            MonsterAction("Bite", 10, "2d10+6", DamageType.PIERCING, 10,
                          "Melee weapon attack; also deals 1d6 fire damage."),
            MonsterAction("Claw", 10, "2d6+6", DamageType.SLASHING, 5, "Melee weapon attack."),
            MonsterAction("Fire Breath", None, "16d6", DamageType.FIRE, 30,
                          "30-ft cone; DC 18 Dexterity save for half damage."),
        ],
        special_traits=["Frightful Presence: Creatures within 120 ft aware of the dragon make DC 16 Wisdom save or are frightened for 1 minute."],
        legendary_actions=[],
    ),
    MonsterData(
        name="Vampire", cr=13.0, size="Medium", type="undead",
        hp_dice="17d8+68", hp_avg=144, ac=16, speed_ft=30,
        strength=18, dexterity=18, constitution=18, intelligence=17, wisdom=15, charisma=18,
        damage_immunities=[],
        damage_resistances=[
            DamageType.NECROTIC,
            DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING,
        ],
        condition_immunities=[],
        saving_throw_proficiencies=[
            Ability.DEXTERITY, Ability.WISDOM, Ability.CHARISMA,
        ],
        actions=[
            MonsterAction("Multiattack", None, "0", DamageType.BLUDGEONING, 5,
                          "Makes two attacks, only one of which can be a bite."),
            MonsterAction("Unarmed Strike", 9, "1d8+4", DamageType.BLUDGEONING, 5,
                          "Grapples on hit (escape DC 18)."),
            MonsterAction("Bite", 9, "1d6+4", DamageType.PIERCING, 5,
                          "Only against grappled, incapacitated, or willing creatures; deals 3d6 necrotic, reduces HP max."),
        ],
        special_traits=["Legendary Resistance (3/Day): If it fails a save, it can choose to succeed instead.",
                        "Regeneration: Regains 20 HP at start of turn if it has at least 1 HP (not in sunlight or running water).",
                        "Spider Climb: Can climb difficult surfaces including upside down.",
                        "Vampire Weaknesses: Harmed by sunlight and running water; cannot enter without invitation."],
        legendary_actions=["Move up to speed without provoking opportunity attacks.",
                           "Unarmed Strike (costs 2 actions).",
                           "Bite (costs 2 actions)."],
    ),
    MonsterData(
        name="Beholder", cr=13.0, size="Large", type="aberration",
        hp_dice="19d10+76", hp_avg=180, ac=18, speed_ft=0,
        strength=10, dexterity=14, constitution=18, intelligence=17, wisdom=15, charisma=17,
        damage_immunities=[],
        damage_resistances=[],
        condition_immunities=[Condition.PRONE],
        saving_throw_proficiencies=[Ability.INTELLIGENCE, Ability.WISDOM, Ability.CHARISMA],
        actions=[
            MonsterAction("Bite", 5, "4d6", DamageType.PIERCING, 5, "Melee weapon attack."),
            MonsterAction("Eye Rays", None, "0", DamageType.PSYCHIC, 120,
                          "Shoots 3 random eye rays at targets within 120 ft. Effects vary by ray."),
        ],
        special_traits=["Antimagic Cone: Central eye creates a 150-ft cone; magic is suppressed in the cone.",
                        "Legendary Resistance (3/Day): May choose to succeed on a failed save."],
        legendary_actions=["Eye Ray: Use one random eye ray.",
                           "Eye Ray (costs 2 actions): Use two random eye rays."],
    ),
    # CR 21 ───────────────────────────────────────────────────────────────────
    MonsterData(
        name="Lich", cr=21.0, size="Medium", type="undead",
        hp_dice="18d8+90", hp_avg=135, ac=17, speed_ft=30,
        strength=11, dexterity=16, constitution=16, intelligence=20, wisdom=14, charisma=16,
        damage_immunities=[DamageType.POISON, DamageType.COLD],
        damage_resistances=[
            DamageType.NECROTIC,
            DamageType.BLUDGEONING, DamageType.PIERCING, DamageType.SLASHING,
        ],
        condition_immunities=[
            Condition.CHARMED, Condition.EXHAUSTION, Condition.FRIGHTENED,
            Condition.PARALYZED, Condition.POISONED,
        ],
        saving_throw_proficiencies=[
            Ability.CONSTITUTION, Ability.INTELLIGENCE, Ability.WISDOM,
        ],
        actions=[
            MonsterAction("Paralyzing Touch", 7, "3d6", DamageType.COLD, 5,
                          "Melee spell attack. Target makes DC 18 Constitution save or is paralyzed until end of its next turn."),
        ],
        special_traits=["Legendary Resistance (3/Day): If it fails a saving throw, it can choose to succeed instead.",
                        "Rejuvenation: If it has a phylactery, the lich gains a new body in 1d10 days after death.",
                        "Spellcasting: Intelligence-based, spell save DC 20, +12 to hit. Casts 9th-level spells.",
                        "Turn Resistance: Advantage on saving throws against effects that turn undead."],
        legendary_actions=["Cantrip: Cast a cantrip.",
                           "Paralyzing Touch (costs 2 actions): Use Paralyzing Touch.",
                           "Frightening Gaze (costs 2 actions): Target within 10 ft makes DC 18 Wisdom save or is frightened for 1 minute.",
                           "Disrupt Life (costs 3 actions): Each creature within 20 ft makes DC 18 Constitution save, taking 21 (6d6) necrotic on failure."],
    ),
]
