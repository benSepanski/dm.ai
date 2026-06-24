"""
D&D 5.5e death saving throws and stabilization.

Internal module — import via :class:`DnD55eEngine`.
"""

from __future__ import annotations

from game_engine.core.dice import roll_dice
from game_engine.interface import DeathSaveResult
from game_engine.rules.dnd_5_5e._damage import _apply_healing_impl
from game_engine.types import CharacterSheet, DeathSaveOutcome


def _roll_death_save_impl(char: CharacterSheet) -> DeathSaveResult:
    """Roll a death saving throw for a dying character.

    Rules (2024 PHB):
    - Natural 20 (raw): regain 1 hit point (conscious again) — triggers on raw roll.
    - Natural 1 (raw): two failures — triggers on raw roll.
    - Adjusted total ≥ 10: one success; three successes → stable.
    - Adjusted total < 10: one failure; three failures → dead.

    Exhaustion applies: the 2024 PHB defines death saving throws as "special
    D20 Tests," and the exhaustion penalty (−2 per level) applies to all D20
    Tests. Natural 1/20 effects trigger on the unmodified raw d20; only the
    10+ success threshold uses the exhaustion-adjusted total.

    Args:
        char: Character sheet. Must be dying (0 HP, not stable, not dead).

    Returns:
        :class:`~game_engine.interface.DeathSaveResult`.

    Raises:
        ValueError: If the character is not currently dying.
    """
    if not char.is_dying:
        raise ValueError(f"{char.name or char.id} is not dying; no death save is needed.")

    raw_roll, _ = roll_dice(1, 20)
    total = raw_roll + char.d20_modifier
    saves = char.death_saves
    regained_hp = False

    if raw_roll == 20:
        outcome = DeathSaveOutcome.CRITICAL_SUCCESS
        _apply_healing_impl(char, 1)
        regained_hp = True
    elif raw_roll == 1:
        outcome = DeathSaveOutcome.CRITICAL_FAILURE
        saves.failures += 2
    elif total >= 10:
        outcome = DeathSaveOutcome.SUCCESS
        saves.successes += 1
    else:
        outcome = DeathSaveOutcome.FAILURE
        saves.failures += 1

    if saves.failures >= 3:
        saves.is_dead = True
    elif saves.successes >= 3:
        saves.is_stable = True

    return DeathSaveResult(
        outcome=outcome,
        roll=raw_roll,
        total=total,
        successes=saves.successes,
        failures=saves.failures,
        is_stable=saves.is_stable,
        is_dead=saves.is_dead,
        regained_hp=regained_hp,
    )


def _stabilize_impl(char: CharacterSheet) -> CharacterSheet:
    """Stabilize a dying character (e.g. via a DC 10 Medicine check or Healer's Kit).

    A stable character stays unconscious at 0 HP but no longer makes death
    saves. Death save counters are cleared (2024 PHB).

    Args:
        char: Character sheet. Modified in-place and returned.

    Returns:
        Updated character sheet.
    """
    if char.is_dead or char.hp_current > 0:
        return char
    char.death_saves.successes = 0
    char.death_saves.failures = 0
    char.death_saves.is_stable = True
    return char
