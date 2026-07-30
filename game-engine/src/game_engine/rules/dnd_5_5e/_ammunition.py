"""Ammunition property: precondition check and inventory spend (EQP-08).

Split out of ``_attacks.py`` (file-length guideline) — a weapon with the
Ammunition property draws from a matching ``InventoryItem`` (e.g. "Arrows"),
named on ``AttackDetails.ammunition_name`` by :mod:`._weapon_bridge`.

Internal module — import via ``_attacks._validate_attack``/``_resolve_attack``.
"""

from __future__ import annotations

from game_engine.types import CharacterSheet


def _has_ammunition(actor: CharacterSheet, ammo_name: str) -> bool:
    """True if *actor*'s inventory has at least one unit of *ammo_name* left."""
    return any(
        item.name.lower() == ammo_name.lower() and item.quantity > 0 for item in actor.inventory
    )


def _consume_ammunition(actor: CharacterSheet, ammo_name: str) -> None:
    """Spend one unit of *ammo_name* from *actor*'s inventory, if any is there.

    A no-op if none is found — callers are expected to have already gated on
    :func:`_has_ammunition` via ``_validate_attack``.
    """
    for item in actor.inventory:
        if item.name.lower() == ammo_name.lower() and item.quantity > 0:
            item.quantity -= 1
            return
