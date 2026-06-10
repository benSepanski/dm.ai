"""D&D 5.5e Wizard class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, SpellcasterType, Subclass

WIZARD_PROGRESSION = ClassProgression(
    character_class=CharacterClass.WIZARD,
    features=[
        ClassFeatureData(
            "Spellcasting",
            1,
            "You study arcane formulas in your spellbook, preparing and casting spells from "
            "the wizard list using Intelligence.",
        ),
        ClassFeatureData(
            "Ritual Adept",
            1,
            "You can cast any ritual spell in your spellbook as a ritual without preparing "
            "it first.",
        ),
        ClassFeatureData(
            "Arcane Recovery",
            1,
            "Once per day during a short rest, recover expended spell slots whose combined "
            "levels are up to half your wizard level, rounded up.",
        ),
        ClassFeatureData(
            "Scholar",
            2,
            "Your studies grant Expertise in one academic skill such as Arcana, History, "
            "Investigation, Medicine, Nature, or Religion.",
        ),
        ClassFeatureData(
            "Wizard Subclass",
            3,
            "Choose an arcane tradition subclass that grants features at levels 3, 6, 10, "
            "and 14.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Memorize Spell",
            5,
            "During a short rest, you can study your spellbook to swap one prepared wizard "
            "spell for another.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
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
            "Spell Mastery",
            18,
            "Choose one level-1 and one level-2 wizard spell; you can cast them at their "
            "lowest level without expending spell slots.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "erudition.",
        ),
        ClassFeatureData(
            "Signature Spells",
            20,
            "Choose two level-3 wizard spells that are always prepared and can each be cast "
            "once without a slot between rests.",
        ),
        ClassFeatureData(
            "Evocation Savant",
            3,
            "You add two free evocation spells to your spellbook and can cheaply scribe "
            "more evocation spells you find.",
            subclass=Subclass.EVOKER,
        ),
        ClassFeatureData(
            "Potent Cantrip",
            3,
            "Your damaging cantrips still deal half damage when a target saves or when you "
            "miss with the attack roll.",
            subclass=Subclass.EVOKER,
        ),
        ClassFeatureData(
            "Sculpt Spells",
            6,
            "Carve safe pockets in your evocation spells so chosen allies automatically "
            "succeed on their saves and take no damage.",
            subclass=Subclass.EVOKER,
        ),
        ClassFeatureData(
            "Empowered Evocation",
            10,
            "Add your Intelligence modifier to one damage roll of any wizard evocation "
            "spell you cast.",
            subclass=Subclass.EVOKER,
        ),
        ClassFeatureData(
            "Overchannel",
            14,
            "Force a spell of level 5 or lower to deal maximum damage; repeating this "
            "before a long rest wracks your body with necrotic backlash.",
            subclass=Subclass.EVOKER,
        ),
    ],
    spellcaster_type=SpellcasterType.FULL,
    spellcasting_ability=Ability.INTELLIGENCE,
    cantrips_known=[3] * 3 + [4] * 6 + [5] * 11,
    prepared_spells=[4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 18, 18, 19, 21, 22, 23, 25],
)
