"""Scripted mock backend for development and testing without API credentials.

Use ``AI_PROVIDER=mock`` in ``.env`` (or the environment) to run the full
dm.ai stack locally without an Anthropic API key or the Claude CLI.

The backend cycles through a list of canned responses so integration tests
can drive deterministic flows, and developers can explore the UI / WebSocket
behaviour without burning API quota.
"""

from __future__ import annotations

import logging

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse

logger = logging.getLogger(__name__)

_DEFAULT_RESPONSE = (
    "You stand at a crossroads deep in the Thornwood. "
    "The old oak tree groans in the wind, its branches reaching like gnarled fingers "
    "toward an iron sky. Torchlight flickers on mossy cobblestones. "
    "What will you do?\n\n"
    "[Note: mock backend active — set AI_PROVIDER=anthropic or claude_cli for real DM responses.]"
)


class MockBackend(AIBackend):
    """Scripted AI backend that returns canned responses without any API call.

    Cycles through ``responses`` in order; wraps around when exhausted.
    Token counts are estimated from character lengths (same convention as
    :class:`~dm_api.ai.backends.claude_cli_backend.ClaudeCLIBackend`).

    Args:
        responses: Response strings to cycle through.  Defaults to a single
            placeholder narrative so a bare ``MockBackend()`` produces
            visible, harmless output on every call.
    """

    MOCK_MODEL = "mock-v1"

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = responses if responses is not None else [_DEFAULT_RESPONSE]
        self._index = 0

    async def complete(
        self,
        *,
        messages: list[AIMessage],
        system: str,
        model: str,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Return the next scripted response, cycling when exhausted.

        Args:
            messages: Conversation history (used only for token estimation).
            system: System prompt (used only for token estimation).
            model: Ignored; the mock always reports :attr:`MOCK_MODEL`.
            max_tokens: Ignored by the mock.

        Returns:
            :class:`~dm_api.ai.backends.base.AIResponse` with canned content
            and estimated token counts.
        """
        content = self._responses[self._index % len(self._responses)]
        self._index += 1
        tokens_in = (sum(len(m.content) for m in messages) + len(system)) // 4
        tokens_out = len(content) // 4
        logger.debug(
            "mock complete  model=%s tokens_in_est=%d tokens_out_est=%d",
            self.MOCK_MODEL,
            tokens_in,
            tokens_out,
        )
        return AIResponse(
            content=content,
            model=self.MOCK_MODEL,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
        )
