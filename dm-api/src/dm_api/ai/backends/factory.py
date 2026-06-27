"""Factory for creating AI backends from configuration."""

from __future__ import annotations

import shutil

from dm_api.ai.backends.base import AIBackend, AIReadiness


def check_ai_readiness(provider: str, api_key: str = "") -> AIReadiness:
    """Cheaply check whether the configured AI backend looks usable.

    No network calls: for "anthropic" it verifies a real-looking API key (the
    Anthropic key prefix), which catches empty/placeholder values; for
    "claude_cli" it verifies the `claude` binary is on PATH. Used by /health
    and the startup banner so a misconfigured backend is caught before the
    first chat turn, not mid-session.
    """
    if provider == "anthropic":
        if api_key.startswith("sk-ant-"):
            return AIReadiness(provider, True, "ANTHROPIC_API_KEY is set.")
        return AIReadiness(
            provider,
            False,
            "ANTHROPIC_API_KEY is missing or looks like a placeholder "
            "(expected a key starting with 'sk-ant-').",
        )
    if provider == "claude_cli":
        if shutil.which("claude") is not None:
            return AIReadiness(provider, True, "`claude` CLI found on PATH.")
        return AIReadiness(
            provider,
            False,
            "`claude` CLI not found on PATH — claude_cli requires running the "
            "api on the host, not in the Docker image.",
        )
    return AIReadiness(provider, False, f"Unknown AI provider {provider!r}.")


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
