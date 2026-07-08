import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentOrder(Base):
    """Local payment order tracked before and after provider callbacks."""

    __tablename__ = "payment_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), default="wechat")
    out_trade_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    prepay_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_request: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_response: Mapped[dict] = mapped_column(JSONB, default=dict)
    raw_notify: Mapped[dict] = mapped_column(JSONB, default=dict)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_payment_orders_user_status", "user_id", "status", "created_at"),
        Index("idx_payment_orders_out_trade_no", "out_trade_no"),
    )
