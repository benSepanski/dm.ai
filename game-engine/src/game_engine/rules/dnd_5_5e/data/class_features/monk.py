"""D&D 5.5e Monk class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import CharacterClass, ClassResource, Subclass

MONK_PROGRESSION = ClassProgression(
    character_class=CharacterClass.MONK,
    features=[
        ClassFeatureData(
            "Martial Arts",
            1,
            "Your unarmed strikes and monk weapons use a scaling Martial Arts die and can "
            "rely on Dexterity, and you can make an unarmed strike as a bonus action.",
        ),
        ClassFeatureData(
            "Unarmored Defense",
            1,
            "While you wear no armor and wield no shield, your AC equals 10 plus your "
            "Dexterity and Wisdom modifiers.",
        ),
        ClassFeatureData(
            "Monk's Focus",
            2,
            "You gain a pool of Focus Points to fuel techniques such as Flurry of Blows, "
            "Patient Defense, and Step of the Wind, recharging on a short or long rest.",
        ),
        ClassFeatureData(
            "Unarmored Movement",
            2,
            "Your speed increases while you wear no armor or shield, with the bonus growing "
            "as you gain monk levels.",
        ),
        ClassFeatureData(
            "Uncanny Metabolism",
            2,
            "Once per long rest, when you roll initiative you can restore all your Focus "
            "Points and regain some hit points.",
        ),
        ClassFeatureData(
            "Monk Subclass",
            3,
            "Choose a warrior tradition subclass that grants features at levels 3, 6, 11, "
            "and 17.",
        ),
        ClassFeatureData(
            "Deflect Attacks",
            3,
            "As a reaction, reduce the damage of an attack against you; if you reduce it to "
            "0, you can spend a Focus Point to redirect the strike at another creature.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Slow Fall",
            4,
            "You can use your reaction to reduce falling damage by five times your monk " "level.",
        ),
        ClassFeatureData(
            "Extra Attack",
            5,
            "When you take the Attack action, you can make two attacks instead of one.",
        ),
        ClassFeatureData(
            "Stunning Strike",
            5,
            "Once per turn when you hit with a monk weapon or unarmed strike, you can spend "
            "a Focus Point to force a save; failure stuns the target until your next turn.",
        ),
        ClassFeatureData(
            "Empowered Strikes",
            6,
            "Your unarmed strikes can deal force damage instead of bludgeoning, letting them "
            "bypass many defenses.",
        ),
        ClassFeatureData(
            "Evasion",
            7,
            "When you make a Dexterity save against an effect that deals half damage on a "
            "success, you instead take no damage on a success and half on a failure.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Acrobatic Movement",
            9,
            "While unarmored, you can run along vertical surfaces and across liquids without "
            "falling during your move.",
        ),
        ClassFeatureData(
            "Heightened Focus",
            10,
            "Your Flurry of Blows, Patient Defense, and Step of the Wind techniques each "
            "gain an enhanced effect.",
        ),
        ClassFeatureData(
            "Self-Restoration",
            10,
            "You can end the charmed, frightened, or poisoned condition on yourself at the "
            "end of your turn, and going without food or water no longer exhausts you.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Deflect Energy",
            13,
            "Your Deflect Attacks technique now works against attacks dealing any damage "
            "type, not just bludgeoning, piercing, or slashing.",
        ),
        ClassFeatureData(
            "Disciplined Survivor",
            14,
            "You gain proficiency in all saving throws, and you can spend a Focus Point to "
            "reroll a failed save.",
        ),
        ClassFeatureData(
            "Perfect Focus",
            15,
            "When you roll initiative with few Focus Points remaining, you regain enough to "
            "bring your total up to four.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Superior Defense",
            18,
            "Spend Focus Points at the start of your turn to gain a minute of resistance to "
            "all damage except force.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "mastery.",
        ),
        ClassFeatureData(
            "Body and Mind",
            20,
            "Your training perfects you: your Dexterity and Wisdom scores each increase "
            "by 4, to a maximum of 25.",
        ),
        ClassFeatureData(
            "Open Hand Technique",
            3,
            "When you hit with a Flurry of Blows attack, you can also addle the target, "
            "knock it prone, push it away, or stop it from taking reactions.",
            subclass=Subclass.WARRIOR_OF_THE_OPEN_HAND,
        ),
        ClassFeatureData(
            "Wholeness of Body",
            6,
            "As a bonus action, channel inner energy to heal yourself a limited number of "
            "times per long rest.",
            subclass=Subclass.WARRIOR_OF_THE_OPEN_HAND,
        ),
        ClassFeatureData(
            "Fleet Step",
            11,
            "Whenever you take a bonus action other than Step of the Wind, you can also use "
            "Step of the Wind as part of it.",
            subclass=Subclass.WARRIOR_OF_THE_OPEN_HAND,
        ),
        ClassFeatureData(
            "Quivering Palm",
            17,
            "Imbue a struck creature with lethal vibrations that you can later detonate, "
            "dealing massive force damage on a failed save.",
            subclass=Subclass.WARRIOR_OF_THE_OPEN_HAND,
        ),
    ],
    resources={
        ClassResource.MARTIAL_ARTS_DIE: [6] * 4 + [8] * 6 + [10] * 6 + [12] * 4,
        ClassResource.FOCUS_POINT: [0] + list(range(2, 21)),
    },
)
