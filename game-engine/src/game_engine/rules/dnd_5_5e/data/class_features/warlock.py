"""D&D 5.5e Warlock class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

WARLOCK_PROGRESSION = ClassProgression(
    character_class=CharacterClass.WARLOCK,
    features=[
        ClassFeatureData(
            "Eldritch Invocations",
            1,
            "You learn occult invocations — permanent magical augments such as Pact of the "
            "Blade or Agonizing Blast — gaining more as you level.",
        ),
        ClassFeatureData(
            "Pact Magic",
            1,
            "Your patron grants spell slots that are few but always cast at your highest "
            "pact level and recharge on a short or long rest; you cast with Charisma.",
        ),
        ClassFeatureData(
            "Magical Cunning",
            2,
            "Once per long rest, perform a brief occult rite to recover half your expended "
            "Pact Magic spell slots.",
        ),
        ClassFeatureData(
            "Warlock Subclass",
            3,
            "Bind yourself to a patron subclass that grants features at levels 3, 6, 10, "
            "and 14.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Contact Patron",
            9,
            "You can always cast Contact Other Plane to reach your patron, and once per "
            "long rest you automatically succeed on its saving throw.",
        ),
        ClassFeatureData(
            "Mystic Arcanum (Level 6 Spell)",
            11,
            "Choose a level-6 warlock spell as an arcanum you can cast once per long rest "
            "without a spell slot.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Mystic Arcanum (Level 7 Spell)",
            13,
            "Choose a level-7 warlock spell as an arcanum you can cast once per long rest "
            "without a spell slot.",
        ),
        ClassFeatureData(
            "Mystic Arcanum (Level 8 Spell)",
            15,
            "Choose a level-8 warlock spell as an arcanum you can cast once per long rest "
            "without a spell slot.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Mystic Arcanum (Level 9 Spell)",
            17,
            "Choose a level-9 warlock spell as an arcanum you can cast once per long rest "
            "without a spell slot.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "occult power.",
        ),
        ClassFeatureData(
            "Eldritch Master",
            20,
            "When you use Magical Cunning, you now recover all of your expended Pact Magic "
            "spell slots.",
        ),
        ClassFeatureData(
            "Dark One's Blessing",
            3,
            "When you reduce an enemy to 0 hit points, infernal power grants you temporary "
            "hit points based on your Charisma and warlock level.",
            subclass=Subclass.FIEND_PATRON,
        ),
        ClassFeatureData(
            "Fiend Spells",
            3,
            "You always have a set of fire- and fear-themed spells prepared, gaining more "
            "as you level.",
            subclass=Subclass.FIEND_PATRON,
        ),
        ClassFeatureData(
            "Dark One's Own Luck",
            6,
            "Add a d10 to one of your ability checks or saving throws, a number of times "
            "per long rest equal to your Charisma modifier.",
            subclass=Subclass.FIEND_PATRON,
        ),
        ClassFeatureData(
            "Fiendish Resilience",
            10,
            "After a rest, choose a damage type other than force; you have resistance to it "
            "until you choose a different one.",
            subclass=Subclass.FIEND_PATRON,
        ),
        ClassFeatureData(
            "Hurl Through Hell",
            14,
            "Once per long rest when you hit a creature, banish it on a tour of the lower "
            "planes, dealing heavy psychic damage when it returns.",
            subclass=Subclass.FIEND_PATRON,
        ),
    ],
    resources={
        ClassResource.ELDRITCH_INVOCATION: [1]
        + [3] * 3
        + [5] * 2
        + [6] * 2
        + [7] * 3
        + [8] * 3
        + [9] * 3
        + [10] * 3,
    },
    spellcaster_type=SpellcasterType.PACT,
    spellcasting_ability=Ability.CHARISMA,
    cantrips_known=[2] * 3 + [3] * 6 + [4] * 11,
    prepared_spells=[2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15],
)
