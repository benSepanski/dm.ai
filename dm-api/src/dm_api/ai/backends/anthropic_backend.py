"""Anthropic API backend using the anthropic SDK."""

from __future__ import annotations

import logging
import time

import anthropic
from anthropic.types import MessageParam, TextBlock

from dm_api.ai.backends.base import (
    AIBackend,
    AIBackendError,
    AIErrorCategory,
    AIMessage,
    AIResponse,
)

logger = logging.getLogger(__name__)


def _to_backend_error(exc: anthropic.APIError) -> AIBackendError:
    """Map an anthropic SDK error to a categorized, DM-facing AIBackendError."""
    if isinstance(exc, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return AIBackendError(
            AIErrorCategory.AUTH,
            "AI provider rejected the request (authentication failed) — "
            "check ANTHROPIC_API_KEY.",
        )
    if isinstance(exc, anthropic.RateLimitError):
        return AIBackendError(
            AIErrorCategory.RATE_LIMIT,
            "AI provider rate limit reached — wait a moment and try again.",
        )
    logger.warning("anthropic provider error: %s", exc)
    return AIBackendError(
        AIErrorCategory.TRANSIENT,
        "The AI provider is temporarily unavailable — your message was saved; try again.",
    )


class AnthropicBackend(AIBackend):
    """Backend that calls the Anthropic API directly using an API key.

    Requires ANTHROPIC_API_KEY to be set in the environment.
    """

    def __init__(self, api_key: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        *,
        messages: list[AIMessage],
        system: str,
        model: str,
        max_tokens: int = 4096,
    ) -> AIResponse:
        sdk_messages: list[MessageParam] = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        start = time.monotonic()
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=sdk_messages,
            )
        except anthropic.APIError as exc:
            raise _to_backend_error(exc) from exc
        duration_ms = int((time.monotonic() - start) * 1000)
        text_blocks = [b for b in response.content if isinstance(b, TextBlock)]
        if not text_blocks:
            logger.warning(
                "anthropic returned no text block  model=%s stop_reason=%s",
                response.model,
                response.stop_reason,
            )
        content = text_blocks[0].text if text_blocks else ""
        logger.debug(
            "anthropic complete  model=%s tokens_in=%d tokens_out=%d duration_ms=%d",
            response.model,
            response.usage.input_tokens,
            response.usage.output_tokens,
            duration_ms,
        )
        return AIResponse(
            content=content,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
