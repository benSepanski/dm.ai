"""
Subclass enum and parent-class mapping (2024 PHB + Tasha's Artificer).

Internal module — import via :mod:`game_engine.types.enums`.
"""

from __future__ import annotations

from enum import Enum

from game_engine.types.enums._character import CharacterClass


class Subclass(str, Enum):
    """All subclasses from the 2024 PHB (plus Artificer specialists)."""

    # Artificer (Tasha's Cauldron of Everything)
    ALCHEMIST = "Alchemist"
    ARMORER = "Armorer"
    ARTILLERIST = "Artillerist"
    BATTLE_SMITH = "Battle Smith"
    # Barbarian
    PATH_OF_THE_BERSERKER = "Path of the Berserker"
    PATH_OF_THE_WILD_HEART = "Path of the Wild Heart"
    PATH_OF_THE_WORLD_TREE = "Path of the World Tree"
    PATH_OF_THE_ZEALOT = "Path of the Zealot"
    # Bard
    COLLEGE_OF_DANCE = "College of Dance"
    COLLEGE_OF_GLAMOUR = "College of Glamour"
    COLLEGE_OF_LORE = "College of Lore"
    COLLEGE_OF_VALOR = "College of Valor"
    # Cleric
    LIFE_DOMAIN = "Life Domain"
    LIGHT_DOMAIN = "Light Domain"
    TRICKERY_DOMAIN = "Trickery Domain"
    WAR_DOMAIN = "War Domain"
    # Druid
    CIRCLE_OF_THE_LAND = "Circle of the Land"
    CIRCLE_OF_THE_MOON = "Circle of the Moon"
    CIRCLE_OF_THE_SEA = "Circle of the Sea"
    CIRCLE_OF_THE_STARS = "Circle of the Stars"
    # Fighter
    BATTLE_MASTER = "Battle Master"
    CHAMPION = "Champion"
    ELDRITCH_KNIGHT = "Eldritch Knight"
    PSI_WARRIOR = "Psi Warrior"
    # Monk
    WARRIOR_OF_MERCY = "Warrior of Mercy"
    WARRIOR_OF_SHADOW = "Warrior of Shadow"
    WARRIOR_OF_THE_ELEMENTS = "Warrior of the Elements"
    WARRIOR_OF_THE_OPEN_HAND = "Warrior of the Open Hand"
    # Paladin
    OATH_OF_DEVOTION = "Oath of Devotion"
    OATH_OF_GLORY = "Oath of Glory"
    OATH_OF_THE_ANCIENTS = "Oath of the Ancients"
    OATH_OF_VENGEANCE = "Oath of Vengeance"
    # Ranger
    BEAST_MASTER = "Beast Master"
    FEY_WANDERER = "Fey Wanderer"
    GLOOM_STALKER = "Gloom Stalker"
    HUNTER = "Hunter"
    # Rogue
    ARCANE_TRICKSTER = "Arcane Trickster"
    ASSASSIN = "Assassin"
    SOULKNIFE = "Soulknife"
    THIEF = "Thief"
    # Sorcerer
    ABERRANT_SORCERY = "Aberrant Sorcery"
    CLOCKWORK_SORCERY = "Clockwork Sorcery"
    DRACONIC_SORCERY = "Draconic Sorcery"
    WILD_MAGIC_SORCERY = "Wild Magic Sorcery"
    # Warlock
    ARCHFEY_PATRON = "Archfey Patron"
    CELESTIAL_PATRON = "Celestial Patron"
    FIEND_PATRON = "Fiend Patron"
    GREAT_OLD_ONE_PATRON = "Great Old One Patron"
    # Wizard
    ABJURER = "Abjurer"
    DIVINER = "Diviner"
    EVOKER = "Evoker"
    ILLUSIONIST = "Illusionist"

    @property
    def parent_class(self) -> CharacterClass:
        """Return the class this subclass belongs to."""
        return _SUBCLASS_PARENT[self]


def _parents() -> dict[Subclass, CharacterClass]:
    groups: dict[CharacterClass, list[Subclass]] = {
        CharacterClass.ARTIFICER: [
            Subclass.ALCHEMIST,
            Subclass.ARMORER,
            Subclass.ARTILLERIST,
            Subclass.BATTLE_SMITH,
        ],
        CharacterClass.BARBARIAN: [
            Subclass.PATH_OF_THE_BERSERKER,
            Subclass.PATH_OF_THE_WILD_HEART,
            Subclass.PATH_OF_THE_WORLD_TREE,
            Subclass.PATH_OF_THE_ZEALOT,
        ],
        CharacterClass.BARD: [
            Subclass.COLLEGE_OF_DANCE,
            Subclass.COLLEGE_OF_GLAMOUR,
            Subclass.COLLEGE_OF_LORE,
            Subclass.COLLEGE_OF_VALOR,
        ],
        CharacterClass.CLERIC: [
            Subclass.LIFE_DOMAIN,
            Subclass.LIGHT_DOMAIN,
            Subclass.TRICKERY_DOMAIN,
            Subclass.WAR_DOMAIN,
        ],
        CharacterClass.DRUID: [
            Subclass.CIRCLE_OF_THE_LAND,
            Subclass.CIRCLE_OF_THE_MOON,
            Subclass.CIRCLE_OF_THE_SEA,
            Subclass.CIRCLE_OF_THE_STARS,
        ],
        CharacterClass.FIGHTER: [
            Subclass.BATTLE_MASTER,
            Subclass.CHAMPION,
            Subclass.ELDRITCH_KNIGHT,
            Subclass.PSI_WARRIOR,
        ],
        CharacterClass.MONK: [
            Subclass.WARRIOR_OF_MERCY,
            Subclass.WARRIOR_OF_SHADOW,
            Subclass.WARRIOR_OF_THE_ELEMENTS,
            Subclass.WARRIOR_OF_THE_OPEN_HAND,
        ],
        CharacterClass.PALADIN: [
            Subclass.OATH_OF_DEVOTION,
            Subclass.OATH_OF_GLORY,
            Subclass.OATH_OF_THE_ANCIENTS,
            Subclass.OATH_OF_VENGEANCE,
        ],
        CharacterClass.RANGER: [
            Subclass.BEAST_MASTER,
            Subclass.FEY_WANDERER,
            Subclass.GLOOM_STALKER,
            Subclass.HUNTER,
        ],
        CharacterClass.ROGUE: [
            Subclass.ARCANE_TRICKSTER,
            Subclass.ASSASSIN,
            Subclass.SOULKNIFE,
            Subclass.THIEF,
        ],
        CharacterClass.SORCERER: [
            Subclass.ABERRANT_SORCERY,
            Subclass.CLOCKWORK_SORCERY,
            Subclass.DRACONIC_SORCERY,
            Subclass.WILD_MAGIC_SORCERY,
        ],
        CharacterClass.WARLOCK: [
            Subclass.ARCHFEY_PATRON,
            Subclass.CELESTIAL_PATRON,
            Subclass.FIEND_PATRON,
            Subclass.GREAT_OLD_ONE_PATRON,
        ],
        CharacterClass.WIZARD: [
            Subclass.ABJURER,
            Subclass.DIVINER,
            Subclass.EVOKER,
            Subclass.ILLUSIONIST,
        ],
    }
    return {sub: cls for cls, subs in groups.items() for sub in subs}


_SUBCLASS_PARENT: dict[Subclass, CharacterClass] = _parents()


def subclasses_for(character_class: CharacterClass) -> list[Subclass]:
    """Return all subclasses belonging to *character_class*."""
    return [s for s, c in _SUBCLASS_PARENT.items() if c == character_class]
