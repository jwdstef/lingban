"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("phone", sa.String(20), unique=True, nullable=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("nickname", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.String(500), server_default=""),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("selected_character_id", sa.String(50), nullable=True),
        sa.Column("push_token", sa.String(500), nullable=True),
        sa.Column("push_platform", sa.String(20), nullable=True),
        sa.Column("emotion_profile", JSONB, server_default="{}"),
        sa.Column("settings", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── characters ──
    op.create_table(
        "characters",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("avatar_url", sa.String(500), server_default=""),
        sa.Column("color", sa.BigInteger, server_default="0"),
        sa.Column("personality", JSONB, nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── user_character_relations ──
    op.create_table(
        "user_character_relations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("character_id", sa.String(50), sa.ForeignKey("characters.id"), nullable=False),
        sa.Column("level", sa.Integer, server_default="1"),
        sa.Column("label", sa.String(50), server_default="陌生"),
        sa.Column("intimacy", sa.Integer, server_default="0"),
        sa.Column("milestones", JSONB, server_default="[]"),
        sa.Column("first_chat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_chat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_days", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ucr_user_id", "user_character_relations", ["user_id"])
    op.create_index("ix_ucr_character_id", "user_character_relations", ["character_id"])
    op.create_unique_constraint("uq_user_character", "user_character_relations", ["user_id", "character_id"])

    # ── chat_messages ──
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.String(50), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("message_type", sa.String(20), server_default="text"),
        sa.Column("emotion_tags", JSONB, server_default="[]"),
        sa.Column("is_proactive", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])
    op.create_index("ix_chat_messages_character_id", "chat_messages", ["character_id"])
    op.create_index("idx_chat_history", "chat_messages", ["user_id", "character_id", "created_at"])

    # ── memories (with pgvector embedding) ──
    op.create_table(
        "memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("importance", sa.Integer, server_default="5"),
        sa.Column("emotion_tags", JSONB, server_default="[]"),
        sa.Column("source_message_id", UUID(as_uuid=True), nullable=True),
        sa.Column("embedding", sa.Text, nullable=True),  # managed as vector(4096) via raw SQL
        sa.Column("recall_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_memories_user_id", "memories", ["user_id"])
    op.create_index("ix_memories_character_id", "memories", ["character_id"])
    op.create_index("idx_memories_active", "memories", ["user_id", "character_id", "is_active", "created_at"])

    # Replace the text embedding column with actual pgvector type
    op.execute("ALTER TABLE memories ALTER COLUMN embedding TYPE vector(4096) USING embedding::vector(4096)")

    # ── proactive_messages ──
    op.create_table(
        "proactive_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.String(50), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("delivered", sa.Boolean, server_default="false"),
        sa.Column("replied", sa.Boolean, server_default="false"),
        sa.Column("push_status", sa.String(20), server_default="pending"),
        sa.Column("push_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_proactive_user_id", "proactive_messages", ["user_id"])

    # ── emotion_diary ──
    op.create_table(
        "emotion_diary",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.DateTime, nullable=False),
        sa.Column("dominant_emotion", sa.String(50), nullable=True),
        sa.Column("intensity", sa.Float, nullable=True),
        sa.Column("triggers", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_emotion_diary_user_id", "emotion_diary", ["user_id"])


def downgrade() -> None:
    op.drop_table("emotion_diary")
    op.drop_table("proactive_messages")
    op.drop_table("memories")
    op.drop_table("chat_messages")
    op.drop_table("user_character_relations")
    op.drop_table("characters")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
