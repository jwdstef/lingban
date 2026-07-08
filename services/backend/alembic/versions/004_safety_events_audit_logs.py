"""safety events and audit logs

Revision ID: 004_safety_events_audit_logs
Revises: 003_push_tokens_deliveries
Create Date: 2026-07-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "004_safety_events_audit_logs"
down_revision: Union[str, None] = "003_push_tokens_deliveries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "safety_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("character_id", sa.String(50), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="chat_message"),
        sa.Column(
            "source_message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="high"),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending_review",
        ),
        sa.Column("content_excerpt", sa.Text, nullable=False),
        sa.Column("matched_terms", JSONB, nullable=False, server_default="[]"),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_message_id", name="uq_safety_events_source_message"),
    )
    op.create_index("ix_safety_events_user_id", "safety_events", ["user_id"])
    op.create_index(
        "idx_safety_events_status_created",
        "safety_events",
        ["status", "created_at"],
    )
    op.create_index(
        "idx_safety_events_user_status",
        "safety_events",
        ["user_id", "status"],
    )

    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("actor_type", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.String(100), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_audit_logs_target",
        "audit_logs",
        ["target_type", "target_id", "created_at"],
    )
    op.create_index(
        "idx_audit_logs_actor",
        "audit_logs",
        ["actor_type", "actor_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_audit_logs_actor", table_name="audit_logs")
    op.drop_index("idx_audit_logs_target", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("idx_safety_events_user_status", table_name="safety_events")
    op.drop_index("idx_safety_events_status_created", table_name="safety_events")
    op.drop_index("ix_safety_events_user_id", table_name="safety_events")
    op.drop_table("safety_events")
