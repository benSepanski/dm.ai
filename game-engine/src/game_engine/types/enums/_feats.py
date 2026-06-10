"""
Feat enums (2024 PHB chapter 5).

Internal module — import via :mod:`game_engine.types.enums`.
"""

from __future__ import annotations

from enum import Enum


class FeatCategory(str, Enum):
    """Feat categories in the 2024 PHB."""

    ORIGIN = "origin"
    GENERAL = "general"
    FIGHTING_STYLE = "fighting style"
    EPIC_BOON = "epic boon"


class Feat(str, Enum):
    """All feats in the 2024 PHB."""

    # Origin feats
    ALERT = "Alert"
    CRAFTER = "Crafter"
    HEALER = "Healer"
    LUCKY = "Lucky"
    MAGIC_INITIATE = "Magic Initiate"
    MUSICIAN = "Musician"
    SAVAGE_ATTACKER = "Savage Attacker"
    SKILLED = "Skilled"
    TAVERN_BRAWLER = "Tavern Brawler"
    TOUGH = "Tough"
    # General feats
    ABILITY_SCORE_IMPROVEMENT = "Ability Score Improvement"
    ACTOR = "Actor"
    ATHLETE = "Athlete"
    CHARGER = "Charger"
    CHEF = "Chef"
    CROSSBOW_EXPERT = "Crossbow Expert"
    CRUSHER = "Crusher"
    DEFENSIVE_DUELIST = "Defensive Duelist"
    DUAL_WIELDER = "Dual Wielder"
    DURABLE = "Durable"
    ELEMENTAL_ADEPT = "Elemental Adept"
    FEY_TOUCHED = "Fey-Touched"
    GRAPPLER = "Grappler"
    GREAT_WEAPON_MASTER = "Great Weapon Master"
    HEAVILY_ARMORED = "Heavily Armored"
    HEAVY_ARMOR_MASTER = "Heavy Armor Master"
    INSPIRING_LEADER = "Inspiring Leader"
    KEEN_MIND = "Keen Mind"
    LIGHTLY_ARMORED = "Lightly Armored"
    MAGE_SLAYER = "Mage Slayer"
    MARTIAL_WEAPON_TRAINING = "Martial Weapon Training"
    MEDIUM_ARMOR_MASTER = "Medium Armor Master"
    MODERATELY_ARMORED = "Moderately Armored"
    MOUNTED_COMBATANT = "Mounted Combatant"
    OBSERVANT = "Observant"
    PIERCER = "Piercer"
    POISONER = "Poisoner"
    POLEARM_MASTER = "Polearm Master"
    RESILIENT = "Resilient"
    RITUAL_CASTER = "Ritual Caster"
    SENTINEL = "Sentinel"
    SHADOW_TOUCHED = "Shadow-Touched"
    SHARPSHOOTER = "Sharpshooter"
    SHIELD_MASTER = "Shield Master"
    SKILL_EXPERT = "Skill Expert"
    SKULKER = "Skulker"
    SLASHER = "Slasher"
    SPEEDY = "Speedy"
    SPELL_SNIPER = "Spell Sniper"
    TELEKINETIC = "Telekinetic"
    TELEPATHIC = "Telepathic"
    WAR_CASTER = "War Caster"
    WEAPON_MASTER = "Weapon Master"
    # Fighting style feats
    ARCHERY = "Archery"
    BLIND_FIGHTING = "Blind Fighting"
    DEFENSE = "Defense"
    DUELING = "Dueling"
    GREAT_WEAPON_FIGHTING = "Great Weapon Fighting"
    INTERCEPTION = "Interception"
    PROTECTION = "Protection"
    THROWN_WEAPON_FIGHTING = "Thrown Weapon Fighting"
    TWO_WEAPON_FIGHTING = "Two-Weapon Fighting"
    UNARMED_FIGHTING = "Unarmed Fighting"
    # Epic boons
    BOON_OF_COMBAT_PROWESS = "Boon of Combat Prowess"
    BOON_OF_DIMENSIONAL_TRAVEL = "Boon of Dimensional Travel"
    BOON_OF_ENERGY_RESISTANCE = "Boon of Energy Resistance"
    BOON_OF_FATE = "Boon of Fate"
    BOON_OF_FORTITUDE = "Boon of Fortitude"
    BOON_OF_IRRESISTIBLE_OFFENSE = "Boon of Irresistible Offense"
    BOON_OF_RECOVERY = "Boon of Recovery"
    BOON_OF_SKILL = "Boon of Skill"
    BOON_OF_SPEED = "Boon of Speed"
    BOON_OF_SPELL_RECALL = "Boon of Spell Recall"
    BOON_OF_THE_NIGHT_SPIRIT = "Boon of the Night Spirit"
    BOON_OF_TRUESIGHT = "Boon of Truesight"

    @property
    def category(self) -> FeatCategory:
        """Return the category this feat belongs to."""
        return _FEAT_CATEGORY[self]


def _categories() -> dict[Feat, FeatCategory]:
    feats = list(Feat)
    origin_end = feats.index(Feat.TOUGH) + 1
    general_end = feats.index(Feat.WEAPON_MASTER) + 1
    style_end = feats.index(Feat.UNARMED_FIGHTING) + 1
    result: dict[Feat, FeatCategory] = {}
    for i, feat in enumerate(feats):
        if i < origin_end:
            result[feat] = FeatCategory.ORIGIN
        elif i < general_end:
            result[feat] = FeatCategory.GENERAL
        elif i < style_end:
            result[feat] = FeatCategory.FIGHTING_STYLE
        else:
            result[feat] = FeatCategory.EPIC_BOON
    return result


_FEAT_CATEGORY: dict[Feat, FeatCategory] = _categories()
