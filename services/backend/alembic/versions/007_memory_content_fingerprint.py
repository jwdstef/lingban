"""add memory content fingerprint for writeback dedupe

Revision ID: 007
Revises: 006
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memories",
        sa.Column("content_fingerprint", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_memories_content_fingerprint",
        "memories",
        ["content_fingerprint"],
    )
    op.create_index(
        "ix_memories_user_character_fingerprint",
        "memories",
        ["user_id", "character_id", "content_fingerprint"],
    )


def downgrade() -> None:
    op.drop_index("ix_memories_user_character_fingerprint", table_name="memories")
    op.drop_index("ix_memories_content_fingerprint", table_name="memories")
    op.drop_column("memories", "content_fingerprint")
