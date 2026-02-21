"""
Abstract character sheet for the RPG game engine.

Provides a rule-agnostic representation of any participant in the game:
player characters, non-player characters, and monsters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CharacterType(Enum):
    """Broad classification for a character's role in the game."""

    PC = "PC"          # Player Character
    NPC = "NPC"        # Non-Player Character
    MONSTER = "MONSTER"  # Monster / creature


@dataclass
class AbilityScores:
    """The six core ability scores used in D&D-style games.

    Attribute names follow Python conventions (``str_`` avoids shadowing the
    built-in ``str``, ``int_`` avoids shadowing ``int``).

    Attributes:
        str_: Strength score.
        dex: Dexterity score.
        con: Constitution score.
        int_: Intelligence score.
        wis: Wisdom score.
        cha: Charisma score.
    """

    str_: int = 10
    dex: int = 10
    con: int = 10
    int_: int = 10
    wis: int = 10
    cha: int = 10

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict of the ability scores."""
        return {
            "strength": self.str_,
            "dexterity": self.dex,
            "constitution": self.con,
            "intelligence": self.int_,
            "wisdom": self.wis,
            "charisma": self.cha,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AbilityScores":
        """Create an :class:`AbilityScores` from a dict.

        Accepts both long-form keys (``"strength"``) and short-form keys
        (``"str"`` / ``"str_"``).
        """
        return cls(
            str_=data.get("strength", data.get("str_", data.get("str", 10))),
            dex=data.get("dexterity", data.get("dex", 10)),
            con=data.get("constitution", data.get("con", 10)),
            int_=data.get("intelligence", data.get("int_", data.get("int", 10))),
            wis=data.get("wisdom", data.get("wis", 10)),
            cha=data.get("charisma", data.get("cha", 10)),
        )


def get_modifier(score: int) -> int:
    """Calculate the D&D ability modifier for a given score.

    Uses the standard formula: ``(score - 10) // 2``.

    Args:
        score: Ability score value (typically 1-30).

    Returns:
        Integer modifier (negative for scores below 10).

    Examples:
        >>> get_modifier(10)
        0
        >>> get_modifier(16)
        3
        >>> get_modifier(8)
        -1
    """
    return (score - 10) // 2


#: Conditions that prevent a character from acting.
_INCAPACITATING_CONDITIONS: frozenset[str] = frozenset(
    {"incapacitated", "paralyzed", "petrified", "stunned", "unconscious"}
)

#: Map of lowercase ability name aliases to attribute names on AbilityScores.
_ABILITY_ATTR: dict[str, str] = {
    "strength": "str_",
    "str": "str_",
    "str_": "str_",
    "dexterity": "dex",
    "dex": "dex",
    "constitution": "con",
    "con": "con",
    "intelligence": "int_",
    "int": "int_",
    "int_": "int_",
    "wisdom": "wis",
    "wis": "wis",
    "charisma": "cha",
    "cha": "cha",
}


class AbstractCharacter:
    """Rule-agnostic character sheet.

    This class is intended to be subclassed by rule-specific implementations
    that add game-specific fields (spell slots, class features, etc.).

    Attributes:
        id: Unique identifier string.
        name: Display name.
        char_type: :class:`CharacterType` enum value.
        ability_scores: :class:`AbilityScores` instance.
        hp_current: Current hit points.
        hp_max: Maximum hit points.
        ac: Armour class.
        speed: Movement speed in feet.
        level: Character level (1-20).
        conditions: List of active condition name strings.
    """

    def __init__(
        self,
        id: str,
        name: str,
        char_type: CharacterType = CharacterType.PC,
        ability_scores: AbilityScores | None = None,
        hp_current: int = 10,
        hp_max: int = 10,
        ac: int = 10,
        speed: int = 30,
        level: int = 1,
        conditions: list[str] | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.char_type = char_type
        self.ability_scores: AbilityScores = ability_scores or AbilityScores()
        self.hp_current = hp_current
        self.hp_max = hp_max
        self.ac = ac
        self.speed = speed
        self.level = level
        self.conditions: list[str] = conditions or []

    # ------------------------------------------------------------------
    # Ability score helpers
    # ------------------------------------------------------------------

    def modifier(self, ability: str) -> int:
        """Return the D&D ability modifier for the named ability.

        Args:
            ability: Ability name (case-insensitive). Accepts full names
                (``"strength"``) and abbreviations (``"str"``).

        Returns:
            Integer modifier.

        Raises:
            ValueError: If *ability* is not a recognised ability name.
        """
        attr = _ABILITY_ATTR.get(ability.lower())
        if attr is None:
            raise ValueError(
                f"Unknown ability {ability!r}. "
                f"Valid names: {sorted(_ABILITY_ATTR.keys())}"
            )
        score = getattr(self.ability_scores, attr)
        return get_modifier(score)

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        """Return True if the character has more than 0 hit points."""
        return self.hp_current > 0

    def is_conscious(self) -> bool:
        """Return True if the character is alive and not incapacitated.

        A character is unconscious if they are dead, or if they have any of:
        unconscious, stunned, paralyzed, or petrified conditions.
        """
        if not self.is_alive():
            return False
        incap_conditions = {"unconscious", "stunned", "paralyzed", "petrified"}
        active = {c.lower() for c in self.conditions}
        return not bool(active & incap_conditions)

    def can_act(self) -> bool:
        """Return True if the character can take actions this turn.

        Characters cannot act if they are dead or have any incapacitating
        condition.
        """
        if not self.is_alive():
            return False
        active = {c.lower() for c in self.conditions}
        return not bool(active & _INCAPACITATING_CONDITIONS)

    # ------------------------------------------------------------------
    # HP manipulation
    # ------------------------------------------------------------------

    def take_damage(self, amount: int) -> int:
        """Reduce current HP by *amount*, flooring at 0.

        Args:
            amount: Positive integer damage amount.

        Returns:
            New value of :attr:`hp_current`.
        """
        self.hp_current = max(0, self.hp_current - amount)
        return self.hp_current

    def heal(self, amount: int) -> int:
        """Increase current HP by *amount*, capped at :attr:`hp_max`.

        Args:
            amount: Positive integer healing amount.

        Returns:
            New value of :attr:`hp_current`.
        """
        self.hp_current = min(self.hp_max, self.hp_current + amount)
        return self.hp_current

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict representation of this character."""
        return {
            "id": self.id,
            "name": self.name,
            "char_type": self.char_type.value,
            "ability_scores": self.ability_scores.to_dict(),
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "ac": self.ac,
            "speed": self.speed,
            "level": self.level,
            "conditions": list(self.conditions),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AbstractCharacter":
        """Create an :class:`AbstractCharacter` from a dict.

        Args:
            data: Dict as produced by :meth:`to_dict`.

        Returns:
            A new :class:`AbstractCharacter` instance.
        """
        char_type_raw = data.get("char_type", "PC")
        try:
            char_type = CharacterType(char_type_raw)
        except ValueError:
            char_type = CharacterType.PC

        ability_scores = AbilityScores.from_dict(data.get("ability_scores", {}))

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            char_type=char_type,
            ability_scores=ability_scores,
            hp_current=data.get("hp_current", 10),
            hp_max=data.get("hp_max", 10),
            ac=data.get("ac", 10),
            speed=data.get("speed", 30),
            level=data.get("level", 1),
            conditions=list(data.get("conditions", [])),
        )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.id!r} name={self.name!r} "
            f"hp={self.hp_current}/{self.hp_max}>"
        )
