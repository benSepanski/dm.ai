"""
Tests for game_engine.core.initiative — InitiativeTracker and InitiativeEntry.
"""

from __future__ import annotations

import pytest

from game_engine.core.initiative import InitiativeEntry, InitiativeTracker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tracker() -> InitiativeTracker:
    return InitiativeTracker()


# ---------------------------------------------------------------------------
# Adding combatants and basic entry creation
# ---------------------------------------------------------------------------


class TestAddCombatant:
    def test_add_returns_entry(self, tracker: InitiativeTracker):
        entry = tracker.add_combatant("hero-1", "Aria", roll=15, dex_modifier=2)
        assert isinstance(entry, InitiativeEntry)

    def test_entry_fields(self, tracker: InitiativeTracker):
        entry = tracker.add_combatant("hero-1", "Aria", roll=15, dex_modifier=2)
        assert entry.char_id == "hero-1"
        assert entry.name == "Aria"
        assert entry.roll == 15
        assert entry.dex_modifier == 2
        assert entry.total == 17  # 15 + 2

    def test_total_computed_correctly(self, tracker: InitiativeTracker):
        entry = tracker.add_combatant("g-1", "Goblin", roll=8, dex_modifier=1)
        assert entry.total == 9

    def test_negative_dex_modifier(self, tracker: InitiativeTracker):
        entry = tracker.add_combatant("orc-1", "Orc", roll=12, dex_modifier=-1)
        assert entry.total == 11

    def test_is_active_defaults_true(self, tracker: InitiativeTracker):
        entry = tracker.add_combatant("hero-1", "Hero", roll=10, dex_modifier=0)
        assert entry.is_active is True


# ---------------------------------------------------------------------------
# sort() — ordering
# ---------------------------------------------------------------------------


class TestSort:
    def test_sorted_descending_by_total(self, tracker: InitiativeTracker):
        tracker.add_combatant("c", "C", roll=8, dex_modifier=0)  # total=8
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)  # total=20
        tracker.add_combatant("b", "B", roll=14, dex_modifier=0)  # total=14

        entries = tracker.sort()
        totals = [e.total for e in entries]
        assert totals == sorted(totals, reverse=True)
        assert totals[0] == 20

    def test_dex_modifier_tiebreaker(self, tracker: InitiativeTracker):
        """When totals are equal, higher dex_modifier breaks the tie."""
        tracker.add_combatant("low-dex", "LowDex", roll=15, dex_modifier=0)  # total=15
        tracker.add_combatant("high-dex", "HighDex", roll=14, dex_modifier=1)  # total=15

        entries = tracker.sort()
        # Both have total=15; high-dex has higher dex_modifier → goes first
        assert entries[0].char_id == "high-dex"
        assert entries[1].char_id == "low-dex"

    def test_sort_returns_list(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        result = tracker.sort()
        assert isinstance(result, list)

    def test_higher_dex_scores_produce_higher_average_totals(self, tracker: InitiativeTracker):
        """Adding same roll but higher dex_modifier → higher total."""
        entry_high = tracker.add_combatant("high", "High", roll=10, dex_modifier=4)
        entry_low = tracker.add_combatant("low", "Low", roll=10, dex_modifier=-1)
        entries = tracker.sort()
        assert entries[0].char_id == "high"
        assert entries[1].char_id == "low"


# ---------------------------------------------------------------------------
# next_turn() — advancing turns
# ---------------------------------------------------------------------------


class TestNextTurn:
    def test_first_next_turn_returns_first_entry(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)
        tracker.add_combatant("b", "B", roll=10, dex_modifier=0)
        tracker.sort()

        first = tracker.next_turn()
        assert first.char_id == "a"  # highest initiative

    def test_sequential_turns_advance(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)
        tracker.add_combatant("b", "B", roll=10, dex_modifier=0)
        tracker.sort()

        first = tracker.next_turn()
        second = tracker.next_turn()
        assert first.char_id != second.char_id

    def test_wraps_around_on_new_round(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)
        tracker.add_combatant("b", "B", roll=10, dex_modifier=0)
        tracker.sort()

        tracker.next_turn()  # A
        tracker.next_turn()  # B
        third = tracker.next_turn()  # wraps back to A
        assert third.char_id == "a"

    def test_skips_inactive_combatant(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)
        tracker.add_combatant("b", "B", roll=15, dex_modifier=0)
        tracker.add_combatant("c", "C", roll=10, dex_modifier=0)
        tracker.sort()

        tracker.set_active("b", False)

        first = tracker.next_turn()  # A
        second = tracker.next_turn()  # should skip B → go to C
        assert first.char_id == "a"
        assert second.char_id == "c"

    def test_no_combatants_raises(self):
        empty_tracker = InitiativeTracker()
        with pytest.raises(RuntimeError):
            empty_tracker.next_turn()

    def test_all_inactive_raises(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        tracker.sort()
        tracker.set_active("a", False)
        with pytest.raises(RuntimeError):
            tracker.next_turn()


# ---------------------------------------------------------------------------
# current_turn()
# ---------------------------------------------------------------------------


class TestCurrentTurn:
    def test_current_turn_before_next_is_none(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        assert tracker.current_turn() is None

    def test_current_turn_matches_last_next_turn(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)
        tracker.add_combatant("b", "B", roll=10, dex_modifier=0)
        tracker.sort()

        entry = tracker.next_turn()
        assert tracker.current_turn() is entry


# ---------------------------------------------------------------------------
# remove_combatant()
# ---------------------------------------------------------------------------


class TestRemoveCombatant:
    def test_remove_existing_returns_true(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        assert tracker.remove_combatant("a") is True

    def test_remove_nonexistent_returns_false(self, tracker: InitiativeTracker):
        assert tracker.remove_combatant("ghost") is False

    def test_removed_combatant_not_in_order(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=20, dex_modifier=0)
        tracker.add_combatant("b", "B", roll=10, dex_modifier=0)
        tracker.sort()
        tracker.remove_combatant("b")

        entries = tracker.to_list()
        char_ids = [e["char_id"] for e in entries]
        assert "b" not in char_ids


# ---------------------------------------------------------------------------
# set_active()
# ---------------------------------------------------------------------------


class TestSetActive:
    def test_set_inactive(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        tracker.set_active("a", False)
        entries = tracker._entries
        assert not entries[0].is_active

    def test_set_active_again(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        tracker.set_active("a", False)
        tracker.set_active("a", True)
        assert tracker._entries[0].is_active is True


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_entries(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        tracker.reset()
        assert tracker.to_list() == []

    def test_reset_allows_reuse(self, tracker: InitiativeTracker):
        tracker.add_combatant("a", "A", roll=10, dex_modifier=0)
        tracker.sort()
        tracker.next_turn()
        tracker.reset()
        tracker.add_combatant("b", "B", roll=15, dex_modifier=0)
        tracker.sort()
        first = tracker.next_turn()
        assert first.char_id == "b"


# ---------------------------------------------------------------------------
# to_list() serialisation
# ---------------------------------------------------------------------------


class TestToList:
    def test_to_list_structure(self, tracker: InitiativeTracker):
        tracker.add_combatant("hero-1", "Hero", roll=18, dex_modifier=3)
        data = tracker.to_list()
        assert len(data) == 1
        record = data[0]
        assert record["char_id"] == "hero-1"
        assert record["name"] == "Hero"
        assert record["roll"] == 18
        assert record["dex_modifier"] == 3
        assert record["total"] == 21
        assert record["is_active"] is True

    def test_to_list_empty(self, tracker: InitiativeTracker):
        assert tracker.to_list() == []

    def test_to_list_reflects_sort_order(self, tracker: InitiativeTracker):
        tracker.add_combatant("low", "Low", roll=5, dex_modifier=0)
        tracker.add_combatant("high", "High", roll=18, dex_modifier=0)
        tracker.sort()
        data = tracker.to_list()
        assert data[0]["char_id"] == "high"
        assert data[1]["char_id"] == "low"
