"""
DM Orchestrator – the core AI agent that drives the dungeon-master experience.

The orchestrator receives a player/DM message, assembles context (world lore,
character sheets, recent chat history), calls the Claude API, and returns a
structured response that may include a world-building proposal.
"""

from __future__ import annotations

from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.ai.prompts.system_prompt import build_system_prompt


class DMOrchestrator:
    """Stateless orchestrator that turns a chat message into an AI response."""

    def __init__(
        self,
        anthropic_client: anthropic.AsyncAnthropic,
        model: str = "claude-opus-4-6",
    ) -> None:
        self._client = anthropic_client
        self._model = model

    async def handle_message(
        self,
        *,
        message: str,
        session_id: str,
        world_id: str,
        history: list[dict[str, str]],
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Process a chat message and return the AI response.

        Returns:
            Dict with keys:
                response (str): The AI's narrative response text.
                proposal (dict | None): An optional world-building proposal
                    with ``type`` and ``content`` keys.
        """
        system_prompt = build_system_prompt(world_id=world_id, session_id=session_id)

        # Convert history to Anthropic message format
        messages: list[dict[str, str]] = []
        for entry in history:
            role = "user" if entry["role"] == "dm" else "assistant"
            messages.append({"role": role, "content": entry["content"]})

        # Ensure the conversation ends with the latest user message
        if not messages or messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": message})

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        )

        ai_text = response.content[0].text

        # Parse proposal from AI response if present
        proposal = self._extract_proposal(ai_text)

        return {"response": ai_text, "proposal": proposal}

    @staticmethod
    def _extract_proposal(text: str) -> dict[str, Any] | None:
        """Extract a structured proposal from the AI response text.

        Looks for a JSON block tagged with ``[PROPOSAL]`` markers.
        Returns None if no proposal is found.
        """
        import json

        start_marker = "[PROPOSAL]"
        end_marker = "[/PROPOSAL]"

        start = text.find(start_marker)
        if start == -1:
            return None

        end = text.find(end_marker, start)
        if end == -1:
            return None

        json_str = text[start + len(start_marker) : end].strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
