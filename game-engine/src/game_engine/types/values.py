"""
Validated value types for the game engine.

These types enforce domain constraints at construction time,
eliminating the need for runtime validation in business logic.
"""

from __future__ import annotations

import re

_NOTATION_RE = re.compile(
    r"^(?P<count>\d+)?d(?P<sides>\d+)(?P<mod>[+-]\d+)?$",
    re.IGNORECASE,
)


class DiceNotation(str):
    """A validated dice notation string (e.g. '2d6+3', 'd20', '1d8-1').

    Inherits from ``str`` so it can be used anywhere a string is expected.
    Validates format on construction and caches parsed components.
    """

    __slots__ = ("_num_dice", "_sides", "_modifier")

    def __new__(cls, value: str) -> DiceNotation:
        value = str(value).strip()
        match = _NOTATION_RE.match(value)
        if not match:
            raise ValueError(
                f"Invalid dice notation {value!r}. "
                "Expected format: [N]dS[+/-M]  e.g. '2d6+3' or 'd20'."
            )
        sides = int(match.group("sides"))
        if sides < 1:
            raise ValueError(f"Dice must have at least 1 side, got {sides}.")
        count = int(match.group("count")) if match.group("count") else 1
        instance = str.__new__(cls, value)
        # Cache parsed components to avoid re-parsing on every property access
        object.__setattr__(instance, "_num_dice", count)
        object.__setattr__(instance, "_sides", sides)
        mod = int(match.group("mod")) if match.group("mod") else 0
        object.__setattr__(instance, "_modifier", mod)
        return instance

    @property
    def num_dice(self) -> int:
        return int(self._num_dice)  # type: ignore[attr-defined]

    @property
    def sides(self) -> int:
        return int(self._sides)  # type: ignore[attr-defined]

    @property
    def modifier(self) -> int:
        return int(self._modifier)  # type: ignore[attr-defined]

    def parsed(self) -> tuple[int, int, int]:
        """Return (count, sides, modifier) tuple."""
        return self.num_dice, self.sides, self.modifier
