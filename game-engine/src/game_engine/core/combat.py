"""
Abstract combat loop for the RPG game engine.

Provides the base class that rule-specific combat implementations extend.
The class manages the combat phase state machine, the initiative tracker,
a structured combat log, and helpers for finding and updating combatants.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum, auto

from game_engine.core.initiative import InitiativeEntry, InitiativeTracker


class CombatPhase(Enum):
    """High-level phases of a combat encounter."""

    INITIATIVE = auto()  # Waiting for initiative to be rolled / sorted
    ACTIVE = auto()      # Combat is ongoing; turns are being taken
    ENDED = auto()       # Combat is over; a winner has been determined


class AbstractCombat(ABC):
    """Base class for a combat encounter.

    Subclasses must implement :meth:`_roll_initiative_for` to integrate with
    a concrete rule engine.

    Attributes:
        combatants: List of character sheet dicts currently in the encounter.
        initiative_tracker: :class:`~game_engine.core.initiative.InitiativeTracker`
            managing turn order.
        round_number: Which round of combat is currently active (starts at 1).
        phase: Current :class:`CombatPhase`.
        combat_log: Ordered list of structured log entry dicts.
    """

    def __init__(self) -> None:
        self.combatants: list[dict] = []
        self.initiative_tracker: InitiativeTracker = InitiativeTracker()
        self.round_number: int = 0
        self.phase: CombatPhase = CombatPhase.INITIATIVE
        self.combat_log: list[dict] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, combatants: list[dict]) -> list[InitiativeEntry]:
        """Initialise the encounter: roll initiative for all combatants and sort.

        Args:
            combatants: List of character sheet dicts entering the encounter.
                Each dict must have at least an ``id`` and ``name`` key.

        Returns:
            The sorted list of :class:`~game_engine.core.initiative.InitiativeEntry`
            objects representing the turn order.
        """
        self.combatants = list(combatants)
        self.initiative_tracker.reset()
        self.round_number = 1
        self.phase = CombatPhase.ACTIVE

        for char in self.combatants:
            initiative_roll = self._roll_initiative_for(char)
            dex_mod = self._dex_modifier_for(char)
            self.initiative_tracker.add_combatant(
                char_id=char["id"],
                name=char.get("name", char["id"]),
                roll=initiative_roll,
                dex_modifier=dex_mod,
            )

        sorted_order = self.initiative_tracker.sort()

        self.log_action(
            actor_id="system",
            action="combat_start",
            result={
                "order": [
                    {"char_id": e.char_id, "total": e.total}
                    for e in sorted_order
                ],
                "round": self.round_number,
            },
            flavor="Combat begins! Roll for initiative.",
        )

        return sorted_order

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def log_action(
        self,
        actor_id: str,
        action: str,
        result: dict,
        flavor: str = "",
    ) -> dict:
        """Append a structured entry to the combat log.

        Args:
            actor_id: ID of the character (or "system") performing the action.
            action: Short action identifier string (e.g. "attack", "cast_spell").
            result: Dict of rule-specific outcome data.
            flavor: Optional human-readable narrative string.

        Returns:
            The log entry dict that was appended.
        """
        entry: dict = {
            "timestamp": time.time(),
            "round": self.round_number,
            "actor_id": actor_id,
            "action": action,
            "result": result,
            "flavor": flavor,
        }
        self.combat_log.append(entry)
        return entry

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_combat_over(self) -> bool:
        """Return True if all remaining active combatants share the same side.

        Sides are determined by the ``side`` key on the character dict
        (default ``"players"`` for PCs, ``"enemies"`` for everything else).
        Combat ends when only one side has living combatants.

        Returns:
            True if combat should end.
        """
        active_sides: set[str] = set()
        for char in self.combatants:
            if char.get("hp_current", 0) > 0:
                side = char.get("side", "enemies" if char.get("char_type") == "MONSTER" else "players")
                active_sides.add(side)

        if len(active_sides) <= 1:
            if self.phase == CombatPhase.ACTIVE:
                self.phase = CombatPhase.ENDED
            return True
        return False

    def get_combatant(self, char_id: str) -> dict | None:
        """Find and return a combatant's character sheet by ID.

        Args:
            char_id: The character ID to look up.

        Returns:
            The character sheet dict, or None if not found.
        """
        for char in self.combatants:
            if char.get("id") == char_id:
                return char
        return None

    def update_combatant(self, char_id: str, updates: dict) -> dict:
        """Apply a dict of updates to a combatant's character sheet.

        Args:
            char_id: The character ID to update.
            updates: Dict of keys/values to merge into the character sheet.

        Returns:
            The updated character sheet dict.

        Raises:
            KeyError: If no combatant with *char_id* is found.
        """
        for char in self.combatants:
            if char.get("id") == char_id:
                char.update(updates)
                return char
        raise KeyError(f"Combatant {char_id!r} not found.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dex_modifier_for(char: dict) -> int:
        """Extract the Dexterity modifier from a character sheet dict.

        Supports both ``ability_scores.dexterity`` nested dicts and a flat
        ``dex_modifier`` key for convenience.

        Args:
            char: Character sheet dict.

        Returns:
            Integer Dexterity modifier.
        """
        if "dex_modifier" in char:
            return int(char["dex_modifier"])
        ability_scores = char.get("ability_scores", {})
        dex = ability_scores.get("dexterity", ability_scores.get("dex", 10))
        return (int(dex) - 10) // 2

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def _roll_initiative_for(self, char: dict) -> int:
        """Roll initiative for a single character.

        Subclasses delegate to their :class:`~game_engine.interface.RuleEngine`
        implementation.

        Args:
            char: Character sheet dict.

        Returns:
            The raw d20 initiative roll (not including DEX modifier).
        """
