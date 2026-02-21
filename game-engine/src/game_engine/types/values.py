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
    Validates format on construction.
    """

    __slots__ = ()

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
        if count < 0:
            raise ValueError(f"Dice count cannot be negative, got {count}.")
        return str.__new__(cls, value)

    @property
    def num_dice(self) -> int:
        match = _NOTATION_RE.match(self)
        assert match is not None
        return int(match.group("count")) if match.group("count") else 1

    @property
    def sides(self) -> int:
        match = _NOTATION_RE.match(self)
        assert match is not None
        return int(match.group("sides"))

    @property
    def modifier(self) -> int:
        match = _NOTATION_RE.match(self)
        assert match is not None
        return int(match.group("mod")) if match.group("mod") else 0

    def parsed(self) -> tuple[int, int, int]:
        """Return (count, sides, modifier) tuple."""
        return self.num_dice, self.sides, self.modifier
