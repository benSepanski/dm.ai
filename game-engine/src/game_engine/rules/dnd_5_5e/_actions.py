"""
D&D 5.5e action availability and resolution logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.dice import roll as dice_roll
from game_engine.core.dice import roll_dice
from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus, _roll_check_impl
from game_engine.rules.dnd_5_5e._conditions import _apply_condition_impl, _remove_condition_impl
from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl
from game_engine.types import (
    ActionType,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
    DamageType,
    Skill,
)
from game_engine.types.enums import Condition

#: Actions available to a combatant with positive HP and no incapacitating conditions.
_ALL_BASIC_ACTIONS: list[ActionType] = [
    ActionType.ATTACK,
    ActionType.CAST_SPELL,
    ActionType.DASH,
    ActionType.DISENGAGE,
    ActionType.DODGE,
    ActionType.HELP,
    ActionType.HIDE,
    ActionType.READY,
    ActionType.SEARCH,
    ActionType.USE_OBJECT,
]

_DEFAULT_ATTACK = AttackDetails()


def _get_available_actions_impl(
    char: CharacterSheet,
    combat_state: CombatStateData,
) -> list[Action]:
    """Return the list of actions the character may legally take.

    - Dead characters (3 death save failures) have no available actions.
    - Dying characters (0 HP, < 3 failures) may only make a death saving throw.
    - All other conditions (incapacitating, etc.) remove all actions.

    Args:
        char: Character sheet.
        combat_state: Current combat state (used to look up targets).

    Returns:
        List of :class:`~game_engine.interface.Action` objects.
    """
    if char.is_dead:
        return []

    if char.is_dying:
        return [Action(action_type=ActionType.DEATH_SAVE, actor_id=char.id, target_id=None)]

    if not char.can_act:
        return []

    return [
        Action(action_type=action_type, actor_id=char.id, target_id=None)
        for action_type in _ALL_BASIC_ACTIONS
    ]


def _resolve_action_impl(
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
    dispatch: dict = {
        ActionType.ATTACK: _resolve_attack,
        ActionType.DASH: _resolve_dash,
        ActionType.DEATH_SAVE: _resolve_death_save,
        ActionType.DISENGAGE: _resolve_disengage,
        ActionType.DODGE: _resolve_dodge,
        ActionType.HELP: _resolve_help,
        ActionType.HIDE: _resolve_hide,
        ActionType.READY: _resolve_ready,
        ActionType.SEARCH: _resolve_search,
        ActionType.USE_OBJECT: _resolve_use_object,
        ActionType.CAST_SPELL: _resolve_cast_spell,
    }
    handler = dispatch.get(action.action_type)
    if handler is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"Unknown action type: {action.action_type}",
            log_entry={"error": "unknown_action_type", "action_type": str(action.action_type)},
        )
    return handler(action, combat_state)


# ---------------------------------------------------------------------------
# Attack
# ---------------------------------------------------------------------------


def _resolve_attack(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Resolve an Attack action with a full to-hit and damage roll."""
    actor = combat_state.get_combatant(action.actor_id)
    target = combat_state.get_combatant(action.target_id) if action.target_id else None

    if actor is None:
        actor_name = action.actor_id
        actor_level = 1
        actor_ability_mod = 0
    else:
        actor_name = actor.name
        actor_level = actor.level
        actor_ability_mod = actor.ability_scores.modifier(
            (action.details or _DEFAULT_ATTACK).attack_ability
        )

    if target is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text="No target found.",
            log_entry={
                "error": "target_not_found",
                "target_id": action.target_id,
            },
        )

    target_ac = target.ac
    details = action.details or _DEFAULT_ATTACK
    damage_dice = details.damage_dice
    damage_type = details.damage_type
    prof_bonus = _calc_prof_bonus(actor_level)

    # Roll to hit
    attack_roll_raw, _ = roll_dice(1, 20)
    attack_total = attack_roll_raw + actor_ability_mod + prof_bonus

    hit = attack_roll_raw == 20 or attack_total >= target_ac
    critical = attack_roll_raw == 20
    target_name = target.name

    if not hit:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=damage_type,
            conditions_applied=[],
            flavor_text=(
                f"{actor_name} misses {target_name}! "
                f"(rolled {attack_roll_raw} + {actor_ability_mod + prof_bonus} "
                f"= {attack_total} vs AC {target_ac})"
            ),
            log_entry={
                "actor_id": action.actor_id,
                "target_id": action.target_id,
                "attack_roll": attack_roll_raw,
                "attack_total": attack_total,
                "target_ac": target_ac,
                "hit": False,
            },
        )

    # Roll damage (critical = roll damage dice twice, PHB 2024 p. 345)
    damage_mod = actor_ability_mod
    if critical:
        dmg1, _ = dice_roll(damage_dice)
        dmg2, _ = dice_roll(damage_dice)
        total_damage = max(0, dmg1 + dmg2 + damage_mod)
    else:
        raw_dmg, _ = dice_roll(damage_dice)
        total_damage = max(0, raw_dmg + damage_mod)

    # Apply damage to target in-place
    _apply_damage_impl(target, total_damage, damage_type, is_critical=critical)

    flavor = (
        f"{'CRITICAL HIT! ' if critical else ''}"
        f"{actor_name} hits {target_name} for {total_damage} "
        f"{damage_type.value} damage! "
        f"(roll {attack_roll_raw} + {actor_ability_mod + prof_bonus} "
        f"= {attack_total} vs AC {target_ac})"
    )

    return ActionResult(
        success=True,
        damage=total_damage,
        damage_type=damage_type,
        conditions_applied=[],
        flavor_text=flavor,
        log_entry={
            "actor_id": action.actor_id,
            "target_id": action.target_id,
            "attack_roll": attack_roll_raw,
            "attack_total": attack_total,
            "target_ac": target_ac,
            "hit": True,
            "critical": critical,
            "damage": total_damage,
            "damage_type": damage_type.value,
            "target_hp_remaining": target.hp_current,
        },
    )


# ---------------------------------------------------------------------------
# Death Saving Throw (PHB 2024 p. 369)
# ---------------------------------------------------------------------------


def _resolve_death_save(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Roll a death saving throw for a dying character.

    - Roll 1d20 (no modifiers).
    - Natural 20: regain 1 HP and remove UNCONSCIOUS condition.
    - Natural 1: suffer 2 death save failures (counts as 2 failures).
    - 10–19: 1 success.
    - 2–9: 1 failure.
    - 3 successes: stable (stop rolling, remain unconscious until healed).
    - 3 failures: dead.
    """
    actor = combat_state.get_combatant(action.actor_id)
    if actor is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"Character '{action.actor_id}' not found.",
            log_entry={"error": "actor_not_found", "actor_id": action.actor_id},
        )

    if actor.hp_current > 0:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"{actor.name} is not dying and does not need to make a death save.",
            log_entry={"error": "not_dying", "actor_id": action.actor_id},
        )

    roll, _ = roll_dice(1, 20)
    actor_name = actor.name

    # Natural 20: miraculous recovery
    if roll == 20:
        actor.hp_current = 1
        actor.death_save_successes = 0
        actor.death_save_failures = 0
        _remove_condition_impl(actor, Condition.UNCONSCIOUS)
        return ActionResult(
            success=True,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"Natural 20! {actor_name} miraculously regains 1 HP and stabilizes!",
            log_entry={
                "actor_id": action.actor_id,
                "action_type": ActionType.DEATH_SAVE.value,
                "roll": roll,
                "outcome": "miraculous_recovery",
                "hp_current": actor.hp_current,
            },
        )

    # Natural 1: 2 failures
    if roll == 1:
        actor.death_save_failures = min(3, actor.death_save_failures + 2)
        failures_added = 2
    elif roll >= 10:
        actor.death_save_successes = min(3, actor.death_save_successes + 1)
        failures_added = 0
    else:
        actor.death_save_failures = min(3, actor.death_save_failures + 1)
        failures_added = 1

    # Check outcomes
    if actor.death_save_failures >= 3:
        outcome = "dead"
        flavor = f"{actor_name} has died. (rolled {roll})"
        success = False
    elif actor.death_save_successes >= 3:
        outcome = "stable"
        flavor = f"{actor_name} is now stable! (rolled {roll}, 3 successes)"
        success = True
    elif roll >= 10:
        outcome = "success"
        flavor = (
            f"{actor_name} passes a death save! "
            f"(rolled {roll}, {actor.death_save_successes}/3 successes, "
            f"{actor.death_save_failures}/3 failures)"
        )
        success = True
    else:
        outcome = "failure"
        nat_one_note = " (natural 1 — 2 failures!)" if failures_added == 2 else ""
        flavor = (
            f"{actor_name} fails a death save{nat_one_note}. "
            f"(rolled {roll}, {actor.death_save_successes}/3 successes, "
            f"{actor.death_save_failures}/3 failures)"
        )
        success = False

    return ActionResult(
        success=success,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=flavor,
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.DEATH_SAVE.value,
            "roll": roll,
            "outcome": outcome,
            "death_save_successes": actor.death_save_successes,
            "death_save_failures": actor.death_save_failures,
        },
    )


# ---------------------------------------------------------------------------
# Dash (PHB 2024 p. 192)
# ---------------------------------------------------------------------------


def _resolve_dash(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Dash: gain extra movement equal to your speed until end of turn."""
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id
    extra_movement = actor.speed if actor else 30

    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=f"{actor_name} dashes, gaining {extra_movement} ft. of extra movement.",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.DASH.value,
            "extra_movement": extra_movement,
            "dash_active": True,
        },
    )


# ---------------------------------------------------------------------------
# Disengage (PHB 2024 p. 192)
# ---------------------------------------------------------------------------


def _resolve_disengage(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Disengage: movement does not provoke opportunity attacks this turn."""
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id

    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=f"{actor_name} disengages — movement won't provoke opportunity attacks.",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.DISENGAGE.value,
            "disengage_active": True,
        },
    )


# ---------------------------------------------------------------------------
# Dodge (PHB 2024 p. 192)
# ---------------------------------------------------------------------------


def _resolve_dodge(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Dodge: attacks against this character have disadvantage until start of next turn.

    Also grants advantage on Dexterity saving throws.
    """
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id

    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=(
            f"{actor_name} takes the Dodge action — attacks against them have "
            f"disadvantage and they have advantage on Dex saves until their next turn."
        ),
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.DODGE.value,
            "dodge_active": True,
        },
    )


# ---------------------------------------------------------------------------
# Help (PHB 2024 p. 192)
# ---------------------------------------------------------------------------


def _resolve_help(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Help: grant a friendly creature advantage on their next attack roll or ability check."""
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id

    if action.target_id is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"{actor_name} tried to Help but no target was specified.",
            log_entry={"error": "no_target", "actor_id": action.actor_id},
        )

    target = combat_state.get_combatant(action.target_id)
    target_name = target.name if target else action.target_id

    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=(
            f"{actor_name} helps {target_name}! "
            f"{target_name} has advantage on their next attack roll or ability check."
        ),
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.HELP.value,
            "target_id": action.target_id,
            "advantage_granted": True,
        },
    )


# ---------------------------------------------------------------------------
# Hide (PHB 2024 p. 177)
# ---------------------------------------------------------------------------


def _resolve_hide(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Hide: make a Dexterity (Stealth) check to become hidden.

    The Stealth roll total is returned in the log for the combat manager
    to compare against enemy passive Perception scores.  If the roll meets
    or exceeds DC 15 (the default), the INVISIBLE condition is applied to
    represent being hidden.
    """
    actor = combat_state.get_combatant(action.actor_id)
    if actor is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"Character '{action.actor_id}' not found.",
            log_entry={"error": "actor_not_found", "actor_id": action.actor_id},
        )

    # Default DC 15 — typical enemy passive Perception
    _HIDE_DC = 15
    check = _roll_check_impl(actor, Skill.STEALTH, dc=_HIDE_DC)
    actor_name = actor.name

    conditions_applied: list[Condition] = []
    if check.success:
        _apply_condition_impl(actor, Condition.INVISIBLE)
        conditions_applied = [Condition.INVISIBLE]
        flavor = (
            f"{actor_name} hides! (Stealth {check.total} vs DC {_HIDE_DC}) "
            f"They are now hidden."
        )
    else:
        flavor = f"{actor_name} fails to hide. (Stealth {check.total} vs DC {_HIDE_DC})"

    return ActionResult(
        success=check.success,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=conditions_applied,
        flavor_text=flavor,
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.HIDE.value,
            "stealth_roll": check.roll,
            "stealth_total": check.total,
            "hide_dc": _HIDE_DC,
            "hidden": check.success,
        },
    )


# ---------------------------------------------------------------------------
# Ready (PHB 2024 p. 193)
# ---------------------------------------------------------------------------


def _resolve_ready(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Ready: hold an action until a specified trigger occurs.

    The trigger description and readied action type are stored in the log
    for the combat manager to evaluate on subsequent turns.
    """
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id

    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=f"{actor_name} readies an action, waiting for the right moment.",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.READY.value,
            "readied": True,
        },
    )


# ---------------------------------------------------------------------------
# Search (PHB 2024 p. 193)
# ---------------------------------------------------------------------------


def _resolve_search(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Search: make a Wisdom (Perception) or Intelligence (Investigation) check.

    Defaults to Perception.  The log entry includes the roll total for the
    DM / combat manager to interpret.
    """
    actor = combat_state.get_combatant(action.actor_id)
    if actor is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type=DamageType.BLUDGEONING,
            conditions_applied=[],
            flavor_text=f"Character '{action.actor_id}' not found.",
            log_entry={"error": "actor_not_found", "actor_id": action.actor_id},
        )

    _SEARCH_DC = 15
    check = _roll_check_impl(actor, Skill.PERCEPTION, dc=_SEARCH_DC)
    actor_name = actor.name
    result_note = "notices something!" if check.success else "finds nothing obvious."

    return ActionResult(
        success=check.success,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=(
            f"{actor_name} searches their surroundings and {result_note} "
            f"(Perception {check.total})"
        ),
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.SEARCH.value,
            "perception_roll": check.roll,
            "perception_total": check.total,
            "search_dc": _SEARCH_DC,
            "found": check.success,
        },
    )


# ---------------------------------------------------------------------------
# Use Object (PHB 2024 p. 193)
# ---------------------------------------------------------------------------


def _resolve_use_object(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Use Object: interact with a second object during your turn."""
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id

    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=f"{actor_name} uses an object.",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.USE_OBJECT.value,
        },
    )


# ---------------------------------------------------------------------------
# Cast Spell (stub — full spell system is a future feature)
# ---------------------------------------------------------------------------


def _resolve_cast_spell(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Cast Spell: placeholder — full spell system not yet implemented."""
    actor = combat_state.get_combatant(action.actor_id)
    actor_name = actor.name if actor else action.actor_id

    return ActionResult(
        success=False,
        damage=0,
        damage_type=DamageType.FORCE,
        conditions_applied=[],
        flavor_text=f"{actor_name} attempts to cast a spell (spell system not yet implemented).",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": ActionType.CAST_SPELL.value,
            "error": "spell_system_not_implemented",
        },
    )
