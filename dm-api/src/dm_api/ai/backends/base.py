"""Abstract base for AI provider backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIMessage:
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class AIResponse:
    """Response from an AI backend."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class AIBackend(ABC):
    """Abstract AI provider backend.

    Implementations must be async-compatible.
    """

    @abstractmethod
    async def complete(
        self,
        *,
        messages: list[AIMessage],
        system: str,
        model: str,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Send messages and return the assistant response.

        Args:
            messages: Conversation history.
            system: System prompt.
            model: Model identifier string.
            max_tokens: Maximum tokens in the response.

        Returns:
            AIResponse with content and usage metadata.
        """
