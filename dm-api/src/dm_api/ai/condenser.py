"""
Context condensation for long DM sessions.

Implements OpenAI's harness-engineering principles
(https://openai.com/index/harness-engineering/) for AI-driven workflows:

- **Typed boundaries.** Every input and output is a ``@dataclass``; no
  ``dict[str, Any]`` is allowed to cross the condenser's public surface.
- **Citation anchors.** Each chat message is wrapped in a ``MessageAnchor``
  (``msg:<uuid>@<iso-timestamp>``) — the DM-session analog of ``filepath:lineno``
  — so condensed output can be traced back to source messages.
- **Focused sub-agent.** Condensation is a narrow sub-task delegated to the
  fast generation model (Haiku) with a minimal, role-play-free system prompt.
- **Silent on success.** Below the token budget, the condenser is a no-op and
  returns the original history wrapped in a ``CondensedContext``.
- **Single source of truth.** All context-window arithmetic lives here; the
  orchestrator and route handlers never compute token budgets themselves.
- **Depth-first decomposition.** The condensation task is split into
  design → extract → validate → assemble stages inside ``condense()``.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from game_engine.types import ChatRole

from dm_api.ai.backends.base import AIBackend, AIMessage
from dm_api.ai.prompts.condense_prompt import build_condense_prompt

# ---------------------------------------------------------------------------
# Typed boundaries — no dict[str, Any] crosses the condenser API.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MessageAnchor:
    """Citation anchor to a specific chat message.

    Harness-engineering analog of ``filepath:lineno`` — a stable, human-readable
    reference the sub-agent can preserve in condensed output.
    """

    message_id: uuid.UUID
    timestamp: datetime
    role: ChatRole

    def to_citation(self) -> str:
        return f"msg:{self.message_id}@{self.timestamp.isoformat()}"


@dataclass(frozen=True)
class HistoryMessage:
    """A chat message with anchor metadata, ready for condensation."""

    anchor: MessageAnchor
    content: str
    token_count: int

    @property
    def role(self) -> ChatRole:
        return self.anchor.role


@dataclass
class CondensedContext:
    """Structured result of condensation.

    Never ``dict[str, Any]``. Downstream consumers read typed fields directly
    and call :meth:`as_ai_messages` to render into backend-ready messages.

    Attributes:
        synopsis: Narrative summary of the condensed span.
        key_facts: Established world/character facts that must persist.
        open_threads: Unresolved plot threads or pending player choices.
        condensed_span: (first, last) anchors of the condensed range, or
            ``None`` if nothing was condensed.
        preserved: Messages kept verbatim (always the tail of the history).
        tokens_in: Token count of the original history before condensation.
        tokens_out: Estimated token count of the condensed artifact plus
            preserved tail.
    """

    synopsis: str
    key_facts: list[str] = field(default_factory=list)
    open_threads: list[str] = field(default_factory=list)
    condensed_span: tuple[MessageAnchor, MessageAnchor] | None = None
    preserved: list[HistoryMessage] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0

    @property
    def was_condensed(self) -> bool:
        return self.condensed_span is not None

    def as_ai_messages(self) -> list[AIMessage]:
        """Render the condensed context into backend-ready AI messages.

        The condensation artifact is injected as a single ``user`` message with
        labelled sections; preserved tail messages follow in original order.
        """
        rendered: list[AIMessage] = []
        sections: list[str] = []

        if self.synopsis:
            sections.append(f"[CONDENSED SYNOPSIS]\n{self.synopsis}")
        if self.key_facts:
            sections.append("[ESTABLISHED FACTS]\n" + "\n".join(f"- {f}" for f in self.key_facts))
        if self.open_threads:
            sections.append("[OPEN THREADS]\n" + "\n".join(f"- {t}" for t in self.open_threads))
        if self.condensed_span is not None:
            first, last = self.condensed_span
            sections.append(f"[SPAN] {first.to_citation()} → {last.to_citation()}")

        if sections:
            rendered.append(AIMessage(role="user", content="\n\n".join(sections)))

        for message in self.preserved:
            role = "user" if message.role == ChatRole.DM else "assistant"
            rendered.append(AIMessage(role=role, content=message.content))

        return rendered


# ---------------------------------------------------------------------------
# Condenser
# ---------------------------------------------------------------------------


class ContextCondenser:
    """Fast, narrowly-scoped sub-agent that compresses chat history.

    Selected by the orchestrator whenever running-total tokens exceed a budget.
    Uses the configured fast generation model (Haiku by default).
    """

    def __init__(self, backend: AIBackend, model: str) -> None:
        self._backend = backend
        self._model = model

    async def condense(
        self,
        *,
        messages: list[HistoryMessage],
        token_limit: int,
        preserve_last_n: int,
    ) -> CondensedContext:
        """Condense ``messages`` down to fit ``token_limit``.

        Depth-first decomposition:
            1. **design** — compute totals, decide pass-through vs. condense.
            2. **extract** — build the sub-agent transcript with anchors.
            3. **validate** — parse the sub-agent JSON into a typed shape.
            4. **assemble** — wrap the result plus preserved tail.

        Silent-on-success: if the running total is within budget or there are
        fewer messages than the preserve window, returns a pass-through
        ``CondensedContext`` with no AI call made.
        """
        # Stage 1: design — totals and fast path.
        total_tokens = sum(m.token_count for m in messages)
        if total_tokens <= token_limit or len(messages) <= preserve_last_n:
            return CondensedContext(
                synopsis="",
                preserved=list(messages),
                tokens_in=total_tokens,
                tokens_out=total_tokens,
            )

        # Stage 2: extract — split into condense range + preserved tail.
        to_condense = messages[:-preserve_last_n]
        preserved = messages[-preserve_last_n:]
        first_anchor = to_condense[0].anchor
        last_anchor = to_condense[-1].anchor
        transcript = _format_transcript(to_condense)

        # Stage 3: validate — call sub-agent and parse typed JSON.
        response = await self._backend.complete(
            messages=[AIMessage(role="user", content=_build_user_prompt(transcript))],
            system=build_condense_prompt(),
            model=self._model,
            max_tokens=2048,
        )
        parsed = _parse_condensation(response.content)

        # Stage 4: assemble — produce typed CondensedContext.
        preserved_tokens = sum(m.token_count for m in preserved)
        artifact_tokens = (
            _estimate_tokens(parsed.synopsis)
            + sum(_estimate_tokens(fact) for fact in parsed.key_facts)
            + sum(_estimate_tokens(thread) for thread in parsed.open_threads)
        )
        return CondensedContext(
            synopsis=parsed.synopsis,
            key_facts=parsed.key_facts,
            open_threads=parsed.open_threads,
            condensed_span=(first_anchor, last_anchor),
            preserved=list(preserved),
            tokens_in=total_tokens,
            tokens_out=artifact_tokens + preserved_tokens,
        )


# ---------------------------------------------------------------------------
# Internal helpers — typed parsing at the sub-agent boundary.
# ---------------------------------------------------------------------------


@dataclass
class _ParsedCondensation:
    """Validated shape of the sub-agent JSON response."""

    synopsis: str
    key_facts: list[str]
    open_threads: list[str]


def _format_transcript(messages: list[HistoryMessage]) -> str:
    """Render messages with inline citation anchors for the sub-agent."""
    return "\n".join(
        f"[{m.anchor.to_citation()}] {m.role.value.upper()}: {m.content}" for m in messages
    )


def _build_user_prompt(transcript: str) -> str:
    return (
        "Condense the following DM session excerpt into JSON matching the "
        "schema in your instructions. Preserve msg:<uuid>@<timestamp> "
        "anchors when citing specific events.\n\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        "Output ONLY valid JSON. No prose, no markdown fences."
    )


def _parse_condensation(text: str) -> _ParsedCondensation:
    """Parse and validate the sub-agent JSON at the boundary.

    Harness-engineering principle: AI output is an untrusted boundary and
    therefore validated structurally before entering typed internals. Strings
    that fail parsing degrade to a safe synopsis-only shape rather than raise;
    the orchestrator decides whether to retry.
    """
    stripped = _strip_fences(text.strip())
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return _ParsedCondensation(
            synopsis=_clip(stripped, max_chars=2000),
            key_facts=[],
            open_threads=[],
        )

    if not isinstance(data, dict):
        return _ParsedCondensation(
            synopsis=_clip(str(data), max_chars=2000),
            key_facts=[],
            open_threads=[],
        )

    synopsis_raw = data.get("synopsis", "")
    facts_raw = data.get("key_facts", [])
    threads_raw = data.get("open_threads", [])

    synopsis = synopsis_raw if isinstance(synopsis_raw, str) else ""
    key_facts = [f for f in facts_raw if isinstance(f, str)] if isinstance(facts_raw, list) else []
    open_threads = (
        [t for t in threads_raw if isinstance(t, str)] if isinstance(threads_raw, list) else []
    )
    return _ParsedCondensation(
        synopsis=synopsis,
        key_facts=key_facts,
        open_threads=open_threads,
    )


def _strip_fences(text: str) -> str:
    """Strip common markdown wrappers before JSON decoding."""
    if not text.startswith("```"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start : end + 1]


def _clip(text: str, *, max_chars: int) -> str:
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def _estimate_tokens(text: str) -> int:
    """Rough 4-chars-per-token estimate; matches the rest of dm-api."""
    if not text:
        return 0
    return max(1, len(text) // 4)
