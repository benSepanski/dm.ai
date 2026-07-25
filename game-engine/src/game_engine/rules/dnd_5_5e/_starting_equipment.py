"""
Starting-equipment expansion for character creation (2024 PHB ch. 6, EQP-05).

``BackgroundData.equipment`` is a free-text list (e.g. ``"Dagger (2)"``,
``"8 gp"``, ``"Explorer's Pack"``) copied straight from the PHB background
tables. :func:`resolve_starting_equipment` turns that into a structured
``list[InventoryItem]`` plus a ``Currency``, so ``build_character`` can
actually populate ``CharacterSheet.inventory``/``CharacterSheet.currency``
instead of leaving them at their empty/zero defaults.

Internal module — import :func:`resolve_starting_equipment` via
:mod:`game_engine.rules.dnd_5_5e`.
"""

from __future__ import annotations

import re

from game_engine.rules.dnd_5_5e.data.gear import PACKS_BY_NAME
from game_engine.types import Currency, InventoryItem

#: "8 gp", "32 gp" — a bare gold amount, folded into Currency.gp.
_GOLD_RE = re.compile(r"^(\d+)\s*gp$", re.IGNORECASE)

#: A trailing parenthetical that is *purely* digits is a quantity, e.g.
#: "Dagger (2)" -> quantity 2. Anything else in parens ("Book (prayers)",
#: "Artisan's Tools (choice)", "Parchment (10 sheets)") is a descriptor and
#: stays part of the item name verbatim — it isn't a count we can parse
#: without guessing units.
_QUANTITY_RE = re.compile(r"^(.+?)\s*\((\d+)\)$")


def _append_item(text: str, items: list[InventoryItem]) -> None:
    """Append one :class:`InventoryItem` for *text*, splitting a bare quantity."""
    match = _QUANTITY_RE.match(text)
    if match:
        items.append(InventoryItem(name=match.group(1), quantity=int(match.group(2))))
    else:
        items.append(InventoryItem(name=text))


def resolve_starting_equipment(equipment: list[str]) -> tuple[list[InventoryItem], Currency]:
    """Expand raw background ``equipment`` strings into inventory + currency.

    - Gold entries (``"N gp"``) accumulate into the returned ``Currency.gp``.
    - Pack names (``"Explorer's Pack"``) expand into their registered
      ``PackData.contents`` rather than being added as one opaque item.
    - Everything else becomes one ``InventoryItem``, with a purely-numeric
      parenthetical read as ``quantity`` (see ``_QUANTITY_RE``).
    """
    items: list[InventoryItem] = []
    gp = 0
    for raw_entry in equipment:
        entry = raw_entry.strip()
        gold_match = _GOLD_RE.match(entry)
        if gold_match:
            gp += int(gold_match.group(1))
            continue
        pack = PACKS_BY_NAME.get(entry.lower())
        if pack is not None:
            for content in pack.contents:
                _append_item(content, items)
            continue
        _append_item(entry, items)
    return items, Currency(gp=gp)
