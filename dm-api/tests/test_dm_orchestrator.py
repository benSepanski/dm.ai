"""Tests for DMOrchestrator (condense integration + proposal parsing)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from game_engine.types import ChatRole

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse
from dm_api.ai.condenser import HistoryMessage, MessageAnchor
from dm_api.ai.dm_orchestrator import DMOrchestrator


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

    assert result.proposal == {"type": "location", "content": {"name": "Glenbrook"}}


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
