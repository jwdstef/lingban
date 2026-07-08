"""push tokens and deliveries

Revision ID: 003_push_tokens_deliveries
Revises: 002_character_color_bigint
Create Date: 2026-07-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003_push_tokens_deliveries"
down_revision: Union[str, None] = "002_character_color_bigint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("token", sa.String(1000), nullable=False),
        sa.Column("permission_status", sa.String(20), server_default="unknown"),
        sa.Column("device_id", sa.String(100), nullable=True),
        sa.Column("app_version", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "token", name="uq_push_tokens_provider_token"),
    )
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"])
    op.create_index("idx_push_tokens_user_active", "push_tokens", ["user_id", "is_active"])

    op.create_table(
        "push_deliveries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("push_token_id", UUID(as_uuid=True), sa.ForeignKey("push_tokens.id"), nullable=True),
        sa.Column(
            "proactive_message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("proactive_messages.id"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("deep_link", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("provider_message_id", sa.String(200), nullable=True),
        sa.Column("failure_reason", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_push_deliveries_user_id", "push_deliveries", ["user_id"])
    op.create_index(
        "idx_push_deliveries_user_status",
        "push_deliveries",
        ["user_id", "status", "created_at"],
    )
    op.create_index(
        "idx_push_deliveries_message",
        "push_deliveries",
        ["proactive_message_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_push_deliveries_message", table_name="push_deliveries")
    op.drop_index("idx_push_deliveries_user_status", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_user_id", table_name="push_deliveries")
    op.drop_table("push_deliveries")
    op.drop_index("idx_push_tokens_user_active", table_name="push_tokens")
    op.drop_index("ix_push_tokens_user_id", table_name="push_tokens")
    op.drop_table("push_tokens")
