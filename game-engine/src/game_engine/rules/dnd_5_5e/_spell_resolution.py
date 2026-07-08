"""
D&D 5.5e spell cast resolution.

Internal module — import :func:`cast_spell` via
:mod:`game_engine.rules.dnd_5_5e` (the package ``__init__.py`` re-exports it).
"""

from __future__ import annotations

from game_engine.core.dice import roll_dice, roll_with_disadvantage
from game_engine.rules.dnd_5_5e._damage import _apply_damage_impl, _apply_healing_impl
from game_engine.rules.dnd_5_5e._saves import _roll_saving_throw_impl
from game_engine.rules.dnd_5_5e.data.spells import SpellData
from game_engine.rules.dnd_5_5e.spellcasting import (
    SpellCastResult,
    SpellTargetOutcome,
    _consume_slot,
    _scale_dice,
    cantrip_dice_multiplier,
    duration_rounds,
    spell_attack_bonus,
    spell_save_dc,
)
from game_engine.types import (
    Ability,
    CharacterSheet,
    CombatStateData,
    DiceNotation,
)


def _fail(spell: SpellData, error: str, flavor: str) -> SpellCastResult:
    return SpellCastResult(
        success=False,
        spell_name=spell.name,
        slot_level_used=None,
        outcomes=[],
        flavor_text=flavor,
        error=error,
    )


def _roll_damage(
    spell: SpellData,
    dice: DiceNotation | None,
    upcast_per_slot: DiceNotation | None,
    caster_level: int,
    upcast_levels: int,
) -> int:
    """Roll one of the spell's damage pools with cantrip/upcast scaling."""
    if dice is None:
        return 0
    multiplier = cantrip_dice_multiplier(caster_level) if spell.is_cantrip else 1
    extra_dice = 0
    if upcast_levels > 0 and upcast_per_slot is not None:
        extra_dice = upcast_per_slot.num_dice * upcast_levels
    total, _ = roll_dice(*_scale_dice(dice, multiplier, extra_dice).parsed())
    return max(0, total)


def cast_spell(
    caster: CharacterSheet,
    spell: SpellData,
    spellcasting_ability: Ability,
    combat_state: CombatStateData,
    target_ids: list[str],
    slot_level: int | None = None,
    as_ritual: bool = False,
) -> SpellCastResult:
    """Cast *spell* at the given targets, consuming a slot and resolving effects.

    Validates slot availability (leveled spells), supports upcasting and
    ritual casting, applies attack rolls or saving throws per target, rolls
    damage/healing, applies rider conditions on failed saves, and starts
    concentration (ending any previous concentration).

    Whether the spell is known/prepared, and the Magic action's economy,
    are the caller's responsibility (see :mod:`._actions`).

    Args:
        caster: The casting character.
        spell: Spell definition.
        spellcasting_ability: The caster's spellcasting ability.
        combat_state: Combat state containing the targets.
        target_ids: IDs of targets (may be empty for utility spells).
        slot_level: Slot level to use (defaults to the spell's level).
        as_ritual: Cast as a ritual (no slot; spell must be a ritual).

    Returns:
        :class:`~game_engine.rules.dnd_5_5e.spellcasting.SpellCastResult`.
    """
    used_slot: int | None = None
    if as_ritual:
        if not spell.ritual:
            return _fail(spell, "not_a_ritual", f"{spell.name} can't be cast as a ritual.")
    elif not spell.is_cantrip:
        used_slot = slot_level if slot_level is not None else spell.level
        if used_slot < spell.level:
            return _fail(
                spell,
                "slot_too_low",
                f"{spell.name} requires a level {spell.level}+ slot.",
            )
        if not _consume_slot(caster, used_slot):
            return _fail(spell, "no_slot", f"No level {used_slot} spell slots remaining.")

    upcast_levels = (used_slot - spell.level) if used_slot is not None else 0
    dc = spell_save_dc(caster, spellcasting_ability)
    attack_bonus = spell_attack_bonus(caster, spellcasting_ability) + caster.d20_modifier
    rider_duration = duration_rounds(spell.duration)

    concentration_started = False
    if spell.concentration:
        caster.concentrating_on = spell.name
        concentration_started = True

    outcomes: list[SpellTargetOutcome] = []
    for target_id in target_ids:
        target = combat_state.get_combatant(target_id)
        if target is None:
            continue
        outcome = SpellTargetOutcome(target_id=target_id)

        # 2024 PHB Dodge: attacks against a dodging creature have disadvantage;
        # DEX saves made by a dodging creature have advantage.
        target_ts = combat_state.turn_state_for(target_id)
        target_dodging = target_ts.dodging and target.can_act

        if spell.attack_roll:
            if target_dodging:
                raw, _ = roll_with_disadvantage(20)
            else:
                raw, _ = roll_dice(1, 20)
            total = raw + attack_bonus
            outcome.attack_total = total
            outcome.hit = raw == 20 or (raw != 1 and total >= target.ac)
            if not outcome.hit:
                outcomes.append(outcome)
                continue
        elif spell.save is not None:
            dex_save_advantage = target_dodging and spell.save is Ability.DEXTERITY
            save = _roll_saving_throw_impl(target, spell.save, dc, advantage=dex_save_advantage)
            outcome.save_total = save.total
            outcome.save_success = save.success

        damage = _roll_damage(
            spell, spell.damage_dice, spell.upcast_damage_per_slot, caster.level, upcast_levels
        )
        if spell.secondary_damage_dice is not None and spell.secondary_damage_type is not None:
            secondary = _roll_damage(spell, spell.secondary_damage_dice, None, caster.level, 0)
        else:
            secondary = 0

        saved = outcome.save_success is True
        if saved and spell.half_damage_on_save:
            damage //= 2
            secondary //= 2
        elif saved:
            damage = 0
            secondary = 0

        if damage > 0 and spell.damage_type is not None:
            _apply_damage_impl(target, damage, spell.damage_type)
            outcome.damage += damage
        if secondary > 0 and spell.secondary_damage_type is not None:
            _apply_damage_impl(target, secondary, spell.secondary_damage_type)
            outcome.damage += secondary

        # Revival bypasses the "no healing while dead" rule: clearing the
        # death-save state here lets the healing below (or the full-heal
        # carve-out) reach a target that _apply_healing_impl would otherwise
        # reject outright.
        if spell.revives and target.death_saves.is_dead:
            target.death_saves.reset()
            outcome.revived = True

        healing = _roll_damage(
            spell, spell.healing_dice, spell.upcast_healing_per_slot, caster.level, upcast_levels
        )
        if spell.healing_dice is not None:
            healing += caster.ability_scores.modifier(spellcasting_ability)
        healing += spell.healing_flat + spell.upcast_healing_flat_per_slot * upcast_levels
        if healing > 0 and (spell.healing_dice is not None or spell.healing_flat > 0):
            _apply_healing_impl(target, max(0, healing))
            outcome.healing = max(0, healing)

        if outcome.revived and spell.revive_full_heal:
            target.hp_current = target.hp_max
            outcome.healing = target.hp_max

        if not saved and spell.conditions_applied:
            for condition in spell.conditions_applied:
                if condition not in target.conditions:
                    target.conditions.append(condition)
                    outcome.conditions_applied.append(condition)
                if rider_duration is not None:
                    target.condition_durations[condition] = rider_duration

        outcomes.append(outcome)

    hits = sum(1 for o in outcomes if o.hit and (o.save_success is not True))
    flavor = f"{caster.name} casts {spell.name}"
    if used_slot is not None and used_slot > spell.level:
        flavor += f" (level {used_slot} slot)"
    if as_ritual:
        flavor += " as a ritual"
    flavor += "."
    if outcomes:
        total_damage = sum(o.damage for o in outcomes)
        total_healing = sum(o.healing for o in outcomes)
        revived_count = sum(1 for o in outcomes if o.revived)
        if total_damage:
            flavor += f" {hits}/{len(outcomes)} targets affected for {total_damage} damage."
        if total_healing:
            flavor += f" Restores {total_healing} hit points."
        if revived_count:
            flavor += f" {revived_count} target(s) return to life."

    return SpellCastResult(
        success=True,
        spell_name=spell.name,
        slot_level_used=used_slot,
        outcomes=outcomes,
        flavor_text=flavor,
        concentration_started=concentration_started,
    )
