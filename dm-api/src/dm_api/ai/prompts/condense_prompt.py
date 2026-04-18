"""Sub-agent prompt for context condensation.

Harness-engineering principles applied:
- Narrow, focused sub-task: one job (condense chat history) with no role-play.
- Typed output contract: JSON schema explicitly enumerated in the prompt.
- Citation anchors: the sub-agent is instructed to preserve ``msg:<id>@<ts>``
  references so the condensed output traces back to source messages (the DM
  session analog of ``filepath:lineno``).
"""

from __future__ import annotations


def build_condense_prompt() -> str:
    """Return the system prompt for the condensation sub-agent.

    Kept short on purpose — OpenAI's harness-engineering guidance recommends
    concise, universally-applicable agent instructions and discourages
    bundled role-play, conditional logic, or unrelated context.
    """
    return (
        "You are a condensation sub-agent for a D&D session assistant.\n"
        "Your ONLY job is to compress a transcript into structured JSON.\n"
        "\n"
        "Output schema (strict):\n"
        '  {"synopsis": string,\n'
        '   "key_facts": string[],\n'
        '   "open_threads": string[]}\n'
        "\n"
        "Rules:\n"
        "- synopsis: 2-4 sentences capturing what happened, in past tense.\n"
        "- key_facts: established world / character / rules facts that must\n"
        "  persist into future turns (names, relationships, locations, HP, etc.).\n"
        "- open_threads: unresolved hooks, questions, or pending player choices.\n"
        "- When referencing a specific event, cite the anchor in the form\n"
        "  msg:<uuid>@<iso-timestamp> exactly as it appears in the transcript.\n"
        "- Do NOT invent facts. Do NOT role-play. Do NOT wrap in markdown.\n"
        "- Output valid JSON only, nothing before or after."
    )
