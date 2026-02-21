"""
Abstract character sheet for the RPG game engine.

Provides a rule-agnostic representation of any participant in the game:
player characters, non-player characters, and monsters.
"""

from __future__ import annotations

from game_engine.types import (
    Ability,
    AbilityScoreSet,
    CharacterType,
    Condition,
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


#: Map of lowercase ability name aliases to :class:`~game_engine.types.Ability` values.
_ABILITY_ATTR: dict[str, Ability] = {
    "strength": Ability.STRENGTH,
    "str": Ability.STRENGTH,
    "str_": Ability.STRENGTH,
    "dexterity": Ability.DEXTERITY,
    "dex": Ability.DEXTERITY,
    "constitution": Ability.CONSTITUTION,
    "con": Ability.CONSTITUTION,
    "intelligence": Ability.INTELLIGENCE,
    "int": Ability.INTELLIGENCE,
    "int_": Ability.INTELLIGENCE,
    "wisdom": Ability.WISDOM,
    "wis": Ability.WISDOM,
    "charisma": Ability.CHARISMA,
    "cha": Ability.CHARISMA,
}

#: Conditions that prevent a character from acting.
_INCAPACITATING_CONDITIONS: frozenset[str] = frozenset(
    {"incapacitated", "paralyzed", "petrified", "stunned", "unconscious"}
)


class AbstractCharacter:
    """Rule-agnostic character sheet.

    This class is intended to be subclassed by rule-specific implementations
    that add game-specific fields (spell slots, class features, etc.).

    Attributes:
        id: Unique identifier string.
        name: Display name.
        char_type: :class:`~game_engine.types.CharacterType` enum value.
        ability_scores: :class:`~game_engine.types.AbilityScoreSet` instance.
        hp_current: Current hit points.
        hp_max: Maximum hit points.
        ac: Armour class.
        speed: Movement speed in feet.
        level: Character level (1-20).
        conditions: List of active :class:`~game_engine.types.Condition` enums.
    """

    def __init__(
        self,
        id: str,
        name: str,
        char_type: CharacterType = CharacterType.PC,
        ability_scores: AbilityScoreSet | None = None,
        hp_current: int = 10,
        hp_max: int = 10,
        ac: int = 10,
        speed: int = 30,
        level: int = 1,
        conditions: list[Condition | str] | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.char_type = char_type
        self.ability_scores: AbilityScoreSet = ability_scores or AbilityScoreSet()
        self.hp_current = hp_current
        self.hp_max = hp_max
        self.ac = ac
        self.speed = speed
        self.level = level
        # Coerce any raw strings to Condition enums where possible.
        self.conditions: list[Condition] = _coerce_conditions(conditions or [])

    # ------------------------------------------------------------------
    # Ability score helpers
    # ------------------------------------------------------------------

    def modifier(self, ability: str | Ability) -> int:
        """Return the D&D ability modifier for the named ability.

        Args:
            ability: :class:`~game_engine.types.Ability` enum or name string
                (case-insensitive). Accepts full names (``"strength"``) and
                abbreviations (``"str"``).

        Returns:
            Integer modifier.

        Raises:
            ValueError: If *ability* is not a recognised ability name.
        """
        if isinstance(ability, Ability):
            return ability.modifier(self.ability_scores.get(ability))

        ability_enum = _ABILITY_ATTR.get(ability.lower())
        if ability_enum is None:
            raise ValueError(
                f"Unknown ability {ability!r}. " f"Valid names: {sorted(_ABILITY_ATTR.keys())}"
            )
        return ability_enum.modifier(self.ability_scores.get(ability_enum))

    # ------------------------------------------------------------------
    # Status checks
    # ------------------------------------------------------------------

    def is_alive(self) -> bool:
        """Return True if the character has more than 0 hit points."""
        return self.hp_current > 0

    def is_conscious(self) -> bool:
        """Return True if the character is alive and not incapacitated."""
        if not self.is_alive():
            return False
        incap = {
            Condition.UNCONSCIOUS,
            Condition.STUNNED,
            Condition.PARALYZED,
            Condition.PETRIFIED,
        }
        return not bool(set(self.conditions) & incap)

    def can_act(self) -> bool:
        """Return True if the character can take actions this turn."""
        if not self.is_alive():
            return False
        return not any(Condition.prevents_action(c) for c in self.conditions)

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
            "conditions": [c.value for c in self.conditions],
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

        ability_scores = AbilityScoreSet.from_dict(data.get("ability_scores", {}))

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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_conditions(raw: list) -> list[Condition]:
    """Coerce a list of strings or Condition enums to Condition enums."""
    result: list[Condition] = []
    for item in raw:
        if isinstance(item, Condition):
            result.append(item)
        else:
            try:
                result.append(Condition(str(item).lower()))
            except ValueError:
                pass  # Unknown condition string — silently skip
    return result
