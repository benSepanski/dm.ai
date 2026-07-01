"""Tests for DMOrchestrator (condense integration + proposal parsing)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from game_engine.types import CharacterType, ChatRole, LocationType, ProposalType

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse
from dm_api.ai.condenser import HistoryMessage, MessageAnchor
from dm_api.ai.dm_orchestrator import DMOrchestrator, ProposalPayload
from dm_api.ai.prompts.system_prompt import WorldContext, build_system_prompt


class _ScriptedBackend(AIBackend):
    """Replays a queue of responses, recording every call."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls: list[dict] = []

    async def complete(
        self,
        *,
        messages: list[AIMessage],
        system: str,
        model: str,
        max_tokens: int = 4096,
    ) -> AIResponse:
        reply = self._replies.pop(0) if self._replies else ""
        self.calls.append({"messages": messages, "system": system, "model": model})
        return AIResponse(content=reply, model=model)


def _history(count: int, *, tokens_each: int = 100) -> list[HistoryMessage]:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    out: list[HistoryMessage] = []
    for i in range(count):
        role = ChatRole.DM if i % 2 == 0 else ChatRole.AI
        out.append(
            HistoryMessage(
                anchor=MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=role),
                content=f"turn-{i}",
                token_count=tokens_each,
            )
        )
    return out


@pytest.mark.asyncio
async def test_handle_message_returns_typed_response() -> None:
    backend = _ScriptedBackend(["The tavern is quiet tonight."])
    orchestrator = DMOrchestrator(
        backend=backend,
        orchestrator_model="main",
        generation_model="fast",
    )

    result = await orchestrator.handle_message(
        message="Describe the tavern.",
        session_id="s1",
        world_id="w1",
        history=_history(2),
    )

    assert result.response == "The tavern is quiet tonight."
    assert result.proposals == []
    assert result.was_condensed is False
    assert backend.calls[0]["model"] == "main"


@pytest.mark.asyncio
async def test_handle_message_extracts_proposal() -> None:
    body = (
        "You arrive at a village.\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Glenbrook"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend,
        orchestrator_model="main",
        generation_model="fast",
    )

    result = await orchestrator.handle_message(
        message="What's next?",
        session_id="s1",
        world_id="w1",
        history=_history(1),
    )

    assert result.proposals == [
        ProposalPayload(type=ProposalType.LOCATION, content={"name": "Glenbrook"})
    ]
    # The raw block is stripped from the narration shown to players.
    assert "[PROPOSAL]" not in result.response
    assert result.response == "You arrive at a village."


@pytest.mark.asyncio
async def test_handle_message_extracts_multiple_proposals() -> None:
    """One block per new entity: a single turn can carry several proposals
    (regression: only the first block used to be captured, silently)."""
    body = (
        "You reach Mirebrook, where Ossian Dray waits.\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Mirebrook"}}'
        "[/PROPOSAL]\n"
        "The road continues.\n"
        "[PROPOSAL]"
        '{"type": "character", "content": {"name": "Ossian Dray"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )

    result = await orchestrator.handle_message(
        message="Onward.", session_id="s1", world_id="w1", history=_history(1)
    )

    assert result.proposals == [
        ProposalPayload(type=ProposalType.LOCATION, content={"name": "Mirebrook"}),
        ProposalPayload(type=ProposalType.CHARACTER, content={"name": "Ossian Dray"}),
    ]
    assert "[PROPOSAL]" not in result.response
    assert "You reach Mirebrook, where Ossian Dray waits." in result.response
    assert "The road continues." in result.response


@pytest.mark.asyncio
async def test_handle_message_condenses_when_over_budget() -> None:
    """Large history triggers the condense sub-call before the orchestrator call."""
    condense_json = '{"synopsis": "s", "key_facts": [], "open_threads": []}'
    backend = _ScriptedBackend([condense_json, "narrative reply"])
    orchestrator = DMOrchestrator(
        backend=backend,
        orchestrator_model="main",
        generation_model="fast",
        context_token_limit=200,
        context_preserve_last_n=2,
    )

    history = _history(6, tokens_each=100)
    result = await orchestrator.handle_message(
        message="continue",
        session_id="s1",
        world_id="w1",
        history=history,
    )

    assert result.was_condensed is True
    # 2 backend calls: condenser (fast) + orchestrator (main).
    assert [c["model"] for c in backend.calls] == ["fast", "main"]
    assert result.response == "narrative reply"


@pytest.mark.asyncio
async def test_extract_proposal_unknown_type_returns_none() -> None:
    """Unknown proposal type is silently dropped rather than raising."""
    body = (
        "Response text.\n"
        "[PROPOSAL]"
        '{"type": "invalid_type", "content": {"foo": "bar"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )
    result = await orchestrator.handle_message(
        message="test", session_id="s1", world_id="w1", history=_history(1)
    )
    assert result.proposals == []


def test_system_prompt_contains_all_enum_values() -> None:
    """Verify the system prompt lists every ProposalType, LocationType, and CharacterType value.

    This guards against enum additions that are not reflected in the prompt.
    """
    prompt = build_system_prompt(world_id="test-world", session_id="test-session")
    for pt in ProposalType:
        assert pt.value in prompt, f"ProposalType.{pt.name} ({pt.value!r}) missing from prompt"
    for lt in LocationType:
        assert lt.value in prompt, f"LocationType.{lt.name} ({lt.value!r}) missing from prompt"
    for ct in CharacterType:
        assert ct.value in prompt, f"CharacterType.{ct.name} ({ct.value!r}) missing from prompt"


def test_system_prompt_includes_world_context() -> None:
    """Setting, lore, and prior session summaries all appear in the prompt."""
    ctx = WorldContext(
        setting_description="A storm-wracked archipelago.",
        lore_summary="The Sea Queen rules the tides.",
        prior_session_summaries=("Session 1: The party met the Sea Queen.",),
    )
    prompt = build_system_prompt(world_id="w", session_id="s", world_context=ctx)
    assert "WORLD CONTEXT" in prompt
    assert "A storm-wracked archipelago." in prompt
    assert "The Sea Queen rules the tides." in prompt
    assert "Session 1: The party met the Sea Queen." in prompt


def test_system_prompt_world_context_silent_when_empty() -> None:
    """No WORLD CONTEXT section when there is no durable world knowledge yet."""
    assert "WORLD CONTEXT" not in build_system_prompt(world_id="w", session_id="s")
    assert "WORLD CONTEXT" not in build_system_prompt(
        world_id="w", session_id="s", world_context=WorldContext()
    )


def test_system_prompt_includes_known_entities() -> None:
    """Known NPCs and locations appear in the WORLD CONTEXT section."""
    ctx = WorldContext(
        known_npcs=("Gareth (NPC, Human Fighter, lawful neutral)",),
        known_locations=("Thornwall Keep (building) — ancient fortress",),
    )
    prompt = build_system_prompt(world_id="w", session_id="s", world_context=ctx)
    assert "WORLD CONTEXT" in prompt
    assert "Known NPCs and monsters:" in prompt
    assert "Gareth (NPC, Human Fighter, lawful neutral)" in prompt
    assert "Known locations:" in prompt
    assert "Thornwall Keep (building) — ancient fortress" in prompt


def test_system_prompt_known_entities_silent_when_absent() -> None:
    """No entity-roster sections when no NPCs or locations are provided."""
    ctx = WorldContext(setting_description="A dark realm.")
    prompt = build_system_prompt(world_id="w", session_id="s", world_context=ctx)
    assert "Known NPCs" not in prompt
    assert "Known locations" not in prompt


@pytest.mark.asyncio
async def test_handle_message_passes_world_context_to_system_prompt() -> None:
    backend = _ScriptedBackend(["reply"])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )
    ctx = WorldContext(lore_summary="Dragons rule the north.")

    await orchestrator.handle_message(
        message="hi",
        session_id="s1",
        world_id="w1",
        history=_history(1),
        world_context=ctx,
    )

    assert "Dragons rule the north." in backend.calls[0]["system"]


@pytest.mark.asyncio
async def test_extract_proposal_strips_markdown_fences() -> None:
    """Proposals wrapped in ```json fences are parsed correctly."""
    body = (
        "You arrive at a village.\n"
        "[PROPOSAL]\n"
        "```json\n"
        '{"type": "location", "content": {"name": "Maplewood"}}\n'
        "```\n"
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )
    result = await orchestrator.handle_message(
        message="Where are we?", session_id="s1", world_id="w1", history=_history(1)
    )
    assert result.proposals == [
        ProposalPayload(type=ProposalType.LOCATION, content={"name": "Maplewood"})
    ]


@pytest.mark.asyncio
async def test_extract_proposal_non_dict_content_is_none() -> None:
    """Non-dict content is coerced to None rather than leaking an untyped value."""
    body = (
        "Response text.\n"
        "[PROPOSAL]"
        '{"type": "location", "content": "not-a-dict"}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )
    result = await orchestrator.handle_message(
        message="test", session_id="s1", world_id="w1", history=_history(1)
    )
    assert result.proposals == [ProposalPayload(type=ProposalType.LOCATION, content=None)]


# ---------------------------------------------------------------------------
# PT-21: [PENDING] narration is gated at the source until the paired
# [PROPOSAL] is accepted.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_message_strips_pending_narration_from_response() -> None:
    """Narration wrapped in [PENDING] is withheld from the returned response
    and instead carried on the paired proposal's ``pending_narration``."""
    body = (
        "You crest the hill and the coastline comes into view.\n"
        "[PENDING]**Saltmere** spreads above the waterfront, its lantern-lit "
        "docks humming with trade.[/PENDING]\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Saltmere"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )

    result = await orchestrator.handle_message(
        message="What do we see?", session_id="s1", world_id="w1", history=_history(1)
    )

    assert "[PENDING]" not in result.response
    assert "[/PENDING]" not in result.response
    assert "Saltmere" not in result.response
    assert "You crest the hill and the coastline comes into view." in result.response

    assert len(result.proposals) == 1
    assert result.proposals[0].type == ProposalType.LOCATION
    assert result.proposals[0].pending_narration == (
        "**Saltmere** spreads above the waterfront, its lantern-lit docks " "humming with trade."
    )


@pytest.mark.asyncio
async def test_handle_message_pairs_multiple_pending_blocks_by_order() -> None:
    """Nth [PENDING] pairs with Nth [PROPOSAL], in emission order."""
    body = (
        "The road forks ahead.\n"
        "[PENDING]Mirebrook squats in the marsh, half-swallowed by reeds.[/PENDING]\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Mirebrook"}}'
        "[/PROPOSAL]\n"
        "A figure steps from the shadows.\n"
        "[PENDING]Ossian Dray, cloaked and wary, blocks the path.[/PENDING]\n"
        "[PROPOSAL]"
        '{"type": "character", "content": {"name": "Ossian Dray"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )

    result = await orchestrator.handle_message(
        message="Onward.", session_id="s1", world_id="w1", history=_history(1)
    )

    assert len(result.proposals) == 2
    location_proposal, character_proposal = result.proposals
    assert location_proposal.type == ProposalType.LOCATION
    assert location_proposal.pending_narration == (
        "Mirebrook squats in the marsh, half-swallowed by reeds."
    )
    assert character_proposal.type == ProposalType.CHARACTER
    assert character_proposal.pending_narration == (
        "Ossian Dray, cloaked and wary, blocks the path."
    )
    assert "Mirebrook squats" not in result.response
    assert "Ossian Dray, cloaked" not in result.response
    assert "The road forks ahead." in result.response
    assert "A figure steps from the shadows." in result.response


@pytest.mark.asyncio
async def test_handle_message_pending_count_mismatch_drops_all_pending_text() -> None:
    """A PENDING/PROPOSAL count mismatch drops ALL pending text (never
    guessed) but keeps every proposal intact."""
    body = (
        "You arrive at the crossroads.\n"
        "[PENDING]Glenbrook's rooftops catch the last light.[/PENDING]\n"
        "[PENDING]An extra, unpaired pending block.[/PENDING]\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Glenbrook"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )

    result = await orchestrator.handle_message(
        message="test", session_id="s1", world_id="w1", history=_history(1)
    )

    assert len(result.proposals) == 1
    assert result.proposals[0].type == ProposalType.LOCATION
    assert result.proposals[0].pending_narration is None
    assert "Glenbrook's rooftops" not in result.response
    assert "unpaired pending block" not in result.response
    assert "[PENDING]" not in result.response
    assert "You arrive at the crossroads." in result.response


@pytest.mark.asyncio
async def test_handle_message_proposal_without_pending_block_has_none() -> None:
    """A proposal that introduces nothing narratively pre-committed may omit
    its [PENDING] block entirely — pending_narration stays None."""
    body = (
        "You notice a distant tower on the horizon, unremarked upon.\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Distant Tower"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )

    result = await orchestrator.handle_message(
        message="test", session_id="s1", world_id="w1", history=_history(1)
    )

    assert len(result.proposals) == 1
    assert result.proposals[0].pending_narration is None
    assert "You notice a distant tower on the horizon, unremarked upon." in result.response


@pytest.mark.asyncio
async def test_handle_message_partial_pending_coverage_pairs_by_adjacency() -> None:
    """One proposal with no [PENDING] block followed by another that has one
    is NOT a count mismatch — the system prompt explicitly allows partial
    coverage. The single PENDING block must still pair with its adjacent
    proposal instead of being dropped for every proposal."""
    body = (
        "You spot a distant tower on the horizon, unremarked upon.\n"
        "[PROPOSAL]"
        '{"type": "location", "content": {"name": "Distant Tower"}}'
        "[/PROPOSAL]\n"
        "A figure steps from the shadows nearby.\n"
        "[PENDING]Ossian Dray, cloaked and wary, blocks the path.[/PENDING]\n"
        "[PROPOSAL]"
        '{"type": "character", "content": {"name": "Ossian Dray"}}'
        "[/PROPOSAL]"
    )
    backend = _ScriptedBackend([body])
    orchestrator = DMOrchestrator(
        backend=backend, orchestrator_model="main", generation_model="fast"
    )

    result = await orchestrator.handle_message(
        message="test", session_id="s1", world_id="w1", history=_history(1)
    )

    assert len(result.proposals) == 2
    location_proposal, character_proposal = result.proposals
    assert location_proposal.type == ProposalType.LOCATION
    assert location_proposal.pending_narration is None
    assert character_proposal.type == ProposalType.CHARACTER
    assert character_proposal.pending_narration == (
        "Ossian Dray, cloaked and wary, blocks the path."
    )
    assert "Ossian Dray, cloaked" not in result.response
