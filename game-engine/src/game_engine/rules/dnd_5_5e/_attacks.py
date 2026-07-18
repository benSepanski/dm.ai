"""
D&D 5.5e attack resolution (2024 rules).

Handles to-hit advantage/disadvantage from conditions and turn flags,
cover, critical hits (including melee auto-crits vs paralyzed/unconscious),
weapon masteries, off-hand attacks, unarmed grapple/shove, and
concentration checks on damage. Reaction resolution (opportunity attacks,
readied actions) lives in :mod:`._reactions`, which reuses ``_validate_attack``/
``_resolve_attack``/``_failure`` from here.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from typing import Any

from game_engine.core.conditions import CONDITION_EFFECTS
from game_engine.core.dice import roll_dice, roll_with_advantage, roll_with_disadvantage
from game_engine.interface import Action, ActionResult
from game_engine.rules.dnd_5_5e._checks import _calc_prof_bonus
from game_engine.rules.dnd_5_5e._conditions import _apply_condition_impl
from game_engine.rules.dnd_5_5e._damage import (
    ConcentrationSaveResult,
    _apply_damage_effective,
    _concentration_check,
)
from game_engine.rules.dnd_5_5e._saves import _roll_saving_throw_impl
from game_engine.types import (
    Ability,
    AdvantageType,
    AttackDetails,
    CharacterSheet,
    CombatStateData,
    Condition,
    Feat,
    TurnState,
    UnarmedStrikeOption,
    WeaponMastery,
    WeaponProperty,
)

_DEFAULT_ATTACK = AttackDetails()


def _failure(action: Action, reason: str, flavor: str) -> ActionResult:
    return ActionResult(
        success=False,
        damage=0,
        damage_type=None,
        conditions_applied=[],
        flavor_text=flavor,
        log_entry={
            "actor_id": action.actor_id,
            "action_type": action.action_type.value,
            "target_id": action.target_id,
            "error": reason,
        },
    )


def _advantage_state(
    actor: CharacterSheet,
    target: CharacterSheet,
    details: AttackDetails,
    actor_ts: TurnState,
    target_ts: TurnState,
) -> tuple[bool, bool]:
    """Aggregate advantage/disadvantage sources for an attack roll.

    Consumes one-shot flags (Help, Vex, Sap, hidden) from the turn states.
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
            if details.is_ranged:
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
    if details.long_range:
        disadvantage = True
    if (
        WeaponProperty.HEAVY in details.properties
        and actor.ability_scores.get(details.attack_ability) < 13
    ):
        disadvantage = True

    return advantage, disadvantage


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
        log["slowed_ft"] = 10
    elif mastery is WeaponMastery.PUSH:
        log["pushed_ft"] = 10
    elif mastery is WeaponMastery.CLEAVE:
        log["cleave_available"] = True
    elif mastery is WeaponMastery.NICK:
        log["nick_extra_attack"] = True
    return applied


def _log_concentration_result(log: dict[str, Any], result: ConcentrationSaveResult | None) -> None:
    """Record a :func:`_concentration_check` outcome into an attack's log entry."""
    if result is None:
        return
    log["concentration_save"] = {
        "spell": result.spell,
        "dc": result.dc,
        "total": result.total,
        "success": result.success,
    }
    if not result.success:
        log["concentration_broken"] = result.spell


def _resolve_unarmed_special(
    action: Action,
    actor: CharacterSheet,
    target: CharacterSheet,
    option: UnarmedStrikeOption,
    target_ts: TurnState | None = None,
) -> ActionResult:
    """Resolve an unarmed strike used to Grapple or Shove (2024 rules)."""
    dc = 8 + actor.ability_scores.modifier(Ability.STRENGTH) + _calc_prof_bonus(actor.level)
    # The target chooses STR or DEX; assume it picks its better save.
    str_mod = target.ability_scores.modifier(Ability.STRENGTH)
    dex_mod = target.ability_scores.modifier(Ability.DEXTERITY)
    save_ability = Ability.STRENGTH if str_mod >= dex_mod else Ability.DEXTERITY
    # 2024 PHB: Dodge grants advantage on DEX saves while active. A dodger
    # with speed 0 (e.g. Grappled, Restrained, exhaustion 5+) can't take the
    # Dodge action's evasive-movement benefit.
    dodging_advantage = (
        save_ability is Ability.DEXTERITY
        and target_ts is not None
        and target_ts.dodging
        and target.can_act
        and target.effective_speed > 0
    )
    save = _roll_saving_throw_impl(target, save_ability, dc, advantage=dodging_advantage)

    condition = Condition.GRAPPLED if option is UnarmedStrikeOption.GRAPPLE else Condition.PRONE
    applied: list[Condition] = []
    if not save.success:
        # EFF-10: route through the centralized helper so a Grappled/Prone-
        # immune target can't be grappled or shoved.
        was_present = condition in target.conditions
        _apply_condition_impl(target, condition)
        if not was_present and condition in target.conditions:
            applied.append(condition)

    verb = "grapples" if option is UnarmedStrikeOption.GRAPPLE else "shoves"
    flavor = (
        f"{actor.name} {verb} {target.name}: "
        f"{'fails' if not save.success else 'succeeds on'} the DC {dc} "
        f"{save_ability.value} save"
        f"{' — ' + condition.value if applied else ''}."
    )
    return ActionResult(
        success=not save.success,
        damage=0,
        damage_type=None,
        conditions_applied=applied,
        flavor_text=flavor,
        log_entry={
            "actor_id": action.actor_id,
            "action_type": action.action_type.value,
            "target_id": action.target_id,
            "unarmed_option": option.value,
            "save_dc": dc,
            "save_ability": save_ability.value,
            "save_total": save.total,
            "save_success": save.success,
        },
    )


def _validate_attack(
    action: Action, combat_state: CombatStateData
) -> ActionResult | tuple[CharacterSheet, CharacterSheet, AttackDetails]:
    """Check that *action* names a real actor/target not behind total cover.

    Pure lookup — rolls no dice and mutates no state — so callers (notably
    :mod:`._actions`'s action-economy gate, ACT-05) can validate an attack
    *before* spending any action-economy slot on it.
    """
    actor = combat_state.get_combatant(action.actor_id)
    target = combat_state.get_combatant(action.target_id) if action.target_id else None
    details = action.details or _DEFAULT_ATTACK

    if actor is None:
        return _failure(action, "actor_not_found", "Attacker not found.")
    if target is None:
        return _failure(action, "target_not_found", "No target found.")
    if details.target_cover is not None and details.target_cover.blocks_targeting:
        return _failure(
            action, "total_cover", f"{target.name} has total cover and can't be targeted."
        )
    return actor, target, details


def _resolve_attack(action: Action, combat_state: CombatStateData) -> ActionResult:
    """Resolve an Attack action under the 2024 rules."""
    validated = _validate_attack(action, combat_state)
    if isinstance(validated, ActionResult):
        return validated
    actor, target, details = validated

    actor_ts = combat_state.turn_state_for(actor.id)
    target_ts = combat_state.turn_state_for(target.id)

    if details.unarmed_option in (UnarmedStrikeOption.GRAPPLE, UnarmedStrikeOption.SHOVE):
        return _resolve_unarmed_special(action, actor, target, details.unarmed_option, target_ts)

    ability_mod = actor.ability_scores.modifier(details.attack_ability)
    prof_bonus = _calc_prof_bonus(actor.level) if details.proficient else 0
    attack_mod = ability_mod + prof_bonus + actor.d20_modifier
    target_ac = target.ac + (details.target_cover.ac_bonus if details.target_cover else 0)

    advantage, disadvantage = _advantage_state(actor, target, details, actor_ts, target_ts)
    if advantage and not disadvantage:
        attack_roll_raw, _ = roll_with_advantage(20)
    elif disadvantage and not advantage:
        attack_roll_raw, _ = roll_with_disadvantage(20)
    else:
        attack_roll_raw, _ = roll_dice(1, 20)
    attack_total = attack_roll_raw + attack_mod

    hit = attack_roll_raw == 20 or (attack_roll_raw != 1 and attack_total >= target_ac)
    auto_crit = not details.is_ranged and any(
        c in target.conditions for c in (Condition.PARALYZED, Condition.UNCONSCIOUS)
    )
    critical = hit and (attack_roll_raw == 20 or auto_crit)
    actor_ts.attacks_made += 1

    log: dict[str, Any] = {
        "actor_id": action.actor_id,
        "action_type": action.action_type.value,
        "target_id": action.target_id,
        "weapon": details.weapon_name,
        "attack_roll": attack_roll_raw,
        "attack_total": attack_total,
        "target_ac": target_ac,
        "advantage": advantage and not disadvantage,
        "disadvantage": disadvantage and not advantage,
        "hit": hit,
    }

    if not hit:
        graze_damage = 0
        if details.mastery is WeaponMastery.GRAZE and _has_mastery(actor, details):
            graze_damage = max(1, ability_mod)
            if graze_damage:
                effective = _apply_damage_effective(target, graze_damage, details.damage_type)
                _log_concentration_result(log, _concentration_check(target, effective))
                log["graze_damage"] = graze_damage
        flavor = (
            f"{actor.name} misses {target.name}! "
            f"(rolled {attack_roll_raw} + {attack_mod} = {attack_total} vs AC {target_ac})"
        )
        if graze_damage:
            flavor += f" Graze deals {graze_damage} {details.damage_type.value} damage."
        return ActionResult(
            success=False,
            damage=graze_damage,
            damage_type=details.damage_type,
            conditions_applied=[],
            flavor_text=flavor,
            log_entry=log,
        )

    # Damage: off-hand attacks omit a *positive* ability modifier unless the
    # Two-Weapon Fighting style is known; a negative modifier still applies.
    damage_mod = ability_mod
    if details.is_offhand and Feat.TWO_WEAPON_FIGHTING not in actor.feats and ability_mod > 0:
        damage_mod = 0
    # A critical hit doubles the dice, not the flat modifier baked into the
    # notation (ACT-09) — rolling the full notation twice would double a
    # "1d6+2"'s +2 as well as the 1d6.
    dice_total, _ = roll_dice(
        details.damage_dice.num_dice, details.damage_dice.sides, details.damage_dice.modifier
    )
    if critical:
        crit_dice, _ = roll_dice(details.damage_dice.num_dice, details.damage_dice.sides)
        dice_total += crit_dice
    total_damage = max(0, dice_total + damage_mod)

    was_dying = target.hp_current <= 0
    effective_damage = _apply_damage_effective(
        target, total_damage, details.damage_type, critical=critical
    )
    _log_concentration_result(log, _concentration_check(target, effective_damage))

    conditions_applied: list[Condition] = []
    if target.hp_current == 0 and not was_dying and Condition.UNCONSCIOUS in target.conditions:
        conditions_applied.append(Condition.UNCONSCIOUS)
    if _has_mastery(actor, details):
        conditions_applied += _apply_mastery_effects(actor, target, details, combat_state, log)

    log.update(
        critical=critical,
        damage=total_damage,
        damage_type=details.damage_type.value,
        target_hp_remaining=target.hp_current,
    )
    flavor = (
        f"{'CRITICAL HIT! ' if critical else ''}"
        f"{actor.name} hits {target.name} for {total_damage} "
        f"{details.damage_type.value} damage! "
        f"(roll {attack_roll_raw} + {attack_mod} = {attack_total} vs AC {target_ac})"
    )
    if target.death_saves.is_dead:
        flavor += f" {target.name} is slain!"
    elif target.hp_current == 0 and not was_dying:
        flavor += f" {target.name} falls unconscious!"

    return ActionResult(
        success=True,
        damage=total_damage,
        damage_type=details.damage_type,
        conditions_applied=conditions_applied,
        flavor_text=flavor,
        log_entry=log,
    )
