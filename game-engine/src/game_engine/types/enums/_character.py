"""
Character-origin enums: classes, species, backgrounds, languages, resources.

Internal module — import via :mod:`game_engine.types.enums`.
"""

from __future__ import annotations

from enum import Enum


class CharacterClass(str, Enum):
    """Valid D&D 5.5e character classes."""

    ARTIFICER = "Artificer"
    BARBARIAN = "Barbarian"
    BARD = "Bard"
    CLERIC = "Cleric"
    DRUID = "Druid"
    FIGHTER = "Fighter"
    MONK = "Monk"
    PALADIN = "Paladin"
    RANGER = "Ranger"
    ROGUE = "Rogue"
    SORCERER = "Sorcerer"
    WARLOCK = "Warlock"
    WIZARD = "Wizard"

    @classmethod
    def all(cls) -> list["CharacterClass"]:
        return list(cls)


class CharacterType(str, Enum):
    """Broad classification for a character's role in the game."""

    PC = "PC"
    NPC = "NPC"
    MONSTER = "MONSTER"


class Species(str, Enum):
    """Playable species (SRD 5.2 / 2024 PHB)."""

    DRAGONBORN = "Dragonborn"
    DWARF = "Dwarf"
    ELF = "Elf"
    GNOME = "Gnome"
    GOLIATH = "Goliath"
    HALFLING = "Halfling"
    HUMAN = "Human"
    ORC = "Orc"
    TIEFLING = "Tiefling"


class Background(str, Enum):
    """Character backgrounds (2024 PHB chapter 4)."""

    ACOLYTE = "Acolyte"
    ARTISAN = "Artisan"
    CHARLATAN = "Charlatan"
    CRIMINAL = "Criminal"
    ENTERTAINER = "Entertainer"
    FARMER = "Farmer"
    GUARD = "Guard"
    GUIDE = "Guide"
    HERMIT = "Hermit"
    MERCHANT = "Merchant"
    NOBLE = "Noble"
    SAGE = "Sage"
    SAILOR = "Sailor"
    SCRIBE = "Scribe"
    SOLDIER = "Soldier"
    WAYFARER = "Wayfarer"


class Language(str, Enum):
    """Languages (2024 PHB: standard and rare)."""

    # Standard
    COMMON = "Common"
    COMMON_SIGN_LANGUAGE = "Common Sign Language"
    DRACONIC = "Draconic"
    DWARVISH = "Dwarvish"
    ELVISH = "Elvish"
    GIANT = "Giant"
    GNOMISH = "Gnomish"
    GOBLIN = "Goblin"
    HALFLING = "Halfling"
    ORC = "Orc"
    # Rare
    ABYSSAL = "Abyssal"
    CELESTIAL = "Celestial"
    DEEP_SPEECH = "Deep Speech"
    DRUIDIC = "Druidic"
    INFERNAL = "Infernal"
    PRIMORDIAL = "Primordial"
    SYLVAN = "Sylvan"
    THIEVES_CANT = "Thieves' Cant"
    UNDERCOMMON = "Undercommon"


class Alignment(str, Enum):
    """The nine alignments plus unaligned."""

    LAWFUL_GOOD = "Lawful Good"
    NEUTRAL_GOOD = "Neutral Good"
    CHAOTIC_GOOD = "Chaotic Good"
    LAWFUL_NEUTRAL = "Lawful Neutral"
    TRUE_NEUTRAL = "True Neutral"
    CHAOTIC_NEUTRAL = "Chaotic Neutral"
    LAWFUL_EVIL = "Lawful Evil"
    NEUTRAL_EVIL = "Neutral Evil"
    CHAOTIC_EVIL = "Chaotic Evil"
    UNALIGNED = "Unaligned"


class SpellcasterType(str, Enum):
    """How a class contributes to spell slot progression."""

    NONE = "none"
    FULL = "full"  # bard, cleric, druid, sorcerer, wizard
    HALF = "half"  # paladin, ranger, artificer (round up)
    THIRD = "third"  # eldritch knight, arcane trickster
    PACT = "pact"  # warlock (separate pact magic slots)


class ClassResource(str, Enum):
    """Named per-class resources tracked in class feature tables."""

    RAGE = "rage"
    RAGE_DAMAGE = "rage damage"
    WEAPON_MASTERY = "weapon mastery"
    BARDIC_INSPIRATION = "bardic inspiration"
    CHANNEL_DIVINITY = "channel divinity"
    WILD_SHAPE = "wild shape"
    SECOND_WIND = "second wind"
    ACTION_SURGE = "action surge"
    INDOMITABLE = "indomitable"
    FOCUS_POINT = "focus point"
    MARTIAL_ARTS_DIE = "martial arts die"
    LAY_ON_HANDS = "lay on hands"
    SNEAK_ATTACK_DICE = "sneak attack dice"
    SORCERY_POINT = "sorcery point"
    ELDRITCH_INVOCATION = "eldritch invocation"
    ARCANE_RECOVERY = "arcane recovery"
    INFUSION = "infusion"
