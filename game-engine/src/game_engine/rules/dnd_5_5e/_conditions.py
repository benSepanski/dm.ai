"""
D&D 5.5e condition application and removal logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.conditions import is_immune_to_condition
from game_engine.types import CharacterSheet, Condition


def _apply_condition_impl(
    target: CharacterSheet,
    condition: Condition | str,
    duration_rounds: int | None = None,
) -> CharacterSheet:
    """Apply *condition* to *target* if not immune.

    Args:
        target: Character sheet. Modified in-place and returned.
        condition: :class:`~game_engine.types.Condition` enum or name string.
        duration_rounds: Optional duration in rounds (stored for reference).

    Returns:
        Updated character sheet.
    """
    # Normalise to Condition enum
    if isinstance(condition, str):
        try:
            condition = Condition(condition.lower())
        except ValueError:
            return target  # Unknown condition — no-op

    if is_immune_to_condition(target, condition):
        return target

    if condition not in target.conditions:
        target.conditions.append(condition)

    if duration_rounds is not None:
        target.condition_durations[condition] = duration_rounds

    return target


def _remove_condition_impl(
    target: CharacterSheet,
    condition: Condition | str,
) -> CharacterSheet:
    """Remove *condition* from *target*.

    Args:
        target: Character sheet. Modified in-place and returned.
        condition: :class:`~game_engine.types.Condition` enum or name string.

    Returns:
        Updated character sheet.
    """
    if isinstance(condition, str):
        try:
            condition = Condition(condition.lower())
        except ValueError:
            return target  # Unknown condition — no-op

    target.conditions = [c for c in target.conditions if c != condition]
    target.condition_durations.pop(condition, None)
    return target
