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
    nick_used: bool = False
    dodging: bool = False
    disengaging: bool = False
    dashing: bool = False
    hidden: bool = False
    # ACT-04: set when a main-hand attack this turn used a Light weapon,
    # the prerequisite for a later bonus-action Two-Weapon Fighting attack.
    light_attack_used: bool = False
    # SPL-06: at most one leveled (non-cantrip, non-ritual) spell per turn.
    leveled_spell_cast: bool = False
    helped: bool = False
    helped_expiry: EffectExpiry | None = None
    # Weapon mastery carry-over effects
    sapped: bool = False
    sapped_expiry: EffectExpiry | None = None
    vexed_target_id: str | None = None
    vexed_expiry: EffectExpiry | None = None
    # ACT-07: Slow mastery reduces the target's speed by 10 ft until the
    # start of the attacker's next turn.
    slowed: bool = False
    slowed_expiry: EffectExpiry | None = None
    # ACT-07: Cleave mastery grants one free follow-up attack against a
    # different creature, once per turn — action-economy state (like
    # nick_used), not a cross-turn effect, so it resets every turn.
    cleave_available: bool = False
    cleave_used: bool = False
    cleave_original_target_id: str | None = None
    # Ready action (2024 PHB): the stored attack to trigger via a reaction.
    # Lost if unused at the start of the readier's own next turn — see
    # CombatStateData.reset_turn.
    readied: ReadiedAction | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict so turn state survives between requests."""
        return {
            "action_used": self.action_used,
            "bonus_action_used": self.bonus_action_used,
            "reaction_used": self.reaction_used,
            "movement_used_ft": self.movement_used_ft,
            "attacks_made": self.attacks_made,
            "nick_used": self.nick_used,
            "dodging": self.dodging,
            "disengaging": self.disengaging,
            "dashing": self.dashing,
            "hidden": self.hidden,
            "light_attack_used": self.light_attack_used,
            "leveled_spell_cast": self.leveled_spell_cast,
            "helped": self.helped,
            "helped_expiry": self.helped_expiry.to_dict() if self.helped_expiry else None,
            "sapped": self.sapped,
            "sapped_expiry": self.sapped_expiry.to_dict() if self.sapped_expiry else None,
            "vexed_target_id": self.vexed_target_id,
            "vexed_expiry": self.vexed_expiry.to_dict() if self.vexed_expiry else None,
            "slowed": self.slowed,
            "slowed_expiry": self.slowed_expiry.to_dict() if self.slowed_expiry else None,
            "cleave_available": self.cleave_available,
            "cleave_used": self.cleave_used,
            "cleave_original_target_id": self.cleave_original_target_id,
            "readied": self.readied.to_dict() if self.readied else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TurnState":
        """Create a :class:`TurnState` from a dict; tolerant of missing keys."""
        vexed = d.get("vexed_target_id")
        helped_expiry = d.get("helped_expiry")
        sapped_expiry = d.get("sapped_expiry")
        vexed_expiry = d.get("vexed_expiry")
        slowed_expiry = d.get("slowed_expiry")
        cleave_original_target_id = d.get("cleave_original_target_id")
        readied = d.get("readied")
        return cls(
            action_used=bool(d.get("action_used", False)),
            bonus_action_used=bool(d.get("bonus_action_used", False)),
            reaction_used=bool(d.get("reaction_used", False)),
            movement_used_ft=int(d.get("movement_used_ft", 0)),
            attacks_made=int(d.get("attacks_made", 0)),
            nick_used=bool(d.get("nick_used", False)),
            dodging=bool(d.get("dodging", False)),
            disengaging=bool(d.get("disengaging", False)),
            dashing=bool(d.get("dashing", False)),
            hidden=bool(d.get("hidden", False)),
            light_attack_used=bool(d.get("light_attack_used", False)),
            leveled_spell_cast=bool(d.get("leveled_spell_cast", False)),
            helped=bool(d.get("helped", False)),
            helped_expiry=EffectExpiry.from_dict(helped_expiry) if helped_expiry else None,
            sapped=bool(d.get("sapped", False)),
            readied=ReadiedAction.from_dict(readied) if readied else None,
            sapped_expiry=EffectExpiry.from_dict(sapped_expiry) if sapped_expiry else None,
            vexed_target_id=str(vexed) if vexed is not None else None,
            vexed_expiry=EffectExpiry.from_dict(vexed_expiry) if vexed_expiry else None,
            slowed=bool(d.get("slowed", False)),
            slowed_expiry=EffectExpiry.from_dict(slowed_expiry) if slowed_expiry else None,
            cleave_available=bool(d.get("cleave_available", False)),
            cleave_used=bool(d.get("cleave_used", False)),
            cleave_original_target_id=(
                str(cleave_original_target_id) if cleave_original_target_id is not None else None
            ),
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
        movement, attacks made, Nick's once-per-turn attack, Cleave's
        once-per-turn follow-up, the Light main-hand attack and
        one-leveled-spell-per-turn flags, dodging/disengaging/dashing) are
        cleared here, plus an unused Readied action — 2024 PHB: a readied
        action is lost if its trigger doesn't happen before the start of your
        next turn. Cross-turn effect flags (Help/Sap/Vex/Slow, and Hide's
        ``hidden``) are left alone — they expire on their own rule-defined
        trigger, not simply because *some* combatant's turn began. See
        :meth:`grant_help`, :meth:`grant_sap`, :meth:`grant_vex`,
        :meth:`grant_slow`, and :meth:`_expire_cross_turn_effects`.
        """
        ts = self.turn_state_for(char_id)
        ts.action_used = False
        ts.bonus_action_used = False
        ts.reaction_used = False
        ts.movement_used_ft = 0
        ts.attacks_made = 0
        ts.nick_used = False
        ts.dodging = False
        ts.disengaging = False
        ts.dashing = False
        ts.light_attack_used = False
        ts.leveled_spell_cast = False
        ts.cleave_available = False
        ts.cleave_used = False
        ts.cleave_original_target_id = None
        ts.readied = None
        self._expire_cross_turn_effects(char_id)
        return ts

    def _expire_cross_turn_effects(self, trigger_char_id: str) -> None:
        """Clear Help/Sap/Vex/Slow flags whose expiry trigger is *trigger_char_id*'s turn."""
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
            if _expiry_reached(ts.slowed_expiry, trigger_char_id, self.round_number):
                ts.slowed = False
                ts.slowed_expiry = None

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

    def grant_slow(self, attacker_id: str, target_id: str) -> None:
        """Reduce *target_id*'s speed by 10 ft (Slow mastery).

        Lasts until the start of *attacker_id*'s next turn.
        """
        ts = self.turn_state_for(target_id)
        ts.slowed = True
        ts.slowed_expiry = EffectExpiry(attacker_id, self.round_number + 1)


@dataclass
class AttackDetails:
    """Details for an Attack action."""

    weapon_name: str = "Unarmed Strike"
    # ACT-11: the 2024 PHB unarmed strike deals a fixed 1 + Strength modifier,
    # not a rolled die — "1d1" always rolls 1, giving the correct flat total
    # via the same dice-notation plumbing every other weapon uses. Classes
    # with scaling unarmed damage (e.g. Monk martial arts) pass their own
    # damage_dice and never fall through to this default.
    damage_dice: DiceNotation = DiceNotation("1d1")
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
    # ACT-07: Cleave's free follow-up attack deals damage without the
    # ability modifier (2024 PHB) — mirrors how is_offhand zeroes a
    # *positive* modifier, except Cleave always zeroes it.
    is_cleave_followup: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict (needed to persist a Readied attack)."""
        return {
            "weapon_name": self.weapon_name,
            "damage_dice": str(self.damage_dice),
            "damage_type": self.damage_type.value,
            "attack_ability": self.attack_ability.value,
            "is_ranged": self.is_ranged,
            "properties": [p.value for p in self.properties],
            "mastery": self.mastery.value if self.mastery else None,
            "proficient": self.proficient,
            "is_offhand": self.is_offhand,
            "long_range": self.long_range,
            "target_cover": self.target_cover.value if self.target_cover else None,
            "unarmed_option": self.unarmed_option.value if self.unarmed_option else None,
            "is_cleave_followup": self.is_cleave_followup,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AttackDetails":
        """Create an :class:`AttackDetails` from a dict; tolerant of missing keys."""
        target_cover = d.get("target_cover")
        unarmed_option = d.get("unarmed_option")
        mastery = d.get("mastery")
        return cls(
            weapon_name=str(d.get("weapon_name", "Unarmed Strike")),
            damage_dice=DiceNotation(d.get("damage_dice", "1d1")),
            damage_type=DamageType(d.get("damage_type", DamageType.BLUDGEONING.value)),
            attack_ability=Ability(d.get("attack_ability", Ability.STRENGTH.value)),
            is_ranged=bool(d.get("is_ranged", False)),
            properties=[WeaponProperty(p) for p in d.get("properties", [])],
            mastery=WeaponMastery(mastery) if mastery else None,
            proficient=bool(d.get("proficient", True)),
            is_offhand=bool(d.get("is_offhand", False)),
            long_range=bool(d.get("long_range", False)),
            target_cover=CoverType(target_cover) if target_cover else None,
            unarmed_option=UnarmedStrikeOption(unarmed_option) if unarmed_option else None,
            is_cleave_followup=bool(d.get("is_cleave_followup", False)),
        )


@dataclass(frozen=True)
class ReadiedAction:
    """A stored Ready action (2024 PHB), triggered later via a reaction.

    Only readying an attack is supported — the common table use of Ready
    ("I ready an attack on whoever comes through the door") — not readying a
    spell or other action; ``trigger`` is a free-text record of the
    player-stated condition for the DM/UI to adjudicate, not itself enforced
    by the engine.
    """

    trigger: str
    target_id: str | None
    details: AttackDetails | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict."""
        return {
            "trigger": self.trigger,
            "target_id": self.target_id,
            "details": self.details.to_dict() if self.details else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReadiedAction":
        """Create a :class:`ReadiedAction` from a dict."""
        details = d.get("details")
        return cls(
            trigger=str(d.get("trigger", "")),
            target_id=d.get("target_id"),
            details=AttackDetails.from_dict(details) if details else None,
        )
