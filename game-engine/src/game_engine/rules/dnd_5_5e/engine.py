"""
D&D 5.5e Rule Engine implementation.

Implements the :class:`~game_engine.interface.RuleEngine` abstract interface
for the 2024 revision of the Dungeons & Dragons 5th Edition rules (5.5e /
"One D&D").
"""

from __future__ import annotations

from game_engine.core.conditions import (
    CONDITION_EFFECTS,
    condition_prevents_action,
    is_immune_to_condition,
)
from game_engine.core.dice import (
    roll_dice,
    roll_with_advantage,
    roll_with_disadvantage,
)
from game_engine.interface import (
    Action,
    ActionResult,
    CheckResult,
    RuleEngine,
    ValidationResult,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Maps every D&D 5e skill to its governing ability score (lowercase).
SKILL_ABILITY_MAP: dict[str, str] = {
    "acrobatics": "dexterity",
    "animal handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight of hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
    # Allow raw ability checks too
    "strength": "strength",
    "dexterity": "dexterity",
    "constitution": "constitution",
    "intelligence": "intelligence",
    "wisdom": "wisdom",
    "charisma": "charisma",
}

#: Ability score short names to full names.
_ABILITY_FULL: dict[str, str] = {
    "str": "strength",
    "dex": "dexterity",
    "con": "constitution",
    "int": "intelligence",
    "wis": "wisdom",
    "cha": "charisma",
}

#: All basic combat actions available in D&D 5.5e.
_ALL_BASIC_ACTIONS: list[str] = [
    "Attack",
    "Dash",
    "Disengage",
    "Dodge",
    "Help",
    "Hide",
    "Ready",
    "Search",
    "Use Object",
]

#: Actions that require the character to be able to act.
_REQUIRES_ABILITY_TO_ACT: set[str] = {
    "Attack",
    "Dash",
    "Disengage",
    "Dodge",
    "Help",
    "Hide",
    "Ready",
    "Search",
    "Use Object",
}

#: Valid D&D class names (5.5e / 2024 PHB).
_VALID_CLASSES: frozenset[str] = frozenset(
    {
        "Artificer",
        "Barbarian",
        "Bard",
        "Cleric",
        "Druid",
        "Fighter",
        "Monk",
        "Paladin",
        "Ranger",
        "Rogue",
        "Sorcerer",
        "Warlock",
        "Wizard",
    }
)

#: Valid D&D race/species names (non-exhaustive sample).
_VALID_RACES: frozenset[str] = frozenset(
    {
        "Aasimar",
        "Dragonborn",
        "Dwarf",
        "Elf",
        "Gnome",
        "Goliath",
        "Half-Elf",
        "Half-Orc",
        "Halfling",
        "Human",
        "Orc",
        "Tiefling",
        # monsters / other
        "Custom",
        "Other",
    }
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class DnD55eEngine(RuleEngine):
    """Concrete rule engine for D&D 5.5e (2024 Player's Handbook).

    All methods operate on plain :class:`dict` objects representing character
    sheets so that they integrate easily with REST APIs and serialisation
    layers.  The expected shape of a character dict is documented on each
    method.
    """

    # ------------------------------------------------------------------
    # Proficiency bonus
    # ------------------------------------------------------------------

    def calculate_proficiency_bonus(self, level: int) -> int:
        """Return the proficiency bonus for *level*.

        Args:
            level: Character level (1-20).

        Returns:
            Proficiency bonus: +2 (1-4), +3 (5-8), +4 (9-12), +5 (13-16),
            +6 (17-20).

        Raises:
            ValueError: If *level* is outside 1-20.
        """
        if not 1 <= level <= 20:
            raise ValueError(f"Level must be between 1 and 20, got {level}.")
        return 2 + (level - 1) // 4

    # ------------------------------------------------------------------
    # Initiative
    # ------------------------------------------------------------------

    def roll_initiative(self, char: dict) -> int:
        """Roll initiative: d20 + Dexterity modifier.

        Args:
            char: Character sheet dict containing ``ability_scores.dexterity``.

        Returns:
            Integer initiative total.
        """
        dex = self._get_ability_score(char, "dexterity")
        dex_mod = (dex - 10) // 2
        raw, _ = roll_dice(1, 20)
        return raw + dex_mod

    # ------------------------------------------------------------------
    # Skill / ability checks
    # ------------------------------------------------------------------

    def roll_check(
        self,
        char: dict,
        skill: str,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False,
    ) -> CheckResult:
        """Roll a skill or ability check against *dc*.

        The governing ability is looked up via :data:`SKILL_ABILITY_MAP`.
        If the character is proficient in the skill (``skill`` present in
        ``char["proficiencies"]``), the proficiency bonus is added.

        Args:
            char: Character sheet dict.
            skill: Skill name or raw ability name (case-insensitive).
            dc: Difficulty class (integer).
            advantage: Roll twice and take the higher result.
            disadvantage: Roll twice and take the lower result.  Advantage
                takes precedence if both are True.

        Returns:
            :class:`~game_engine.interface.CheckResult`.

        Raises:
            ValueError: If *skill* is not recognised.
        """
        skill_lower = skill.lower()
        ability = SKILL_ABILITY_MAP.get(skill_lower)
        if ability is None:
            # Try expanding short ability names
            ability = _ABILITY_FULL.get(skill_lower)
        if ability is None:
            raise ValueError(
                f"Unknown skill or ability {skill!r}.  "
                f"Valid skills: {sorted(SKILL_ABILITY_MAP.keys())}"
            )

        ability_score = self._get_ability_score(char, ability)
        ability_mod = (ability_score - 10) // 2

        level = char.get("level", 1)
        prof_bonus = self.calculate_proficiency_bonus(level)

        proficiencies: list[str] = [
            p.lower() for p in char.get("proficiencies", [])
        ]
        is_proficient = skill_lower in proficiencies or ability in proficiencies
        total_mod = ability_mod + (prof_bonus if is_proficient else 0)

        # Roll
        if advantage and not disadvantage:
            raw_roll, _ = roll_with_advantage(20)
        elif disadvantage and not advantage:
            raw_roll, _ = roll_with_disadvantage(20)
        else:
            raw_roll, _ = roll_dice(1, 20)

        total = raw_roll + total_mod
        return CheckResult(
            success=total >= dc,
            roll=raw_roll,
            total=total,
            dc=dc,
            margin=total - dc,
        )

    # ------------------------------------------------------------------
    # Damage
    # ------------------------------------------------------------------

    def apply_damage(
        self, target: dict, damage: int, damage_type: str
    ) -> dict:
        """Apply damage to *target*, respecting resistances and immunities.

        Damage calculations:
        - **Immunity** → damage = 0
        - **Resistance** → damage = damage // 2
        - **Vulnerability** → damage = damage * 2
        - Petrified creatures have resistance to all damage.

        Args:
            target: Character sheet dict.  Modified in-place.
            damage: Raw damage amount.
            damage_type: Damage type string (e.g. ``"fire"``).

        Returns:
            Updated character sheet dict.
        """
        dt = damage_type.lower()
        immunities: list[str] = [
            x.lower() for x in target.get("damage_immunities", [])
        ]
        resistances: list[str] = [
            x.lower() for x in target.get("damage_resistances", [])
        ]
        vulnerabilities: list[str] = [
            x.lower() for x in target.get("damage_vulnerabilities", [])
        ]

        # Petrified → resistance to all damage
        conditions_lower = [c.lower() for c in target.get("conditions", [])]
        if "petrified" in conditions_lower and dt not in resistances:
            resistances.append(dt)

        if dt in immunities:
            effective_damage = 0
        elif dt in resistances:
            effective_damage = damage // 2
        elif dt in vulnerabilities:
            effective_damage = damage * 2
        else:
            effective_damage = damage

        current_hp = target.get("hp_current", 0)
        target["hp_current"] = max(0, current_hp - effective_damage)
        return target

    # ------------------------------------------------------------------
    # Conditions
    # ------------------------------------------------------------------

    def apply_condition(
        self,
        target: dict,
        condition: str,
        duration_rounds: int | None = None,
    ) -> dict:
        """Apply *condition* to *target* if not immune.

        Args:
            target: Character sheet dict.
            condition: Condition name (case-insensitive).
            duration_rounds: Optional duration in rounds (stored for reference).

        Returns:
            Updated character sheet dict.
        """
        condition_lower = condition.lower()

        if is_immune_to_condition(target, condition_lower):
            return target

        conditions: list[str] = target.setdefault("conditions", [])
        if condition_lower not in [c.lower() for c in conditions]:
            conditions.append(condition_lower)

        # Store duration metadata if provided
        if duration_rounds is not None:
            durations: dict = target.setdefault("condition_durations", {})
            durations[condition_lower] = duration_rounds

        return target

    def remove_condition(self, target: dict, condition: str) -> dict:
        """Remove *condition* from *target*.

        Args:
            target: Character sheet dict.
            condition: Condition name (case-insensitive).

        Returns:
            Updated character sheet dict.
        """
        condition_lower = condition.lower()
        conditions: list[str] = target.get("conditions", [])
        target["conditions"] = [
            c for c in conditions if c.lower() != condition_lower
        ]
        # Also clear any stored duration
        durations: dict = target.get("condition_durations", {})
        durations.pop(condition_lower, None)
        return target

    # ------------------------------------------------------------------
    # Available actions
    # ------------------------------------------------------------------

    def get_available_actions(
        self, char: dict, combat_state: dict
    ) -> list[Action]:
        """Return the list of actions the character may legally take.

        Actions are filtered by the character's current conditions.

        Args:
            char: Character sheet dict.
            combat_state: Current combat state dict (used to look up targets).

        Returns:
            List of :class:`~game_engine.interface.Action` objects.
        """
        char_id = char.get("id", "unknown")
        available: list[Action] = []

        can_act = not condition_prevents_action(char) and char.get("hp_current", 0) > 0

        for action_name in _ALL_BASIC_ACTIONS:
            if action_name in _REQUIRES_ABILITY_TO_ACT and not can_act:
                continue
            available.append(
                Action(
                    action_type=action_name,
                    actor_id=char_id,
                    target_id=None,
                    details={},
                )
            )

        return available

    # ------------------------------------------------------------------
    # Action resolution
    # ------------------------------------------------------------------

    def resolve_action(
        self, action: Action, combat_state: dict
    ) -> ActionResult:
        """Resolve *action* and return the outcome.

        Currently handles the **Attack** action with a full to-hit and damage
        roll.  Other action types are logged as successful with 0 damage.

        Args:
            action: The action to resolve.
            combat_state: Combat state dict, expected to contain a
                ``"combatants"`` list of character sheet dicts.

        Returns:
            :class:`~game_engine.interface.ActionResult`.
        """
        if action.action_type == "Attack":
            return self._resolve_attack(action, combat_state)
        # Generic non-attack action — simply succeeds.
        return ActionResult(
            success=True,
            damage=0,
            damage_type="",
            conditions_applied=[],
            flavor_text=f"{action.actor_id} uses {action.action_type}.",
            log_entry={
                "actor_id": action.actor_id,
                "action_type": action.action_type,
                "target_id": action.target_id,
                "details": action.details,
            },
        )

    def _resolve_attack(
        self, action: Action, combat_state: dict
    ) -> ActionResult:
        """Resolve an Attack action."""
        combatants: list[dict] = combat_state.get("combatants", [])
        actor = next(
            (c for c in combatants if c.get("id") == action.actor_id), {}
        )
        target = next(
            (c for c in combatants if c.get("id") == action.target_id), None
        )

        if target is None:
            return ActionResult(
                success=False,
                damage=0,
                damage_type="",
                conditions_applied=[],
                flavor_text="No target found.",
                log_entry={"error": "target_not_found", "target_id": action.target_id},
            )

        target_ac: int = target.get("ac", 10)

        # Determine attack modifier
        weapon = action.details.get("weapon", {})
        attack_ability = weapon.get("attack_ability", "strength")
        ability_score = self._get_ability_score(actor, attack_ability)
        ability_mod = (ability_score - 10) // 2
        level = actor.get("level", 1)
        prof_bonus = self.calculate_proficiency_bonus(level)

        # Roll to hit
        attack_roll_raw, _ = roll_dice(1, 20)
        attack_total = attack_roll_raw + ability_mod + prof_bonus

        hit = attack_roll_raw == 20 or attack_total >= target_ac
        critical = attack_roll_raw == 20

        if not hit:
            return ActionResult(
                success=False,
                damage=0,
                damage_type=weapon.get("damage_type", "bludgeoning"),
                conditions_applied=[],
                flavor_text=(
                    f"{actor.get('name', action.actor_id)} misses "
                    f"{target.get('name', action.target_id)}! "
                    f"(rolled {attack_roll_raw} + {ability_mod + prof_bonus} = "
                    f"{attack_total} vs AC {target_ac})"
                ),
                log_entry={
                    "actor_id": action.actor_id,
                    "target_id": action.target_id,
                    "attack_roll": attack_roll_raw,
                    "attack_total": attack_total,
                    "target_ac": target_ac,
                    "hit": False,
                },
            )

        # Roll damage
        damage_dice = weapon.get("damage_dice", "1d6")
        damage_type = weapon.get("damage_type", "bludgeoning")
        damage_mod = ability_mod

        from game_engine.core.dice import roll as dice_roll

        if critical:
            # Critical: roll damage dice twice
            dmg1, _ = dice_roll(damage_dice)
            dmg2, _ = dice_roll(damage_dice)
            total_damage = dmg1 + dmg2 + damage_mod
        else:
            raw_dmg, _ = dice_roll(damage_dice)
            total_damage = max(0, raw_dmg + damage_mod)

        # Apply damage to target (in-place)
        self.apply_damage(target, total_damage, damage_type)

        flavor = (
            f"{'CRITICAL HIT! ' if critical else ''}"
            f"{actor.get('name', action.actor_id)} hits "
            f"{target.get('name', action.target_id)} for {total_damage} "
            f"{damage_type} damage! "
            f"(roll {attack_roll_raw} + {ability_mod + prof_bonus} = "
            f"{attack_total} vs AC {target_ac})"
        )

        return ActionResult(
            success=True,
            damage=total_damage,
            damage_type=damage_type,
            conditions_applied=[],
            flavor_text=flavor,
            log_entry={
                "actor_id": action.actor_id,
                "target_id": action.target_id,
                "attack_roll": attack_roll_raw,
                "attack_total": attack_total,
                "target_ac": target_ac,
                "hit": True,
                "critical": critical,
                "damage": total_damage,
                "damage_type": damage_type,
                "target_hp_remaining": target.get("hp_current"),
            },
        )

    # ------------------------------------------------------------------
    # Character validation
    # ------------------------------------------------------------------

    def validate_character(self, sheet: dict) -> ValidationResult:
        """Validate a character sheet for completeness and legality.

        Required fields: ``id``, ``name``, ``level``, ``class``,
        ``ability_scores`` (with all six scores in range 1-30), ``hp_max``
        (> 0), ``ac`` (>= 0).

        Args:
            sheet: Character sheet dict.

        Returns:
            :class:`~game_engine.interface.ValidationResult`.
        """
        errors: list[str] = []

        # Required top-level fields
        for field_name in ("id", "name", "level"):
            if field_name not in sheet:
                errors.append(f"Missing required field: '{field_name}'.")

        # Level range
        level = sheet.get("level")
        if level is not None:
            if not isinstance(level, int) or not 1 <= level <= 20:
                errors.append(
                    f"'level' must be an integer between 1 and 20, got {level!r}."
                )

        # Class
        char_class = sheet.get("class")
        if char_class is None:
            errors.append("Missing required field: 'class'.")
        elif char_class not in _VALID_CLASSES:
            errors.append(
                f"Unknown class {char_class!r}.  "
                f"Valid classes: {sorted(_VALID_CLASSES)}."
            )

        # Ability scores
        ability_scores = sheet.get("ability_scores")
        if ability_scores is None:
            errors.append("Missing required field: 'ability_scores'.")
        elif not isinstance(ability_scores, dict):
            errors.append("'ability_scores' must be a dict.")
        else:
            required_abilities = {
                "strength", "dexterity", "constitution",
                "intelligence", "wisdom", "charisma",
            }
            for ability in required_abilities:
                score = ability_scores.get(ability)
                if score is None:
                    errors.append(f"Missing ability score: '{ability}'.")
                elif not isinstance(score, int) or not 1 <= score <= 30:
                    errors.append(
                        f"Ability score '{ability}' must be an integer between "
                        f"1 and 30, got {score!r}."
                    )

        # HP
        hp_max = sheet.get("hp_max")
        if hp_max is None:
            errors.append("Missing required field: 'hp_max'.")
        elif not isinstance(hp_max, int) or hp_max <= 0:
            errors.append(f"'hp_max' must be a positive integer, got {hp_max!r}.")

        # AC
        ac = sheet.get("ac")
        if ac is None:
            errors.append("Missing required field: 'ac'.")
        elif not isinstance(ac, (int, float)) or ac < 0:
            errors.append(f"'ac' must be a non-negative number, got {ac!r}.")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_ability_score(char: dict, ability: str) -> int:
        """Extract an ability score from a character sheet dict.

        Supports both long-form (``"strength"``) and short-form (``"str"``)
        keys, as well as a flat ``"dex"``-style key at the top level.

        Args:
            char: Character sheet dict.
            ability: Full ability name (e.g. ``"dexterity"``).

        Returns:
            Integer ability score (default 10 if not found).
        """
        ability_scores = char.get("ability_scores", {})
        score = ability_scores.get(ability)
        if score is not None:
            return int(score)
        # Try short-form
        short = ability[:3]
        score = ability_scores.get(short)
        if score is not None:
            return int(score)
        # Fall back to top-level key (legacy format)
        score = char.get(ability, char.get(short, 10))
        return int(score)
