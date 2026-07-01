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

from game_engine.types import CharacterType, LocationType, ProposalType

# Build enum value lists once at module load time so the prompt is always in
# sync with the canonical enum definitions in game_engine.types.enums.
_PROPOSAL_TYPES = "|".join(pt.value for pt in ProposalType)
_LOCATION_TYPES = "|".join(lt.value for lt in LocationType)
_CHARACTER_TYPES = "|".join(ct.value for ct in CharacterType)


@dataclass(frozen=True)
class WorldContext:
    """Typed world-grounding input for the system prompt.

    Carries durable campaign knowledge (world setting/lore, summaries of
    previously ended sessions, and the entity roster of known NPCs/monsters and
    locations) so the orchestrator keeps continuity across sessions. Built by
    the Runtime layer from the worlds/sessions/characters/locations tables.
    """

    setting_description: str | None = None
    lore_summary: str | None = None
    prior_session_summaries: tuple[str, ...] = field(default_factory=tuple)
    known_npcs: tuple[str, ...] = field(default_factory=tuple)
    known_locations: tuple[str, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return (
            not self.setting_description
            and not self.lore_summary
            and not self.prior_session_summaries
            and not self.known_npcs
            and not self.known_locations
        )


def _world_context_block(world_context: WorldContext | None) -> str:
    """Render the WORLD CONTEXT prompt section.

    Silent no-op (empty string) when there is no durable world knowledge yet,
    e.g. a brand-new world with no lore, no ended sessions, and no entities.
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
    if world_context.known_npcs:
        lines.append("Known NPCs and monsters:")
        lines.extend(f"- {npc}" for npc in world_context.known_npcs)
    if world_context.known_locations:
        lines.append("Known locations:")
        lines.extend(f"- {loc}" for loc in world_context.known_locations)
    return "\n".join(lines) + "\n\n"


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
        "STRUCTURED PROPOSALS — REQUIRED\n"
        "You MUST append a [PROPOSAL] block every time you introduce a new\n"
        "named NPC, monster, or location for the first time. This is not\n"
        "optional. Without a proposal block the entity is never saved to the\n"
        "world database and the DM cannot capture it — the world stays empty.\n"
        "One block per new entity; multiple blocks in a single response are fine.\n"
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
        "  when accepted. Items, factions, omens belong in prose, not proposals.\n"
        "- Re-emit a proposal if you reference an entity that has not yet been\n"
        "  accepted (the DM may have missed the first one).\n"
        "\n"
        "GATING NEW-ENTITY NARRATION — REQUIRED\n"
        "Only `location` and `character` proposals create canon world entities,\n"
        "so only those two carry gated narration. Any sentence(s) that assert a\n"
        "brand-new (this-turn) location or character as settled, established\n"
        "fact must be wrapped in [PENDING]...[/PENDING], placed immediately\n"
        "adjacent to that entity's [PROPOSAL] block. Text outside [PENDING]\n"
        "must still read as complete, coherent narration on its own — describe\n"
        "atmosphere, action, and approach, and defer only the specific reveal\n"
        "or fact into the pending block.\n"
        "- Exactly one [PENDING] block per [PROPOSAL] that introduces new\n"
        "  narrative-committing facts, emitted in the same order as the\n"
        "  proposals.\n"
        "- If a proposal introduces nothing narratively pre-committed yet\n"
        "  (e.g. a location noticed in the distance but not yet described),\n"
        "  omit the [PENDING] block for it.\n"
        "- dungeon/dialogue/combat_action proposals never carry [PENDING]\n"
        "  blocks — they do not create canon entities.\n"
        "\n"
        "  [PENDING]The specific reveal sentence(s) for this entity.[/PENDING]\n"
        "  [PROPOSAL]\n"
        f'  {{"type": "<{_PROPOSAL_TYPES}>",\n'
        '   "content": { ... typed payload ... }}\n'
        "  [/PROPOSAL]\n"
        "\n"
        "PROPOSAL CONTENT SCHEMAS (required field names)\n"
        f"location: {{name, type ({_LOCATION_TYPES}),\n"
        "           description, lore, history}\n"
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
