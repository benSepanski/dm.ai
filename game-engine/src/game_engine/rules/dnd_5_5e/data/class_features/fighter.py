"""D&D 5.5e Fighter class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import CharacterClass, ClassResource, Subclass

FIGHTER_PROGRESSION = ClassProgression(
    character_class=CharacterClass.FIGHTER,
    features=[
        ClassFeatureData(
            "Fighting Style",
            1,
            "You gain a Fighting Style feat of your choice, reflecting your specialized "
            "combat training.",
        ),
        ClassFeatureData(
            "Second Wind",
            1,
            "As a bonus action, draw on your stamina to regain hit points; you have a "
            "limited number of uses that recharge on rests.",
        ),
        ClassFeatureData(
            "Weapon Mastery",
            1,
            "You can use the mastery properties of several weapons of your choice, swapping "
            "your selections after a long rest.",
        ),
        ClassFeatureData(
            "Action Surge",
            2,
            "Once per rest, push beyond your limits to take one additional action (other "
            "than the Magic action) on your turn.",
        ),
        ClassFeatureData(
            "Tactical Mind",
            2,
            "When you fail an ability check, you can expend a use of Second Wind to add a "
            "d10 to the roll, keeping the use if the check still fails.",
        ),
        ClassFeatureData(
            "Fighter Subclass",
            3,
            "Choose a martial archetype subclass that grants features at levels 3, 7, 10, "
            "15, and 18.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Extra Attack",
            5,
            "When you take the Attack action, you can make two attacks instead of one.",
        ),
        ClassFeatureData(
            "Tactical Shift",
            5,
            "When you use Second Wind, you can also move up to half your speed without "
            "provoking opportunity attacks.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            6,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Indomitable",
            9,
            "When you fail a saving throw, you can reroll it with a bonus equal to your "
            "fighter level; you must use the new result.",
        ),
        ClassFeatureData(
            "Tactical Master",
            9,
            "When you attack with a mastery weapon, you can replace its mastery property "
            "with the Push, Sap, or Slow property for that attack.",
        ),
        ClassFeatureData(
            "Two Extra Attacks",
            11,
            "When you take the Attack action, you can make three attacks instead of one.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Studied Attacks",
            13,
            "When you miss a creature with an attack roll, you study its defenses and gain "
            "advantage on your next attack roll against it.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            14,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "prowess.",
        ),
        ClassFeatureData(
            "Three Extra Attacks",
            20,
            "When you take the Attack action, you can make four attacks instead of one.",
        ),
        ClassFeatureData(
            "Improved Critical",
            3,
            "Your weapon and unarmed attacks score a critical hit on a roll of 19 or 20.",
            subclass=Subclass.CHAMPION,
        ),
        ClassFeatureData(
            "Remarkable Athlete",
            7,
            "Your physical conditioning grants advantage on initiative rolls and Strength "
            "(Athletics) checks, and you can move farther after scoring a critical hit.",
            subclass=Subclass.CHAMPION,
        ),
        ClassFeatureData(
            "Additional Fighting Style",
            10,
            "You gain a second Fighting Style feat of your choice.",
            subclass=Subclass.CHAMPION,
        ),
        ClassFeatureData(
            "Heroic Warrior",
            15,
            "Your combat spirit grants you Heroic Inspiration at the start of each of your "
            "turns in battle if you don't already have it.",
            subclass=Subclass.CHAMPION,
        ),
        ClassFeatureData(
            "Superior Critical",
            18,
            "Your weapon and unarmed attacks score a critical hit on a roll of 18-20.",
            subclass=Subclass.CHAMPION,
        ),
    ],
    resources={
        ClassResource.SECOND_WIND: [2] * 3 + [3] * 6 + [4] * 11,
        ClassResource.ACTION_SURGE: [0] + [1] * 15 + [2] * 4,
        ClassResource.INDOMITABLE: [0] * 8 + [1] * 4 + [2] * 4 + [3] * 4,
        ClassResource.WEAPON_MASTERY: [3] * 3 + [4] * 6 + [5] * 6 + [6] * 5,
    },
)
