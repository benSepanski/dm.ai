"""
D&D 5.5e weapon mastery on-hit effects (2024 rules).

Split out of :mod:`._attacks` (file-length guideline, AGENTS.md #3) — reuses
its saving-throw/condition helpers. Called from :func:`._attacks._resolve_attack`
after a hit lands.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from typing import Any

from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.rules.dnd_5_5e._conditions import _apply_condition_impl
from game_engine.rules.dnd_5_5e._saves import _roll_saving_throw_impl
from game_engine.types import (
    Ability,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
    Condition,
    WeaponMastery,
)


def _has_mastery(actor: CharacterSheet, details: AttackDetails) -> bool:
    """True when the actor has unlocked this weapon's mastery property."""
    if details.mastery is None:
        return False
    return details.weapon_name.lower() in (w.lower() for w in actor.weapon_masteries)


def _apply_mastery_effects(
    actor: CharacterSheet,
    target: CharacterSheet,
    details: AttackDetails,
    combat_state: CombatStateData,
    log: dict[str, Any],
) -> list[Condition]:
    """Apply on-hit weapon mastery effects. Returns conditions applied."""
    applied: list[Condition] = []
    mastery = details.mastery
    if mastery is WeaponMastery.TOPPLE:
        dc = (
            8
            + actor.ability_scores.modifier(details.attack_ability)
            + _calc_prof_bonus(actor.level)
        )
        save = _roll_saving_throw_impl(target, Ability.CONSTITUTION, dc)
        log["topple_save"] = {"dc": dc, "total": save.total, "success": save.success}
        if not save.success:
            # EFF-10: route through the centralized helper so a Prone-immune
            # target can't be toppled.
            was_present = Condition.PRONE in target.conditions
            _apply_condition_impl(target, Condition.PRONE)
            if not was_present and Condition.PRONE in target.conditions:
                applied.append(Condition.PRONE)
    elif mastery is WeaponMastery.SAP:
        combat_state.grant_sap(actor.id, target.id)
        log["sapped"] = True
    elif mastery is WeaponMastery.VEX:
        combat_state.grant_vex(actor.id, target.id)
        log["vexed"] = True
    elif mastery is WeaponMastery.SLOW:
        # ACT-07: reduces the target's speed by 10 ft until the start of the
        # attacker's own next turn — see CombatStateData.grant_slow.
        combat_state.grant_slow(actor.id, target.id)
        log["slowed_ft"] = 10
    elif mastery is WeaponMastery.PUSH:
        log["pushed_ft"] = 10
    elif mastery is WeaponMastery.CLEAVE:
        # ACT-07: grants one free follow-up attack against a different
        # creature this turn — see ActionType.CLEAVE_ATTACK in _actions.py.
        actor_ts = combat_state.turn_state_for(actor.id)
        actor_ts.cleave_available = True
        actor_ts.cleave_original_target_id = target.id
        log["cleave_available"] = True
    elif mastery is WeaponMastery.NICK:
        log["nick_extra_attack"] = True
    return applied
