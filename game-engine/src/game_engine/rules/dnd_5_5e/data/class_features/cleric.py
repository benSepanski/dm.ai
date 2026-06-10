"""D&D 5.5e Cleric class progression (2024 rules)."""

from __future__ import annotations

from game_engine.rules.dnd_5_5e.data.class_features._base import (
    ClassFeatureData,
    ClassProgression,
)
from game_engine.types import Ability, CharacterClass, ClassResource, SpellcasterType, Subclass

CLERIC_PROGRESSION = ClassProgression(
    character_class=CharacterClass.CLERIC,
    features=[
        ClassFeatureData(
            "Spellcasting",
            1,
            "You channel divine power, preparing and casting spells from the cleric list "
            "using Wisdom.",
        ),
        ClassFeatureData(
            "Divine Order",
            1,
            "Dedicate yourself as a Protector, gaining martial weapon and heavy armor "
            "training, or as a Thaumaturge, gaining an extra cantrip and keener "
            "religious insight.",
        ),
        ClassFeatureData(
            "Channel Divinity",
            2,
            "Invoke your deity directly to fuel effects such as Turn Undead or Divine Spark, "
            "with limited uses that return on rests.",
        ),
        ClassFeatureData(
            "Cleric Subclass",
            3,
            "Choose a divine domain subclass that grants features at levels 3, 6, and 17.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            4,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Sear Undead",
            5,
            "When you use Turn Undead, affected creatures also take radiant damage based on "
            "your Wisdom modifier.",
        ),
        ClassFeatureData(
            "Blessed Strikes",
            7,
            "Divine power infuses your offense: add bonus radiant damage to a creature you "
            "damage with a cantrip or weapon strike.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            8,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Divine Intervention",
            10,
            "Call on your deity to cast a cleric spell of level 5 or lower without a slot, "
            "once per long rest.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            12,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Improved Blessed Strikes",
            14,
            "Your Blessed Strikes grow stronger, dealing more damage or sharing healing with "
            "an ally.",
        ),
        ClassFeatureData(
            "Ability Score Improvement",
            16,
            "Increase your ability scores or gain a feat of your choice.",
        ),
        ClassFeatureData(
            "Epic Boon",
            19,
            "Gain an Epic Boon feat or another feat of your choice, marking near-legendary "
            "faith.",
        ),
        ClassFeatureData(
            "Greater Divine Intervention",
            20,
            "Your Divine Intervention can now invoke the Wish spell, though doing so "
            "requires a long recovery before repeating it.",
        ),
        ClassFeatureData(
            "Disciple of Life",
            3,
            "Your healing spells restore additional hit points equal to 2 plus the spell "
            "slot's level.",
            subclass=Subclass.LIFE_DOMAIN,
        ),
        ClassFeatureData(
            "Life Domain Spells",
            3,
            "You always have a set of restorative spells prepared, gaining more as you "
            "reach higher levels.",
            subclass=Subclass.LIFE_DOMAIN,
        ),
        ClassFeatureData(
            "Preserve Life",
            3,
            "Use Channel Divinity to distribute a pool of healing among wounded creatures "
            "near you, up to half their hit point maximums.",
            subclass=Subclass.LIFE_DOMAIN,
        ),
        ClassFeatureData(
            "Blessed Healer",
            6,
            "When you cast a healing spell on others, you also regain hit points equal to "
            "2 plus the spell slot's level.",
            subclass=Subclass.LIFE_DOMAIN,
        ),
        ClassFeatureData(
            "Supreme Healing",
            17,
            "When you roll dice to restore hit points with a spell or Channel Divinity, "
            "treat every die as its maximum result.",
            subclass=Subclass.LIFE_DOMAIN,
        ),
    ],
    resources={
        ClassResource.CHANNEL_DIVINITY: [0] + [2] * 4 + [3] * 12 + [4] * 3,
    },
    spellcaster_type=SpellcasterType.FULL,
    spellcasting_ability=Ability.WISDOM,
    cantrips_known=[3] * 3 + [4] * 6 + [5] * 11,
    prepared_spells=[4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 17, 18, 18, 19, 20, 21, 22],
)
