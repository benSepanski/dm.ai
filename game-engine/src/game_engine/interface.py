"""
Rule-agnostic interfaces for the RPG game engine.

This module defines the abstract base class RuleEngine and the data classes
used to communicate results between the engine and the game layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CheckResult:
    """Result of a skill or ability check.

    Attributes:
        success: Whether the check met or exceeded the DC.
        roll: The raw d20 roll (before modifiers).
        total: The final total (roll + modifiers).
        dc: The difficulty class that was set for this check.
        margin: total - dc; positive means success by that amount.
    """
    success: bool
    roll: int
    total: int
    dc: int
    margin: int


@dataclass
class ActionResult:
    """Result of resolving a combat or non-combat action.

    Attributes:
        success: Whether the action succeeded (e.g. attack hit).
        damage: Total damage dealt (0 if not applicable).
        damage_type: The type of damage dealt (e.g. "fire", "slashing").
        conditions_applied: Names of any conditions applied to the target.
        flavor_text: Human-readable narrative of what happened.
        log_entry: Structured dict suitable for the combat log / API.
    """
    success: bool
    damage: int
    damage_type: str
    conditions_applied: list[str]
    flavor_text: str
    log_entry: dict


@dataclass
class ValidationResult:
    """Result of validating a character sheet.

    Attributes:
        valid: Whether the sheet passed all validation rules.
        errors: List of human-readable error messages (empty when valid).
    """
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class Action:
    """A player or NPC action to be resolved by the rule engine.

    Attributes:
        action_type: Type of action (e.g. "Attack", "Dash", "CastSpell").
        actor_id: ID of the character performing the action.
        target_id: ID of the target character, or None for untargeted actions.
        details: Rule-specific payload (weapon info, spell name, etc.).
    """
    action_type: str
    actor_id: str
    target_id: str | None
    details: dict = field(default_factory=dict)


class RuleEngine(ABC):
    """Abstract base class for rule system implementations.

    Every rule system (D&D 5.5e, Pathfinder, etc.) must implement all of
    these methods.  The engine operates on plain dicts representing character
    sheets and combat state so that no rule-specific classes bleed into the
    generic game layer.
    """

    @abstractmethod
    def roll_check(
        self,
        char: dict,
        skill: str,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> CheckResult:
        """Roll a skill or ability check against a DC.

        Args:
            char: Character sheet dict.
            skill: Skill or ability name (e.g. "Perception", "Strength").
            dc: Difficulty class to meet or exceed.
            advantage: Roll two dice and take the higher.
            disadvantage: Roll two dice and take the lower.

        Returns:
            CheckResult with roll details and success flag.
        """

    @abstractmethod
    def apply_damage(self, target: dict, damage: int, damage_type: str) -> dict:
        """Apply damage to a character, accounting for resistances/immunities.

        Args:
            target: Character sheet dict (modified in place and returned).
            damage: Raw damage amount before resistance calculations.
            damage_type: Damage type string (e.g. "fire", "piercing").

        Returns:
            Updated character sheet dict.
        """

    @abstractmethod
    def apply_condition(
        self,
        target: dict,
        condition: str,
        duration_rounds: int | None = None,
    ) -> dict:
        """Apply a condition to a character.

        Args:
            target: Character sheet dict.
            condition: Condition name (e.g. "poisoned", "stunned").
            duration_rounds: How many rounds the condition lasts; None = indefinite.

        Returns:
            Updated character sheet dict.
        """

    @abstractmethod
    def remove_condition(self, target: dict, condition: str) -> dict:
        """Remove a condition from a character.

        Args:
            target: Character sheet dict.
            condition: Condition name to remove.

        Returns:
            Updated character sheet dict.
        """

    @abstractmethod
    def get_available_actions(
        self, char: dict, combat_state: dict
    ) -> list[Action]:
        """Return the list of actions available to a character this turn.

        Args:
            char: Character sheet dict.
            combat_state: Current combat state dict.

        Returns:
            List of Action objects the character may legally take.
        """

    @abstractmethod
    def resolve_action(
        self, action: Action, combat_state: dict
    ) -> ActionResult:
        """Resolve an action and return the outcome.

        Args:
            action: The Action to resolve.
            combat_state: Current combat state dict (may be mutated).

        Returns:
            ActionResult describing what happened.
        """

    @abstractmethod
    def roll_initiative(self, char: dict) -> int:
        """Roll initiative for a character.

        Args:
            char: Character sheet dict.

        Returns:
            Integer initiative total.
        """

    @abstractmethod
    def validate_character(self, sheet: dict) -> ValidationResult:
        """Validate a character sheet for completeness and legality.

        Args:
            sheet: Character sheet dict to validate.

        Returns:
            ValidationResult with valid flag and any error messages.
        """

    @abstractmethod
    def calculate_proficiency_bonus(self, level: int) -> int:
        """Return the proficiency bonus for the given character level.

        Args:
            level: Character level (1-20).

        Returns:
            Integer proficiency bonus.
        """
