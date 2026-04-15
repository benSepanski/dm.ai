"""Factory for creating AI backends from configuration."""

from __future__ import annotations

from dm_api.ai.backends.base import AIBackend


def create_backend(provider: str, api_key: str = "") -> AIBackend:
    """Create and return the configured AI backend.

    Args:
        provider: "anthropic" or "claude_cli"
        api_key: Anthropic API key (only required for "anthropic" provider)

    Returns:
        Configured AIBackend instance.

    Raises:
        ValueError: If provider is not recognized.
        RuntimeError: If "claude_cli" is selected but `claude` is not on PATH.
    """
    if provider == "anthropic":
        from dm_api.ai.backends.anthropic_backend import AnthropicBackend

        return AnthropicBackend(api_key=api_key)
    if provider == "claude_cli":
        from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend

        return ClaudeCLIBackend()
    raise ValueError(
        f"Unknown AI provider {provider!r}. " "Valid options: 'anthropic', 'claude_cli'"
    )
