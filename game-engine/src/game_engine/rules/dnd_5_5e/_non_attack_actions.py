"""
D&D 5.5e non-attack action resolution (Dash, Disengage, Dodge, Help, Hide,
Ready, and the generic Influence/Magic/Search/Study/Utilize success path).

Split out of :mod:`._actions` (which retains action availability and the
attack/reaction action-economy gating) to stay under the repo's 400-LoC
file-length guideline. ``_simple_result`` lives here rather than in
``_actions`` so both modules can depend on it without a import cycle.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from typing import Any

from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._checks import _roll_check_impl
from game_engine.rules.dnd_5_5e._equipment import effective_speed as _armor_effective_speed
from game_engine.rules.dnd_5_5e._equipment import has_stealth_disadvantage
from game_engine.types import (
    ActionType,
    CharacterSheet,
    CombatStateData,
    ReadiedAction,
    Skill,
    TurnState,
)

# DC for the Hide action's Dexterity (Stealth) check (2024 PHB).
_HIDE_DC = 15


def _effective_speed(actor: CharacterSheet, ts: TurnState) -> int:
    """*actor*'s speed after exhaustion/speed-zero conditions, under-Strength
    armor, and Slow mastery.

    ``CharacterSheet.effective_speed`` is a pure sheet property with no
    visibility into combat state or the rules-layer armor registry, so the
    Strength-minimum armor penalty (D2, EQP-04, via
    ``_equipment.effective_speed``) and the Slow mastery's -10 ft (ACT-07,
    granted on the *target's* :class:`TurnState` via
    :meth:`CombatStateData.grant_slow`) are both applied here instead.
    """
    speed = _armor_effective_speed(actor)
    if ts.slowed:
        speed = max(0, speed - 10)
    return speed


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


def _resolve_non_attack(
    action: Action,
    actor: CharacterSheet,
    combat_state: CombatStateData,
    ts: TurnState,
) -> ActionResult:
    """Resolve the non-attack 2024 actions."""
    name = actor.name

    if action.action_type is ActionType.DASH:
        ts.dashing = True
        speed = _effective_speed(actor, ts)
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
            combat_state.grant_help(action.actor_id, action.target_id)
        return _simple_result(
            action, True, f"{name} helps an ally, granting advantage on their next roll."
        )
    if action.action_type is ActionType.HIDE:
        # D2/EQP-02: noisy armor imposes disadvantage on the Stealth check.
        check = _roll_check_impl(
            actor,
            Skill.STEALTH,
            _HIDE_DC,
            disadvantage=has_stealth_disadvantage(actor),
            turn_state=ts,
        )
        ts.hidden = check.success
        outcome = "hides successfully" if check.success else "fails to hide"
        return _simple_result(
            action,
            check.success,
            f"{name} {outcome} (Stealth {check.total} vs DC {_HIDE_DC}).",
            {"stealth_total": check.total, "dc": _HIDE_DC},
        )

    if action.action_type is ActionType.READY:
        ts.readied = ReadiedAction(
            trigger=action.readied_trigger or "unspecified trigger",
            target_id=action.target_id,
            details=action.details,
        )
        return _simple_result(
            action,
            True,
            f"{name} readies an action, waiting: {ts.readied.trigger}",
            {"trigger": ts.readied.trigger},
        )

    # Influence / Magic / Search / Study / Utilize: generic success; detailed
    # resolution happens at the orchestration layer (Influence uses a CHA
    # check against the monster's Influence DC; Magic is resolved by the
    # spellcasting module).
    return _simple_result(action, True, f"{name} uses {action.action_type.value}.")
