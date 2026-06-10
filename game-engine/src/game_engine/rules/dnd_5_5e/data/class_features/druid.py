"""D&D 5.5e Druid class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

DRUID_PROGRESSION = ClassProgression(
    character_class=CharacterClass.DRUID,
    features=[
        ClassFeatureData(
            "Spellcasting",
            1,
            "You draw on the magic of nature, preparing and casting spells from the druid "
            "list using Wisdom.",
        ),
        ClassFeatureData(
            "Druidic",
            1,
            "You know the secret language of druids and always have the Speak with Animals "
            "spell prepared.",
        ),
        ClassFeatureData(
            "Primal Order",
            1,
            "Dedicate yourself as a Magician, sharpening your nature lore and gaining an "
            "extra cantrip, or as a Warden, gaining martial weapon and medium armor "
            "training.",
        ),
        ClassFeatureData(
            "Wild Shape",
            2,
            "As a bonus action, transform into a beast form you have learned, with uses that "
            "recharge on rests and stronger forms unlocking at higher levels.",
        ),
        ClassFeatureData(
            "Wild Companion",
            2,
            "Expend a Wild Shape use or spell slot to summon a nature spirit familiar via "
            "the Find Familiar spell.",
        ),
        ClassFeatureData(
            "Druid Subclass",
            3,
            "Choose a druidic circle subclass that grants features at levels 3, 6, 10, " "and 14.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Wild Resurgence",
            5,
            "Trade resources fluidly: regain a Wild Shape use by expending a spell slot, or "
            "convert a Wild Shape use into a level-1 spell slot once per long rest.",
        ),
        ClassFeatureData(
            "Elemental Fury",
            7,
            "Choose Potent Spellcasting, adding Wisdom to your cantrip damage, or Primal "
            "Strike, adding elemental damage to your weapon and beast-form attacks.",
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
            "Improved Elemental Fury",
            15,
            "Your Elemental Fury option strengthens, extending your cantrip reach or adding "
            "more dice to your primal strikes.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Beast Spells",
            18,
            "You can cast most of your spells while in Wild Shape, performing components in "
            "beast form.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "attunement.",
        ),
        ClassFeatureData(
            "Archdruid",
            20,
            "Rolling initiative can restore a Wild Shape use, and your beast form lets you "
            "convert uses into nature magic; you also age at a vastly slowed rate.",
        ),
        ClassFeatureData(
            "Circle of the Land Spells",
            3,
            "You always have a set of spells prepared tied to a land type you choose — "
            "arid, polar, temperate, or tropical — and can change it on a long rest.",
            subclass=Subclass.CIRCLE_OF_THE_LAND,
        ),
        ClassFeatureData(
            "Land's Aid",
            3,
            "Expend a Wild Shape use to conjure restorative natural energy that damages foes "
            "and heals an ally in an area you choose.",
            subclass=Subclass.CIRCLE_OF_THE_LAND,
        ),
        ClassFeatureData(
            "Natural Recovery",
            6,
            "Regain expended spell slots during a short rest once per long rest, and cast "
            "one of your circle spells without a slot each day.",
            subclass=Subclass.CIRCLE_OF_THE_LAND,
        ),
        ClassFeatureData(
            "Nature's Ward",
            10,
            "Your bond with the land grants immunity to the poisoned condition and a damage "
            "resistance matched to your chosen land type.",
            subclass=Subclass.CIRCLE_OF_THE_LAND,
        ),
        ClassFeatureData(
            "Nature's Sanctuary",
            14,
            "Expend a Wild Shape use to raise a grove of spectral plants that shields allies "
            "and hinders enemies, moving with you each turn.",
            subclass=Subclass.CIRCLE_OF_THE_LAND,
        ),
    ],
    resources={
        ClassResource.WILD_SHAPE: [0] + [2] * 4 + [3] * 11 + [4] * 4,
    },
    spellcaster_type=SpellcasterType.FULL,
    spellcasting_ability=Ability.WISDOM,
    cantrips_known=[2] * 3 + [3] * 6 + [4] * 11,
    prepared_spells=[4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
)
