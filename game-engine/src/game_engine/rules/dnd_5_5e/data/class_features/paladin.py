"""D&D 5.5e Paladin class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

PALADIN_PROGRESSION = ClassProgression(
    character_class=CharacterClass.PALADIN,
    features=[
        ClassFeatureData(
            "Lay On Hands",
            1,
            "As a bonus action, draw on a pool of healing power equal to five times your "
            "paladin level to restore hit points or cure the poisoned condition.",
        ),
        ClassFeatureData(
            "Spellcasting",
            1,
            "You channel sacred oaths into magic, preparing and casting spells from the "
            "paladin list using Charisma.",
        ),
        ClassFeatureData(
            "Weapon Mastery",
            1,
            "You can use the mastery properties of two weapons of your choice, swapping your "
            "picks after a long rest.",
        ),
        ClassFeatureData(
            "Fighting Style",
            2,
            "You gain a Fighting Style feat of your choice, or you can instead learn the "
            "Blessed Warrior cantrip option.",
        ),
        ClassFeatureData(
            "Paladin's Smite",
            2,
            "You always have the Divine Smite spell prepared, and once per turn you can cast "
            "it without expending a spell slot's action economy beyond the usual cost.",
        ),
        ClassFeatureData(
            "Channel Divinity",
            3,
            "Channel your oath's power into effects such as Divine Sense, with limited uses "
            "that return on rests.",
        ),
        ClassFeatureData(
            "Paladin Subclass",
            3,
            "Swear a sacred oath subclass that grants features at levels 3, 7, 15, and 20.",
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
            attacks_granted=2,
        ),
        ClassFeatureData(
            "Faithful Steed",
            5,
            "You always have the Find Steed spell prepared and can cast it once per long "
            "rest without a spell slot.",
        ),
        ClassFeatureData(
            "Aura of Protection",
            6,
            "You and allies within your aura add your Charisma modifier to all saving "
            "throws while you are conscious.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Abjure Foes",
            9,
            "Use Channel Divinity to overawe nearby enemies, frightening those that fail a "
            "Wisdom save and hampering their actions.",
        ),
        ClassFeatureData(
            "Aura of Courage",
            10,
            "You and allies in your aura are immune to the frightened condition while you "
            "are conscious.",
        ),
        ClassFeatureData(
            "Radiant Strikes",
            11,
            "Your weapon and unarmed attacks deal an extra die of radiant damage on every " "hit.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Restoring Touch",
            14,
            "Your Lay On Hands can also remove conditions such as blinded, charmed, "
            "frightened, paralyzed, or stunned at a cost from the healing pool.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Aura Expansion",
            18,
            "Your Aura of Protection widens, extending its protective reach to 30 feet.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "devotion.",
        ),
        ClassFeatureData(
            "Oath of Devotion Spells",
            3,
            "You always have a set of protective and radiant spells prepared, gaining more "
            "as you level.",
            subclass=Subclass.OATH_OF_DEVOTION,
        ),
        ClassFeatureData(
            "Sacred Weapon",
            3,
            "Use Channel Divinity to bless a weapon, adding your Charisma modifier to its "
            "attack rolls and making it shed radiant light.",
            subclass=Subclass.OATH_OF_DEVOTION,
        ),
        ClassFeatureData(
            "Aura of Devotion",
            7,
            "You and allies in your aura are immune to the charmed condition while you are "
            "conscious.",
            subclass=Subclass.OATH_OF_DEVOTION,
        ),
        ClassFeatureData(
            "Smite of Protection",
            15,
            "When you cast Divine Smite, your aura also grants you and nearby allies half "
            "cover until your next turn.",
            subclass=Subclass.OATH_OF_DEVOTION,
        ),
        ClassFeatureData(
            "Holy Nimbus",
            20,
            "As a bonus action, radiate searing holy light that damages nearby enemies and "
            "fortifies your saving throws for a time, once per long rest or via a slot.",
            subclass=Subclass.OATH_OF_DEVOTION,
        ),
    ],
    resources={
        ClassResource.CHANNEL_DIVINITY: [0, 0] + [2] * 8 + [3] * 10,
        ClassResource.LAY_ON_HANDS: [5 * level for level in range(1, 21)],
    },
    spellcaster_type=SpellcasterType.HALF,
    spellcasting_ability=Ability.CHARISMA,
    cantrips_known=None,
    prepared_spells=[2, 3, 4, 5, 6, 6, 7, 7, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 15, 15],
)
