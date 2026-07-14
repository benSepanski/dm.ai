"""
D&D 5.5e condition application and removal logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.conditions import is_immune_to_condition
from game_engine.types import CharacterSheet, Condition


def _break_concentration_on_incapacitation(target: CharacterSheet, condition: Condition) -> None:
    """Clear *target*'s concentration if *condition* is Incapacitating.

    SRD 5.2: "You lose concentration on a spell if you are incapacitated."
    ``Condition.prevents_action`` (the same Incapacitated/Paralyzed/
    Petrified/Stunned/Unconscious set that gates ``CharacterSheet.can_act``)
    is the single source of truth for which conditions qualify (EFF-01).

    Every path that applies a condition to a combatant must call this —
    currently :func:`_apply_condition_impl` and the spell-rider apply loop
    in :mod:`._spell_resolution`. Idempotent: safe to call even when the
    target isn't concentrating.
    """
    if Condition.prevents_action(condition):
        target.concentrating_on = None


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

    # SRD 5.2 Unconscious: "You have the Incapacitated and Prone conditions,
    # ... and you fall Prone." Mirrors _fall_unconscious's 0-HP path so
    # Unconscious applied directly (e.g. Sleep) also carries Prone.
    if condition is Condition.UNCONSCIOUS and not is_immune_to_condition(target, Condition.PRONE):
        if Condition.PRONE not in target.conditions:
            target.conditions.append(Condition.PRONE)

    _break_concentration_on_incapacitation(target, condition)

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


def _tick_condition_durations_impl(target: CharacterSheet) -> CharacterSheet:
    """Decrement timed condition durations at end of a combatant's turn.

    Conditions whose remaining duration reaches zero are removed entirely.
    Indefinite conditions (not tracked in ``condition_durations``) are not
    affected. Called by the rule engine once per ``next_turn`` transition.

    Args:
        target: Character sheet. Modified in-place and returned.

    Returns:
        Updated character sheet.
    """
    # Collect conditions that expire this turn (duration ≤ 1).
    expired = [c for c, n in target.condition_durations.items() if n <= 1]
    for cond in expired:
        target.conditions = [c for c in target.conditions if c != cond]
        del target.condition_durations[cond]

    # Decrement remaining timed conditions.
    for cond in list(target.condition_durations):
        target.condition_durations[cond] -= 1

    return target
