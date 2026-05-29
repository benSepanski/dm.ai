from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from game_engine.types import Ability, ActionType, DamageType
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from dm_api.db.session import Base


class CombatState(Base):
    __tablename__ = "combat_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    initiative_order: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    combatants: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    combat_log: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CombatStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    location_id: uuid.UUID | None
    round_number: int
    current_turn_index: int
    initiative_order: list[Any] | None
    combatants: list[Any] | None
    combat_log: list[Any] | None
    started_at: datetime
    ended_at: datetime | None


class StartCombatRequest(BaseModel):
    """Request body for starting a new combat encounter.

    character_ids: Characters to enroll; initiative is rolled immediately.
    location_id: Optional location where combat takes place.
    """

    character_ids: list[uuid.UUID] = []
    location_id: uuid.UUID | None = None


class AttackDetailsRequest(BaseModel):
    """Typed weapon/attack configuration for an Attack action.

    Replaces the previous untyped ``extra: dict[str, Any]`` field so that
    no ``dict[str, Any]`` crosses the API boundary (harness-engineering typed
    boundaries principle).
    """

    weapon_name: str = "Unarmed Strike"
    damage_dice: str = "1d4"
    damage_type: DamageType = DamageType.BLUDGEONING
    attack_ability: Ability = Ability.STRENGTH
    is_ranged: bool = False


class CombatActionRequest(BaseModel):
    """Typed request body for submitting a combat action.

    action_type must be a valid :class:`~game_engine.types.ActionType` value
    (e.g. ``"Attack"``, ``"Dash"``). Validated at the API boundary so invalid
    types are rejected with 422 before reaching the rule engine.
    """

    actor_id: str
    action_type: ActionType
    target_id: str | None = None
    attack_details: AttackDetailsRequest | None = None
