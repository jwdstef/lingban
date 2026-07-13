"""add memory_sources to chat_messages for history provenance

Revision ID: 008
Revises: 007
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("memory_sources", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "memory_sources")
