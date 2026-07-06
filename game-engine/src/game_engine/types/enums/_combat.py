"""
Combat and equipment enums: actions, cover, rests, weapons, armor.

Internal module — import via :mod:`game_engine.types.enums`.
"""

from __future__ import annotations

from enum import Enum


class ActionType(str, Enum):
    """The 2024 PHB action list, plus two reaction-resolution events.

    ``OPPORTUNITY_ATTACK`` and ``READIED_ACTION`` are not on-turn actions —
    a character never has them available at the start of its own turn — but
    routing them through the same discriminated ``Action``/``resolve_action``
    entry point the on-turn actions use lets a reaction be submitted through
    the same API without a parallel dispatch mechanism.
    """

    ATTACK = "Attack"
    DASH = "Dash"
    DISENGAGE = "Disengage"
    DODGE = "Dodge"
    HELP = "Help"
    HIDE = "Hide"
    INFLUENCE = "Influence"
    MAGIC = "Magic"
    READY = "Ready"
    SEARCH = "Search"
    STUDY = "Study"
    UTILIZE = "Utilize"
    OPPORTUNITY_ATTACK = "Opportunity Attack"
    READIED_ACTION = "Readied Action"


class CoverType(str, Enum):
    """Degrees of cover (2024 PHB). Absence of cover is ``None``."""

    HALF = "half"
    THREE_QUARTERS = "three-quarters"
    TOTAL = "total"

    @property
    def ac_bonus(self) -> int:
        """AC and Dexterity saving throw bonus granted by this cover."""
        if self is CoverType.HALF:
            return 2
        if self is CoverType.THREE_QUARTERS:
            return 5
        return 0  # total cover: can't be targeted at all

    @property
    def blocks_targeting(self) -> bool:
        """Whether this cover prevents being targeted directly."""
        return self is CoverType.TOTAL


class RestType(str, Enum):
    """Rest varieties."""

    SHORT = "short"
    LONG = "long"


class DeathSaveOutcome(str, Enum):
    """Outcome of a single death saving throw."""

    SUCCESS = "success"
    FAILURE = "failure"
    CRITICAL_SUCCESS = "critical success"  # natural 20: regain 1 HP
    CRITICAL_FAILURE = "critical failure"  # natural 1: two failures


class UnarmedStrikeOption(str, Enum):
    """The three unarmed strike options (2024 PHB)."""

    DAMAGE = "damage"
    GRAPPLE = "grapple"
    SHOVE = "shove"


class WeaponCategory(str, Enum):
    """Weapon proficiency categories."""

    SIMPLE = "simple"
    MARTIAL = "martial"


class WeaponMastery(str, Enum):
    """Weapon mastery properties (2024 PHB)."""

    CLEAVE = "cleave"
    GRAZE = "graze"
    NICK = "nick"
    PUSH = "push"
    SAP = "sap"
    SLOW = "slow"
    TOPPLE = "topple"
    VEX = "vex"


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


class ArmorCategory(str, Enum):
    """Armor weight categories in D&D 5.5e."""

    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SHIELD = "shield"
