"""
D&D 5.5e attack-roll advantage/disadvantage aggregation.

Shared by weapon attacks (:mod:`._attacks`) and spell attacks
(:mod:`._spell_resolution`, SPL-08) so condition-based advantage/
disadvantage, Dodge, and the one-shot Help/Vex/Sap/Hide turn-state flags
are computed in exactly one place for both attack kinds.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.conditions import CONDITION_EFFECTS
from game_engine.types import AdvantageType, CharacterSheet, Condition, TurnState


def _base_advantage_state(
    actor: CharacterSheet,
    target: CharacterSheet,
    is_ranged: bool,
    actor_ts: TurnState,
    target_ts: TurnState,
) -> tuple[bool, bool]:
    """Aggregate the condition/Dodge/turn-state advantage sources shared by
    every attack roll — weapon or spell (SPL-08).

    Consumes one-shot flags (Help, Vex, Sap, hidden) from the turn states.
    Weapon-only modifiers (long range, the Heavy property) are layered on
    top by :func:`_attacks._advantage_state`; there's no equivalent for
    spells.
    """
    advantage = False
    disadvantage = False

    for cond in actor.conditions:
        effect = CONDITION_EFFECTS.get(cond)
        if effect is None or effect.attack_modifier is None:
            continue
        if effect.attack_modifier is AdvantageType.ADVANTAGE:
            advantage = True
        else:
            disadvantage = True

    for cond in target.conditions:
        if cond is Condition.PRONE:
            # Melee attacks vs prone have advantage; ranged have disadvantage.
            if is_ranged:
                disadvantage = True
            else:
                advantage = True
            continue
        effect = CONDITION_EFFECTS.get(cond)
        if effect is None or effect.attack_against_modifier is None:
            continue
        if effect.attack_against_modifier is AdvantageType.ADVANTAGE:
            advantage = True
        else:
            disadvantage = True

    if target_ts.dodging and target.can_act and target.effective_speed > 0:
        disadvantage = True
    if actor_ts.helped:
        advantage = True
        actor_ts.helped = False
    if actor_ts.vexed_target_id == target.id:
        advantage = True
        actor_ts.vexed_target_id = None
    if actor_ts.sapped:
        disadvantage = True
        actor_ts.sapped = False
    if actor_ts.hidden:
        advantage = True
        actor_ts.hidden = False  # attacking reveals you

    return advantage, disadvantage
