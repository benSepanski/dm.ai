"""
Typed combat-state dataclasses for the game engine.

Split out of :mod:`game_engine.types.sheets` (file-length guideline,
AGENTS.md #3): these are the per-encounter structures (turn economy,
cross-turn effect expiry, attack details) as opposed to the persistent
:class:`~game_engine.types.sheets.CharacterSheet`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from game_engine.types.enums import (
    Ability,
    CoverType,
    DamageType,
    UnarmedStrikeOption,
    WeaponMastery,
    WeaponProperty,
)
from game_engine.types.sheets import CharacterSheet
from game_engine.types.values import DiceNotation


@dataclass(frozen=True)
class EffectExpiry:
    """When a cross-turn effect flag (Help/Sap/Vex) should clear.

    These effects are granted by one combatant but often held on a
    *different* combatant's :class:`TurnState` (e.g. Sap is granted by the
    attacker but disadvantages the target), so their expiry can't be "this
    holder's own turn begins" — it has to name whose turn actually ends the
    effect. The flag clears the next time ``trigger_char_id``'s turn begins
    at a round number ``>= expires_at_round``.
    """

    trigger_char_id: str
    expires_at_round: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict."""
        return {"trigger_char_id": self.trigger_char_id, "expires_at_round": self.expires_at_round}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EffectExpiry":
        """Create an :class:`EffectExpiry` from a dict."""
        return cls(
            trigger_char_id=str(d["trigger_char_id"]),
            expires_at_round=int(d["expires_at_round"]),
        )


@dataclass
class TurnState:
    """Per-combatant action economy and transient flags for the current round."""

    action_used: bool = False
    bonus_action_used: bool = False
    reaction_used: bool = False
    movement_used_ft: int = 0
    attacks_made: int = 0
    dodging: bool = False
    disengaging: bool = False
    dashing: bool = False
    hidden: bool = False
    helped: bool = False
    helped_expiry: EffectExpiry | None = None
    # Weapon mastery carry-over effects
    sapped: bool = False
    sapped_expiry: EffectExpiry | None = None
    vexed_target_id: str | None = None
    vexed_expiry: EffectExpiry | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict so turn state survives between requests."""
        return {
            "action_used": self.action_used,
            "bonus_action_used": self.bonus_action_used,
            "reaction_used": self.reaction_used,
            "movement_used_ft": self.movement_used_ft,
            "attacks_made": self.attacks_made,
            "dodging": self.dodging,
            "disengaging": self.disengaging,
            "dashing": self.dashing,
            "hidden": self.hidden,
            "helped": self.helped,
            "helped_expiry": self.helped_expiry.to_dict() if self.helped_expiry else None,
            "sapped": self.sapped,
            "sapped_expiry": self.sapped_expiry.to_dict() if self.sapped_expiry else None,
            "vexed_target_id": self.vexed_target_id,
            "vexed_expiry": self.vexed_expiry.to_dict() if self.vexed_expiry else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TurnState":
        """Create a :class:`TurnState` from a dict; tolerant of missing keys."""
        vexed = d.get("vexed_target_id")
        helped_expiry = d.get("helped_expiry")
        sapped_expiry = d.get("sapped_expiry")
        vexed_expiry = d.get("vexed_expiry")
        return cls(
            action_used=bool(d.get("action_used", False)),
            bonus_action_used=bool(d.get("bonus_action_used", False)),
            reaction_used=bool(d.get("reaction_used", False)),
            movement_used_ft=int(d.get("movement_used_ft", 0)),
            attacks_made=int(d.get("attacks_made", 0)),
            dodging=bool(d.get("dodging", False)),
            disengaging=bool(d.get("disengaging", False)),
            dashing=bool(d.get("dashing", False)),
            hidden=bool(d.get("hidden", False)),
            helped=bool(d.get("helped", False)),
            helped_expiry=EffectExpiry.from_dict(helped_expiry) if helped_expiry else None,
            sapped=bool(d.get("sapped", False)),
            sapped_expiry=EffectExpiry.from_dict(sapped_expiry) if sapped_expiry else None,
            vexed_target_id=str(vexed) if vexed is not None else None,
            vexed_expiry=EffectExpiry.from_dict(vexed_expiry) if vexed_expiry else None,
        )


def _expiry_reached(expiry: EffectExpiry | None, trigger_char_id: str, round_number: int) -> bool:
    """True when *expiry* fires on *trigger_char_id*'s turn at *round_number*."""
    return (
        expiry is not None
        and expiry.trigger_char_id == trigger_char_id
        and round_number >= expiry.expires_at_round
    )


@dataclass
class CombatStateData:
    """Typed combat state for use by the rule engine."""

    combatants: list[CharacterSheet] = field(default_factory=list)
    round_number: int = 1
    current_turn_index: int = 0
    turn_states: dict[str, TurnState] = field(default_factory=dict)

    def get_combatant(self, char_id: str) -> CharacterSheet | None:
        """Return the combatant with *char_id*, or None."""
        return next((c for c in self.combatants if c.id == char_id), None)

    def turn_state_for(self, char_id: str) -> TurnState:
        """Return (creating if needed) the :class:`TurnState` for *char_id*."""
        return self.turn_states.setdefault(char_id, TurnState())

    def reset_turn(self, char_id: str) -> TurnState:
        """Reset action economy for *char_id* at the start of their turn.

        Only the action-economy fields (action/bonus-action/reaction used,
        movement, attacks made, dodging/disengaging/dashing) are cleared
        here. Cross-turn effect flags (Help/Sap/Vex, and Hide's ``hidden``)
        are left alone — they expire on their own rule-defined trigger, not
        simply because *some* combatant's turn began. See
        :meth:`grant_help`, :meth:`grant_sap`, :meth:`grant_vex`, and
        :meth:`_expire_cross_turn_effects`.
        """
        ts = self.turn_state_for(char_id)
        ts.action_used = False
        ts.bonus_action_used = False
        ts.reaction_used = False
        ts.movement_used_ft = 0
        ts.attacks_made = 0
        ts.dodging = False
        ts.disengaging = False
        ts.dashing = False
        self._expire_cross_turn_effects(char_id)
        return ts

    def _expire_cross_turn_effects(self, trigger_char_id: str) -> None:
        """Clear Help/Sap/Vex flags whose expiry trigger is *trigger_char_id*'s turn."""
        for ts in self.turn_states.values():
            if _expiry_reached(ts.helped_expiry, trigger_char_id, self.round_number):
                ts.helped = False
                ts.helped_expiry = None
            if _expiry_reached(ts.sapped_expiry, trigger_char_id, self.round_number):
                ts.sapped = False
                ts.sapped_expiry = None
            if _expiry_reached(ts.vexed_expiry, trigger_char_id, self.round_number):
                ts.vexed_target_id = None
                ts.vexed_expiry = None

    def grant_help(self, helper_id: str, ally_id: str) -> None:
        """Grant *ally_id* advantage on their next roll (2024 Help action).

        Lasts until the start of *helper_id*'s next turn, or until consumed.
        """
        ts = self.turn_state_for(ally_id)
        ts.helped = True
        ts.helped_expiry = EffectExpiry(helper_id, self.round_number + 1)

    def grant_sap(self, sapper_id: str, target_id: str) -> None:
        """Give *target_id* disadvantage on its next attack roll (Sap mastery).

        Lasts until the start of *sapper_id*'s next turn, or until consumed.
        """
        ts = self.turn_state_for(target_id)
        ts.sapped = True
        ts.sapped_expiry = EffectExpiry(sapper_id, self.round_number + 1)

    def grant_vex(self, attacker_id: str, target_id: str) -> None:
        """Give *attacker_id* advantage on their next attack vs *target_id* (Vex mastery).

        Lasts through the end of *attacker_id*'s next turn, or until consumed.
        """
        ts = self.turn_state_for(attacker_id)
        ts.vexed_target_id = target_id
        ts.vexed_expiry = EffectExpiry(attacker_id, self.round_number + 2)


@dataclass
class AttackDetails:
    """Details for an Attack action."""

    weapon_name: str = "Unarmed Strike"
    damage_dice: DiceNotation = DiceNotation("1d4")
    damage_type: DamageType = DamageType.BLUDGEONING
    attack_ability: Ability = Ability.STRENGTH
    is_ranged: bool = False
    properties: list[WeaponProperty] = field(default_factory=list)
    mastery: WeaponMastery | None = None
    proficient: bool = True
    is_offhand: bool = False
    long_range: bool = False
    target_cover: CoverType | None = None
    unarmed_option: UnarmedStrikeOption | None = None
