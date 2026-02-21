"""
D&D 5.5e damage application logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.types import CharacterSheet, Condition, DamageType


def _apply_damage_impl(
    target: CharacterSheet,
    damage: int,
    damage_type: DamageType,
) -> CharacterSheet:
    """Apply damage to *target*, respecting resistances and immunities.

    Damage calculations:
    - **Immunity** → damage = 0
    - **Resistance** → damage = damage // 2
    - **Vulnerability** → damage = damage * 2
    - Petrified creatures have resistance to all damage.

    Args:
        target: Character sheet. Modified in-place and returned.
        damage: Raw damage amount.
        damage_type: :class:`~game_engine.types.DamageType` enum.

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
        dt=damage_type,
    )

    target.hp_current = max(0, target.hp_current - effective_damage)
    return target


def _compute_damage(
    damage: int,
    immunities: list[DamageType],
    resistances: list[DamageType],
    vulnerabilities: list[DamageType],
    dt: DamageType,
) -> int:
    """Compute effective damage after applying immunities/resistances/vulnerabilities."""
    if dt in immunities:
        return 0
    if dt in resistances:
        return damage // 2
    if dt in vulnerabilities:
        return damage * 2
    return damage
