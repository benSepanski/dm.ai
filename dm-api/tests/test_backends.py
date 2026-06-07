"""Unit tests for AI backend implementations and the factory.

These tests mock all external I/O (Anthropic SDK, subprocess) so they
run without any API key or CLI tool installed.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dm_api.ai.backends.base import AIMessage, AIResponse
from dm_api.ai.backends.mock_backend import MockBackend

# ---------------------------------------------------------------------------
# MockBackend
# ---------------------------------------------------------------------------


async def test_mock_backend_returns_response() -> None:
    """MockBackend returns the scripted content as an AIResponse."""
    backend = MockBackend(responses=["Hello, adventurer!"])
    result = await backend.complete(
        messages=[AIMessage(role="user", content="Hello")],
        system="You are a DM.",
        model="any-model",
    )
    assert isinstance(result, AIResponse)
    assert result.content == "Hello, adventurer!"
    assert result.model == MockBackend.MOCK_MODEL


async def test_mock_backend_cycles_responses() -> None:
    """MockBackend wraps around when the response list is exhausted."""
    backend = MockBackend(responses=["First", "Second"])
    r1 = await backend.complete(messages=[], system="", model="m")
    r2 = await backend.complete(messages=[], system="", model="m")
    r3 = await backend.complete(messages=[], system="", model="m")
    assert r1.content == "First"
    assert r2.content == "Second"
    assert r3.content == "First"


async def test_mock_backend_default_response_is_non_empty() -> None:
    """Bare MockBackend() produces a non-empty placeholder response."""
    backend = MockBackend()
    result = await backend.complete(messages=[], system="", model="m")
    assert len(result.content) > 0


async def test_mock_backend_token_estimates() -> None:
    """Token counts are estimated from character lengths (÷4 convention)."""
    # 80 chars of user message + 40 chars of system = 120 chars → 30 tokens in
    # 40 chars of response → 10 tokens out
    backend = MockBackend(responses=["x" * 40])
    result = await backend.complete(
        messages=[AIMessage(role="user", content="y" * 80)],
        system="z" * 40,
        model="m",
    )
    assert result.input_tokens == 30  # (80 + 40) // 4
    assert result.output_tokens == 10  # 40 // 4


# ---------------------------------------------------------------------------
# AnthropicBackend
# ---------------------------------------------------------------------------


async def test_anthropic_backend_complete_returns_ai_response() -> None:
    """AnthropicBackend maps SDK response fields into a typed AIResponse."""
    from anthropic.types import TextBlock

    from dm_api.ai.backends.anthropic_backend import AnthropicBackend

    mock_usage = MagicMock()
    mock_usage.input_tokens = 100
    mock_usage.output_tokens = 50

    mock_response = MagicMock()
    mock_response.model = "claude-sonnet-4-6"
    mock_response.usage = mock_usage
    mock_response.content = [TextBlock(text="The dragon roars.", type="text")]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "dm_api.ai.backends.anthropic_backend.anthropic.AsyncAnthropic",
        return_value=mock_client,
    ):
        backend = AnthropicBackend(api_key="sk-test")
        result = await backend.complete(
            messages=[AIMessage(role="user", content="Describe the dragon.")],
            system="You are a DM.",
            model="claude-sonnet-4-6",
        )

    assert result.content == "The dragon roars."
    assert result.model == "claude-sonnet-4-6"
    assert result.input_tokens == 100
    assert result.output_tokens == 50


async def test_anthropic_backend_empty_content_returns_empty_string() -> None:
    """When the SDK response has no TextBlock, content is an empty string."""
    from dm_api.ai.backends.anthropic_backend import AnthropicBackend

    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 0

    mock_response = MagicMock()
    mock_response.model = "claude-sonnet-4-6"
    mock_response.usage = mock_usage
    mock_response.content = []

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "dm_api.ai.backends.anthropic_backend.anthropic.AsyncAnthropic",
        return_value=mock_client,
    ):
        backend = AnthropicBackend(api_key="sk-test")
        result = await backend.complete(
            messages=[AIMessage(role="user", content="Hello")],
            system="",
            model="claude-sonnet-4-6",
        )

    assert result.content == ""


async def test_anthropic_backend_passes_correct_args_to_sdk() -> None:
    """AnthropicBackend forwards model, system, messages, and max_tokens to the SDK."""
    from anthropic.types import TextBlock

    from dm_api.ai.backends.anthropic_backend import AnthropicBackend

    mock_usage = MagicMock(input_tokens=5, output_tokens=5)
    mock_response = MagicMock(
        model="claude-haiku-4-5",
        usage=mock_usage,
        content=[TextBlock(text="ok", type="text")],
    )
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch(
        "dm_api.ai.backends.anthropic_backend.anthropic.AsyncAnthropic",
        return_value=mock_client,
    ):
        backend = AnthropicBackend(api_key="sk-test")
        await backend.complete(
            messages=[AIMessage(role="user", content="Hi")],
            system="System text",
            model="claude-haiku-4-5",
            max_tokens=512,
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5"
    assert call_kwargs["system"] == "System text"
    assert call_kwargs["max_tokens"] == 512
    assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]


# ---------------------------------------------------------------------------
# ClaudeCLIBackend
# ---------------------------------------------------------------------------


def test_claude_cli_backend_raises_when_not_on_path() -> None:
    """ClaudeCLIBackend raises RuntimeError when ``claude`` is absent from PATH."""
    from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend

    with patch("dm_api.ai.backends.claude_cli_backend.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="claude.*CLI not found"):
            ClaudeCLIBackend()


async def test_claude_cli_backend_parses_json_output() -> None:
    """ClaudeCLIBackend extracts the ``result`` key from JSON stdout."""
    from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend

    json_out = json.dumps({"result": "The goblin charges!"}).encode()
    mock_proc = MagicMock(returncode=0)
    mock_proc.communicate = AsyncMock(return_value=(json_out, b""))

    with patch(
        "dm_api.ai.backends.claude_cli_backend.shutil.which", return_value="/usr/bin/claude"
    ):
        with patch(
            "dm_api.ai.backends.claude_cli_backend.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ):
            backend = ClaudeCLIBackend()
            result = await backend.complete(
                messages=[AIMessage(role="user", content="What does the goblin do?")],
                system="You are a DM.",
                model="claude-haiku-4-5-20251001",
            )

    assert result.content == "The goblin charges!"
    assert result.model == "claude-haiku-4-5-20251001"


async def test_claude_cli_backend_falls_back_to_raw_text_on_non_json() -> None:
    """When CLI stdout is not JSON, raw text is used as content."""
    from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend

    raw_out = b"  Not a JSON response.  "
    mock_proc = MagicMock(returncode=0)
    mock_proc.communicate = AsyncMock(return_value=(raw_out, b""))

    with patch(
        "dm_api.ai.backends.claude_cli_backend.shutil.which", return_value="/usr/bin/claude"
    ):
        with patch(
            "dm_api.ai.backends.claude_cli_backend.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ):
            backend = ClaudeCLIBackend()
            result = await backend.complete(messages=[], system="", model="m")

    assert result.content == "Not a JSON response."


async def test_claude_cli_backend_raises_on_nonzero_exit() -> None:
    """ClaudeCLIBackend raises RuntimeError when the subprocess exits non-zero."""
    from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend

    mock_proc = MagicMock(returncode=1)
    mock_proc.communicate = AsyncMock(return_value=(b"", b"authentication error"))

    with patch(
        "dm_api.ai.backends.claude_cli_backend.shutil.which", return_value="/usr/bin/claude"
    ):
        with patch(
            "dm_api.ai.backends.claude_cli_backend.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ):
            backend = ClaudeCLIBackend()
            with pytest.raises(RuntimeError, match="claude CLI failed"):
                await backend.complete(messages=[], system="", model="m")


async def test_claude_cli_backend_builds_prompt_with_history() -> None:
    """ClaudeCLIBackend injects conversation history into the single CLI prompt."""
    from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend

    captured_cmd: list[str] = []

    async def fake_exec(*args: str, **kwargs: object) -> MagicMock:
        captured_cmd.extend(args)
        proc = MagicMock(returncode=0)
        proc.communicate = AsyncMock(return_value=(b'{"result": "ok"}', b""))
        return proc

    with patch(
        "dm_api.ai.backends.claude_cli_backend.shutil.which", return_value="/usr/bin/claude"
    ):
        with patch(
            "dm_api.ai.backends.claude_cli_backend.asyncio.create_subprocess_exec",
            side_effect=fake_exec,
        ):
            backend = ClaudeCLIBackend()
            await backend.complete(
                messages=[
                    AIMessage(role="user", content="Open door."),
                    AIMessage(role="assistant", content="The door creaks open."),
                    AIMessage(role="user", content="Enter room."),
                ],
                system="Be a dungeon master.",
                model="m",
            )

    # The last positional arg to create_subprocess_exec is the full prompt string.
    prompt = captured_cmd[-1]
    assert "[SYSTEM]" in prompt
    assert "Be a dungeon master." in prompt
    assert "[USER]" in prompt
    assert "Open door." in prompt
    assert "[ASSISTANT]" in prompt
    assert "The door creaks open." in prompt


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_creates_anthropic_backend() -> None:
    from dm_api.ai.backends.anthropic_backend import AnthropicBackend
    from dm_api.ai.backends.factory import create_backend

    with patch("dm_api.ai.backends.anthropic_backend.anthropic.AsyncAnthropic"):
        backend = create_backend(provider="anthropic", api_key="sk-test")
    assert isinstance(backend, AnthropicBackend)


def test_factory_creates_claude_cli_backend() -> None:
    from dm_api.ai.backends.claude_cli_backend import ClaudeCLIBackend
    from dm_api.ai.backends.factory import create_backend

    with patch(
        "dm_api.ai.backends.claude_cli_backend.shutil.which", return_value="/usr/bin/claude"
    ):
        backend = create_backend(provider="claude_cli")
    assert isinstance(backend, ClaudeCLIBackend)


def test_factory_creates_mock_backend() -> None:
    from dm_api.ai.backends.factory import create_backend

    backend = create_backend(provider="mock")
    assert isinstance(backend, MockBackend)


def test_factory_raises_on_unknown_provider() -> None:
    from dm_api.ai.backends.factory import create_backend

    with pytest.raises(ValueError, match="Unknown AI provider"):
        create_backend(provider="totally_unknown")
