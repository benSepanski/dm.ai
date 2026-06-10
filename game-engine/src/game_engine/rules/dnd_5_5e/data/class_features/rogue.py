"""D&D 5.5e Rogue class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import CharacterClass, ClassResource, Subclass

ROGUE_PROGRESSION = ClassProgression(
    character_class=CharacterClass.ROGUE,
    features=[
        ClassFeatureData(
            "Expertise",
            1,
            "Choose two of your skill proficiencies; your proficiency bonus is doubled for "
            "checks using them.",
        ),
        ClassFeatureData(
            "Sneak Attack",
            1,
            "Once per turn, deal bonus damage dice when you hit with a finesse or ranged "
            "weapon while you have advantage or an ally is adjacent to the target.",
        ),
        ClassFeatureData(
            "Thieves' Cant",
            1,
            "You know the secret argot of the criminal underworld, plus one additional "
            "language of your choice.",
        ),
        ClassFeatureData(
            "Weapon Mastery",
            1,
            "You can use the mastery properties of two weapons of your choice, swapping your "
            "picks after a long rest.",
        ),
        ClassFeatureData(
            "Cunning Action",
            2,
            "Your quick thinking lets you Dash, Disengage, or Hide as a bonus action.",
        ),
        ClassFeatureData(
            "Rogue Subclass",
            3,
            "Choose a roguish archetype subclass that grants features at levels 3, 9, 13, "
            "and 17.",
        ),
        ClassFeatureData(
            "Steady Aim",
            3,
            "As a bonus action, forgo moving this turn to gain advantage on your next attack "
            "roll.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Cunning Strike",
            5,
            "Trade Sneak Attack dice for tactical effects on a hit, such as poisoning, "
            "tripping, or withdrawing from a target.",
        ),
        ClassFeatureData(
            "Uncanny Dodge",
            5,
            "When an attacker you can see hits you, you can use your reaction to halve the "
            "damage.",
        ),
        ClassFeatureData(
            "Expertise",
            6,
            "Choose two more of your skill proficiencies to gain double proficiency bonus.",
        ),
        ClassFeatureData(
            "Evasion",
            7,
            "On Dexterity saves against half-damage effects, you take no damage on a success "
            "and only half on a failure.",
        ),
        ClassFeatureData(
            "Reliable Talent",
            7,
            "Whenever you make an ability check using a skill or tool you're proficient "
            "with, treat any d20 roll of 9 or lower as a 10.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            10,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Improved Cunning Strike",
            11,
            "You can apply up to two Cunning Strike effects with a single Sneak Attack, "
            "paying the dice cost for each.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Devious Strikes",
            14,
            "You learn potent new Cunning Strike options that can daze, knock out, or "
            "obscure your target.",
        ),
        ClassFeatureData(
            "Slippery Mind",
            15,
            "Your mental defenses sharpen, granting proficiency in Wisdom and Charisma "
            "saving throws.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Elusive",
            18,
            "Attack rolls against you can't have advantage while you aren't incapacitated.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "skill.",
        ),
        ClassFeatureData(
            "Stroke of Luck",
            20,
            "Once per rest, turn a failed d20 test into a natural 20.",
        ),
        ClassFeatureData(
            "Fast Hands",
            3,
            "Your bonus-action Cunning Action can also be used to pick locks, disarm traps, "
            "pick pockets, or use a utility object.",
            subclass=Subclass.THIEF,
        ),
        ClassFeatureData(
            "Second-Story Work",
            3,
            "You gain a climb speed equal to your walking speed, and your running jumps "
            "stretch farther thanks to your Dexterity.",
            subclass=Subclass.THIEF,
        ),
        ClassFeatureData(
            "Supreme Sneak",
            9,
            "You gain a Cunning Strike option that keeps you hidden after a Sneak Attack "
            "while you remain obscured.",
            subclass=Subclass.THIEF,
        ),
        ClassFeatureData(
            "Use Magic Device",
            13,
            "You can attune to more magic items, sometimes preserve charges when using them, "
            "and use spell scrolls regardless of class lists.",
            subclass=Subclass.THIEF,
        ),
        ClassFeatureData(
            "Thief's Reflexes",
            17,
            "In combat, you can take a second turn during the first round at a reduced "
            "initiative count.",
            subclass=Subclass.THIEF,
        ),
    ],
    resources={
        ClassResource.SNEAK_ATTACK_DICE: [
            1,
            1,
            2,
            2,
            3,
            3,
            4,
            4,
            5,
            5,
            6,
            6,
            7,
            7,
            8,
            8,
            9,
            9,
            10,
            10,
        ],
        ClassResource.WEAPON_MASTERY: [2] * 20,
    },
)
