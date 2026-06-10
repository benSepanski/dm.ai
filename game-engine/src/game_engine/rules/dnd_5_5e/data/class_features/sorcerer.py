"""D&D 5.5e Sorcerer class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

SORCERER_PROGRESSION = ClassProgression(
    character_class=CharacterClass.SORCERER,
    features=[
        ClassFeatureData(
            "Spellcasting",
            1,
            "Magic flows from within you; you prepare and cast spells from the sorcerer "
            "list using Charisma.",
        ),
        ClassFeatureData(
            "Innate Sorcery",
            1,
            "As a bonus action, unleash your inner magic for a minute, raising your spell "
            "save DC and granting advantage on sorcerer spell attack rolls.",
        ),
        ClassFeatureData(
            "Font of Magic",
            2,
            "You gain Sorcery Points equal to your level, which you can convert to and from "
            "spell slots or spend on other sorcerous abilities.",
        ),
        ClassFeatureData(
            "Metamagic",
            2,
            "Learn two Metamagic options that let you spend Sorcery Points to reshape your "
            "spells, such as twinning, quickening, or subtle casting.",
        ),
        ClassFeatureData(
            "Sorcerer Subclass",
            3,
            "Choose a sorcerous origin subclass that grants features at levels 3, 6, 14, "
            "and 18.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Sorcerous Restoration",
            5,
            "Finishing a short rest restores some of your expended Sorcery Points, once per "
            "long rest.",
        ),
        ClassFeatureData(
            "Sorcery Incarnate",
            7,
            "Spend Sorcery Points to reactivate Innate Sorcery, and while it is active you "
            "can apply two Metamagic options to one spell.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Metamagic",
            10,
            "Learn an additional Metamagic option of your choice and replace one you know "
            "if desired.",
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
            "Metamagic",
            17,
            "Learn an additional Metamagic option of your choice and replace one you know "
            "if desired.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "power.",
        ),
        ClassFeatureData(
            "Arcane Apotheosis",
            20,
            "While Innate Sorcery is active, one Metamagic use per turn costs you no "
            "Sorcery Points.",
        ),
        ClassFeatureData(
            "Draconic Resilience",
            3,
            "Draconic vitality raises your hit points, and dragon-like scales give you a "
            "higher AC when unarmored.",
            subclass=Subclass.DRACONIC_SORCERY,
        ),
        ClassFeatureData(
            "Draconic Spells",
            3,
            "You always have a set of dragon-themed spells prepared, gaining more as you "
            "level.",
            subclass=Subclass.DRACONIC_SORCERY,
        ),
        ClassFeatureData(
            "Elemental Affinity",
            6,
            "Choose a draconic damage type; you gain resistance to it and add your Charisma "
            "modifier to one damage roll of spells dealing that type.",
            subclass=Subclass.DRACONIC_SORCERY,
        ),
        ClassFeatureData(
            "Dragon Wings",
            14,
            "As a bonus action, manifest spectral dragon wings that grant a fly speed for "
            "an hour.",
            subclass=Subclass.DRACONIC_SORCERY,
        ),
        ClassFeatureData(
            "Dragon Companion",
            18,
            "You can cast Summon Dragon without material components, and once per long rest "
            "without a spell slot.",
            subclass=Subclass.DRACONIC_SORCERY,
        ),
    ],
    resources={
        ClassResource.SORCERY_POINT: [0] + list(range(2, 21)),
    },
    spellcaster_type=SpellcasterType.FULL,
    spellcasting_ability=Ability.CHARISMA,
    cantrips_known=[4] * 3 + [5] * 6 + [6] * 11,
    prepared_spells=[2, 4, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
)
