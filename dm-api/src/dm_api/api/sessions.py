import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from game_engine.types import ChatRole, ProposalStatus, ProposalType
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dm_api.ai.backends.base import AIBackend
from dm_api.ai.dm_orchestrator import ChatHistoryEntry, DMOrchestrator
from dm_api.config import settings
from dm_api.db.models.chat import ChatMessage, ChatMessageRead
from dm_api.db.models.proposal import Proposal, ProposalRead
from dm_api.db.models.session import GameSession, SessionCreate, SessionRead
from dm_api.db.session import get_db

router = APIRouter()


def _get_backend() -> AIBackend:
    from dm_api.ai.backends.factory import create_backend

    return create_backend(
        provider=settings.ai_provider,
        api_key=settings.anthropic_api_key,
    )


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
    result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionRead.model_validate(session)


@router.get("/{session_id}/messages", response_model=list[ChatMessageRead])
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageRead]:
    # Verify session exists
    session_result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    if session_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    messages = result.scalars().all()
    return [ChatMessageRead.model_validate(m) for m in messages]


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def session_chat(
    session_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    # Fetch session
    session_result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    game_session = session_result.scalar_one_or_none()
    if game_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save DM message
    dm_message = ChatMessage(
        session_id=session_id,
        role=ChatRole.DM,
        content=payload.message,
        token_count=len(payload.message) // 4,
    )
    db.add(dm_message)
    await db.flush()

    # Fetch recent chat history for context
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    history = [
        ChatHistoryEntry(role=m.role, content=m.content) for m in history_result.scalars().all()
    ]

    # Call DM Orchestrator
    orchestrator = DMOrchestrator(
        backend=_get_backend(),
        orchestrator_model=settings.orchestrator_model,
        generation_model=settings.generation_model,
    )
    result = await orchestrator.handle_message(
        message=payload.message,
        session_id=str(session_id),
        world_id=str(game_session.world_id),
        history=history,
    )

    ai_response_text: str = result["response"]
    proposal_data: dict | None = result.get("proposal")

    # Save AI response
    ai_message = ChatMessage(
        session_id=session_id,
        role=ChatRole.AI,
        content=ai_response_text,
        token_count=len(ai_response_text) // 4,
    )
    db.add(ai_message)

    # Persist proposal if generated
    proposal_read: ProposalRead | None = None
    if proposal_data:
        raw_type = proposal_data.get("type", ProposalType.LOCATION.value)
        try:
            proposal_type = ProposalType(raw_type)
        except ValueError:
            proposal_type = ProposalType.LOCATION
        proposal = Proposal(
            session_id=session_id,
            world_id=game_session.world_id,
            type=proposal_type,
            content=proposal_data.get("content"),
            status=ProposalStatus.PENDING,
        )
        db.add(proposal)
        await db.flush()
        await db.refresh(proposal)
        proposal_read = ProposalRead.model_validate(proposal)

    await db.commit()

    return ChatResponse(response=ai_response_text, proposal=proposal_read)


@router.put("/{session_id}/end", response_model=SessionRead)
async def end_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionRead:
    result = await db.execute(select(GameSession).where(GameSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.ended_at = datetime.now(tz=timezone.utc)

    # Generate a brief session summary from chat history
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.timestamp.asc())
    )
    messages = history_result.scalars().all()

    if messages:
        try:
            orchestrator = DMOrchestrator(
                backend=_get_backend(),
                orchestrator_model=settings.orchestrator_model,
                generation_model=settings.generation_model,
            )
            summary_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in messages[-20:])
            session.session_summary = await orchestrator.summarize(summary_text)
        except Exception:
            # Non-fatal: summary generation failure should not block ending a session
            session.session_summary = "Session ended."

    await db.commit()
    await db.refresh(session)
    return SessionRead.model_validate(session)
