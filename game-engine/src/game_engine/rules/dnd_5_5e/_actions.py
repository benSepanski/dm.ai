"""
D&D 5.5e action availability and resolution logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.dice import roll as dice_roll, roll_dice
from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl
from game_engine.types import (
    Ability,
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

#: Actions that require the character to be able to act.
_REQUIRES_ABILITY_TO_ACT: set[ActionType] = set(_ALL_BASIC_ACTIONS)


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
    available: list[Action] = []

    for action_type in _ALL_BASIC_ACTIONS:
        if action_type in _REQUIRES_ABILITY_TO_ACT and not char.can_act:
            continue
        available.append(
            Action(
                action_type=action_type,
                actor_id=char.id,
                target_id=None,
                details={},
            )
        )

    return available


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
    action_type = action.action_type
    # Normalise string → enum
    if isinstance(action_type, str):
        try:
            action_type = ActionType(action_type)
        except ValueError:
            pass

    if action_type == ActionType.ATTACK:
        return _resolve_attack(action, combat_state)

    # Generic non-attack action — simply succeeds.
    action_type_str = (
        action_type.value if isinstance(action_type, ActionType) else str(action_type)
    )
    return ActionResult(
        success=True,
        damage=0,
        damage_type="",
        conditions_applied=[],
        flavor_text=f"{action.actor_id} uses {action_type_str}.",
        log_entry={
            "actor_id": action.actor_id,
            "action_type": action_type_str,
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
        # Will be set once we know attack_ability
        actor_ability_mod = 0

    if target is None:
        return ActionResult(
            success=False,
            damage=0,
            damage_type="",
            conditions_applied=[],
            flavor_text="No target found.",
            log_entry={
                "error": "target_not_found",
                "target_id": action.target_id,
            },
        )

    target_ac = target.ac

    # Determine attack details
    details = action.details
    if isinstance(details, AttackDetails):
        attack_ability = details.attack_ability
        damage_dice = details.damage_dice
        damage_type = details.damage_type
    elif isinstance(details, dict):
        weapon = details.get("weapon", {})
        raw_ability = weapon.get("attack_ability", "strength")
        try:
            attack_ability = Ability(raw_ability.lower())
        except (ValueError, AttributeError):
            attack_ability = Ability.STRENGTH
        damage_dice = weapon.get("damage_dice", "1d6")
        raw_dt = weapon.get("damage_type", "bludgeoning")
        try:
            damage_type = DamageType(raw_dt.lower())
        except (ValueError, AttributeError):
            damage_type = DamageType.BLUDGEONING
    else:
        attack_ability = Ability.STRENGTH
        damage_dice = "1d6"
        damage_type = DamageType.BLUDGEONING

    if actor is not None:
        actor_ability_mod = actor.ability_scores.modifier(attack_ability)
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
        total_damage = dmg1 + dmg2 + damage_mod
    else:
        raw_dmg, _ = dice_roll(damage_dice)
        total_damage = max(0, raw_dmg + damage_mod)

    # Apply damage to target in-place
    _apply_damage_impl(target, total_damage, damage_type)

    flavor = (
        f"{'CRITICAL HIT! ' if critical else ''}"
        f"{actor_name} hits {target_name} for {total_damage} "
        f"{damage_type.value if isinstance(damage_type, DamageType) else damage_type} "
        f"damage! "
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
            "damage_type": (
                damage_type.value
                if isinstance(damage_type, DamageType)
                else str(damage_type)
            ),
            "target_hp_remaining": target.hp_current,
        },
    )
