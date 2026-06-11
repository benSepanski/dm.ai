"""Per-game configuration — DM-tunable overrides scoped to one world.

Each game (a :class:`~dm_api.db.models.world.World` campaign) owns at most one
``GameConfig`` row. Every column is nullable: NULL means "inherit the
deployment default from :mod:`dm_api.config`". :func:`resolve_game_config`
merges a row (or its absence) with those defaults into a fully concrete
:class:`EffectiveGameConfig`, which is the only shape the AI layer consumes —
callers never branch on missing fields.

Covered settings:

- **AI model roles** — which provider/model drives full narrative turns
  (``orchestrator_model``) versus fast narrow sub-agents such as the
  condenser and session summaries (``generation_model``).
- **Context budget** — token limit that triggers condensation and how many
  recent messages survive verbatim.
- **Storage locations** — where this game's relational database and Redis
  instance live. These are resolved into :class:`EffectiveGameConfig` so all
  storage routing reads them from one seam; the API process currently binds
  its engine at startup, so overrides take effect for tooling and for
  deployments that point a worker at the game's stores.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.config import settings
from dm_api.db.session import Base

# Matches Settings.ai_provider — the finite set of supported AI backends.
AIProviderName = Literal["anthropic", "claude_cli"]


class GameConfig(Base):
    __tablename__ = "game_configs"

    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worlds.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # AI model roles — NULL inherits the deployment default.
    ai_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    orchestrator_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Context-budget knobs for the condenser.
    context_token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_preserve_last_n: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Storage locations for this game's data stores.
    database_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    redis_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


@dataclass(frozen=True)
class EffectiveGameConfig:
    """Fully resolved per-game configuration — no optional fields.

    Produced by :func:`resolve_game_config`; consumed by the AI layer when
    constructing backends/orchestrators so per-game overrides apply without
    the call sites knowing about fallback logic.
    """

    ai_provider: str
    orchestrator_model: str
    generation_model: str
    context_token_limit: int
    context_preserve_last_n: int
    database_url: str
    redis_url: str


def resolve_game_config(overrides: GameConfig | None) -> EffectiveGameConfig:
    """Merge a game's stored overrides with the deployment defaults.

    ``None`` (no row, or a NULL field) falls back to the corresponding
    :mod:`dm_api.config` setting, so a game with no config behaves exactly
    as before this table existed.
    """
    if overrides is None:
        return EffectiveGameConfig(
            ai_provider=settings.ai_provider,
            orchestrator_model=settings.orchestrator_model,
            generation_model=settings.generation_model,
            context_token_limit=settings.context_token_limit,
            context_preserve_last_n=settings.context_preserve_last_n,
            database_url=settings.database_url,
            redis_url=settings.redis_url,
        )
    return EffectiveGameConfig(
        ai_provider=overrides.ai_provider or settings.ai_provider,
        orchestrator_model=overrides.orchestrator_model or settings.orchestrator_model,
        generation_model=overrides.generation_model or settings.generation_model,
        context_token_limit=(
            overrides.context_token_limit
            if overrides.context_token_limit is not None
            else settings.context_token_limit
        ),
        context_preserve_last_n=(
            overrides.context_preserve_last_n
            if overrides.context_preserve_last_n is not None
            else settings.context_preserve_last_n
        ),
        database_url=overrides.database_url or settings.database_url,
        redis_url=overrides.redis_url or settings.redis_url,
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class GameConfigUpdate(BaseModel):
    """Full-replace payload for PUT /worlds/{world_id}/config.

    A null (or omitted) field clears the override and reverts that setting to
    the deployment default — PUT is idempotent and never merges.
    """

    ai_provider: AIProviderName | None = None
    orchestrator_model: str | None = Field(default=None, min_length=1, max_length=100)
    generation_model: str | None = Field(default=None, min_length=1, max_length=100)
    context_token_limit: int | None = Field(default=None, gt=0)
    context_preserve_last_n: int | None = Field(default=None, ge=0)
    database_url: str | None = Field(default=None, min_length=1)
    redis_url: str | None = Field(default=None, min_length=1)


class EffectiveGameConfigRead(BaseModel):
    """Resolved settings actually in effect for the game (overrides + defaults)."""

    model_config = ConfigDict(from_attributes=True)

    ai_provider: str
    orchestrator_model: str
    generation_model: str
    context_token_limit: int
    context_preserve_last_n: int
    database_url: str
    redis_url: str


class GameConfigRead(BaseModel):
    """API shape for a game's config: raw overrides plus the resolved values.

    ``overrides`` mirrors the stored row (nulls = inherited) so the UI can
    distinguish "DM picked this" from "deployment default"; ``effective``
    is what the engine will actually use.
    """

    world_id: uuid.UUID
    overrides: GameConfigUpdate
    effective: EffectiveGameConfigRead


def build_game_config_read(world_id: uuid.UUID, row: GameConfig | None) -> GameConfigRead:
    """Assemble the API read model from a stored row (or its absence)."""
    overrides = (
        GameConfigUpdate()
        if row is None
        else GameConfigUpdate(
            ai_provider=row.ai_provider,  # type: ignore[arg-type]  # validated on write
            orchestrator_model=row.orchestrator_model,
            generation_model=row.generation_model,
            context_token_limit=row.context_token_limit,
            context_preserve_last_n=row.context_preserve_last_n,
            database_url=row.database_url,
            redis_url=row.redis_url,
        )
    )
    return GameConfigRead(
        world_id=world_id,
        overrides=overrides,
        effective=EffectiveGameConfigRead.model_validate(resolve_game_config(row)),
    )
