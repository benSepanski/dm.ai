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

    ``pending_narration`` carries the gated narration sentence(s) — wrapped by
    the model in ``[PENDING]...[/PENDING]`` adjacent to this proposal's
    ``[PROPOSAL]`` block — that assert this (not-yet-canon) entity as settled
    fact. ``None`` when the turn had no matching pending block for this
    proposal (either the model omitted one, or PENDING/PROPOSAL pairing was
    unsafe for this message).
    """

    type: ProposalType
    content: dict[str, Any] | None
    pending_narration: str | None = None


@dataclass
class NarrationExtraction:
    """Result of :func:`_extract_narration_and_proposals`.

    ``narration`` has both ``[PROPOSAL]`` and ``[PENDING]`` tag families
    stripped; ``proposals`` carries each proposal's paired ``pending_narration``
    (if any).
    """

    narration: str
    proposals: list[ProposalPayload]


@dataclass
class DMResponse:
    """Typed orchestrator result — no ``dict[str, Any]`` at the API boundary.

    ``response`` is the display narration with all ``[PROPOSAL]`` and
    ``[PENDING]`` blocks stripped; the parsed proposals live in ``proposals``
    (the model may emit one block per new entity, so a single turn can carry
    several), each carrying its own gated ``pending_narration`` (PT-21) that
    only reaches chat once the DM accepts that proposal.
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

        # Stage 4: extract structured proposals (validated at the AI boundary),
        # pair each with its gated [PENDING] narration, and strip both tag
        # families from the narration shown to players.
        extraction = _extract_narration_and_proposals(response.content)
        proposals = extraction.proposals
        narration = extraction.narration
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


def _iter_pending_spans(text: str) -> list[tuple[int, int, str]]:
    """Locate every [PENDING]...[/PENDING] block in ``text``.

    Mirrors :func:`_iter_proposal_spans`. Returns (start, end_exclusive,
    inner_text) tuples covering the full block including its markers.
    """
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        start = text.find("[PENDING]", cursor)
        if start == -1:
            break
        end = text.find("[/PENDING]", start)
        if end == -1:
            break
        inner = text[start + len("[PENDING]") : end].strip()
        spans.append((start, end + len("[/PENDING]"), inner))
        cursor = end + len("[/PENDING]")
    return spans


def _parse_proposal(json_str: str) -> ProposalPayload | None:
    """Parse one proposal body. Validates at the AI boundary: malformed JSON
    or unknown proposal types are silently dropped rather than raised, so a
    bad proposal never breaks chat."""
    try:
        raw = json.loads(_strip_json_fences(json_str))
    except json.JSONDecodeError as exc:
        logger.debug("proposal json decode failed: %s — snippet: %.80r", exc, json_str)
        return None
    if not isinstance(raw, dict):
        logger.debug("proposal is not a dict: %.80r", raw)
        return None
    try:
        proposal_type = ProposalType(raw.get("type", ""))
    except ValueError:
        logger.debug("unknown proposal type: %.40r", raw.get("type"))
        return None
    content = raw.get("content")
    return ProposalPayload(
        type=proposal_type, content=content if isinstance(content, dict) else None
    )


def _strip_spans(text: str, spans: list[tuple[int, int, str]]) -> str:
    """Remove the given (start, end_exclusive, ...) spans from ``text``,
    collapsing resulting blank-line runs down to a single blank line."""
    if not spans:
        return text
    pieces: list[str] = []
    cursor = 0
    for start, end, *_ in sorted(spans, key=lambda s: s[0]):
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    cleaned = "".join(pieces)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def _extract_narration_and_proposals(text: str) -> NarrationExtraction:
    """Extract every [PROPOSAL] block plus its paired [PENDING] narration.

    The system prompt allows a [PROPOSAL] to have zero PENDING blocks
    (partial coverage — e.g. a location merely noticed, not yet described),
    so pairing cannot assume the Nth PENDING matches the Nth PROPOSAL by
    count alone. Instead each PENDING block is paired with the nearest
    following, not-yet-claimed [PROPOSAL] block — mirroring the system
    prompt's instruction to place a PENDING block "immediately adjacent" to
    (i.e. directly before) the proposal it gates. If any PENDING block has no
    following unclaimed proposal to attach to, pairing is unsafe: a warning
    is logged and ALL pending text in this message is dropped — never
    guessed — while every proposal is still kept and shown normally. Both tag
    families are stripped from the returned narration regardless.
    """
    proposal_spans = _iter_proposal_spans(text)
    pending_spans = _iter_pending_spans(text)

    pending_by_proposal_index: dict[int, str] = {}
    pairing_failed = False
    next_proposal_idx = 0
    for pending_start, _, pending_inner in pending_spans:
        while (
            next_proposal_idx < len(proposal_spans)
            and proposal_spans[next_proposal_idx][0] < pending_start
        ):
            next_proposal_idx += 1
        if next_proposal_idx >= len(proposal_spans):
            pairing_failed = True
            break
        pending_by_proposal_index[next_proposal_idx] = pending_inner
        next_proposal_idx += 1

    if pairing_failed:
        logger.warning(
            "PENDING/PROPOSAL pairing failed (pending=%d proposals=%d) — "
            "dropping all pending narration for this message",
            len(pending_spans),
            len(proposal_spans),
        )
        pending_by_proposal_index = {}

    proposals: list[ProposalPayload] = []
    for idx, (_, _, inner) in enumerate(proposal_spans):
        parsed = _parse_proposal(inner)
        if parsed is not None:
            parsed.pending_narration = pending_by_proposal_index.get(idx)
            proposals.append(parsed)

    narration = _strip_spans(text, [*proposal_spans, *pending_spans])
    return NarrationExtraction(narration=narration, proposals=proposals)
