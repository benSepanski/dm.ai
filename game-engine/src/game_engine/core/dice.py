"""
Dice notation parser and roller for the RPG game engine.

Supports standard dice notation such as:
    "d20"       -> 1d20+0
    "1d6"       -> 1d6+0
    "2d8+4"     -> 2d8+4
    "3d6-1"     -> 3d6-1
"""

import random
import re


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_NOTATION_RE = re.compile(
    r"^(?P<count>\d+)?d(?P<sides>\d+)(?P<mod>[+-]\d+)?$",
    re.IGNORECASE,
)


def parse_notation(notation: str) -> tuple[int, int, int]:
    """Parse a dice notation string into its component parts.

    Args:
        notation: A string like "2d6+3", "d20", "1d8-1".

    Returns:
        A tuple of (count, sides, modifier).

    Raises:
        ValueError: If *notation* cannot be parsed.

    Examples:
        >>> parse_notation("2d6+3")
        (2, 6, 3)
        >>> parse_notation("d20")
        (1, 20, 0)
        >>> parse_notation("3d6-1")
        (3, 6, -1)
    """
    notation = notation.strip()
    match = _NOTATION_RE.match(notation)
    if not match:
        raise ValueError(
            f"Invalid dice notation {notation!r}. "
            "Expected format: [N]dS[+/-M]  e.g. '2d6+3' or 'd20'."
        )

    count = int(match.group("count")) if match.group("count") else 1
    sides = int(match.group("sides"))
    modifier = int(match.group("mod")) if match.group("mod") else 0

    if sides < 1:
        raise ValueError(f"Dice must have at least 1 side, got {sides}.")
    if count < 0:
        raise ValueError(f"Dice count cannot be negative, got {count}.")

    return count, sides, modifier


# ---------------------------------------------------------------------------
# Rolling
# ---------------------------------------------------------------------------


def roll_dice(
    count: int, sides: int, modifier: int = 0
) -> tuple[int, list[int]]:
    """Roll *count* dice with *sides* faces and add *modifier*.

    Args:
        count: Number of dice to roll (0 is allowed and returns modifier).
        sides: Number of faces on each die (must be >= 1).
        modifier: Flat integer added to the sum of all dice.

    Returns:
        A tuple of (total, individual_rolls) where *individual_rolls* is the
        list of raw die results before the modifier is applied.

    Raises:
        ValueError: If *sides* < 1 or *count* < 0.

    Examples:
        >>> total, rolls = roll_dice(2, 6, 3)
        >>> len(rolls)
        2
        >>> all(1 <= r <= 6 for r in rolls)
        True
    """
    if sides < 1:
        raise ValueError(f"Dice must have at least 1 side, got {sides}.")
    if count < 0:
        raise ValueError(f"Dice count cannot be negative, got {count}.")

    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    return total, rolls


def roll(notation: str) -> tuple[int, list[int]]:
    """Parse and roll a dice notation string.

    This is a convenience wrapper around :func:`parse_notation` and
    :func:`roll_dice`.

    Args:
        notation: Dice notation string (e.g. "2d6+3").

    Returns:
        A tuple of (total, individual_rolls).

    Raises:
        ValueError: If *notation* is invalid.

    Examples:
        >>> total, rolls = roll("2d6+3")
        >>> 5 <= total <= 15  # 2*[1..6] + 3
        True
    """
    count, sides, modifier = parse_notation(notation)
    return roll_dice(count, sides, modifier)


def roll_with_advantage(sides: int) -> tuple[int, list[int]]:
    """Roll a single die twice and take the higher result.

    Args:
        sides: Number of faces on the die.

    Returns:
        A tuple of (higher_roll, [roll1, roll2]).

    Raises:
        ValueError: If *sides* < 1.

    Examples:
        >>> total, rolls = roll_with_advantage(20)
        >>> total == max(rolls)
        True
        >>> len(rolls)
        2
    """
    if sides < 1:
        raise ValueError(f"Dice must have at least 1 side, got {sides}.")
    roll1 = random.randint(1, sides)
    roll2 = random.randint(1, sides)
    return max(roll1, roll2), [roll1, roll2]


def roll_with_disadvantage(sides: int) -> tuple[int, list[int]]:
    """Roll a single die twice and take the lower result.

    Args:
        sides: Number of faces on the die.

    Returns:
        A tuple of (lower_roll, [roll1, roll2]).

    Raises:
        ValueError: If *sides* < 1.

    Examples:
        >>> total, rolls = roll_with_disadvantage(20)
        >>> total == min(rolls)
        True
        >>> len(rolls)
        2
    """
    if sides < 1:
        raise ValueError(f"Dice must have at least 1 side, got {sides}.")
    roll1 = random.randint(1, sides)
    roll2 = random.randint(1, sides)
    return min(roll1, roll2), [roll1, roll2]


# ---------------------------------------------------------------------------
# Convenience functions for common die sizes
# ---------------------------------------------------------------------------


def d4(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d4.

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 4, modifier)


def d6(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d6.

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 6, modifier)


def d8(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d8.

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 8, modifier)


def d10(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d10.

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 10, modifier)


def d12(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d12.

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 12, modifier)


def d20(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d20.

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 20, modifier)


def d100(modifier: int = 0) -> tuple[int, list[int]]:
    """Roll a single d100 (percentile die).

    Args:
        modifier: Flat modifier to add to the roll.

    Returns:
        A tuple of (total, [roll]).
    """
    return roll_dice(1, 100, modifier)
