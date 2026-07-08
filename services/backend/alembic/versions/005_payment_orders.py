"""payment orders

Revision ID: 005_payment_orders
Revises: 004_safety_events_audit_logs
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "005_payment_orders"
down_revision: Union[str, None] = "004_safety_events_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_orders",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False, server_default="wechat"),
        sa.Column("out_trade_no", sa.String(64), nullable=False),
        sa.Column("prepay_id", sa.String(128), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="CNY"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("transaction_id", sa.String(128), nullable=True),
        sa.Column("raw_request", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_response", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_notify", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("out_trade_no", name="uq_payment_orders_out_trade_no"),
    )
    op.create_index("ix_payment_orders_user_id", "payment_orders", ["user_id"])
    op.create_index(
        "idx_payment_orders_user_status",
        "payment_orders",
        ["user_id", "status", "created_at"],
    )
    op.create_index(
        "idx_payment_orders_out_trade_no",
        "payment_orders",
        ["out_trade_no"],
    )


def downgrade() -> None:
    op.drop_index("idx_payment_orders_out_trade_no", table_name="payment_orders")
    op.drop_index("idx_payment_orders_user_status", table_name="payment_orders")
    op.drop_index("ix_payment_orders_user_id", table_name="payment_orders")
    op.drop_table("payment_orders")
