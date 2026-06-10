"""D&D 5.5e Ranger class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, SpellcasterType, Subclass

RANGER_PROGRESSION = ClassProgression(
    character_class=CharacterClass.RANGER,
    features=[
        ClassFeatureData(
            "Spellcasting",
            1,
            "You blend martial skill with primal magic, preparing and casting spells from "
            "the ranger list using Wisdom.",
        ),
        ClassFeatureData(
            "Favored Enemy",
            1,
            "You always have the Hunter's Mark spell prepared and can cast it a limited "
            "number of times without a spell slot, growing with your level.",
        ),
        ClassFeatureData(
            "Weapon Mastery",
            1,
            "You can use the mastery properties of two weapons of your choice, swapping your "
            "picks after a long rest.",
        ),
        ClassFeatureData(
            "Deft Explorer",
            2,
            "Gain Expertise in one of your skills and learn two additional languages, "
            "reflecting your wide travels.",
        ),
        ClassFeatureData(
            "Fighting Style",
            2,
            "You gain a Fighting Style feat of your choice, or you can instead learn the "
            "Druidic Warrior cantrip option.",
        ),
        ClassFeatureData(
            "Ranger Subclass",
            3,
            "Choose a ranger conclave subclass that grants features at levels 3, 7, 11, "
            "and 15.",
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
            "Roving",
            6,
            "Your speed increases by 10 feet, and you gain climb and swim speeds while not "
            "in heavy armor.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Expertise",
            9,
            "Choose two of your skill proficiencies; your proficiency bonus is doubled for "
            "checks using them.",
        ),
        ClassFeatureData(
            "Tireless",
            10,
            "Grant yourself temporary hit points several times per long rest, and short "
            "rests reduce your exhaustion.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Relentless Hunter",
            13,
            "Taking damage can no longer break your concentration on Hunter's Mark.",
        ),
        ClassFeatureData(
            "Nature's Veil",
            14,
            "As a bonus action, briefly turn invisible by slipping into nature's weave, a "
            "limited number of times per long rest.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Precise Hunter",
            17,
            "You have advantage on attack rolls against the creature marked by your "
            "Hunter's Mark.",
        ),
        ClassFeatureData(
            "Feral Senses",
            18,
            "You gain blindsight out to 30 feet, sensing your surroundings without relying "
            "on sight.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "skill in the wild.",
        ),
        ClassFeatureData(
            "Foe Slayer",
            20,
            "Your Hunter's Mark strikes harder, its extra damage die growing to a d10 "
            "against your marked quarry.",
        ),
        ClassFeatureData(
            "Hunter's Lore",
            3,
            "While a creature is marked by your Hunter's Mark, you can discern its "
            "immunities, resistances, and vulnerabilities.",
            subclass=Subclass.HUNTER,
        ),
        ClassFeatureData(
            "Hunter's Prey",
            3,
            "Choose a slaying technique: Colossus Slayer adds damage against wounded foes, "
            "while Horde Breaker grants a second attack against a nearby different target.",
            subclass=Subclass.HUNTER,
        ),
        ClassFeatureData(
            "Defensive Tactics",
            7,
            "Choose a defensive technique: escape attacks of opportunity more easily or "
            "shrug off some damage from multiattacking foes.",
            subclass=Subclass.HUNTER,
        ),
        ClassFeatureData(
            "Superior Hunter's Prey",
            11,
            "Once per turn, your Hunter's Mark damage can also strike a second creature "
            "near your original target.",
            subclass=Subclass.HUNTER,
        ),
        ClassFeatureData(
            "Superior Hunter's Defense",
            15,
            "As a reaction when you take damage, gain resistance to that damage type until "
            "the start of your next turn.",
            subclass=Subclass.HUNTER,
        ),
    ],
    spellcaster_type=SpellcasterType.HALF,
    spellcasting_ability=Ability.WISDOM,
    cantrips_known=None,
    prepared_spells=[2, 3, 4, 5, 6, 6, 7, 7, 9, 9, 10, 10, 11, 11, 12, 12, 14, 14, 15, 15],
)
