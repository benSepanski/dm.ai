"""D&D 5.5e Bard class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, SpellcasterType, Subclass

BARD_PROGRESSION = ClassProgression(
    character_class=CharacterClass.BARD,
    features=[
        ClassFeatureData(
            "Bardic Inspiration",
            1,
            "As a bonus action, grant an ally an inspiration die they can add to a d20 test; "
            "uses equal your Charisma modifier, and the die grows from d6 to d12 as you "
            "level (d8 at 5, d10 at 10, d12 at 15).",
        ),
        ClassFeatureData(
            "Spellcasting",
            1,
            "You weave magic through performance, preparing and casting spells from the bard "
            "list using Charisma.",
        ),
        ClassFeatureData(
            "Expertise",
            2,
            "Choose two of your skill proficiencies; your proficiency bonus is doubled for "
            "checks using them.",
        ),
        ClassFeatureData(
            "Jack of All Trades",
            2,
            "Add half your proficiency bonus to any ability check that doesn't already "
            "include it.",
        ),
        ClassFeatureData(
            "Bard Subclass",
            3,
            "Choose a bardic college subclass that grants features at levels 3, 6, and 14.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Font of Inspiration",
            5,
            "Your Bardic Inspiration uses return on a short or long rest, and you can spend "
            "a spell slot to regain one.",
        ),
        ClassFeatureData(
            "Countercharm",
            7,
            "As a reaction, your performance can grant an ally a reroll against an effect "
            "that would charm or frighten them.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Expertise",
            9,
            "Choose two more of your skill proficiencies to gain double proficiency bonus.",
        ),
        ClassFeatureData(
            "Magical Secrets",
            10,
            "Your prepared spells can now also come from the cleric, druid, and wizard spell "
            "lists.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Superior Inspiration",
            18,
            "When you roll initiative, you regain expended Bardic Inspiration uses until you "
            "have at least two.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "artistry.",
        ),
        ClassFeatureData(
            "Words of Creation",
            20,
            "You always have the Power Word Heal and Power Word Kill spells prepared, and "
            "each can affect a second nearby creature.",
        ),
        ClassFeatureData(
            "Bonus Proficiencies",
            3,
            "Your broad studies grant you proficiency in three additional skills of your "
            "choice.",
            subclass=Subclass.COLLEGE_OF_LORE,
        ),
        ClassFeatureData(
            "Cutting Words",
            3,
            "As a reaction, expend a Bardic Inspiration die to subtract it from an enemy's "
            "ability check, attack roll, or damage roll.",
            subclass=Subclass.COLLEGE_OF_LORE,
        ),
        ClassFeatureData(
            "Magical Discoveries",
            6,
            "Learn two spells of your choice drawn from the cleric, druid, or wizard lists; "
            "they count as bard spells you always have prepared.",
            subclass=Subclass.COLLEGE_OF_LORE,
        ),
        ClassFeatureData(
            "Peerless Skill",
            14,
            "Spend a Bardic Inspiration die to boost your own ability check or attack roll, "
            "keeping the use if you still fail.",
            subclass=Subclass.COLLEGE_OF_LORE,
        ),
    ],
    spellcaster_type=SpellcasterType.FULL,
    spellcasting_ability=Ability.CHARISMA,
    cantrips_known=[2] * 3 + [3] * 6 + [4] * 11,
    prepared_spells=[4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
)
