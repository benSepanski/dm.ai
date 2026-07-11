"""
D&D 5.5e action availability, action economy, and non-attack resolution.

Attack resolution lives in :mod:`._attacks`; reaction resolution
(opportunity attacks, triggering a stored Ready) lives in :mod:`._reactions`.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from typing import Any

from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._attacks import _has_mastery, _resolve_attack, _validate_attack
from game_engine.rules.dnd_5_5e._checks import _roll_check_impl
from game_engine.rules.dnd_5_5e._reactions import (
    resolve_opportunity_attack,
    resolve_readied_action,
)
from game_engine.rules.dnd_5_5e.data.class_features import CLASS_PROGRESSIONS
from game_engine.types import (
    ActionType,
    CharacterSheet,
    ClassLevelEntry,
    CombatStateData,
    ReadiedAction,
    Skill,
    TurnState,
    UnarmedStrikeOption,
    WeaponMastery,
    WeaponProperty,
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

    The Magic action is included only for characters with spells known or
    prepared. Returned ``Action`` objects have ``target_id=None``; the
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
    if char.prepared_spells or char.known_spells:
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


def _attacks_per_action(actor: CharacterSheet) -> int:
    """How many attacks *actor* makes per Attack action (2024 Extra Attack).

    Reads the ``attacks_granted`` field of each class's "Extra Attack"
    feature (``data/class_features/*.py``) through the actor's level in
    that class. Multiclass characters take the single best tier available
    from any one class — 2024 PHB: Extra Attack features don't stack, so a
    Fighter 11/Barbarian 5 attacks 3 times (the Fighter tier), not 5.
    """
    class_levels = actor.class_levels or [
        ClassLevelEntry(
            character_class=actor.char_class, level=actor.level, subclass=actor.subclass
        )
    ]
    best = 1
    for entry in class_levels:
        progression = CLASS_PROGRESSIONS.get(entry.character_class)
        if progression is None:
            continue
        subclass = entry.subclass or actor.subclass
        for feature in progression.features_through_level(entry.level, subclass):
            if feature.attacks_granted is not None:
                best = max(best, feature.attacks_granted)
    return best


def _resolve_action_impl(
    action: Action,
    combat_state: CombatStateData,
) -> ActionResult:
    """Resolve *action*, enforcing the action/bonus-action economy.

    An off-hand attack (``details.is_offhand``) consumes the bonus action
    unless the weapon's Nick mastery is unlocked, in which case it folds
    into the Attack action itself, once per turn (ACT-08). Every other
    on-turn action type consumes the action. Extra Attack (ACT-01) lets the
    Attack action resolve up to :func:`_attacks_per_action` attacks before
    the action slot is spent. Validation (unknown actor/target, total cover)
    always runs before any economy slot is touched (ACT-05), so a rejected
    attack costs the actor nothing and an unknown actor never creates a
    "ghost" :class:`TurnState` entry. The Magic action is validated and
    resolved by the spellcasting module — here it only consumes the action
    slot. ``ActionType.OPPORTUNITY_ATTACK`` and ``ActionType.READIED_ACTION``
    are reactions (ACT-02, ACT-06): they consume the reactor's reaction
    instead of the action/bonus-action slot, so they're dispatched before the
    on-turn ``action_used`` gate below.

    Args:
        action: The action to resolve.
        combat_state: Combat state (may be mutated).

    Returns:
        :class:`~game_engine.interface.ActionResult`.
    """
    actor = combat_state.get_combatant(action.actor_id)
    if actor is None:
        return _simple_result(action, False, "Attacker not found.", {"error": "actor_not_found"})
    if not actor.can_act:
        return _simple_result(action, False, f"{actor.name} can't act.", {"error": "cannot_act"})

    ts = combat_state.turn_state_for(actor.id)

    if action.action_type is ActionType.ATTACK:
        return _resolve_attack_action(action, actor, ts, combat_state)
    if action.action_type is ActionType.OPPORTUNITY_ATTACK:
        return resolve_opportunity_attack(action, combat_state)
    if action.action_type is ActionType.READIED_ACTION:
        return resolve_readied_action(action, actor, ts, combat_state)

    if ts.action_used:
        return _simple_result(
            action, False, "Action already used this turn.", {"error": "action_used"}
        )
    ts.action_used = True
    return _resolve_non_attack(action, actor, combat_state, ts)


def _resolve_attack_action(
    action: Action,
    actor: CharacterSheet,
    ts: TurnState,
    combat_state: CombatStateData,
) -> ActionResult:
    """Gate an Attack-action submission's economy, then resolve it.

    Validates the attack (actor/target/cover) before spending any slot.
    Off-hand attacks spend the bonus action, unless Nick applies (spends a
    once-per-turn Nick slot instead). A bonus-action off-hand attack also
    requires the 2024 Two-Weapon Fighting prerequisites (ACT-04): the
    off-hand weapon must have the Light property, and the actor must already
    have attacked with a Light weapon in hand this turn via the Attack
    action (``ts.light_attack_used``) — Nick attacks are exempt since Nick
    only unlocks on Light weapons and folds into the same Attack action.
    Ordinary main-hand attacks draw from the actor's Extra Attack pool, and
    the action slot is only marked spent once that pool is exhausted; an
    unarmed grapple/shove is a single use of the action regardless of Extra
    Attack (its interaction with multiple attacks is Workstream E, out of
    scope here).
    """
    validated = _validate_attack(action, combat_state)
    if isinstance(validated, ActionResult):
        return validated
    _, _, details = validated

    is_nick_bonus_attack = (
        details.is_offhand
        and details.mastery is WeaponMastery.NICK
        and _has_mastery(actor, details)
    )

    if details.is_offhand and not is_nick_bonus_attack:
        if WeaponProperty.LIGHT not in details.properties:
            return _simple_result(
                action,
                False,
                "Two-Weapon Fighting requires a Light off-hand weapon.",
                {"error": "offhand_not_light"},
            )
        if not ts.light_attack_used:
            return _simple_result(
                action,
                False,
                "Two-Weapon Fighting requires a prior Attack action with a Light weapon "
                "this turn.",
                {"error": "no_light_attack"},
            )
        if ts.bonus_action_used:
            return _simple_result(
                action, False, "Bonus action already used.", {"error": "bonus_action_used"}
            )
        ts.bonus_action_used = True
        return _resolve_attack(action, combat_state)

    if is_nick_bonus_attack:
        if ts.nick_used:
            return _simple_result(
                action,
                False,
                "Nick's extra attack already used this turn.",
                {"error": "nick_used"},
            )
        ts.nick_used = True
        return _resolve_attack(action, combat_state)

    if ts.action_used:
        return _simple_result(
            action, False, "Action already used this turn.", {"error": "action_used"}
        )

    is_unarmed_special = details.unarmed_option in (
        UnarmedStrikeOption.GRAPPLE,
        UnarmedStrikeOption.SHOVE,
    )
    if is_unarmed_special:
        ts.action_used = True
        return _resolve_attack(action, combat_state)

    max_attacks = _attacks_per_action(actor)
    if ts.attacks_made >= max_attacks:
        ts.action_used = True
        return _simple_result(
            action, False, "Action already used this turn.", {"error": "action_used"}
        )
    if WeaponProperty.LIGHT in details.properties:
        ts.light_attack_used = True
    result = _resolve_attack(action, combat_state)
    if ts.attacks_made >= max_attacks:
        ts.action_used = True
    return result


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
        speed = actor.effective_speed
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
        check = _roll_check_impl(actor, Skill.STEALTH, _HIDE_DC, turn_state=ts)
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
