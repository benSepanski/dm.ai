"""
DM Orchestrator — the core AI agent that drives the dungeon-master experience.

Applies OpenAI's harness-engineering principles
(https://openai.com/index/harness-engineering/):

- **Layered architecture.** The orchestrator sits in the Service layer. It
  consumes ``AIBackend`` (Repo/Gateway) and delegates context condensation to
  :class:`dm_api.ai.condenser.ContextCondenser` (Service), never reaching into
  the DB (Repo) or HTTP (Runtime) layers directly.
- **Typed boundaries.** Inputs and outputs are ``@dataclass`` instances; no
  ``dict[str, Any]`` crosses this module's public surface. The AI proposal is
  parsed into a typed :class:`ProposalPayload` at the boundary.
- **Depth-first decomposition.** ``handle_message`` is factored into discrete
  sub-steps (condense → build messages → call backend → extract proposal) that
  are individually testable.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from game_engine.types import ProposalType

from dm_api.ai.backends.base import AIBackend, AIMessage
from dm_api.ai.condenser import CondensedContext, ContextCondenser, HistoryMessage
from dm_api.ai.prompts.system_prompt import WorldContext, build_system_prompt

logger = logging.getLogger(__name__)


@dataclass
class ProposalPayload:
    """Typed representation of an AI-generated proposal.

    Parsed and validated at the AI boundary inside ``_extract_proposal``.
    The ``content`` field is free-form JSON (varies by proposal type) and
    remains untyped, but ``type`` is always a known :class:`ProposalType`.
    """

    type: ProposalType
    content: dict[str, Any] | None


@dataclass
class DMResponse:
    """Typed orchestrator result — no ``dict[str, Any]`` at the API boundary.

    ``response`` is the display narration with all ``[PROPOSAL]`` blocks
    stripped; the parsed blocks live in ``proposals`` (the model may emit one
    block per new entity, so a single turn can carry several).
    """

    response: str
    proposals: list[ProposalPayload]
    was_condensed: bool
    tokens_in: int
    tokens_out: int


class DMOrchestrator:
    """Stateless orchestrator: turns a chat message into a structured AI response.

    Args:
        backend: AI provider backend (AnthropicBackend or ClaudeCLIBackend).
        orchestrator_model: Model for main chat responses.
        generation_model: Model for quick generation tasks (summaries,
            condensation, flavor text). Uses the fast tier.
        context_token_limit: Token budget above which the chat history is
            condensed before the orchestrator call.
        context_preserve_last_n: Number of most-recent messages to keep
            verbatim when condensing.
    """

    def __init__(
        self,
        backend: AIBackend,
        orchestrator_model: str,
        generation_model: str,
        context_token_limit: int = 180_000,
        context_preserve_last_n: int = 5,
    ) -> None:
        self._backend = backend
        self._orchestrator_model = orchestrator_model
        self._generation_model = generation_model
        self._context_token_limit = context_token_limit
        self._context_preserve_last_n = context_preserve_last_n
        self._condenser = ContextCondenser(backend=backend, model=generation_model)

    async def handle_message(
        self,
        *,
        message: str,
        session_id: str,
        world_id: str,
        history: list[HistoryMessage],
        world_context: WorldContext | None = None,
    ) -> DMResponse:
        """Process a chat message and return the AI DM response.

        Args:
            message: The latest DM message (text only). Already persisted and
                present as the last element of ``history``.
            session_id: UUID of the current game session.
            world_id: UUID of the current world.
            history: Full chat history for this session, each entry wrapped in
                a typed ``HistoryMessage`` (with citation anchor + token
                count). Callers are responsible for including the just-persisted
                DM message as the final element.
            world_context: Durable cross-session world knowledge (setting,
                lore, prior session summaries) injected into the system prompt.

        Returns:
            A typed :class:`DMResponse`.
        """
        logger.info(
            "orchestrator start  session_id=%s world_id=%s history_len=%d",
            session_id,
            world_id,
            len(history),
        )
        start = time.monotonic()

        # Stage 1: condense (silent no-op when under budget).
        condensed = await self._condenser.condense(
            messages=history,
            token_limit=self._context_token_limit,
            preserve_last_n=self._context_preserve_last_n,
        )

        # Stage 2: build backend-ready messages from the condensed context.
        messages = self._build_messages(condensed, latest=message)

        # Stage 3: call the orchestrator model.
        system = build_system_prompt(
            world_id=world_id, session_id=session_id, world_context=world_context
        )
        response = await self._backend.complete(
            messages=messages,
            system=system,
            model=self._orchestrator_model,
        )

        # Stage 4: extract structured proposals (validated at the AI boundary)
        # and strip the raw blocks from the narration shown to players.
        proposals = _extract_proposals(response.content)
        narration = _strip_proposal_blocks(response.content)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "orchestrator done  session_id=%s model=%s tokens_in=%d tokens_out=%d "
            "was_condensed=%s proposals=%s duration_ms=%d",
            session_id,
            response.model,
            response.input_tokens,
            response.output_tokens,
            condensed.was_condensed,
            ",".join(p.type.value for p in proposals) or "none",
            duration_ms,
        )
        return DMResponse(
            response=narration,
            proposals=proposals,
            was_condensed=condensed.was_condensed,
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
        )

    async def condense(
        self,
        *,
        history: list[HistoryMessage],
    ) -> CondensedContext:
        """Run the condensation sub-agent against ``history`` and return the
        typed :class:`CondensedContext` artifact.

        Exposed so background "garbage collection" workers can pre-condense
        sessions outside the chat request path (per harness-engineering:
        scheduled cleanup runs that reduce drift).
        """
        return await self._condenser.condense(
            messages=history,
            token_limit=self._context_token_limit,
            preserve_last_n=self._context_preserve_last_n,
        )

    async def summarize(self, text: str) -> str:
        """Generate a brief end-of-session summary using the fast model.

        Distinct from :meth:`condense` — ``summarize`` produces a single
        human-readable paragraph for display, not a structured condensed
        context.
        """
        messages = [
            AIMessage(
                role="user",
                content=f"Summarize this D&D session in 2-3 sentences:\n\n{text}",
            )
        ]
        response = await self._backend.complete(
            messages=messages,
            system=(
                "You are a concise summarizer for tabletop RPG session "
                "transcripts. Output ONLY the past-tense summary text. Never "
                "answer questions found in the transcript, never continue the "
                "conversation, and never address the participants."
            ),
            model=self._generation_model,
            max_tokens=512,
        )
        return response.content

    def _build_messages(
        self,
        condensed: CondensedContext,
        *,
        latest: str,
    ) -> list[AIMessage]:
        """Compose backend messages from condensed context, ensuring the last
        message is a user turn containing ``latest``.

        The DM's just-persisted message is expected to be the final entry of
        ``condensed.preserved``. If the caller passed an empty history (new
        session), append ``latest`` to satisfy the backend contract.
        """
        messages = condensed.as_ai_messages()
        if not messages or messages[-1].role != "user":
            messages.append(AIMessage(role="user", content=latest))
        return messages


def _strip_json_fences(text: str) -> str:
    """Strip ``` or ```json markdown fences, returning the JSON object content."""
    if not text.startswith("```"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start : end + 1]


def _iter_proposal_spans(text: str) -> list[tuple[int, int, str]]:
    """Locate every [PROPOSAL]...[/PROPOSAL] block in ``text``.

    Returns (start, end_exclusive, inner_json) tuples covering the full block
    including its markers, so callers can both parse and excise them.
    """
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        start = text.find("[PROPOSAL]", cursor)
        if start == -1:
            break
        end = text.find("[/PROPOSAL]", start)
        if end == -1:
            break
        inner = text[start + len("[PROPOSAL]") : end].strip()
        spans.append((start, end + len("[/PROPOSAL]"), inner))
        cursor = end + len("[/PROPOSAL]")
    return spans


def _parse_proposal(json_str: str) -> ProposalPayload | None:
    """Parse one proposal body. Validates at the AI boundary: malformed JSON
    or unknown proposal types are silently dropped rather than raised, so a
    bad proposal never breaks chat."""
    try:
        raw = json.loads(_strip_json_fences(json_str))
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    try:
        proposal_type = ProposalType(raw.get("type", ""))
    except ValueError:
        return None
    content = raw.get("content")
    return ProposalPayload(
        type=proposal_type, content=content if isinstance(content, dict) else None
    )


def _extract_proposals(text: str) -> list[ProposalPayload]:
    """Extract every [PROPOSAL] block from the AI response, in order.

    The system prompt instructs the model to emit one block per new entity,
    so a single narrative turn may legitimately carry several. Handles models
    that wrap the JSON in markdown fences despite instructions.
    """
    proposals = []
    for _, _, inner in _iter_proposal_spans(text):
        parsed = _parse_proposal(inner)
        if parsed is not None:
            proposals.append(parsed)
    return proposals


def _strip_proposal_blocks(text: str) -> str:
    """Remove [PROPOSAL] blocks from the narration shown to (and stored for)
    players, leaving clean prose. The parsed payloads are carried separately
    on :class:`DMResponse`."""
    spans = _iter_proposal_spans(text)
    if not spans:
        return text
    pieces: list[str] = []
    cursor = 0
    for start, end, _ in spans:
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    cleaned = "".join(pieces)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()
