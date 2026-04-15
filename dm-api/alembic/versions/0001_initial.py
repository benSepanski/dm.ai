"""Initial schema — worlds, locations, characters, sessions, chat_messages, proposals, combat_states.

Revision ID: 0001
Revises:
Create Date: 2026-02-21 00:00:00
"""
from __future__ import annotations
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_enums() -> None:
    op.execute("CREATE TYPE character_type AS ENUM ('PC', 'NPC', 'MONSTER')")
    op.execute("""CREATE TYPE location_type AS ENUM (
        'realm', 'country', 'region', 'town', 'district',
        'building', 'room', 'dungeon', 'wilderness'
    )""")
    op.execute("CREATE TYPE chat_role AS ENUM ('dm', 'ai', 'system')")
    op.execute("CREATE TYPE proposal_type AS ENUM ('location', 'character', 'dungeon', 'dialogue', 'combat_action')")
    op.execute("CREATE TYPE proposal_status AS ENUM ('pending', 'accepted', 'rejected', 'modified')")


def _create_worlds() -> None:
    op.create_table(
        "worlds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("setting_description", sa.Text, nullable=True),
        sa.Column("themes", postgresql.JSON, nullable=True),
        sa.Column("lore_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("ALTER TABLE worlds ADD COLUMN embedding vector(1536)")


def _create_locations() -> None:
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.Enum("realm", "country", "region", "town", "district", "building", "room", "dungeon", "wilderness", name="location_type", create_type=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("lore", sa.Text, nullable=True),
        sa.Column("history", sa.Text, nullable=True),
        sa.Column("map_data", postgresql.JSON, nullable=True),
        sa.Column("character_associations", postgresql.JSON, nullable=True),
        sa.Column("interaction_log_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_visited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("ALTER TABLE locations ADD COLUMN embedding vector(1536)")


def _create_characters() -> None:
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Enum("PC", "NPC", "MONSTER", name="character_type", create_type=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("race", sa.String(100), nullable=True),
        sa.Column("char_class", sa.String(100), nullable=True),
        sa.Column("level", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("alignment", sa.String(50), nullable=True),
        sa.Column("stats", postgresql.JSON, nullable=True),
        sa.Column("hp_current", sa.Integer, nullable=True),
        sa.Column("hp_max", sa.Integer, nullable=True),
        sa.Column("ac", sa.Integer, nullable=True),
        sa.Column("speed", sa.Integer, nullable=True),
        sa.Column("abilities", postgresql.JSON, nullable=True),
        sa.Column("spells", postgresql.JSON, nullable=True),
        sa.Column("equipment", postgresql.JSON, nullable=True),
        sa.Column("personality_traits", sa.Text, nullable=True),
        sa.Column("ideals", sa.Text, nullable=True),
        sa.Column("bonds", sa.Text, nullable=True),
        sa.Column("flaws", sa.Text, nullable=True),
        sa.Column("known_facts", postgresql.JSON, nullable=True),
        sa.Column("current_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("interaction_log_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("ALTER TABLE characters ADD COLUMN embedding vector(1536)")


def _create_sessions() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rule_engine_version", sa.String(50), nullable=False, server_default=sa.text("'dnd_5_5e'")),
        sa.Column("player_character_ids", postgresql.JSON, nullable=True),
        sa.Column("current_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_summary", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )


def _create_chat_messages() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Enum("dm", "ai", "system", name="chat_role", create_type=False), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("entity_refs", postgresql.JSON, nullable=True),
        sa.Column("importance_score", sa.Float, nullable=False, server_default=sa.text("0.5")),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def _create_proposals() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Enum("location", "character", "dungeon", "dialogue", "combat_action", name="proposal_type", create_type=False), nullable=False),
        sa.Column("content", postgresql.JSON, nullable=True),
        sa.Column("status", sa.Enum("pending", "accepted", "rejected", "modified", name="proposal_status", create_type=False), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("dm_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def _create_combat_states() -> None:
    op.create_table(
        "combat_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("round_number", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("current_turn_index", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("initiative_order", postgresql.JSON, nullable=True),
        sa.Column("combatants", postgresql.JSON, nullable=True),
        sa.Column("combat_log", postgresql.JSON, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("session_id", name="uq_combat_session"),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    _create_enums()
    _create_worlds()
    _create_locations()
    _create_characters()
    _create_sessions()
    _create_chat_messages()
    _create_proposals()
    _create_combat_states()


def downgrade() -> None:
    op.drop_table("combat_states")
    op.drop_table("proposals")
    op.drop_table("chat_messages")
    op.drop_table("sessions")
    op.drop_table("characters")
    op.drop_table("locations")
    op.drop_table("worlds")
    op.execute("DROP TYPE IF EXISTS proposal_status")
    op.execute("DROP TYPE IF EXISTS proposal_type")
    op.execute("DROP TYPE IF EXISTS chat_role")
    op.execute("DROP TYPE IF EXISTS location_type")
    op.execute("DROP TYPE IF EXISTS character_type")
