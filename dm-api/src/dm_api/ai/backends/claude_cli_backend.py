"""Backend that shells out to the installed `claude` CLI tool.

This allows developers with a Claude.ai subscription (via Claude Code)
to use dm.ai without a separate ANTHROPIC_API_KEY.

Requirements:
  - `claude` must be on $PATH (install via: npm install -g @anthropic-ai/claude-code)
  - The CLI must be authenticated (run `claude` once to authenticate)

Limitations:
  - Does not support conversation history natively; history is injected into
    the user message as formatted text.
  - Token counts are estimated from character counts.
  - Slower than the API due to subprocess overhead.

CLI flags used:
  --print              Non-interactive / headless mode; prints response and exits.
  --model <name>       Model identifier (e.g. claude-sonnet-4-6).
  --output-format json Emit a JSON object so the response can be parsed reliably.
                       NOTE: exact flag availability may vary across CLI versions.
                       If this flag is absent in an older build, the backend falls
                       back to treating the raw stdout as plain text.
"""
from __future__ import annotations

import asyncio
import json
import shutil

from dm_api.ai.backends.base import AIBackend, AIMessage, AIResponse

_HISTORY_SEPARATOR = "\n\n---\n\n"


class ClaudeCLIBackend(AIBackend):
    """Backend that calls the `claude` CLI via subprocess.

    Raises:
        RuntimeError: If `claude` is not found on PATH.
    """

    def __init__(self) -> None:
        if shutil.which("claude") is None:
            raise RuntimeError(
                "`claude` CLI not found on PATH. "
                "Install it with: npm install -g @anthropic-ai/claude-code"
            )

    async def complete(
        self,
        *,
        messages: list[AIMessage],
        system: str,
        model: str,
        max_tokens: int = 4096,
    ) -> AIResponse:
        prompt = self._build_prompt(messages, system)
        cmd = [
            "claude",
            "--print",           # non-interactive mode
            "--model", model,
            "--output-format", "json",
            prompt,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode().strip()
            raise RuntimeError(f"claude CLI failed (exit {proc.returncode}): {error}")

        return self._parse_output(stdout.decode(), model)

    def _build_prompt(self, messages: list[AIMessage], system: str) -> str:
        """Combine system prompt and history into a single string prompt."""
        parts = [f"[SYSTEM]\n{system}"]
        for msg in messages:
            label = "USER" if msg.role == "user" else "ASSISTANT"
            parts.append(f"[{label}]\n{msg.content}")
        return _HISTORY_SEPARATOR.join(parts)

    def _parse_output(self, raw: str, model: str) -> AIResponse:
        """Parse claude CLI JSON output or fall back to raw text."""
        try:
            data = json.loads(raw)
            content = data.get("result", raw)
        except json.JSONDecodeError:
            content = raw.strip()
        return AIResponse(
            content=content,
            model=model,
            input_tokens=0,   # not available from CLI
            output_tokens=len(content) // 4,  # rough estimate
        )
