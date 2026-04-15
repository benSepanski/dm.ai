"""
D&D 5.5e action availability and resolution logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.dice import roll as dice_roll
from game_engine.core.dice import roll_dice
from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl
from game_engine.types import (
    ActionType,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
    DamageType,
)

#: All basic combat actions available in D&D 5.5e.
_ALL_BASIC_ACTIONS: list[ActionType] = [
    ActionType.ATTACK,
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

    Actions are filtered by the character's current conditions.

    Args:
        char: Character sheet.
        combat_state: Current combat state (used to look up targets).

    Returns:
        List of :class:`~game_engine.interface.Action` objects.
    """
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

    Currently handles the **Attack** action with a full to-hit and damage
    roll.  Other action types are logged as successful with 0 damage.

    Args:
        action: The action to resolve.
        combat_state: Combat state (may be mutated).

    Returns:
        :class:`~game_engine.interface.ActionResult`.
    """
    if action.action_type == ActionType.ATTACK:
        return _resolve_attack(action, combat_state)

    # Generic non-attack action — simply succeeds.
    return ActionResult(
        success=True,
        damage=0,
        damage_type=DamageType.BLUDGEONING,
        conditions_applied=[],
        flavor_text=f"{action.actor_id} uses {action.action_type.value}.",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": action.action_type.value,
            "target_id": action.target_id,
        },
    )


def _resolve_attack(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Resolve an Attack action."""
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

    # Roll damage
    damage_mod = actor_ability_mod
    if critical:
        dmg1, _ = dice_roll(damage_dice)
        dmg2, _ = dice_roll(damage_dice)
        total_damage = max(0, dmg1 + dmg2 + damage_mod)
    else:
        raw_dmg, _ = dice_roll(damage_dice)
        total_damage = max(0, raw_dmg + damage_mod)

    # Apply damage to target in-place
    _apply_damage_impl(target, total_damage, damage_type)

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
