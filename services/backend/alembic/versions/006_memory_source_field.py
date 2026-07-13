"""add memory source field for layered trust

Revision ID: 006
Revises: 005
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005_payment_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memories",
        sa.Column("source", sa.String(30), server_default="human_original", nullable=False),
    )
    op.create_index("ix_memories_source", "memories", ["source"])


def downgrade() -> None:
    op.drop_index("ix_memories_source", table_name="memories")
    op.drop_column("memories", "source")
