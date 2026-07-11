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
    DeathSaveResult,
    RuleEngine,
    SaveResult,
    ValidationResult,
)
from game_engine.rules.dnd_5_5e._actions import (
    _begin_turn_impl,
    _get_available_actions_impl,
    _resolve_action_impl,
)
from game_engine.rules.dnd_5_5e._checks import (
    _calc_prof_bonus,
    _passive_score_impl,
    _roll_check_impl,
    _roll_initiative_impl,
)
from game_engine.rules.dnd_5_5e._conditions import (
    _apply_condition_impl,
    _remove_condition_impl,
    _tick_condition_durations_impl,
)
from game_engine.rules.dnd_5_5e._damage import (
    _apply_damage_impl,
    _apply_healing_impl,
    _grant_temp_hp_impl,
    concentration_save_dc,
)
from game_engine.rules.dnd_5_5e._death import _roll_death_save_impl, _stabilize_impl
from game_engine.rules.dnd_5_5e._saves import _roll_saving_throw_impl
from game_engine.rules.dnd_5_5e._validation import _validate_character_impl
from game_engine.types import (
    Ability,
    CharacterSheet,
    CombatStateData,
    Condition,
    DamageType,
    Skill,
    TurnState,
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
        """Roll initiative: d20 + Dexterity modifier + exhaustion penalty.

        Args:
            char: Character sheet.

        Returns:
            Integer initiative total (raw roll + DEX modifier + d20_modifier).
        """
        raw = _roll_initiative_impl(char)
        return raw + char.ability_scores.modifier(Ability.DEXTERITY) + char.d20_modifier

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
        turn_state: TurnState | None = None,
    ) -> CheckResult:
        """Roll a skill or ability check against *dc*.

        Args:
            char: Character sheet.
            skill: Skill or ability enum, or a name string (case-insensitive).
            dc: Difficulty class (integer).
            advantage: Roll twice and take the higher result.
            disadvantage: Roll twice and take the lower result.
            turn_state: The roller's :class:`TurnState`, if this check happens
                in combat. A pending Help grant (``turn_state.helped``) adds
                advantage and is consumed by the roll.

        Returns:
            :class:`~game_engine.interface.CheckResult`.

        Raises:
            ValueError: If *skill* is not recognised.
        """
        return _roll_check_impl(char, skill, dc, advantage, disadvantage, turn_state)

    # ------------------------------------------------------------------
    # Saving throws & death saves
    # ------------------------------------------------------------------

    def roll_saving_throw(
        self,
        char: CharacterSheet,
        ability: Ability,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> SaveResult:
        """Roll a saving throw against *dc* (2024 rules).

        Applies save proficiency, condition auto-failures (e.g. paralyzed
        creatures auto-fail STR/DEX saves), restrained's disadvantage on
        DEX saves, and exhaustion's flat d20 penalty.

        Args:
            char: Character sheet.
            ability: The ability being saved with.
            dc: Difficulty class.
            advantage: Roll twice, take higher.
            disadvantage: Roll twice, take lower.

        Returns:
            :class:`~game_engine.interface.SaveResult`.
        """
        return _roll_saving_throw_impl(char, ability, dc, advantage, disadvantage)

    def roll_death_save(self, char: CharacterSheet) -> DeathSaveResult:
        """Roll a death saving throw for a dying character.

        Args:
            char: Character sheet (must be at 0 HP, not stable, not dead).

        Returns:
            :class:`~game_engine.interface.DeathSaveResult`.

        Raises:
            ValueError: If the character is not dying.
        """
        return _roll_death_save_impl(char)

    def stabilize(self, char: CharacterSheet) -> CharacterSheet:
        """Stabilize a dying character (e.g. DC 10 Medicine check succeeded).

        Args:
            char: Character sheet. Modified in-place and returned.

        Returns:
            Updated character sheet.
        """
        return _stabilize_impl(char)

    # ------------------------------------------------------------------
    # Damage & healing
    # ------------------------------------------------------------------

    def apply_healing(self, target: CharacterSheet, amount: int) -> CharacterSheet:
        """Restore hit points (capped at max; wakes a dying character).

        Args:
            target: Character sheet. Modified in-place and returned.
            amount: Hit points to restore.

        Returns:
            Updated character sheet.
        """
        return _apply_healing_impl(target, amount)

    def grant_temp_hp(self, target: CharacterSheet, amount: int) -> CharacterSheet:
        """Grant temporary hit points (doesn't stack — larger pool wins).

        Args:
            target: Character sheet. Modified in-place and returned.
            amount: Temporary hit points to grant.

        Returns:
            Updated character sheet.
        """
        return _grant_temp_hp_impl(target, amount)

    def concentration_save_dc(self, damage: int) -> int:
        """Return the CON save DC to keep concentration after taking damage.

        Args:
            damage: Damage dealt by the triggering event.

        Returns:
            ``max(10, damage // 2)``.
        """
        return concentration_save_dc(damage)

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

    def tick_condition_durations(self, target: CharacterSheet) -> CharacterSheet:
        """Decrement timed condition durations at end of a combatant's turn.

        Conditions whose remaining duration reaches zero are removed. Call once
        per combatant per turn (at ``next_turn`` time).

        Args:
            target: Character sheet.

        Returns:
            Updated character sheet.
        """
        return _tick_condition_durations_impl(target)

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
    # Turn management & passive scores
    # ------------------------------------------------------------------

    def begin_turn(self, char: CharacterSheet, combat_state: CombatStateData) -> TurnState:
        """Reset *char*'s action economy at the start of their turn.

        Args:
            char: Character sheet.
            combat_state: Current combat state.

        Returns:
            The fresh :class:`~game_engine.types.TurnState`.
        """
        return _begin_turn_impl(char, combat_state)

    def passive_score(self, char: CharacterSheet, skill: Skill) -> int:
        """Return the passive score for *skill* (10 + check modifiers).

        Args:
            char: Character sheet.
            skill: The skill (e.g. ``Skill.PERCEPTION``).

        Returns:
            Integer passive score.
        """
        return _passive_score_impl(char, skill)

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
