"""Proposal + gated-narration extraction from raw AI DM narration text.

Split out of ``dm_orchestrator.py`` (file-length guideline) — owns parsing
``[PROPOSAL]...[/PROPOSAL]`` and ``[PENDING]...[/PENDING]`` tags out of the
model's response and validating each proposal's JSON body at the AI
boundary (malformed input degrades gracefully, never raises).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from game_engine.types import ProposalType

logger = logging.getLogger(__name__)


@dataclass
class ProposalPayload:
    """Typed representation of an AI-generated proposal.

    Parsed and validated at the AI boundary inside ``_parse_proposal``.
    The ``content`` field is free-form JSON (varies by proposal type) and
    remains untyped, but ``type`` is always a known :class:`ProposalType`.

    ``pending_narration`` carries the gated narration sentence(s) — wrapped by
    the model in ``[PENDING]...[/PENDING]`` adjacent to this proposal's
    ``[PROPOSAL]`` block — that assert this (not-yet-canon) entity as settled
    fact. ``None`` when the turn had no matching pending block for this
    proposal (either the model omitted one, or PENDING/PROPOSAL pairing was
    unsafe for this message).
    """

    type: ProposalType
    content: dict[str, Any] | None
    pending_narration: str | None = None


@dataclass
class NarrationExtraction:
    """Result of :func:`extract_narration_and_proposals`.

    ``narration`` has both ``[PROPOSAL]`` and ``[PENDING]`` tag families
    stripped; ``proposals`` carries each proposal's paired ``pending_narration``
    (if any).
    """

    narration: str
    proposals: list[ProposalPayload]


def _strip_json_fences(text: str) -> str:
    """Strip ``` or ```json markdown fences, returning the JSON object content."""
    if not text.startswith("```"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return text
    return text[start : end + 1]


def _iter_proposal_spans(text: str) -> list[tuple[int, int, str]]:
    """Locate every [PROPOSAL]...[/PROPOSAL] block in ``text``.

    Returns (start, end_exclusive, inner_json) tuples covering the full block
    including its markers, so callers can both parse and excise them.
    """
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        start = text.find("[PROPOSAL]", cursor)
        if start == -1:
            break
        end = text.find("[/PROPOSAL]", start)
        if end == -1:
            break
        inner = text[start + len("[PROPOSAL]") : end].strip()
        spans.append((start, end + len("[/PROPOSAL]"), inner))
        cursor = end + len("[/PROPOSAL]")
    return spans


def _iter_pending_spans(text: str) -> list[tuple[int, int, str]]:
    """Locate every [PENDING]...[/PENDING] block in ``text``.

    Mirrors :func:`_iter_proposal_spans`. Returns (start, end_exclusive,
    inner_text) tuples covering the full block including its markers.
    """
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    while True:
        start = text.find("[PENDING]", cursor)
        if start == -1:
            break
        end = text.find("[/PENDING]", start)
        if end == -1:
            break
        inner = text[start + len("[PENDING]") : end].strip()
        spans.append((start, end + len("[/PENDING]"), inner))
        cursor = end + len("[/PENDING]")
    return spans


def _parse_proposal(json_str: str) -> ProposalPayload | None:
    """Parse one proposal body. Validates at the AI boundary: malformed JSON
    or unknown proposal types are silently dropped rather than raised, so a
    bad proposal never breaks chat."""
    try:
        raw = json.loads(_strip_json_fences(json_str))
    except json.JSONDecodeError as exc:
        logger.debug("proposal json decode failed: %s — snippet: %.80r", exc, json_str)
        return None
    if not isinstance(raw, dict):
        logger.debug("proposal is not a dict: %.80r", raw)
        return None
    try:
        proposal_type = ProposalType(raw.get("type", ""))
    except ValueError:
        logger.debug("unknown proposal type: %.40r", raw.get("type"))
        return None
    content = raw.get("content")
    return ProposalPayload(
        type=proposal_type, content=content if isinstance(content, dict) else None
    )


def _strip_spans(text: str, spans: list[tuple[int, int, str]]) -> str:
    """Remove the given (start, end_exclusive, ...) spans from ``text``,
    collapsing resulting blank-line runs down to a single blank line."""
    if not spans:
        return text
    pieces: list[str] = []
    cursor = 0
    for start, end, *_ in sorted(spans, key=lambda s: s[0]):
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    cleaned = "".join(pieces)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def extract_narration_and_proposals(text: str) -> NarrationExtraction:
    """Extract every [PROPOSAL] block plus its paired [PENDING] narration.

    The system prompt allows a [PROPOSAL] to have zero PENDING blocks
    (partial coverage — e.g. a location merely noticed, not yet described),
    so pairing cannot assume the Nth PENDING matches the Nth PROPOSAL by
    count alone. Instead each PENDING block is paired with the nearest
    following, not-yet-claimed [PROPOSAL] block — mirroring the system
    prompt's instruction to place a PENDING block "immediately adjacent" to
    (i.e. directly before) the proposal it gates. If any PENDING block has no
    following unclaimed proposal to attach to, pairing is unsafe: a warning
    is logged and ALL pending text in this message is dropped — never
    guessed — while every proposal is still kept and shown normally. Both tag
    families are stripped from the returned narration regardless.
    """
    proposal_spans = _iter_proposal_spans(text)
    pending_spans = _iter_pending_spans(text)

    pending_by_proposal_index: dict[int, str] = {}
    pairing_failed = False
    next_proposal_idx = 0
    for pending_start, _, pending_inner in pending_spans:
        while (
            next_proposal_idx < len(proposal_spans)
            and proposal_spans[next_proposal_idx][0] < pending_start
        ):
            next_proposal_idx += 1
        if next_proposal_idx >= len(proposal_spans):
            pairing_failed = True
            break
        pending_by_proposal_index[next_proposal_idx] = pending_inner
        next_proposal_idx += 1

    if pairing_failed:
        logger.warning(
            "PENDING/PROPOSAL pairing failed (pending=%d proposals=%d) — "
            "dropping all pending narration for this message",
            len(pending_spans),
            len(proposal_spans),
        )
        pending_by_proposal_index = {}

    proposals: list[ProposalPayload] = []
    for idx, (_, _, inner) in enumerate(proposal_spans):
        parsed = _parse_proposal(inner)
        if parsed is not None:
            parsed.pending_narration = pending_by_proposal_index.get(idx)
            proposals.append(parsed)

    narration = _strip_spans(text, [*proposal_spans, *pending_spans])
    return NarrationExtraction(narration=narration, proposals=proposals)
