"""
D&D 5.5e damage, healing, and temporary hit point logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from typing import Any

from game_engine.core.conditions import CONDITION_EFFECTS
from game_engine.types import Ability, CharacterSheet, Condition, DamageType, Feat


def _apply_damage_impl(
    target: CharacterSheet,
    damage: int,
    damage_type: DamageType,
    critical: bool = False,
) -> CharacterSheet:
    """Apply damage to *target*, respecting resistances and immunities.

    Damage calculations:
    - **Immunity** → damage = 0 (character immunities AND condition-based immunities)
    - **Resistance** → damage = damage // 2
    - **Vulnerability** → damage = damage * 2
    - Petrified creatures have resistance to all damage and immunity to poison/psychic.

    Temporary hit points absorb damage first. Dropping to 0 HP knocks the
    character unconscious and prone (2024 PHB "Dropping to 0 Hit Points");
    if the remaining damage meets or exceeds the HP maximum, the character
    dies instantly. Damage taken while already at 0 HP causes one death
    save failure (two on a critical hit).

    Args:
        target: Character sheet. Modified in-place and returned.
        damage: Raw damage amount.
        damage_type: :class:`~game_engine.types.DamageType` enum.
        critical: Whether the damage came from a critical hit (affects
            death save failures while dying).

    Returns:
        Updated character sheet.
    """
    # Condition-based immunities (e.g. PETRIFIED → immune to POISON and PSYCHIC).
    for cond in target.conditions:
        effect = CONDITION_EFFECTS.get(cond)
        if effect and damage_type in effect.immunity_types:
            return target

    # Petrified → resistance to all damage
    is_petrified = Condition.PETRIFIED in target.conditions
    resistances = list(target.damage_resistances)
    if is_petrified and damage_type not in resistances:
        resistances.append(damage_type)

    effective_damage = _compute_damage(
        damage,
        immunities=target.damage_immunities,
        resistances=resistances,
        vulnerabilities=target.damage_vulnerabilities,
        damage_type=damage_type,
    )
    if effective_damage <= 0:
        return target

    # Damage while already at 0 HP → death save failures (no HP change).
    if target.hp_current <= 0:
        target.death_saves.is_stable = False
        target.death_saves.failures += 2 if critical else 1
        if target.death_saves.failures >= 3:
            target.death_saves.is_dead = True
        return target

    # Temporary hit points absorb damage first.
    if target.temp_hp > 0:
        absorbed = min(target.temp_hp, effective_damage)
        target.temp_hp -= absorbed
        effective_damage -= absorbed
        if effective_damage <= 0:
            return target

    remaining = effective_damage - target.hp_current
    target.hp_current = max(0, target.hp_current - effective_damage)

    if target.hp_current == 0:
        if remaining >= target.hp_max:
            # Massive damage: instant death.
            target.death_saves.is_dead = True
        else:
            _fall_unconscious(target)
    return target


def _fall_unconscious(target: CharacterSheet) -> None:
    """Knock *target* unconscious and prone at 0 HP (begin dying)."""
    target.death_saves.reset()
    if Condition.UNCONSCIOUS not in target.conditions:
        target.conditions.append(Condition.UNCONSCIOUS)
    if Condition.PRONE not in target.conditions:
        target.conditions.append(Condition.PRONE)
    target.concentrating_on = None


def _apply_healing_impl(target: CharacterSheet, amount: int) -> CharacterSheet:
    """Restore up to *amount* hit points (no effect on the dead).

    Healing a character at 0 HP returns them to consciousness and resets
    death save bookkeeping.

    Args:
        target: Character sheet. Modified in-place and returned.
        amount: Hit points to restore (negative values are ignored).

    Returns:
        Updated character sheet.
    """
    if target.is_dead or amount <= 0:
        return target

    was_dying = target.hp_current <= 0
    target.hp_current = min(target.hp_max, target.hp_current + amount)

    if was_dying and target.hp_current > 0:
        target.death_saves.reset()
        target.conditions = [c for c in target.conditions if c is not Condition.UNCONSCIOUS]
        target.condition_durations.pop(Condition.UNCONSCIOUS, None)
    return target


def _grant_temp_hp_impl(target: CharacterSheet, amount: int) -> CharacterSheet:
    """Grant temporary hit points (doesn't stack — keep the larger pool)."""
    target.temp_hp = max(target.temp_hp, max(0, amount))
    return target


def concentration_save_dc(damage: int) -> int:
    """Return the Constitution save DC to maintain concentration after damage."""
    return max(10, damage // 2)


def _compute_damage(
    damage: int,
    immunities: list[DamageType],
    resistances: list[DamageType],
    vulnerabilities: list[DamageType],
    damage_type: DamageType,
) -> int:
    """Compute effective damage after applying immunities/resistances/vulnerabilities.

    Per D&D 5e rules, resistance and vulnerability cancel each other out.
    Immunity always takes priority over both.
    """
    if damage_type in immunities:
        return 0
    has_resistance = damage_type in resistances
    has_vulnerability = damage_type in vulnerabilities
    if has_resistance and has_vulnerability:
        return damage  # cancel each other out
    if has_resistance:
        return damage // 2
    if has_vulnerability:
        return damage * 2
    return damage


def _concentration_check_impl(
    target: CharacterSheet,
    actual_damage: int,
    log: dict[str, Any],
) -> None:
    """Roll the CON save to maintain concentration after taking damage.

    ``actual_damage`` must be the hit points actually lost (after resistances,
    immunities, and temp-HP absorption — NOT the raw attack roll damage).
    Using the post-resistance value ensures:
    - Immune creatures never roll (actual_damage == 0 → early return).
    - Resistant creatures face the correct lower DC (2024 PHB: DC = max(10, damage_taken // 2)).

    Modifies ``target.concentrating_on`` in-place if the save fails.
    Results are written into ``log`` under ``"concentration_save"`` and
    (on failure) ``"concentration_broken"``.
    """
    # Lazy import avoids a module-level circular dependency:
    # _damage ← _saves ← _checks ← (no _damage import).
    from game_engine.rules.dnd_5_5e._saves import _roll_saving_throw_impl

    if target.concentrating_on is None or actual_damage <= 0 or target.is_dying:
        return
    spell_name = target.concentrating_on
    dc = concentration_save_dc(actual_damage)
    advantage = Feat.WAR_CASTER in target.feats
    save = _roll_saving_throw_impl(target, Ability.CONSTITUTION, dc, advantage=advantage)
    log["concentration_save"] = {
        "spell": spell_name,
        "dc": dc,
        "total": save.total,
        "success": save.success,
    }
    if not save.success:
        log["concentration_broken"] = spell_name
        target.concentrating_on = None
