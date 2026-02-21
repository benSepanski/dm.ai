"""
D&D 5.5e character sheet validation logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.interface import ValidationResult
from game_engine.types import Ability, CharacterClass, CharacterSheet

#: Valid D&D race/species names (non-exhaustive sample).
_VALID_RACES: frozenset[str] = frozenset(
    {
        "Aasimar",
        "Dragonborn",
        "Dwarf",
        "Elf",
        "Gnome",
        "Goliath",
        "Half-Elf",
        "Half-Orc",
        "Halfling",
        "Human",
        "Orc",
        "Tiefling",
        "Custom",
        "Other",
    }
)


def _validate_character_impl(sheet: CharacterSheet | dict) -> ValidationResult:
    """Validate a character sheet for completeness and legality.

    Accepts either a typed :class:`~game_engine.types.CharacterSheet` or a
    raw dict for backward compatibility.

    Args:
        sheet: Character sheet or raw dict to validate.

    Returns:
        :class:`~game_engine.interface.ValidationResult`.
    """
    if isinstance(sheet, CharacterSheet):
        return _validate_typed(sheet)
    return _validate_dict(sheet)


def _validate_typed(sheet: CharacterSheet) -> ValidationResult:
    """Validate a typed :class:`~game_engine.types.CharacterSheet`."""
    errors: list[str] = []

    if not sheet.id:
        errors.append("Missing required field: 'id'.")
    if not sheet.name:
        errors.append("Missing required field: 'name'.")

    if not 1 <= sheet.level <= 20:
        errors.append(
            f"'level' must be an integer between 1 and 20, got {sheet.level!r}."
        )

    # Ability scores
    for ability in Ability:
        score = sheet.ability_scores.get(ability)
        if not isinstance(score, int) or not 1 <= score <= 30:
            errors.append(
                f"Ability score '{ability.value}' must be an integer between "
                f"1 and 30, got {score!r}."
            )

    if sheet.hp_max <= 0:
        errors.append(
            f"'hp_max' must be a positive integer, got {sheet.hp_max!r}."
        )

    if sheet.ac < 0:
        errors.append(f"'ac' must be a non-negative number, got {sheet.ac!r}.")

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def _validate_dict(sheet: dict) -> ValidationResult:
    """Validate a raw character sheet dict (legacy path)."""
    errors: list[str] = []

    for field_name in ("id", "name", "level"):
        if field_name not in sheet:
            errors.append(f"Missing required field: '{field_name}'.")

    level = sheet.get("level")
    if level is not None:
        if not isinstance(level, int) or not 1 <= level <= 20:
            errors.append(
                f"'level' must be an integer between 1 and 20, got {level!r}."
            )

    char_class = sheet.get("class")
    if char_class is None:
        errors.append("Missing required field: 'class'.")
    else:
        valid_classes = {c.value for c in CharacterClass}
        if char_class not in valid_classes:
            errors.append(
                f"Unknown class {char_class!r}.  "
                f"Valid classes: {sorted(valid_classes)}."
            )

    ability_scores = sheet.get("ability_scores")
    if ability_scores is None:
        errors.append("Missing required field: 'ability_scores'.")
    elif not isinstance(ability_scores, dict):
        errors.append("'ability_scores' must be a dict.")
    else:
        for ability in Ability:
            score = ability_scores.get(ability.value)
            if score is None:
                errors.append(f"Missing ability score: '{ability.value}'.")
            elif not isinstance(score, int) or not 1 <= score <= 30:
                errors.append(
                    f"Ability score '{ability.value}' must be an integer between "
                    f"1 and 30, got {score!r}."
                )

    hp_max = sheet.get("hp_max")
    if hp_max is None:
        errors.append("Missing required field: 'hp_max'.")
    elif not isinstance(hp_max, int) or hp_max <= 0:
        errors.append(f"'hp_max' must be a positive integer, got {hp_max!r}.")

    ac = sheet.get("ac")
    if ac is None:
        errors.append("Missing required field: 'ac'.")
    elif not isinstance(ac, (int, float)) or ac < 0:
        errors.append(f"'ac' must be a non-negative number, got {ac!r}.")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
