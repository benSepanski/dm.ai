"""
D&D 5.5e character sheet validation logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.interface import ValidationResult
from game_engine.types import Ability, CharacterSheet


def _validate_character_impl(sheet: CharacterSheet) -> ValidationResult:
    """Validate a character sheet for completeness and legality.

    Args:
        sheet: Character sheet to validate.

    Returns:
        :class:`~game_engine.interface.ValidationResult`.
    """
    errors: list[str] = []

    if not sheet.id:
        errors.append("Missing required field: 'id'.")
    if not sheet.name:
        errors.append("Missing required field: 'name'.")

    if not 1 <= sheet.level <= 20:
        errors.append(f"'level' must be an integer between 1 and 20, got {sheet.level!r}.")

    for ability in Ability:
        score = sheet.ability_scores.get(ability)
        if not isinstance(score, int) or not 1 <= score <= 30:
            errors.append(
                f"Ability score '{ability.value}' must be an integer between "
                f"1 and 30, got {score!r}."
            )

    if sheet.hp_max <= 0:
        errors.append(f"'hp_max' must be a positive integer, got {sheet.hp_max!r}.")

    if sheet.ac < 0:
        errors.append(f"'ac' must be a non-negative number, got {sheet.ac!r}.")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
