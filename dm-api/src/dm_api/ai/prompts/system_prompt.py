"""System prompt builder for the DM orchestrator.

Harness-engineering guidance encoded into the prompt (per
https://openai.com/index/harness-engineering/):

- **Single source of truth.** The prompt points the model at the world/session
  IDs so grounding always goes through the repository, not free-form recall.
- **Typed boundaries.** The ``[PROPOSAL]`` block enumerates its schema
  explicitly — ``type`` must be one of the :class:`ProposalType` values, and
  ``content`` is structured JSON, never prose.
- **Citation anchors.** The model is instructed to cite ``msg:<uuid>@<ts>``
  anchors from any ``[CONDENSED SYNOPSIS]`` / ``[ESTABLISHED FACTS]`` blocks
  injected upstream by the condenser.
- **Concise, role-neutral system text.** Kept short per the harness guidance
  that ``AGENTS.md``-style instructions perform best at < ~60 lines.
- **No raw-string enum drift.** Proposal types, location types, and character
  types are generated from their respective enum classes so the prompt
  automatically stays in sync with ``game_engine.types.enums``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import CharacterType, Condition, LocationType, ProposalType

# Build enum value lists once at module load time so the prompt is always in
# sync with the canonical enum definitions in game_engine.types.enums.
_PROPOSAL_TYPES = "|".join(pt.value for pt in ProposalType)
_LOCATION_TYPES = "|".join(lt.value for lt in LocationType)
_CHARACTER_TYPES = "|".join(ct.value for ct in CharacterType)


@dataclass(frozen=True)
class LocationBrief:
    """Condensed canon location injected into the system prompt."""

    name: str
    type: LocationType
    description: str | None = None


@dataclass(frozen=True)
class CharacterBrief:
    """Condensed canon character (PC, NPC, or monster) injected into the prompt."""

    name: str
    type: CharacterType
    race: str | None = None
    char_class: str | None = None
    level: int = 1
    personality_traits: str | None = None
    ideals: str | None = None
    bonds: str | None = None
    flaws: str | None = None
    known_facts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CombatantBrief:
    """One combatant's line in the live combat snapshot."""

    name: str
    hp_current: int
    hp_max: int
    is_dead: bool = False
    conditions: tuple[Condition, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CombatSnapshot:
    """Live combat-tracker state injected while a fight is in progress."""

    round_number: int
    active_combatant: str | None = None
    combatants: tuple[CombatantBrief, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WorldContext:
    """Typed world-grounding input for the system prompt.

    Carries durable campaign knowledge (world setting/lore, summaries of
    previously ended sessions, and the accepted canon entities) plus the
    live combat snapshot, so the orchestrator keeps continuity across
    sessions and never contradicts its own accepted proposals. Built by the
    Runtime layer from the worlds/sessions/locations/characters tables.
    """

    setting_description: str | None = None
    lore_summary: str | None = None
    prior_session_summaries: tuple[str, ...] = field(default_factory=tuple)
    known_locations: tuple[LocationBrief, ...] = field(default_factory=tuple)
    known_characters: tuple[CharacterBrief, ...] = field(default_factory=tuple)
    active_combat: CombatSnapshot | None = None

    def is_empty(self) -> bool:
        return (
            not self.setting_description
            and not self.lore_summary
            and not self.prior_session_summaries
            and not self.known_locations
            and not self.known_characters
            and self.active_combat is None
        )


def _location_line(loc: LocationBrief) -> str:
    line = f"- {loc.name} ({loc.type.value})"
    if loc.description:
        line += f": {loc.description}"
    return line


def _character_line(char: CharacterBrief) -> str:
    identity = " ".join(part for part in (char.race, char.char_class) if part)
    descriptor = char.type.value.lower()
    descriptor += f", {identity} {char.level}" if identity else f", level {char.level}"
    details: list[str] = []
    for label, value in (
        ("traits", char.personality_traits),
        ("ideals", char.ideals),
        ("bonds", char.bonds),
        ("flaws", char.flaws),
    ):
        if value:
            details.append(f"{label}: {value}")
    if char.known_facts:
        details.append("known facts: " + "; ".join(char.known_facts))
    line = f"- {char.name} ({descriptor})"
    if details:
        line += " — " + " | ".join(details)
    return line


def _combat_lines(snapshot: CombatSnapshot | None) -> list[str]:
    """Render the ACTIVE COMBAT prompt section. Empty when no fight is live."""
    if snapshot is None:
        return []
    header = f"ACTIVE COMBAT (round {snapshot.round_number}"
    if snapshot.active_combatant:
        header += f" — {snapshot.active_combatant}'s turn"
    lines = [header + ")"]
    for combatant in snapshot.combatants:
        suffix = " — DEAD" if combatant.is_dead else ""
        if combatant.conditions:
            suffix += " (" + ", ".join(c.value for c in combatant.conditions) + ")"
        lines.append(f"- {combatant.name}: {combatant.hp_current}/{combatant.hp_max} HP{suffix}")
    lines.append("Narrate strictly from this tracker; the rules engine resolves all mechanics.")
    return lines


def _world_context_block(world_context: WorldContext | None) -> str:
    """Render the WORLD CONTEXT and ACTIVE COMBAT prompt sections.

    Silent no-op (empty string) when there is no durable world knowledge yet,
    e.g. a brand-new world with no lore, no ended sessions, and no accepted
    canon entities.
    """
    if world_context is None or world_context.is_empty():
        return ""
    lines: list[str] = ["WORLD CONTEXT"]
    if world_context.setting_description:
        lines.append(f"Setting: {world_context.setting_description}")
    if world_context.lore_summary:
        lines.append(f"Established lore: {world_context.lore_summary}")
    if world_context.prior_session_summaries:
        lines.append("Previous sessions (oldest first):")
        lines.extend(f"- {summary}" for summary in world_context.prior_session_summaries)
    if world_context.known_locations:
        lines.append("Known locations (canon):")
        lines.extend(_location_line(loc) for loc in world_context.known_locations)
    if world_context.known_characters:
        lines.append("Known characters (canon):")
        lines.extend(_character_line(char) for char in world_context.known_characters)
    if world_context.known_locations or world_context.known_characters:
        lines.append(
            "The entities above are canon: use their names and details exactly, "
            "and never re-propose an entity that already appears above."
        )
    sections = ["\n".join(lines)] if len(lines) > 1 else []
    combat = _combat_lines(world_context.active_combat)
    if combat:
        sections.append("\n".join(combat))
    return "\n\n".join(sections) + "\n\n" if sections else ""


def build_system_prompt(
    *,
    world_id: str,
    session_id: str,
    world_context: WorldContext | None = None,
) -> str:
    """Build the system prompt for the DM orchestrator.

    Args:
        world_id: UUID of the current world.
        session_id: UUID of the current game session.
        world_context: Durable world knowledge (setting, lore, prior session
            summaries) injected so the model keeps cross-session continuity.

    Returns:
        System prompt string.
    """
    return (
        "You are an expert AI Dungeon Master running a D&D 5.5e (2024 rules) "
        "campaign. Your responsibilities:\n"
        "1. Narrate vivid, immersive scenes with sensory details.\n"
        "2. Role-play NPCs with distinct personalities and motivations.\n"
        "3. Adjudicate rules fairly using D&D 5.5e mechanics.\n"
        "4. Maintain continuity with established world lore.\n"
        "\n"
        "GROUNDING\n"
        "- The repository is the single source of truth. When a "
        "[CONDENSED SYNOPSIS], [ESTABLISHED FACTS], or [OPEN THREADS] block is\n"
        "  present, treat it as canonical and cite msg:<uuid>@<timestamp>\n"
        "  anchors when referencing prior events.\n"
        "- Never contradict an [ESTABLISHED FACTS] entry. If a fact appears\n"
        "  ambiguous, raise it with the DM rather than guessing.\n"
        "\n"
        "MECHANICS FIDELITY\n"
        "- Combat is resolved by the deterministic rules engine, not by you.\n"
        "  When a system message summarises a combat outcome, narrate strictly\n"
        "  from it — never invent blow-by-blow details, damage numbers, or\n"
        "  outcomes beyond what it states.\n"
        "- Entities you proposed are not canon until the DM accepts them; do\n"
        "  not reference a proposed NPC or location in narration as an\n"
        "  established fact before acceptance.\n"
        "- Keep each character's identity (class, species, abilities) exactly\n"
        "  as established; never misattribute them.\n"
        "\n"
        "STRUCTURED PROPOSALS\n"
        "When you introduce a new location, character, dungeon, or major\n"
        "decision, append a machine-readable proposal block so the human DM\n"
        "can review it (one block per new entity; multiple blocks per\n"
        "response are fine):\n"
        "\n"
        "  [PROPOSAL]\n"
        f'  {{"type": "<{_PROPOSAL_TYPES}>",\n'
        '   "content": { ... typed payload ... }}\n'
        "  [/PROPOSAL]\n"
        "\n"
        "- `type` MUST be exactly one of the listed values (no variants).\n"
        "- `content` MUST be a JSON object, never a string or array.\n"
        "- Do not wrap the block in markdown fences.\n"
        "- Only `location` and `character` proposals create world entities\n"
        "  when accepted. Items, factions, omens, and similar inventions\n"
        "  belong in the prose narration, never in a proposal block.\n"
        "\n"
        "PROPOSAL CONTENT SCHEMAS (required field names)\n"
        f"location: {{name, type ({_LOCATION_TYPES}),\n"
        "           description, lore, history, map_data (JSON object\n"
        "           describing the map; never a string)}\n"
        f"character: {{name, type ({_CHARACTER_TYPES}), race, class, level, alignment,\n"
        "            personality_traits, ideals, bonds, flaws}\n"
        "dungeon/dialogue/combat_action: free-form but must be a JSON object.\n"
        "\n"
        f"{_world_context_block(world_context)}"
        f"World ID: {world_id}\n"
        f"Session ID: {session_id}\n"
        "\n"
        "Always stay in character as the Dungeon Master. Be creative but "
        "respect the established world lore and player agency."
    )
