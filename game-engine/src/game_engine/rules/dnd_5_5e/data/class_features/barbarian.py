"""D&D 5.5e Barbarian class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import CharacterClass, ClassResource, Subclass

BARBARIAN_PROGRESSION = ClassProgression(
    character_class=CharacterClass.BARBARIAN,
    features=[
        ClassFeatureData(
            "Rage",
            1,
            "As a bonus action, enter a primal fury that grants resistance to bludgeoning, "
            "piercing, and slashing damage plus bonus damage on Strength-based attacks.",
        ),
        ClassFeatureData(
            "Unarmored Defense",
            1,
            "While you wear no armor, your AC equals 10 plus your Dexterity and Constitution "
            "modifiers; you can still benefit from a shield.",
        ),
        ClassFeatureData(
            "Weapon Mastery",
            1,
            "You can use the mastery properties of a limited number of weapons you have "
            "trained with, and you can swap your chosen weapons after a long rest.",
        ),
        ClassFeatureData(
            "Danger Sense",
            2,
            "Your battle instincts grant advantage on Dexterity saving throws unless you are "
            "incapacitated.",
        ),
        ClassFeatureData(
            "Reckless Attack",
            2,
            "Abandon defense to gain advantage on Strength-based attack rolls for the turn, "
            "but attack rolls against you have advantage until your next turn.",
        ),
        ClassFeatureData(
            "Barbarian Subclass",
            3,
            "Choose a Primal Path subclass that shapes your rage, granting features at "
            "levels 3, 6, 10, and 14.",
        ),
        ClassFeatureData(
            "Primal Knowledge",
            3,
            "You learn an additional skill, and while raging you can channel raw instinct to "
            "make certain skill checks with Strength instead of their usual ability.",
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
            "Fast Movement",
            5,
            "Your speed increases by 10 feet while you are not wearing heavy armor.",
        ),
        ClassFeatureData(
            "Feral Instinct",
            7,
            "Your honed reflexes give you advantage on initiative rolls.",
        ),
        ClassFeatureData(
            "Instinctive Pounce",
            7,
            "When you activate your Rage, you can immediately move up to half your speed as "
            "part of the same bonus action.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Brutal Strike",
            9,
            "When you forgo the advantage from Reckless Attack, a hit deals extra damage and "
            "inflicts a hampering effect, such as shoving the target or slowing it.",
        ),
        ClassFeatureData(
            "Relentless Rage",
            11,
            "While raging, you can attempt a Constitution save when reduced to 0 hit points "
            "to drop to 1 hit point instead, with the DC rising on repeated uses.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Improved Brutal Strike",
            13,
            "Your Brutal Strike gains new effect options, such as staggering a foe's "
            "defenses or knocking it off balance.",
        ),
        ClassFeatureData(
            "Persistent Rage",
            15,
            "Rolling initiative can restore your spent Rage uses once per long rest, and "
            "your rage now lasts its full duration unless you end it or fall unconscious.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Improved Brutal Strike",
            17,
            "Your Brutal Strike's bonus damage grows, and you can apply two of its effects "
            "with a single blow.",
        ),
        ClassFeatureData(
            "Indomitable Might",
            18,
            "Whenever you make a Strength check, its total can never be lower than your "
            "Strength score.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "power.",
        ),
        ClassFeatureData(
            "Primal Champion",
            20,
            "Your Strength and Constitution scores each increase by 4, to a new maximum " "of 25.",
        ),
        ClassFeatureData(
            "Frenzy",
            3,
            "While raging recklessly, your first hit each turn deals extra damage dice equal "
            "to your Rage Damage bonus.",
            subclass=Subclass.PATH_OF_THE_BERSERKER,
        ),
        ClassFeatureData(
            "Mindless Rage",
            6,
            "Your rage suppresses the charmed and frightened conditions while it lasts.",
            subclass=Subclass.PATH_OF_THE_BERSERKER,
        ),
        ClassFeatureData(
            "Retaliation",
            10,
            "When a creature within your reach damages you, you can use your reaction to "
            "make a melee attack against it.",
            subclass=Subclass.PATH_OF_THE_BERSERKER,
        ),
        ClassFeatureData(
            "Intimidating Presence",
            14,
            "As a bonus action, unleash a terrifying bellow that forces nearby enemies to "
            "save or become frightened of you.",
            subclass=Subclass.PATH_OF_THE_BERSERKER,
        ),
    ],
    resources={
        ClassResource.RAGE: [2, 2, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 6, 6, 6, 6],
        ClassResource.RAGE_DAMAGE: [2] * 8 + [3] * 7 + [4] * 5,
        ClassResource.WEAPON_MASTERY: [2] * 3 + [3] * 6 + [4] * 11,
    },
)
