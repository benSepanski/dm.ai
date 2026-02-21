"""
DM Orchestrator – the core AI agent that drives the dungeon-master experience.

Uses a configurable AI backend (Anthropic API or claude CLI) and supports
separate model roles for different task types.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.ai.backends.base import AIBackend, AIMessage
from dm_api.ai.prompts.system_prompt import build_system_prompt


class DMOrchestrator:
    """Stateless orchestrator: turns a chat message into a structured AI response.

    Args:
        backend: AI provider backend (AnthropicBackend or ClaudeCLIBackend).
        orchestrator_model: Model for main chat responses.
        generation_model: Model for quick generation tasks (summaries, etc.).
    """

    def __init__(
        self,
        backend: AIBackend,
        orchestrator_model: str,
        generation_model: str,
    ) -> None:
        self._backend = backend
        self._orchestrator_model = orchestrator_model
        self._generation_model = generation_model

    async def handle_message(
        self,
        *,
        message: str,
        session_id: str,
        world_id: str,
        history: list[dict[str, str]],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Process a chat message and return the AI DM response.

        Returns:
            Dict with:
                response (str): Narrative response text.
                proposal (dict | None): Optional world-building proposal with
                    ``type`` and ``content`` keys.
        """
        system = build_system_prompt(world_id=world_id, session_id=session_id)
        messages = self._build_messages(history, message)

        response = await self._backend.complete(
            messages=messages,
            system=system,
            model=self._orchestrator_model,
        )

        proposal = _extract_proposal(response.content)
        return {"response": response.content, "proposal": proposal}

    async def summarize(self, text: str) -> str:
        """Generate a brief summary using the fast generation model."""
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

    def _build_messages(self, history: list[dict[str, str]], latest: str) -> list[AIMessage]:
        messages = []
        for entry in history:
            role = "user" if entry["role"] == "dm" else "assistant"
            messages.append(AIMessage(role=role, content=entry["content"]))
        if not messages or messages[-1].role != "user":
            messages.append(AIMessage(role="user", content=latest))
        return messages


def _extract_proposal(text: str) -> dict[str, Any] | None:
    """Extract a [PROPOSAL]...[/PROPOSAL] JSON block from AI response text."""
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
