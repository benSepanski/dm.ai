"""Tests for DMOrchestrator (condense integration + proposal parsing)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from game_engine.types import CharacterType, ChatRole, LocationType, ProposalType

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse
from dm_api.ai.condenser import HistoryMessage, MessageAnchor
from dm_api.ai.dm_orchestrator import DMOrchestrator, ProposalPayload
from dm_api.ai.prompts.system_prompt import build_system_prompt


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
    assert result.proposal is None
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

    assert result.proposal == ProposalPayload(
        type=ProposalType.LOCATION, content={"name": "Glenbrook"}
    )


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
    assert result.proposal is None


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
    assert result.proposal == ProposalPayload(
        type=ProposalType.LOCATION, content={"name": "Maplewood"}
    )


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
    assert result.proposal == ProposalPayload(type=ProposalType.LOCATION, content=None)


@pytest.mark.asyncio
async def test_summarize_returns_backend_content() -> None:
    """summarize() uses the fast (generation) model and returns its text."""
    backend = _ScriptedBackend(["The party explored the dungeon and defeated the lich."])
    orchestrator = DMOrchestrator(
        backend=backend,
        orchestrator_model="main",
        generation_model="fast",
    )

    result = await orchestrator.summarize("Long session transcript here.")

    assert result == "The party explored the dungeon and defeated the lich."
    assert len(backend.calls) == 1
    assert backend.calls[0]["model"] == "fast"


@pytest.mark.asyncio
async def test_summarize_uses_generation_model_not_orchestrator() -> None:
    """summarize() must use the generation (fast) model, not the orchestrator model."""
    backend = _ScriptedBackend(["Summary text."])
    orchestrator = DMOrchestrator(
        backend=backend,
        orchestrator_model="expensive-main",
        generation_model="cheap-fast",
    )

    await orchestrator.summarize("session text")

    assert backend.calls[0]["model"] == "cheap-fast"


@pytest.mark.asyncio
async def test_condense_method_delegates_to_condenser() -> None:
    """The public condense() method returns a CondensedContext from the condenser sub-agent."""
    from dm_api.ai.condenser import CondensedContext

    condense_json = '{"synopsis": "Heroes saved the village.", "key_facts": ["Tavern burned down"], "open_threads": ["Where did the dragon go?"]}'
    backend = _ScriptedBackend([condense_json])
    orchestrator = DMOrchestrator(
        backend=backend,
        orchestrator_model="main",
        generation_model="fast",
        context_token_limit=100,
        context_preserve_last_n=1,
    )

    history = _history(4, tokens_each=50)
    result = await orchestrator.condense(history=history)

    assert isinstance(result, CondensedContext)
    assert result.was_condensed is True
    assert result.synopsis == "Heroes saved the village."
    assert "Tavern burned down" in result.key_facts
    assert "Where did the dragon go?" in result.open_threads
