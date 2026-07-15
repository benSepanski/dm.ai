"""
D&D 5.5e damage, healing, temporary hit point, and concentration logic.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from dataclasses import dataclass

from game_engine.core.conditions import CONDITION_EFFECTS
from game_engine.rules.dnd_5_5e._saves import _roll_saving_throw_impl
from game_engine.types import Ability, CharacterSheet, CharacterType, Condition, DamageType, Feat


def _apply_damage_impl(
    target: CharacterSheet,
    damage: int,
    damage_type: DamageType,
    critical: bool = False,
) -> CharacterSheet:
    """Apply damage to *target*, respecting resistances and immunities.

    Thin wrapper around :func:`_apply_damage_effective` for callers that
    only need the mutated sheet back, not the effective damage amount.

    Returns:
        Updated character sheet.
    """
    _apply_damage_effective(target, damage, damage_type, critical=critical)
    return target


def _apply_damage_effective(
    target: CharacterSheet,
    damage: int,
    damage_type: DamageType,
    critical: bool = False,
) -> int:
    """Apply damage to *target* and return the effective amount dealt.

    The effective amount is *damage* after character/condition immunities,
    resistances, and vulnerabilities (0 for an immune target) — the same
    figure the 2024 PHB's concentration-save DC is based on ("half the
    damage you take"). Callers that need to trigger a concentration check
    (see :func:`_concentration_check`) must use this return value, not the
    raw pre-mitigation roll (EFF-07).

    Damage calculations:
    - **Immunity** → damage = 0 (character immunities AND condition-based immunities
      from ``ConditionEffect.immunity_types``).
    - **Resistance** → damage = damage // 2 (character resistances AND condition-based
      all-damage resistance from ``ConditionEffect.damage_resistances_all``).
    - **Vulnerability** → damage = damage * 2
    - Resistance and vulnerability cancel each other out; immunity always wins.

    Temporary hit points absorb damage first, regardless of the target's
    current HP. Dropping to 0 HP knocks the character unconscious and prone
    (2024 PHB "Dropping to 0 Hit Points"); if the remaining damage meets or
    exceeds the HP maximum, the character dies instantly. Damage taken while
    already at 0 HP causes one death save failure (two on a critical hit) —
    unless that leftover damage alone meets or exceeds the HP maximum, which
    is instant (massive-damage) death either way.

    Args:
        target: Character sheet. Modified in-place.
        damage: Raw damage amount.
        damage_type: :class:`~game_engine.types.DamageType` enum.
        critical: Whether the damage came from a critical hit (affects
            death save failures while dying).

    Returns:
        The effective (post-immunity/resistance/vulnerability) damage.
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
            return 0
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
        return 0
    result = effective_damage

    # Temporary hit points absorb damage first, at any HP total — a dying
    # character who still has temp HP from an earlier effect is buffered by
    # it exactly like a conscious one (EFF-13).
    if target.temp_hp > 0:
        absorbed = min(target.temp_hp, effective_damage)
        target.temp_hp -= absorbed
        effective_damage -= absorbed
        if effective_damage <= 0:
            return result

    # Damage while already at 0 HP → death save failures (no HP change),
    # unless the leftover damage alone meets/exceeds hp_max, which is
    # instant (massive-damage) death regardless of the failure count
    # (EFF-08). Monsters don't make death saves: any damage at 0 HP
    # finishes them.
    if target.hp_current <= 0:
        if target.char_type is CharacterType.MONSTER:
            target.death_saves.is_dead = True
            return result
        if effective_damage >= target.hp_max:
            target.death_saves.is_dead = True
            return result
        target.death_saves.is_stable = False
        target.death_saves.failures += 2 if critical else 1
        if target.death_saves.failures >= 3:
            target.death_saves.is_dead = True
        return result

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
    return result


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
    """Return the Constitution save DC to maintain concentration after damage.

    2024 PHB: DC 10 or half the damage taken, whichever is higher, capped
    at 30 (SPL-16) — a single instance of damage can never demand more than
    a DC 30 save.
    """
    return min(30, max(10, damage // 2))


@dataclass
class ConcentrationSaveResult:
    """Typed outcome of a concentration-preserving Constitution save."""

    spell: str
    dc: int
    total: int
    success: bool


def _concentration_check(target: CharacterSheet, damage: int) -> ConcentrationSaveResult | None:
    """Roll the CON save to maintain concentration after taking *damage*.

    *damage* must be the effective (post-immunity/resistance) amount from
    :func:`_apply_damage_effective` — an immune target takes 0 and this
    correctly rolls no save (EFF-07). The single entry point for every
    damage-dealing path (weapon attacks, Graze, spell damage) so the DC
    cap, War Caster advantage, and concentration-loss bookkeeping live in
    one place (Workstream F.1).

    Returns:
        ``None`` if no save was necessary (not concentrating, no damage,
        or already dying); otherwise the rolled outcome. Concentration is
        cleared on a failed save as a side effect.
    """
    if target.concentrating_on is None or damage <= 0 or target.is_dying:
        return None
    dc = concentration_save_dc(damage)
    advantage = Feat.WAR_CASTER in target.feats
    save = _roll_saving_throw_impl(target, Ability.CONSTITUTION, dc, advantage=advantage)
    spell = target.concentrating_on
    if not save.success:
        target.concentrating_on = None
    return ConcentrationSaveResult(spell=spell, dc=dc, total=save.total, success=save.success)


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
