"""
D&D 5.5e damage application logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e._conditions import _apply_condition_impl
from game_engine.types import CharacterSheet, Condition, DamageType


def _apply_damage_impl(
    target: CharacterSheet,
    damage: int,
    damage_type: DamageType,
    is_critical: bool = False,
) -> CharacterSheet:
    """Apply damage to *target*, respecting resistances and immunities.

    Damage pipeline (D&D 5.5e rules):
    1. **Immunity** → damage = 0
    2. **Resistance** → damage = damage // 2
    3. **Vulnerability** → damage = damage * 2
    4. Petrified creatures have resistance to all damage (PHB 2024 p. 363).
    5. **Temporary HP** absorbs damage before regular HP.
    6. When HP drops to 0 from above 0: apply UNCONSCIOUS + PRONE conditions.
       If overkill damage ≥ hp_max, the character dies instantly (3 failures).
    7. When already at 0 HP (dying/stable): each hit adds 1 death save failure
       (2 if it was a critical hit), per PHB 2024 p. 369.

    Args:
        target: Character sheet. Modified in-place and returned.
        damage: Raw damage amount.
        damage_type: :class:`~game_engine.types.DamageType` enum.
        is_critical: Whether the hit was a critical hit (doubles death save
            failures when target is already at 0 HP).

    Returns:
        Updated character sheet.
    """
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

    # --- Damage to a creature already at 0 HP ---
    if target.is_dying:
        failures = 2 if is_critical else 1
        target.death_save_failures = min(3, target.death_save_failures + failures)
        # Reset stability if the creature had accumulated 3 successes
        if target.death_save_successes >= 3:
            target.death_save_successes = 0
        return target

    # --- Standard damage to a creature with HP > 0 ---

    # Temp HP absorbs before regular HP (PHB 2024 p. 197)
    if target.temp_hp > 0:
        absorbed = min(target.temp_hp, effective_damage)
        target.temp_hp -= absorbed
        effective_damage -= absorbed

    if effective_damage <= 0:
        return target

    # Compute overkill before updating HP (for instant-death check)
    overkill = max(0, effective_damage - target.hp_current)
    target.hp_current = max(0, target.hp_current - effective_damage)

    if target.hp_current == 0:
        # Instant death: remaining damage ≥ HP maximum (PHB 2024 p. 369)
        if overkill >= target.hp_max:
            target.death_save_failures = 3
        # Unconscious + prone when dropped to 0 HP
        _apply_condition_impl(target, Condition.UNCONSCIOUS)
        _apply_condition_impl(target, Condition.PRONE)

    return target


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
