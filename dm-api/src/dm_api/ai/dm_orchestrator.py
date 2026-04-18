"""
DM Orchestrator — the core AI agent that drives the dungeon-master experience.

Applies OpenAI's harness-engineering principles
(https://openai.com/index/harness-engineering/):

- **Layered architecture.** The orchestrator sits in the Service layer. It
  consumes ``AIBackend`` (Repo/Gateway) and delegates context condensation to
  :class:`dm_api.ai.condenser.ContextCondenser` (Service), never reaching into
  the DB (Repo) or HTTP (Runtime) layers directly.
- **Typed boundaries.** Inputs and outputs are ``@dataclass`` instances; no
  ``dict[str, Any]`` crosses this module's public surface except the minimally
  structured proposal payload parsed from AI output.
- **Depth-first decomposition.** ``handle_message`` is factored into discrete
  sub-steps (condense → build messages → call backend → extract proposal) that
  are individually testable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from dm_api.ai.backends.base import AIBackend, AIMessage
from dm_api.ai.condenser import CondensedContext, ContextCondenser, HistoryMessage
from dm_api.ai.prompts.system_prompt import build_system_prompt


@dataclass
class DMResponse:
    """Typed orchestrator result — no ``dict[str, Any]`` at the API boundary."""

    response: str
    proposal: dict[str, Any] | None
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

        Returns:
            A typed :class:`DMResponse`.
        """
        # Stage 1: condense (silent no-op when under budget).
        condensed = await self._condenser.condense(
            messages=history,
            token_limit=self._context_token_limit,
            preserve_last_n=self._context_preserve_last_n,
        )

        # Stage 2: build backend-ready messages from the condensed context.
        messages = self._build_messages(condensed, latest=message)

        # Stage 3: call the orchestrator model.
        system = build_system_prompt(world_id=world_id, session_id=session_id)
        response = await self._backend.complete(
            messages=messages,
            system=system,
            model=self._orchestrator_model,
        )

        # Stage 4: extract structured proposal (validated at the AI boundary).
        proposal = _extract_proposal(response.content)
        return DMResponse(
            response=response.content,
            proposal=proposal,
            was_condensed=condensed.was_condensed,
            tokens_in=condensed.tokens_in,
            tokens_out=condensed.tokens_out,
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
            system="You are a concise summarizer for tabletop RPG sessions.",
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


def _extract_proposal(text: str) -> dict[str, Any] | None:
    """Extract a [PROPOSAL]...[/PROPOSAL] JSON block from AI response text.

    Validates at the AI boundary: silently drops malformed JSON rather than
    raising, so a single bad proposal never breaks the chat flow.
    """
    start = text.find("[PROPOSAL]")
    if start == -1:
        return None
    end = text.find("[/PROPOSAL]", start)
    if end == -1:
        return None
    json_str = text[start + len("[PROPOSAL]") : end].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None
