"""Anthropic API backend using the anthropic SDK."""
from __future__ import annotations

import anthropic

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse


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
        sdk_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=sdk_messages,
        )
        return AIResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
