"""
D&D 5.5e action availability, action economy, and non-attack resolution.

Attack resolution lives in :mod:`._attacks`.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from typing import Any

from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._attacks import _resolve_attack
from game_engine.rules.dnd_5_5e._checks import _roll_check_impl
from game_engine.types import (
    ActionType,
    CharacterSheet,
    CombatStateData,
    Skill,
    TurnState,
)

# Actions every conscious creature can always take (2024 PHB).
_ALWAYS_AVAILABLE: list[ActionType] = [
    ActionType.ATTACK,
    ActionType.DASH,
    ActionType.DISENGAGE,
    ActionType.DODGE,
    ActionType.HELP,
    ActionType.HIDE,
    ActionType.INFLUENCE,
    ActionType.READY,
    ActionType.SEARCH,
    ActionType.STUDY,
    ActionType.UTILIZE,
]

# DC for the Hide action's Dexterity (Stealth) check (2024 PHB).
_HIDE_DC = 15


def _get_available_actions_impl(
    char: CharacterSheet,
    combat_state: CombatStateData,
) -> list[Action]:
    """Return the list of actions the character may legally take.

    The Magic action is included only for characters with cantrips known or
    spells prepared. Returned ``Action`` objects have ``target_id=None``; the
    caller supplies a concrete target on submission.

    Args:
        char: Character sheet.
        combat_state: Current combat state.

    Returns:
        List of :class:`~game_engine.interface.Action` objects.
    """
    if not char.can_act:
        return []

    available = list(_ALWAYS_AVAILABLE)
    if char.cantrips or char.prepared_spells or char.known_spells:
        available.append(ActionType.MAGIC)

    return [
        Action(action_type=action_type, actor_id=char.id, target_id=None)
        for action_type in available
    ]


def _begin_turn_impl(char: CharacterSheet, combat_state: CombatStateData) -> TurnState:
    """Reset *char*'s action economy at the start of their turn."""
    return combat_state.reset_turn(char.id)


def _simple_result(
    action: Action, success: bool, flavor: str, extra: dict[str, Any] | None = None
) -> ActionResult:
    log: dict[str, Any] = {
        "actor_id": action.actor_id,
        "action_type": action.action_type.value,
        "target_id": action.target_id,
        "success": success,
    }
    if extra:
        log.update(extra)
    return ActionResult(
        success=success,
        damage=0,
        damage_type=None,
        conditions_applied=[],
        flavor_text=flavor,
        log_entry=log,
    )


def _resolve_action_impl(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Resolve *action*, enforcing the action/bonus-action economy.

    An off-hand attack (``details.is_offhand``) consumes the bonus action;
    every other action type consumes the action. The Magic action is
    validated and resolved by the spellcasting module — here it only
    consumes the action slot.

    Args:
        action: The action to resolve.
        combat_state: Combat state (may be mutated).

    Returns:
        :class:`~game_engine.interface.ActionResult`.
    """
    actor = combat_state.get_combatant(action.actor_id)
    if actor is not None and not actor.can_act:
        return _simple_result(action, False, f"{actor.name} can't act.", {"error": "cannot_act"})

    ts = combat_state.turn_state_for(action.actor_id)
    uses_bonus_action = (
        action.action_type is ActionType.ATTACK
        and action.details is not None
        and action.details.is_offhand
    )
    if uses_bonus_action:
        if ts.bonus_action_used:
            return _simple_result(
                action, False, "Bonus action already used.", {"error": "bonus_action_used"}
            )
        ts.bonus_action_used = True
    else:
        if ts.action_used:
            return _simple_result(
                action, False, "Action already used this turn.", {"error": "action_used"}
            )
        ts.action_used = True

    if action.action_type is ActionType.ATTACK:
        return _resolve_attack(action, combat_state)
    return _resolve_non_attack(action, actor, combat_state, ts)


def _resolve_non_attack(
    action: Action,
    actor: CharacterSheet | None,
    combat_state: CombatStateData,
    ts: TurnState,
) -> ActionResult:
    """Resolve the non-attack 2024 actions."""
    name = actor.name if actor else action.actor_id

    if action.action_type is ActionType.DASH:
        ts.dashing = True
        speed = actor.effective_speed if actor else 30
        return _simple_result(
            action, True, f"{name} dashes (+{speed} ft of movement).", {"extra_movement": speed}
        )
    if action.action_type is ActionType.DISENGAGE:
        ts.disengaging = True
        return _simple_result(
            action, True, f"{name} disengages; their movement provokes no opportunity attacks."
        )
    if action.action_type is ActionType.DODGE:
        ts.dodging = True
        return _simple_result(
            action,
            True,
            f"{name} dodges; attacks against them have disadvantage until their next turn.",
        )
    if action.action_type is ActionType.HELP:
        if action.target_id:
            combat_state.turn_state_for(action.target_id).helped = True
        return _simple_result(
            action, True, f"{name} helps an ally, granting advantage on their next roll."
        )
    if action.action_type is ActionType.HIDE and actor is not None:
        check = _roll_check_impl(actor, Skill.STEALTH, _HIDE_DC)
        ts.hidden = check.success
        outcome = "hides successfully" if check.success else "fails to hide"
        return _simple_result(
            action,
            check.success,
            f"{name} {outcome} (Stealth {check.total} vs DC {_HIDE_DC}).",
            {"stealth_total": check.total, "dc": _HIDE_DC},
        )

    # Influence / Magic / Ready / Search / Study / Utilize / Hide-without-actor:
    # generic success; detailed resolution happens at the orchestration layer
    # (Influence uses a CHA check against the monster's Influence DC; Magic is
    # resolved by the spellcasting module).
    return _simple_result(action, True, f"{name} uses {action.action_type.value}.")


def provokes_opportunity_attack(mover_id: str, combat_state: CombatStateData) -> bool:
    """True when a creature leaving reach would provoke an opportunity attack.

    Disengaging suppresses opportunity attacks for the rest of the turn.
    """
    return not combat_state.turn_state_for(mover_id).disengaging
