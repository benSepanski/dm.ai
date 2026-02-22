"""
D&D 5.5e Rule Engine implementation.

Implements the :class:`~game_engine.interface.RuleEngine` abstract interface
for the 2024 revision of the Dungeons & Dragons 5th Edition rules (5.5e /
"One D&D").

The engine delegates to sub-modules for cleaner organisation:
- :mod:`._checks`     — proficiency bonus, initiative, skill/ability checks
- :mod:`._damage`     — damage application with resistances/immunities
- :mod:`._conditions` — condition application and removal
- :mod:`._actions`    — available actions and action resolution
- :mod:`._validation` — character sheet validation
"""

from __future__ import annotations

from game_engine.interface import (
    Action,
    ActionResult,
    CheckResult,
    RuleEngine,
    ValidationResult,
)
from game_engine.rules.dnd_5_5e._actions import (
    _get_available_actions_impl,
    _resolve_action_impl,
)
from game_engine.rules.dnd_5_5e._checks import (
    _calc_prof_bonus,
    _roll_check_impl,
    _roll_initiative_impl,
)
from game_engine.rules.dnd_5_5e._conditions import (
    _apply_condition_impl,
    _remove_condition_impl,
)
from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl
from game_engine.rules.dnd_5_5e._validation import _validate_character_impl
from game_engine.types import (
    Ability,
    CharacterSheet,
    CombatStateData,
    Condition,
    DamageType,
    Skill,
)


class DnD55eEngine(RuleEngine):
    """Concrete rule engine for D&D 5.5e (2024 Player's Handbook).

    All methods operate on typed :class:`~game_engine.types.CharacterSheet`
    and :class:`~game_engine.types.CombatStateData` objects.
    """

    # ------------------------------------------------------------------
    # Proficiency bonus
    # ------------------------------------------------------------------

    def calculate_proficiency_bonus(self, level: int) -> int:
        """Return the proficiency bonus for *level*.

        Args:
            level: Character level (1-20).

        Returns:
            Proficiency bonus: +2 (1-4), +3 (5-8), +4 (9-12), +5 (13-16),
            +6 (17-20).

        Raises:
            ValueError: If *level* is outside 1-20.
        """
        return _calc_prof_bonus(level)

    # ------------------------------------------------------------------
    # Initiative
    # ------------------------------------------------------------------

    def roll_initiative(self, char: CharacterSheet) -> int:
        """Roll initiative: d20 + Dexterity modifier.

        Args:
            char: Character sheet.

        Returns:
            Integer initiative total (raw roll + DEX modifier).
        """
        raw = _roll_initiative_impl(char)
        return raw + char.ability_scores.modifier(Ability.DEXTERITY)

    # ------------------------------------------------------------------
    # Skill / ability checks
    # ------------------------------------------------------------------

    def roll_check(
        self,
        char: CharacterSheet,
        skill: Skill | Ability | str,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> CheckResult:
        """Roll a skill or ability check against *dc*.

        Args:
            char: Character sheet.
            skill: Skill or ability enum, or a name string (case-insensitive).
            dc: Difficulty class (integer).
            advantage: Roll twice and take the higher result.
            disadvantage: Roll twice and take the lower result.

        Returns:
            :class:`~game_engine.interface.CheckResult`.

        Raises:
            ValueError: If *skill* is not recognised.
        """
        return _roll_check_impl(char, skill, dc, advantage, disadvantage)

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------

    def apply_damage(
        self,
        target: CharacterSheet,
        damage: int,
        damage_type: DamageType,
    ) -> CharacterSheet:
        """Apply damage to *target*, respecting resistances and immunities.

        Args:
            target: Character sheet. Modified in-place and returned.
            damage: Raw damage amount.
            damage_type: :class:`~game_engine.types.DamageType` enum.

        Returns:
            Updated character sheet.
        """
        return _apply_damage_impl(target, damage, damage_type)

    # ------------------------------------------------------------------
    # Conditions
    # ------------------------------------------------------------------

    def apply_condition(
        self,
        target: CharacterSheet,
        condition: Condition | str,
        duration_rounds: int | None = None,
    ) -> CharacterSheet:
        """Apply *condition* to *target* if not immune.

        Args:
            target: Character sheet.
            condition: :class:`~game_engine.types.Condition` enum or name string.
            duration_rounds: Optional duration in rounds.

        Returns:
            Updated character sheet.
        """
        return _apply_condition_impl(target, condition, duration_rounds)

    def remove_condition(
        self,
        target: CharacterSheet,
        condition: Condition | str,
    ) -> CharacterSheet:
        """Remove *condition* from *target*.

        Args:
            target: Character sheet.
            condition: :class:`~game_engine.types.Condition` enum or name string.

        Returns:
            Updated character sheet.
        """
        return _remove_condition_impl(target, condition)

    # ------------------------------------------------------------------
    # Available actions
    # ------------------------------------------------------------------

    def get_available_actions(
        self,
        char: CharacterSheet,
        combat_state: CombatStateData,
    ) -> list[Action]:
        """Return the list of actions the character may legally take.

        Args:
            char: Character sheet.
            combat_state: Current combat state.

        Returns:
            List of :class:`~game_engine.interface.Action` objects.
        """
        return _get_available_actions_impl(char, combat_state)

    # ------------------------------------------------------------------
    # Action resolution
    # ------------------------------------------------------------------

    def resolve_action(
        self,
        action: Action,
        combat_state: CombatStateData,
    ) -> ActionResult:
        """Resolve *action* and return the outcome.

        Args:
            action: The action to resolve.
            combat_state: Combat state (may be mutated).

        Returns:
            :class:`~game_engine.interface.ActionResult`.
        """
        return _resolve_action_impl(action, combat_state)

    # ------------------------------------------------------------------
    # Character validation
    # ------------------------------------------------------------------

    def validate_character(self, sheet: CharacterSheet) -> ValidationResult:
        """Validate a character sheet for completeness and legality.

        Args:
            sheet: :class:`~game_engine.types.CharacterSheet`.

        Returns:
            :class:`~game_engine.interface.ValidationResult`.
        """
        return _validate_character_impl(sheet)
