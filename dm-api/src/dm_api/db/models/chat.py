import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from game_engine.types import ChatRole
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ChatRole] = mapped_column(
        sa.Enum(ChatRole, name="chat_role", create_type=False),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entity_refs: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChatMessageCreate(BaseModel):
    session_id: uuid.UUID
    role: ChatRole
    content: str
    token_count: int = 0
    entity_refs: list[Any] | None = None
    importance_score: float = 0.5


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: ChatRole
    content: str
    token_count: int
    entity_refs: list[Any] | None
    importance_score: float
    timestamp: datetime
