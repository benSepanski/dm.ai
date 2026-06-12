from __future__ import annotations

import functools
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from game_engine.types import ChatRole, ProposalStatus
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.ai.backends.base import AIBackend
from dm_api.ai.condenser import HistoryMessage, MessageAnchor
from dm_api.ai.dm_orchestrator import DMOrchestrator, ProposalPayload
from dm_api.ai.prompts.system_prompt import WorldContext
from dm_api.api.ws import broadcast_to_session
from dm_api.config import settings
from dm_api.db.models.chat import ChatMessage, ChatMessageRead
from dm_api.db.models.game_config import EffectiveGameConfig, GameConfig, resolve_game_config
from dm_api.db.models.proposal import Proposal, ProposalRead
from dm_api.db.models.session import GameSession, SessionCreate, SessionRead
from dm_api.db.models.world import World
from dm_api.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# Most recent ended sessions whose summaries are injected into the system
# prompt for cross-session continuity. Summaries are 2-3 sentences each, so
# the token cost stays negligible.
_PRIOR_SESSION_LIMIT = 10


@functools.lru_cache(maxsize=None)
def _get_backend(provider: str) -> AIBackend:
    """Return the process-wide singleton AI backend for ``provider``.

    Cached per provider so the AnthropicBackend (and its underlying HTTP
    connection pool) is created once per process rather than once per request,
    while games configured with different providers each get their own backend.
    """
    from dm_api.ai.backends.factory import create_backend

    return create_backend(
        provider=provider,
        api_key=settings.anthropic_api_key,
    )


async def _fetch_effective_config(db: AsyncSession, world_id: uuid.UUID) -> EffectiveGameConfig:
    """Resolve the game's config (stored overrides merged with deployment defaults)."""
    result = await db.execute(select(GameConfig).where(GameConfig.world_id == world_id))
    return resolve_game_config(result.scalar_one_or_none())


def _make_orchestrator(config: EffectiveGameConfig) -> DMOrchestrator:
    """Return a fresh DMOrchestrator honoring the game's effective config.

    DMOrchestrator is stateless and cheap to construct; only the backend
    (which holds the HTTP connection pool) is cached.
    """
    return DMOrchestrator(
        backend=_get_backend(config.ai_provider),
        orchestrator_model=config.orchestrator_model,
        generation_model=config.generation_model,
        context_token_limit=config.context_token_limit,
        context_preserve_last_n=config.context_preserve_last_n,
    )


async def _fetch_session_or_404(db: AsyncSession, session_id: uuid.UUID) -> GameSession:
    result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _fetch_history(db: AsyncSession, session_id: uuid.UUID) -> list[HistoryMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    return [
        HistoryMessage(
            anchor=MessageAnchor(
                message_id=m.id,
                timestamp=m.timestamp,
                role=m.role,
            ),
            content=m.content,
            token_count=m.token_count,
        )
        for m in result.scalars().all()
    ]


async def _fetch_world_context(
    db: AsyncSession,
    world_id: uuid.UUID,
    current_session_id: uuid.UUID,
) -> WorldContext:
    """Build the typed cross-session context for the orchestrator's system prompt.

    Combines the world's setting/lore with summaries of the most recently
    ended sessions in the same world (chronological order, oldest first).
    """
    world = (await db.execute(select(World).where(World.id == world_id))).scalar_one_or_none()
    result = await db.execute(
        select(GameSession)
        .where(
            GameSession.world_id == world_id,
            GameSession.id != current_session_id,
            GameSession.session_summary.is_not(None),
        )
        .order_by(GameSession.started_at.desc())
        .limit(_PRIOR_SESSION_LIMIT)
    )
    prior_sessions = list(reversed(result.scalars().all()))
    return WorldContext(
        setting_description=world.setting_description if world else None,
        lore_summary=world.lore_summary if world else None,
        prior_session_summaries=tuple(f"{s.name}: {s.session_summary}" for s in prior_sessions),
    )


async def _broadcast_dm_message(
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    content: str,
) -> None:
    """Emit the DM message to WebSocket clients immediately (fire-and-forget).

    Called before the slow orchestrator so player screens update right away.
    Clients dedupe on message_id, so the sender seeing its own echo is safe.
    """
    try:
        await broadcast_to_session(
            session_id,
            {
                "type": "chat_message",
                "session_id": str(session_id),
                "message_id": str(message_id),
                "role": ChatRole.DM.value,
                "content": content,
            },
        )
    except Exception:
        logger.exception("ws broadcast failed session_id=%s", session_id)


async def _broadcast_ai_response(
    session_id: uuid.UUID,
    message_id: str,
    content: str,
    proposals: list[ProposalRead],
) -> None:
    """Emit the AI reply and any proposals to WebSocket clients after commit."""
    try:
        await broadcast_to_session(
            session_id,
            {
                "type": "chat_message",
                "session_id": str(session_id),
                "message_id": message_id,
                "role": ChatRole.AI.value,
                "content": content,
            },
        )
        for proposal in proposals:
            await broadcast_to_session(
                session_id,
                {
                    "type": "proposal_ready",
                    "session_id": str(session_id),
                    "proposal_id": str(proposal.id),
                    "proposal_type": proposal.type.value,
                    "status": ProposalStatus.PENDING.value,
                },
            )
    except Exception:
        logger.exception("ws broadcast failed session_id=%s", session_id)


async def _persist_proposals(
    db: AsyncSession,
    session_id: uuid.UUID,
    world_id: uuid.UUID,
    payloads: list[ProposalPayload],
) -> list[ProposalRead]:
    persisted: list[ProposalRead] = []
    for payload in payloads:
        proposal = Proposal(
            session_id=session_id,
            world_id=world_id,
            type=payload.type,
            content=payload.content,
            status=ProposalStatus.PENDING,
        )
        db.add(proposal)
        await db.flush()
        await db.refresh(proposal)
        persisted.append(ProposalRead.model_validate(proposal))
    return persisted


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    proposals: list[ProposalRead] = []


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionRead:
    session = GameSession(
        world_id=payload.world_id,
        name=payload.name,
        rule_engine_version=payload.rule_engine_version,
        player_character_ids=payload.player_character_ids,
        current_location_id=payload.current_location_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionRead.model_validate(session)


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionRead:
    session = await _fetch_session_or_404(db, session_id)
    return SessionRead.model_validate(session)


@router.get("/{session_id}/messages", response_model=list[ChatMessageRead])
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageRead]:
    await _fetch_session_or_404(db, session_id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    return [ChatMessageRead.model_validate(m) for m in result.scalars().all()]


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def session_chat(
    session_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    game_session = await _fetch_session_or_404(db, session_id)

    dm_message = ChatMessage(
        session_id=session_id,
        role=ChatRole.DM,
        content=payload.message,
        token_count=len(payload.message) // 4,
    )
    db.add(dm_message)
    await db.flush()
    await _broadcast_dm_message(session_id, dm_message.id, payload.message)

    history = await _fetch_history(db, session_id)
    world_context = await _fetch_world_context(db, game_session.world_id, session_id)
    game_config = await _fetch_effective_config(db, game_session.world_id)

    # Condense → build messages → call backend → extract proposal.
    result = await _make_orchestrator(game_config).handle_message(
        message=payload.message,
        session_id=str(session_id),
        world_id=str(game_session.world_id),
        history=history,
        world_context=world_context,
    )

    ai_message = ChatMessage(
        session_id=session_id,
        role=ChatRole.AI,
        content=result.response,
        token_count=result.tokens_out,
    )
    db.add(ai_message)
    await db.flush()
    proposals_read = await _persist_proposals(
        db, session_id, game_session.world_id, result.proposals
    )
    await db.commit()

    await _broadcast_ai_response(session_id, str(ai_message.id), result.response, proposals_read)
    return ChatResponse(response=result.response, proposals=proposals_read)


@router.put("/{session_id}/end", response_model=SessionRead)
async def end_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionRead:
    session = await _fetch_session_or_404(db, session_id)
    session.ended_at = datetime.now(tz=timezone.utc)

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    messages = history_result.scalars().all()

    if messages:
        try:
            summary_text = "\n".join(
                f"{m.role.value.upper()}: {m.content}" for m in messages[-20:]
            )
            game_config = await _fetch_effective_config(db, session.world_id)
            session.session_summary = await _make_orchestrator(game_config).summarize(summary_text)
        except Exception:
            logger.exception("session summary failed session_id=%s", session_id)
            session.session_summary = "Session ended."

    await db.commit()
    await db.refresh(session)
    return SessionRead.model_validate(session)
