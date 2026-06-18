"""
D&D 5.5e damage, healing, and temporary hit point logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.conditions import CONDITION_EFFECTS
from game_engine.types import CharacterSheet, CharacterType, Condition, DamageType


def _apply_damage_impl(
    target: CharacterSheet,
    damage: int,
    damage_type: DamageType,
    critical: bool = False,
) -> CharacterSheet:
    """Apply damage to *target*, respecting resistances and immunities.

    Damage calculations:
    - **Immunity** → damage = 0 (character immunities AND condition-based immunities
      from ``ConditionEffect.immunity_types``).
    - **Resistance** → damage = damage // 2 (character resistances AND condition-based
      all-damage resistance from ``ConditionEffect.damage_resistances_all``).
    - **Vulnerability** → damage = damage * 2
    - Resistance and vulnerability cancel each other out; immunity always wins.

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
    # Condition-based immunities and all-damage resistance.
    # ConditionEffect.immunity_types:      e.g. PETRIFIED → immune to POISON/PSYCHIC
    # ConditionEffect.damage_resistances_all: e.g. PETRIFIED → resistant to all damage
    resistances = list(target.damage_resistances)
    for cond in target.conditions:
        effect = CONDITION_EFFECTS.get(cond)
        if effect is None:
            continue
        if damage_type in effect.immunity_types:
            return target
        if effect.damage_resistances_all and damage_type not in resistances:
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
    # Monsters don't make death saves: any damage at 0 HP finishes them.
    if target.hp_current <= 0:
        if target.char_type is CharacterType.MONSTER:
            target.death_saves.is_dead = True
            return target
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
        if remaining >= target.hp_max or target.char_type is CharacterType.MONSTER:
            # Massive damage — or a monster dropping to 0 HP — is instant
            # death (2024 PHB: monsters die at 0 HP; only PCs/NPCs get
            # death saving throws).
            target.death_saves.is_dead = True
            target.concentrating_on = None
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
