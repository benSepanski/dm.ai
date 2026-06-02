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
    """Condensed context renders with citation anchors visible to the model.

    When the only preserved message is a DM turn, the synopsis is merged into
    it to avoid two consecutive user messages (Anthropic API contract).
    """
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
    # Synopsis is merged into the first (and only) DM message to avoid two
    # consecutive user turns.
    assert len(messages) == 1
    head = messages[0]
    assert head.role == "user"
    assert "[CONDENSED SYNOPSIS]" in head.content
    assert "[ESTABLISHED FACTS]" in head.content
    assert "[OPEN THREADS]" in head.content
    assert first.to_citation() in head.content
    assert last.to_citation() in head.content
    # The preserved DM message content is fused into the same message
    assert "hello" in head.content


def test_as_ai_messages_guards_against_assistant_first_message() -> None:
    """as_ai_messages must never return a list whose first message is 'assistant'.

    If the preserved tail starts with an AI turn and there is no condensed
    synopsis to prepend a user message, the Anthropic API would reject the
    request with a 400. The guard inserts a minimal [Session start] user
    message to maintain the invariant.
    """
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Edge case: no condensation (empty synopsis), first preserved msg is AI.
    ctx = CondensedContext(
        synopsis="",
        key_facts=[],
        open_threads=[],
        condensed_span=None,
        preserved=[
            HistoryMessage(
                anchor=MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=ChatRole.AI),
                content="I am the Dungeon Master.",
                token_count=5,
            ),
            HistoryMessage(
                anchor=MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=ChatRole.DM),
                content="What do I see?",
                token_count=5,
            ),
        ],
        tokens_in=10,
        tokens_out=10,
    )

    messages = ctx.as_ai_messages()

    assert messages, "as_ai_messages must return at least one message"
    assert (
        messages[0].role == "user"
    ), f"First message role must be 'user', got '{messages[0].role}'"
    # Verify alternation invariant
    for i in range(len(messages) - 1):
        assert not (
            messages[i].role == "user" and messages[i + 1].role == "user"
        ), f"Consecutive user messages at indices {i} and {i+1}"


def test_message_anchor_citation_format() -> None:
    """The citation format matches filepath:lineno style: msg:<id>@<ts>."""
    mid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    anchor = MessageAnchor(message_id=mid, timestamp=ts, role=ChatRole.DM)
    assert anchor.to_citation() == f"msg:{mid}@{ts.isoformat()}"


def _mk_anchor(role: ChatRole) -> MessageAnchor:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return MessageAnchor(message_id=uuid.uuid4(), timestamp=now, role=role)


def _mk_msg(content: str, role: ChatRole) -> HistoryMessage:
    return HistoryMessage(anchor=_mk_anchor(role), content=content, token_count=10)


def test_as_ai_messages_merges_synopsis_with_first_dm_message() -> None:
    """When synopsis is non-empty and first preserved message is a DM turn,
    the synopsis is merged into that message to avoid two consecutive user turns,
    which would violate the Anthropic API's alternating-turn contract.
    """
    first_anchor = _mk_anchor(ChatRole.DM)
    last_anchor = _mk_anchor(ChatRole.AI)

    # Preserved tail: DM message first (role == ChatRole.DM → "user")
    preserved = [
        _mk_msg("Player asks about the quest.", ChatRole.DM),
        _mk_msg("The quest leads north.", ChatRole.AI),
    ]

    ctx = CondensedContext(
        synopsis="Party defeated the bandits.",
        key_facts=["Lyra is the party leader"],
        open_threads=[],
        condensed_span=(first_anchor, last_anchor),
        preserved=preserved,
        tokens_in=500,
        tokens_out=100,
    )

    messages = ctx.as_ai_messages()

    # Must not have two consecutive user messages
    roles = [m.role for m in messages]
    for i in range(len(roles) - 1):
        assert not (
            roles[i] == "user" and roles[i + 1] == "user"
        ), f"Consecutive user messages at indices {i} and {i+1}: {roles}"

    # Synopsis content and the DM message content must be fused in the first message
    assert messages[0].role == "user"
    assert "[CONDENSED SYNOPSIS]" in messages[0].content
    assert "Party defeated the bandits." in messages[0].content
    assert "Player asks about the quest." in messages[0].content

    # Remaining preserved message follows as assistant
    assert messages[1].role == "assistant"
    assert messages[1].content == "The quest leads north."

    assert len(messages) == 2


def test_as_ai_messages_synopsis_standalone_when_first_preserved_is_ai() -> None:
    """When the first preserved message is an AI turn, the synopsis is emitted
    as a standalone user message followed by the assistant message — no merging
    needed because the turns already alternate correctly.
    """
    first_anchor = _mk_anchor(ChatRole.DM)
    last_anchor = _mk_anchor(ChatRole.AI)

    # Preserved tail: AI message first (role == ChatRole.AI → "assistant")
    preserved = [
        _mk_msg("The quest leads north.", ChatRole.AI),
        _mk_msg("Player asks about the quest.", ChatRole.DM),
    ]

    ctx = CondensedContext(
        synopsis="Party defeated the bandits.",
        key_facts=[],
        open_threads=["Who hired the bandits?"],
        condensed_span=(first_anchor, last_anchor),
        preserved=preserved,
        tokens_in=300,
        tokens_out=80,
    )

    messages = ctx.as_ai_messages()

    # Must not have two consecutive user messages
    roles = [m.role for m in messages]
    for i in range(len(roles) - 1):
        assert not (
            roles[i] == "user" and roles[i + 1] == "user"
        ), f"Consecutive user messages at indices {i} and {i+1}: {roles}"

    # Synopsis is emitted as its own user message
    assert messages[0].role == "user"
    assert "[CONDENSED SYNOPSIS]" in messages[0].content
    assert "Party defeated the bandits." in messages[0].content
    # The DM message content is NOT merged into the synopsis message
    assert "The quest leads north." not in messages[0].content

    # Next message is the AI turn (assistant), NOT merged
    assert messages[1].role == "assistant"
    assert messages[1].content == "The quest leads north."

    # Final message is the DM turn (user)
    assert messages[2].role == "user"
    assert messages[2].content == "Player asks about the quest."

    assert len(messages) == 3
