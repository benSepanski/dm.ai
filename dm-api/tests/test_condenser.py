"""Tests for the context condenser (harness-engineering).

Covers:
- Silent-on-success pass-through below token budget.
- Condensation path (typed JSON parsed into CondensedContext).
- Malformed sub-agent output falls back safely.
- Citation anchor rendering for traceability.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from game_engine.types import ChatRole

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse
from dm_api.ai.condenser import (
    CondensedContext,
    ContextCondenser,
    HistoryMessage,
    MessageAnchor,
)


class _StubBackend(AIBackend):
    """Records calls and replays a scripted response."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict] = []

    async def complete(
        self,
        *,
        messages: list[AIMessage],
        system: str,
        model: str,
        max_tokens: int = 4096,
    ) -> AIResponse:
        self.calls.append(
            {"messages": messages, "system": system, "model": model, "max_tokens": max_tokens}
        )
        return AIResponse(content=self.reply, model=model, input_tokens=0, output_tokens=0)


def _mk_history(count: int, tokens_each: int = 100) -> list[HistoryMessage]:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    out: list[HistoryMessage] = []
    for i in range(count):
        role = ChatRole.DM if i % 2 == 0 else ChatRole.AI
        out.append(
            HistoryMessage(
                anchor=MessageAnchor(
                    message_id=uuid.uuid4(),
                    timestamp=now,
                    role=role,
                ),
                content=f"turn-{i}",
                token_count=tokens_each,
            )
        )
    return out


@pytest.mark.asyncio
async def test_condense_is_silent_when_under_budget() -> None:
    """Below the token limit the condenser is a pure no-op (no backend call)."""
    backend = _StubBackend(reply='{"synopsis": "x", "key_facts": [], "open_threads": []}')
    condenser = ContextCondenser(backend=backend, model="fast-model")

    history = _mk_history(3, tokens_each=100)
    result = await condenser.condense(messages=history, token_limit=10_000, preserve_last_n=5)

    assert result.was_condensed is False
    assert result.synopsis == ""
    assert result.preserved == history
    assert result.tokens_in == 300
    assert result.tokens_out == 300
    assert backend.calls == []  # silent-on-success: no AI call


@pytest.mark.asyncio
async def test_condense_runs_when_over_budget() -> None:
    """Above the token limit the sub-agent is invoked and output is typed."""
    payload = (
        '{"synopsis": "Party cleared the goblin camp.",\n'
        ' "key_facts": ["Lyra is a halfling rogue", "Camp is north of Glenbrook"],\n'
        ' "open_threads": ["Who hired the goblins?"]}'
    )
    backend = _StubBackend(reply=payload)
    condenser = ContextCondenser(backend=backend, model="fast-model")

    history = _mk_history(10, tokens_each=100)
    result = await condenser.condense(messages=history, token_limit=500, preserve_last_n=3)

    assert result.was_condensed is True
    assert result.synopsis == "Party cleared the goblin camp."
    assert "Lyra is a halfling rogue" in result.key_facts
    assert result.open_threads == ["Who hired the goblins?"]
    assert len(result.preserved) == 3
    assert result.preserved == history[-3:]
    assert result.condensed_span is not None
    first, last = result.condensed_span
    assert first == history[0].anchor
    assert last == history[-4].anchor
    assert len(backend.calls) == 1
    assert backend.calls[0]["model"] == "fast-model"


@pytest.mark.asyncio
async def test_condense_degrades_on_malformed_json() -> None:
    """Bad sub-agent output falls back to synopsis-only rather than crashing."""
    backend = _StubBackend(reply="not actually json at all")
    condenser = ContextCondenser(backend=backend, model="fast-model")

    history = _mk_history(8, tokens_each=100)
    result = await condenser.condense(messages=history, token_limit=200, preserve_last_n=2)

    assert result.was_condensed is True
    assert result.synopsis == "not actually json at all"
    assert result.key_facts == []
    assert result.open_threads == []
    assert len(result.preserved) == 2


@pytest.mark.asyncio
async def test_condense_strips_markdown_fences() -> None:
    """Sub-agent output wrapped in ``` fences is parsed correctly."""
    fenced = "```json\n" '{"synopsis": "ok", "key_facts": ["a"], "open_threads": []}\n' "```"
    backend = _StubBackend(reply=fenced)
    condenser = ContextCondenser(backend=backend, model="fast-model")

    history = _mk_history(6, tokens_each=100)
    result = await condenser.condense(messages=history, token_limit=100, preserve_last_n=2)

    assert result.synopsis == "ok"
    assert result.key_facts == ["a"]


def test_as_ai_messages_renders_sections_and_anchors() -> None:
    """Condensed context renders with citation anchors visible to the model."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    first = MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=ChatRole.DM)
    last = MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=ChatRole.AI)
    preserved = HistoryMessage(
        anchor=MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=ChatRole.DM),
        content="hello",
        token_count=10,
    )

    ctx = CondensedContext(
        synopsis="summary here",
        key_facts=["fact one"],
        open_threads=["thread one"],
        condensed_span=(first, last),
        preserved=[preserved],
        tokens_in=500,
        tokens_out=100,
    )

    messages = ctx.as_ai_messages()
    assert len(messages) == 2
    head = messages[0]
    assert head.role == "user"
    assert "[CONDENSED SYNOPSIS]" in head.content
    assert "[ESTABLISHED FACTS]" in head.content
    assert "[OPEN THREADS]" in head.content
    assert first.to_citation() in head.content
    assert last.to_citation() in head.content

    tail = messages[1]
    assert tail.role == "user"
    assert tail.content == "hello"


def test_message_anchor_citation_format() -> None:
    """The citation format matches filepath:lineno style: msg:<id>@<ts>."""
    mid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    anchor = MessageAnchor(message_id=mid, timestamp=ts, role=ChatRole.DM)
    assert anchor.to_citation() == f"msg:{mid}@{ts.isoformat()}"
