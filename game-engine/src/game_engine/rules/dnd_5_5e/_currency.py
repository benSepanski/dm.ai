"""
Coin debit/credit and equipment purchase (2024 PHB ch. 6, EQP-11).

``Currency`` stores the five denominations and can already report
``total_gp``, but nothing could ever change a character's coin: there was no
debit/credit helper and no path linking a registry item's ``cost_gp`` to a
character's purse. This module adds both, plus :func:`purchase_item`, which
ties spend + inventory together the same way ``_starting_equipment`` ties
starting gold + inventory together.

Internal module — import via :mod:`game_engine.rules.dnd_5_5e`.
"""

from __future__ import annotations

from game_engine.rules.dnd_5_5e._starting_equipment import _append_item
from game_engine.rules.dnd_5_5e.data.armor import get_armor
from game_engine.rules.dnd_5_5e.data.gear import PACKS_BY_NAME, get_gear, get_tool
from game_engine.rules.dnd_5_5e.data.weapons import get_weapon
from game_engine.types import CharacterSheet, Currency, InventoryItem

#: Copper pieces per unit of each denomination (SRD 5.2 coinage table).
_CP_PER_UNIT: dict[str, int] = {"cp": 1, "sp": 10, "ep": 50, "gp": 100, "pp": 1000}


def to_copper(currency: Currency) -> int:
    """Total value of *currency* expressed in whole copper pieces."""
    return (
        currency.cp * _CP_PER_UNIT["cp"]
        + currency.sp * _CP_PER_UNIT["sp"]
        + currency.ep * _CP_PER_UNIT["ep"]
        + currency.gp * _CP_PER_UNIT["gp"]
        + currency.pp * _CP_PER_UNIT["pp"]
    )


def from_copper(total_cp: int) -> Currency:
    """Express *total_cp* copper pieces as the fewest pp/gp/sp/cp coins.

    Electrum is deliberately never (re-)introduced when breaking change —
    it's the one denomination the 2024 PHB itself calls a legacy holdover
    or coins from the pack rather than currency any shop hands back.
    """
    pp, remainder = divmod(total_cp, _CP_PER_UNIT["pp"])
    gp, remainder = divmod(remainder, _CP_PER_UNIT["gp"])
    sp, cp = divmod(remainder, _CP_PER_UNIT["sp"])
    return Currency(cp=cp, sp=sp, ep=0, gp=gp, pp=pp)


def can_afford(currency: Currency, cost_gp: float) -> bool:
    """True if *currency* is worth at least *cost_gp* gold pieces."""
    return to_copper(currency) >= round(cost_gp * _CP_PER_UNIT["gp"])


def spend_gold(currency: Currency, cost_gp: float) -> bool:
    """Debit *cost_gp* gold pieces from *currency* in place.

    Returns ``False`` (no mutation) if *currency* can't cover the cost.
    Coin is re-broken into the fewest denominations after spending — SRD 5.2
    gives no rule for tracking exact coins spent, only total value.
    """
    cost_cp = round(cost_gp * _CP_PER_UNIT["gp"])
    total_cp = to_copper(currency)
    if total_cp < cost_cp:
        return False
    remainder = from_copper(total_cp - cost_cp)
    currency.cp, currency.sp, currency.ep, currency.gp, currency.pp = (
        remainder.cp,
        remainder.sp,
        remainder.ep,
        remainder.gp,
        remainder.pp,
    )
    return True


def credit_gold(currency: Currency, amount_gp: float) -> None:
    """Credit *amount_gp* gold pieces to *currency* in place (loot, sale, pay)."""
    total = from_copper(to_copper(currency) + round(amount_gp * _CP_PER_UNIT["gp"]))
    currency.cp, currency.sp, currency.ep, currency.gp, currency.pp = (
        total.cp,
        total.sp,
        total.ep,
        total.gp,
        total.pp,
    )


def _lookup_item(name: str) -> tuple[str, float, float] | list[str] | None:
    """Resolve *name* against the weapon/armor/gear/tool/pack registries.

    Returns ``(canonical_name, cost_gp, weight_lb)`` for a single item, the
    pack's ``contents`` list for a pack (its own weight comes from those
    contents, mirroring ``resolve_starting_equipment``), or ``None`` if
    *name* matches nothing.
    """
    weapon = get_weapon(name)
    if weapon is not None:
        return weapon.name, weapon.cost_gp, weapon.weight_lb
    armor = get_armor(name)
    if armor is not None:
        return armor.name, armor.cost_gp, armor.weight_lb
    gear = get_gear(name)
    if gear is not None:
        return gear.name, gear.cost_gp, gear.weight_lb
    tool = get_tool(name)
    if tool is not None:
        return tool.name, tool.cost_gp, tool.weight_lb
    pack = PACKS_BY_NAME.get(name.lower())
    if pack is not None:
        return pack.contents
    return None


def _add_or_stack(sheet: CharacterSheet, name: str, quantity: int, weight_lb: float) -> None:
    for item in sheet.inventory:
        if item.name == name and item.weight_lb == weight_lb:
            item.quantity += quantity
            return
    sheet.inventory.append(InventoryItem(name=name, quantity=quantity, weight_lb=weight_lb))


def purchase_item(sheet: CharacterSheet, item_name: str, quantity: int = 1) -> bool:
    """Buy *quantity* of *item_name* from the weapon/armor/gear/tool/pack
    registries, debiting ``sheet.currency`` and adding to ``sheet.inventory``.

    Returns ``False`` with no mutation at all (no partial spend, no partial
    inventory change) if *item_name* is unknown or unaffordable at the given
    *quantity*.
    """
    found = _lookup_item(item_name)
    if found is None:
        return False
    if isinstance(found, list):
        # Packs are priced as a whole (PackData.cost_gp) but expand into
        # their individual contents, exactly like starting equipment.
        pack = PACKS_BY_NAME[item_name.lower()]
        if not spend_gold(sheet.currency, pack.cost_gp * quantity):
            return False
        for _ in range(quantity):
            for content in pack.contents:
                _append_item(content, sheet.inventory)
        return True
    canonical_name, cost_gp, weight_lb = found
    if not spend_gold(sheet.currency, cost_gp * quantity):
        return False
    _add_or_stack(sheet, canonical_name, quantity, weight_lb)
    return True
