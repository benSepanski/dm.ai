"""
Typed string enums for the game engine.

All enums use ``str, Enum`` inheritance so values are wire-compatible
with their string equivalents and support ``Enum(value)`` construction.
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


class Ability(str, Enum):
    """The six core D&D ability scores."""

    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"

    def modifier(self, score: int) -> int:
        """Return the D&D modifier for the given ability score."""
        return (score - 10) // 2

    @property
    def short(self) -> str:
        """Return the three-letter abbreviation (e.g. 'str', 'dex')."""
        return self.value[:3]


class Skill(str, Enum):
    """All D&D 5e skills."""

    ACROBATICS = "acrobatics"
    ANIMAL_HANDLING = "animal handling"
    ARCANA = "arcana"
    ATHLETICS = "athletics"
    DECEPTION = "deception"
    HISTORY = "history"
    INSIGHT = "insight"
    INTIMIDATION = "intimidation"
    INVESTIGATION = "investigation"
    MEDICINE = "medicine"
    NATURE = "nature"
    PERCEPTION = "perception"
    PERFORMANCE = "performance"
    PERSUASION = "persuasion"
    RELIGION = "religion"
    SLEIGHT_OF_HAND = "sleight of hand"
    STEALTH = "stealth"
    SURVIVAL = "survival"

    @property
    def governing_ability(self) -> "Ability":
        """Return the ability score that governs this skill."""
        _MAP: dict[Skill, Ability] = {
            Skill.ACROBATICS: Ability.DEXTERITY,
            Skill.ANIMAL_HANDLING: Ability.WISDOM,
            Skill.ARCANA: Ability.INTELLIGENCE,
            Skill.ATHLETICS: Ability.STRENGTH,
            Skill.DECEPTION: Ability.CHARISMA,
            Skill.HISTORY: Ability.INTELLIGENCE,
            Skill.INSIGHT: Ability.WISDOM,
            Skill.INTIMIDATION: Ability.CHARISMA,
            Skill.INVESTIGATION: Ability.INTELLIGENCE,
            Skill.MEDICINE: Ability.WISDOM,
            Skill.NATURE: Ability.INTELLIGENCE,
            Skill.PERCEPTION: Ability.WISDOM,
            Skill.PERFORMANCE: Ability.CHARISMA,
            Skill.PERSUASION: Ability.CHARISMA,
            Skill.RELIGION: Ability.INTELLIGENCE,
            Skill.SLEIGHT_OF_HAND: Ability.DEXTERITY,
            Skill.STEALTH: Ability.DEXTERITY,
            Skill.SURVIVAL: Ability.WISDOM,
        }
        return _MAP[self]


class DamageType(str, Enum):
    """Standard D&D damage types."""

    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"


class Condition(str, Enum):
    """Standard D&D conditions."""

    BLINDED = "blinded"
    CHARMED = "charmed"
    DEAFENED = "deafened"
    EXHAUSTION = "exhaustion"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"

    @classmethod
    def prevents_action(cls, condition: "Condition") -> bool:
        """Return True if *condition* prevents the character from acting."""
        return condition in {
            cls.INCAPACITATED,
            cls.PARALYZED,
            cls.PETRIFIED,
            cls.STUNNED,
            cls.UNCONSCIOUS,
        }


class ActionType(str, Enum):
    """Combat action types available in D&D 5.5e."""

    ATTACK = "Attack"
    CAST_SPELL = "CastSpell"
    DASH = "Dash"
    DEATH_SAVE = "DeathSave"
    DISENGAGE = "Disengage"
    DODGE = "Dodge"
    HELP = "Help"
    HIDE = "Hide"
    READY = "Ready"
    SEARCH = "Search"
    USE_OBJECT = "Use Object"


class CharacterType(str, Enum):
    """Broad classification for a character's role in the game."""

    PC = "PC"
    NPC = "NPC"
    MONSTER = "MONSTER"


class LocationType(str, Enum):
    """Classification for a location in the game world."""

    REALM = "realm"
    COUNTRY = "country"
    REGION = "region"
    TOWN = "town"
    DISTRICT = "district"
    BUILDING = "building"
    ROOM = "room"
    DUNGEON = "dungeon"
    WILDERNESS = "wilderness"


class ProposalType(str, Enum):
    """Type of AI-generated proposal for the DM to review."""

    LOCATION = "location"
    CHARACTER = "character"
    DUNGEON = "dungeon"
    DIALOGUE = "dialogue"
    COMBAT_ACTION = "combat_action"


class ProposalStatus(str, Enum):
    """Current status of an AI proposal."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ChatRole(str, Enum):
    """Role of the sender in a chat message."""

    DM = "dm"
    AI = "ai"
    SYSTEM = "system"


class SpellSchool(str, Enum):
    """Schools of magic in D&D 5.5e."""

    ABJURATION = "abjuration"
    CONJURATION = "conjuration"
    DIVINATION = "divination"
    ENCHANTMENT = "enchantment"
    EVOCATION = "evocation"
    ILLUSION = "illusion"
    NECROMANCY = "necromancy"
    TRANSMUTATION = "transmutation"


class CreatureSize(str, Enum):
    """Standard D&D creature sizes."""

    TINY = "Tiny"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    HUGE = "Huge"
    GARGANTUAN = "Gargantuan"


class CreatureType(str, Enum):
    """Standard D&D creature types."""

    ABERRATION = "aberration"
    BEAST = "beast"
    CELESTIAL = "celestial"
    CONSTRUCT = "construct"
    DRAGON = "dragon"
    ELEMENTAL = "elemental"
    FEY = "fey"
    FIEND = "fiend"
    GIANT = "giant"
    HUMANOID = "humanoid"
    MONSTROSITY = "monstrosity"
    OOZE = "ooze"
    PLANT = "plant"
    UNDEAD = "undead"


class AdvantageType(str, Enum):
    """Whether a roll has advantage or disadvantage."""

    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


class ArmorCategory(str, Enum):
    """Armor weight categories in D&D 5.5e."""

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SHIELD = "shield"


class WeaponProperty(str, Enum):
    """Weapon properties in D&D 5.5e."""

    AMMUNITION = "ammunition"
    FINESSE = "finesse"
    HEAVY = "heavy"
    LIGHT = "light"
    LOADING = "loading"
    REACH = "reach"
    SPECIAL = "special"
    THROWN = "thrown"
    TWO_HANDED = "two-handed"
    VERSATILE = "versatile"
