"""Abstract base for AI provider backends."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


class AIErrorCategory(str, enum.Enum):
    """Why an AI provider call failed, used to surface an actionable message.

    The AI call is an untrusted boundary: providers fail for distinct reasons
    that warrant different operator action, so the category is carried as an
    enum rather than parsed from a free-form string downstream.
    """

    AUTH = "auth"  # bad/missing credentials (e.g. invalid ANTHROPIC_API_KEY)
    RATE_LIMIT = "rate_limit"  # provider throttled the request
    TRANSIENT = "transient"  # timeout, connection error, or upstream 5xx


class AIBackendError(Exception):
    """A categorized failure from an AI provider backend.

    Backends raise this instead of letting provider-specific exceptions bubble
    up as an opaque 500. ``message`` is safe to show to the DM.
    """

    def __init__(self, category: AIErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


@dataclass(frozen=True)
class AIReadiness:
    """Whether the configured AI backend looks usable, for /health and startup.

    A cheap, no-network config check — it catches the common "placeholder key"
    / "claude not installed" mistakes before game night without paying for an
    auth round-trip on every boot or health poll.
    """

    provider: str
    ready: bool
    detail: str


@dataclass
class AIMessage:
    """A single message in a conversation."""

    role: Literal["user", "assistant"]
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
