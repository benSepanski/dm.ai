"""Unit tests for combat_utils.roll_and_sort_initiatives.

Extracted from test_combat_utils.py to keep both files under the 600-line
test guideline. The function is also exercised end-to-end via start_combat
HTTP tests in test_combat.py.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from game_engine.rules.dnd_5_5e.engine import DnD55eEngine
from game_engine.types import CharacterType

from dm_api.api.combat_utils import roll_and_sort_initiatives


def _make_char(name: str, dex: int = 10, hp: int = 10, ac: int = 14) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        level=1,
        char_class="Fighter",
        hp_current=hp,
        hp_max=hp,
        ac=ac,
        speed=30,
        type=CharacterType.PC,
        stats={"ability_scores": {"dexterity": dex}},
        spells=None,
        alignment=None,
    )


class TestRollAndSortInitiatives:
    def test_sorted_highest_initiative_first(self, monkeypatch):
        """Characters are returned in descending initiative order."""
        chars = [_make_char("Low"), _make_char("High")]
        initiatives = {"Low": 5, "High": 18}
        monkeypatch.setattr(DnD55eEngine, "roll_initiative", lambda self, s: initiatives[s.name])

        order, combatants = roll_and_sort_initiatives(chars, DnD55eEngine())

        assert [e["name"] for e in order] == ["High", "Low"]
        assert len(combatants) == 2

    def test_dex_tiebreak(self, monkeypatch):
        """Tied rolls are broken by Dexterity score (higher DEX wins)."""
        low_dex = _make_char("LowDex", dex=8)
        high_dex = _make_char("HighDex", dex=16)
        monkeypatch.setattr(DnD55eEngine, "roll_initiative", lambda self, s: 12)

        order, _ = roll_and_sort_initiatives([low_dex, high_dex], DnD55eEngine())

        assert order[0]["name"] == "HighDex"
        assert order[1]["name"] == "LowDex"

    def test_returns_parallel_lists(self, monkeypatch):
        """Both returned lists are the same length and aligned by index."""
        chars = [_make_char("A"), _make_char("B")]
        monkeypatch.setattr(DnD55eEngine, "roll_initiative", lambda self, s: 10)

        order, combatants = roll_and_sort_initiatives(chars, DnD55eEngine())

        assert len(order) == len(combatants) == 2
        for entry in order:
            assert "character_id" in entry
            assert "initiative" in entry
        for sheet_dict in combatants:
            assert "hp_current" in sheet_dict

    def test_order_metadata_references_correct_character(self, monkeypatch):
        """The character_id in each order entry matches the combatant's sheet id."""
        chars = [_make_char("Alice"), _make_char("Bob")]
        counter = iter([15, 10])
        monkeypatch.setattr(DnD55eEngine, "roll_initiative", lambda self, s: next(counter))

        order, combatants = roll_and_sort_initiatives(chars, DnD55eEngine())

        for i, entry in enumerate(order):
            assert entry["character_id"] == combatants[i]["id"]

    def test_empty_input_returns_empty_lists(self):
        order, combatants = roll_and_sort_initiatives([], DnD55eEngine())

        assert order == []
        assert combatants == []
