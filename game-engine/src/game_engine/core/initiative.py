"""
Initiative tracker for the RPG game engine.

Manages turn order for combat encounters using the standard D&D initiative
system: highest total goes first, with Dexterity modifier used to break ties.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InitiativeEntry:
    """A single combatant's initiative record.

    Attributes:
        char_id: Unique identifier for the character.
        name: Display name of the character.
        roll: The raw d20 initiative roll.
        dex_modifier: The character's Dexterity modifier (used for tie-breaking).
        total: The final initiative total (roll + dex_modifier).
        is_active: Whether the combatant is still active in combat.
    """

    char_id: str
    name: str
    roll: int
    dex_modifier: int
    total: int
    is_active: bool = True


class InitiativeTracker:
    """Tracks and manages the initiative order for a combat encounter.

    The tracker maintains an ordered list of combatants sorted by initiative
    total (descending), with Dexterity modifier as a tiebreaker.  It supports
    advancing turns, removing combatants (e.g. on death), and toggling a
    combatant's active status.

    Example usage::

        tracker = InitiativeTracker()
        tracker.add_combatant("hero-1", "Aria", roll=15, dex_modifier=2)
        tracker.add_combatant("goblin-1", "Goblin", roll=12, dex_modifier=1)
        tracker.sort()
        first = tracker.next_turn()
    """

    def __init__(self) -> None:
        self._entries: list[InitiativeEntry] = []
        self._current_index: int = -1

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_combatant(
        self,
        char_id: str,
        name: str,
        roll: int,
        dex_modifier: int,
    ) -> InitiativeEntry:
        """Add a combatant to the tracker.

        Args:
            char_id: Unique character identifier.
            name: Display name.
            roll: Raw d20 initiative roll.
            dex_modifier: Dexterity modifier for tie-breaking.

        Returns:
            The newly created :class:`InitiativeEntry`.
        """
        entry = InitiativeEntry(
            char_id=char_id,
            name=name,
            roll=roll,
            dex_modifier=dex_modifier,
            total=roll + dex_modifier,
        )
        self._entries.append(entry)
        return entry

    def sort(self) -> list[InitiativeEntry]:
        """Sort combatants by total (descending), then by dex_modifier (descending).

        Should be called once after all combatants have been added for the
        encounter, and after any mid-combat additions if order matters.

        Returns:
            The sorted list of :class:`InitiativeEntry` objects.
        """
        self._entries.sort(
            key=lambda e: (e.total, e.dex_modifier),
            reverse=True,
        )
        # Reset the current index so the first next_turn() call starts at index 0.
        self._current_index = -1
        return list(self._entries)

    def next_turn(self) -> InitiativeEntry:
        """Advance to the next active combatant and return their entry.

        Skips any combatants whose ``is_active`` flag is False.  Wraps around
        to the beginning of the list when the end is reached.

        Returns:
            The :class:`InitiativeEntry` for the combatant whose turn it now is.

        Raises:
            RuntimeError: If there are no active combatants.
        """
        if not self._entries:
            raise RuntimeError("No combatants in the initiative tracker.")

        active = [e for e in self._entries if e.is_active]
        if not active:
            raise RuntimeError("No active combatants remain.")

        # Walk forward until we find an active entry.
        for _ in range(len(self._entries)):
            self._current_index = (self._current_index + 1) % len(self._entries)
            entry = self._entries[self._current_index]
            if entry.is_active:
                return entry

        raise RuntimeError("No active combatants found after full scan.")

    def current_turn(self) -> InitiativeEntry | None:
        """Return the combatant whose turn it currently is, or None.

        Returns:
            The current :class:`InitiativeEntry`, or None if :meth:`next_turn`
            has not yet been called or the tracker is empty.
        """
        if self._current_index < 0 or not self._entries:
            return None
        return self._entries[self._current_index]

    def remove_combatant(self, char_id: str) -> bool:
        """Remove a combatant from the tracker entirely.

        If the combatant being removed is the current combatant, the current
        index is adjusted so that the next call to :meth:`next_turn` behaves
        correctly.

        Args:
            char_id: The character ID to remove.

        Returns:
            True if the combatant was found and removed; False otherwise.
        """
        for idx, entry in enumerate(self._entries):
            if entry.char_id == char_id:
                self._entries.pop(idx)
                # Adjust current index to remain valid.
                if idx <= self._current_index:
                    self._current_index = max(-1, self._current_index - 1)
                return True
        return False

    def set_active(self, char_id: str, active: bool) -> None:
        """Toggle the active flag for a combatant.

        Inactive combatants are skipped by :meth:`next_turn`.

        Args:
            char_id: The character ID to update.
            active: New value for :attr:`InitiativeEntry.is_active`.
        """
        for entry in self._entries:
            if entry.char_id == char_id:
                entry.is_active = active
                return

    def reset(self) -> None:
        """Clear all combatants and reset the tracker to its initial state."""
        self._entries.clear()
        self._current_index = -1

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_list(self) -> list[dict]:
        """Return a JSON-serialisable representation of the initiative order.

        Returns:
            A list of dicts, one per combatant, in current initiative order.
        """
        return [
            {
                "char_id": e.char_id,
                "name": e.name,
                "roll": e.roll,
                "dex_modifier": e.dex_modifier,
                "total": e.total,
                "is_active": e.is_active,
            }
            for e in self._entries
        ]
