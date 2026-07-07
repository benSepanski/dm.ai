"""
D&D 5.5e reaction resolution (2024 rules): opportunity attacks and readied
actions.

Both consume ``TurnState.reaction_used`` — refreshed once per round at the
start of the reactor's own turn by :meth:`CombatStateData.reset_turn` — via
the same ``Action``/``resolve_action`` entry point on-turn actions use
(dispatched by ``ActionType.OPPORTUNITY_ATTACK``/``ActionType.READIED_ACTION``
in :mod:`._actions`). Split out of :mod:`._attacks` (file-length guideline);
reuses its validate-before-consume attack-resolution helpers.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._attacks import _failure, _resolve_attack, _validate_attack
from game_engine.types import ActionType, CharacterSheet, CombatStateData, TurnState


def provokes_opportunity_attack(mover_id: str, combat_state: CombatStateData) -> bool:
    """True when a creature leaving reach would provoke an opportunity attack.

    Disengaging suppresses opportunity attacks for the rest of the turn.
    """
    return not combat_state.turn_state_for(mover_id).disengaging


def resolve_opportunity_attack(action: Action, combat_state: CombatStateData) -> ActionResult:
    """Resolve a reaction opportunity attack (``ActionType.OPPORTUNITY_ATTACK``).

    ``action.actor_id`` is the reacting creature; ``action.target_id`` is the
    creature whose movement provoked it. Validates the attack (actor/target/
    cover) before consulting :func:`provokes_opportunity_attack` or spending
    the reactor's reaction — mirroring the validate-before-consume ordering
    ACT-05 established for the Attack action — so an unknown actor/target
    never marks a reaction spent. Rejected if the mover disengaged this turn
    or the reactor already used its reaction this round.
    """
    validated = _validate_attack(action, combat_state)
    if isinstance(validated, ActionResult):
        return validated
    actor, mover, _ = validated

    if not provokes_opportunity_attack(mover.id, combat_state):
        return _failure(
            action,
            "no_opportunity",
            f"{mover.name} didn't provoke an opportunity attack.",
        )
    actor_ts = combat_state.turn_state_for(actor.id)
    if actor_ts.reaction_used:
        return _failure(action, "reaction_used", "Reaction already used this round.")

    actor_ts.reaction_used = True
    return _resolve_attack(action, combat_state)


def resolve_readied_action(
    action: Action,
    actor: CharacterSheet,
    ts: TurnState,
    combat_state: CombatStateData,
) -> ActionResult:
    """Trigger *actor*'s stored Ready action (``ActionType.READIED_ACTION``).

    Only a readied attack is supported (see :class:`~game_engine.types.ReadiedAction`
    — stored by the Ready action in :mod:`._actions`). Validates the stored
    attack (target still exists, not behind total cover) before spending the
    reaction (ACT-05's validate-before-consume pattern), then resolves it
    exactly like an Attack action and clears the readied slot — it is
    one-shot, unlike Extra Attack's per-action pool.
    """
    readied = ts.readied
    if readied is None:
        return _failure(action, "no_readied_action", f"{actor.name} has no readied action.")
    if ts.reaction_used:
        return _failure(action, "reaction_used", "Reaction already used this round.")

    attack_action = Action(
        action_type=ActionType.ATTACK,
        actor_id=actor.id,
        target_id=readied.target_id,
        details=readied.details,
    )
    validated = _validate_attack(attack_action, combat_state)
    if isinstance(validated, ActionResult):
        return validated

    ts.readied = None
    ts.reaction_used = True
    return _resolve_attack(attack_action, combat_state)
