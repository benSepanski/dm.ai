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
from dm_api.api.ws import broadcast_to_session
from dm_api.config import settings
from dm_api.db.models.chat import ChatMessage, ChatMessageRead
from dm_api.db.models.proposal import Proposal, ProposalRead
from dm_api.db.models.session import GameSession, SessionCreate, SessionRead
from dm_api.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@functools.lru_cache(maxsize=1)
def _get_backend() -> AIBackend:
    """Return the process-wide singleton AI backend.

    Cached so the AnthropicBackend (and its underlying HTTP connection pool)
    is created once per process rather than once per request.
    """
    from dm_api.ai.backends.factory import create_backend

    return create_backend(
        provider=settings.ai_provider,
        api_key=settings.anthropic_api_key,
    )


def _make_orchestrator() -> DMOrchestrator:
    """Return a fresh DMOrchestrator using the cached backend singleton.

    DMOrchestrator is stateless and cheap to construct; only the backend
    (which holds the HTTP connection pool) is cached.
    """
    return DMOrchestrator(
        backend=_get_backend(),
        orchestrator_model=settings.orchestrator_model,
        generation_model=settings.generation_model,
        context_token_limit=settings.context_token_limit,
        context_preserve_last_n=settings.context_preserve_last_n,
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


async def _persist_proposal(
    db: AsyncSession,
    session_id: uuid.UUID,
    world_id: uuid.UUID,
    proposal_data: ProposalPayload | None,
) -> ProposalRead | None:
    if proposal_data is None:
        return None
    proposal = Proposal(
        session_id=session_id,
        world_id=world_id,
        type=proposal_data.type,
        content=proposal_data.content,
        status=ProposalStatus.PENDING,
    )
    db.add(proposal)
    await db.flush()
    await db.refresh(proposal)
    return ProposalRead.model_validate(proposal)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    proposal: ProposalRead | None = None


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

    db.add(
        ChatMessage(
            session_id=session_id,
            role=ChatRole.DM,
            content=payload.message,
            token_count=len(payload.message) // 4,
        )
    )
    await db.flush()

    history = await _fetch_history(db, session_id)

    logger.info(
        "session_chat start  session_id=%s world_id=%s message_len=%d history_len=%d",
        session_id,
        game_session.world_id,
        len(payload.message),
        len(history),
    )

    # Condense → build messages → call backend → extract proposal.
    result = await _make_orchestrator().handle_message(
        message=payload.message,
        session_id=str(session_id),
        world_id=str(game_session.world_id),
        history=history,
    )

    db.add(
        ChatMessage(
            session_id=session_id,
            role=ChatRole.AI,
            content=result.response,
            token_count=result.tokens_out,
        )
    )
    proposal_read = await _persist_proposal(db, session_id, game_session.world_id, result.proposal)
    await db.commit()

    # Notify all connected WebSocket clients about the new AI message and any proposal.
    try:
        await broadcast_to_session(
            session_id,
            {
                "type": "chat_message",
                "session_id": str(session_id),
                "role": "ai",
                "content": result.response,
            },
        )
        if proposal_read is not None:
            await broadcast_to_session(
                session_id,
                {
                    "type": "proposal_ready",
                    "session_id": str(session_id),
                    "proposal_id": str(proposal_read.id),
                    "proposal_type": proposal_read.type.value,
                    "status": ProposalStatus.PENDING.value,
                },
            )
    except Exception:
        logger.exception("ws broadcast failed session_id=%s", session_id)

    return ChatResponse(response=result.response, proposal=proposal_read)


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
            session.session_summary = await _make_orchestrator().summarize(summary_text)
        except Exception:
            logger.exception("session summary failed session_id=%s", session_id)
            session.session_summary = "Session ended."

    await db.commit()
    await db.refresh(session)
    return SessionRead.model_validate(session)
