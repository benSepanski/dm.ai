"""D&D 5.5e Artificer class progression (Tasha's Cauldron, 2024-style update)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

ARTIFICER_PROGRESSION = ClassProgression(
    character_class=CharacterClass.ARTIFICER,
    features=[
        ClassFeatureData(
            "Magical Tinkering",
            1,
            "Imbue tiny objects with minor magical effects such as light, recorded sound, "
            "or an odor, using your tinker's tools.",
        ),
        ClassFeatureData(
            "Spellcasting",
            1,
            "You cast spells by channeling magic through tools and inventions, preparing "
            "spells from the artificer list using Intelligence.",
        ),
        ClassFeatureData(
            "Infuse Items",
            2,
            "Learn infusion blueprints and imbue mundane items with them after a long rest, "
            "creating temporary magic items; the number you can sustain grows with level.",
        ),
        ClassFeatureData(
            "Artificer Subclass",
            3,
            "Choose an artificer specialist subclass that grants features at levels 3, 5, "
            "9, and 15.",
        ),
        ClassFeatureData(
            "The Right Tool for the Job",
            3,
            "With tinker's tools and an hour of work, conjure any set of artisan's tools "
            "you need.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Tool Expertise",
            6,
            "Your proficiency bonus is doubled for any ability check that uses a tool "
            "you're proficient with.",
        ),
        ClassFeatureData(
            "Flash of Genius",
            7,
            "As a reaction, add your Intelligence modifier to a nearby creature's ability "
            "check or saving throw, a limited number of times per long rest.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Magic Item Adept",
            10,
            "You can attune to more magic items than most, and you craft common and "
            "uncommon magic items faster and cheaper.",
        ),
        ClassFeatureData(
            "Spell-Storing Item",
            11,
            "After a long rest, store a level 1 or 2 artificer spell in an object so any "
            "wielder can cast it repeatedly.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Magic Item Savant",
            14,
            "Your attunement capacity grows again, and you can attune to magic items "
            "regardless of their class or species requirements.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Magic Item Master",
            18,
            "Your attunement capacity reaches its peak, letting you bond with up to six "
            "magic items at once.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "ingenuity.",
        ),
        ClassFeatureData(
            "Soul of Artifice",
            20,
            "Your attuned items lend you a saving-throw bonus, and ending one attunement "
            "can keep you at 1 hit point instead of dropping to 0.",
        ),
        ClassFeatureData(
            "Battle Ready",
            3,
            "Your combat training lets you use Intelligence for attack and damage rolls "
            "with magic weapons, and you gain martial weapon proficiency.",
            subclass=Subclass.BATTLE_SMITH,
        ),
        ClassFeatureData(
            "Steel Defender",
            3,
            "Build a loyal mechanical companion that fights at your side, deflects attacks, "
            "and can be repaired or rebuilt with your tools.",
            subclass=Subclass.BATTLE_SMITH,
        ),
        ClassFeatureData(
            "Battle Smith Spells",
            3,
            "You always have a set of protective and smiting spells prepared, gaining more "
            "as you level.",
            subclass=Subclass.BATTLE_SMITH,
        ),
        ClassFeatureData(
            "Extra Attack",
            5,
            "When you take the Attack action, you can make two attacks instead of one.",
            subclass=Subclass.BATTLE_SMITH,
            attacks_granted=2,
        ),
        ClassFeatureData(
            "Arcane Jolt",
            9,
            "When you or your Steel Defender hit with a magic weapon, channel energy to "
            "deal extra force damage or heal a nearby creature.",
            subclass=Subclass.BATTLE_SMITH,
        ),
        ClassFeatureData(
            "Improved Defender",
            15,
            "Your Arcane Jolt grows stronger, and your Steel Defender's deflection damages "
            "the attacker it thwarts.",
            subclass=Subclass.BATTLE_SMITH,
        ),
    ],
    resources={
        ClassResource.INFUSION: [0] + [2] * 4 + [3] * 4 + [4] * 4 + [5] * 4 + [6] * 3,
    },
    spellcaster_type=SpellcasterType.HALF,
    spellcasting_ability=Ability.INTELLIGENCE,
    cantrips_known=[2] * 9 + [3] * 4 + [4] * 7,
    prepared_spells=None,
)
