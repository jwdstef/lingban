import json
import secrets
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.user_settings import merge_user_settings
from app.models.payment import PaymentOrder
from app.models.user import User
from app.services.payment_service import (
    PaymentNotificationError,
    PaymentProviderError,
    payment_service,
)
from app.services.subscription_service import (
    PLAN_BY_ID,
    activate_paid_subscription,
    get_plan_amount_cents,
    get_subscription_overview,
)

router = APIRouter()


class CreateSubscriptionRequest(BaseModel):
    plan: Literal["basic", "pro"]
    provider: Literal["wechat"] = "wechat"


def generate_out_trade_no(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"LB{now:%Y%m%d%H%M%S}{secrets.token_hex(8)}"[:32]


@router.get("")
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_subscription_overview(user=user, db=db)


@router.post("/create")
async def create_subscription(
    data: CreateSubscriptionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payment_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "payment_provider_not_configured",
                "message": "Payment provider is not configured",
            },
        )

    plan_data = PLAN_BY_ID[data.plan]
    amount_cents = get_plan_amount_cents(data.plan)
    out_trade_no = generate_out_trade_no()
    order = PaymentOrder(
        user_id=user.id,
        plan=data.plan,
        provider=data.provider,
        out_trade_no=out_trade_no,
        amount_cents=amount_cents,
        currency="CNY",
        status="pending",
    )
    db.add(order)
    await db.flush()

    try:
        prepay = await payment_service.create_app_prepay_order(
            description=f"灵伴{plan_data['name']}月度订阅",
            out_trade_no=out_trade_no,
            amount_cents=amount_cents,
            currency="CNY",
            attach=json.dumps(
                {"user_id": str(user.id), "plan": data.plan},
                separators=(",", ":"),
            ),
        )
    except PaymentProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "payment_provider_error",
                "message": str(exc),
            },
        ) from exc

    order.prepay_id = prepay["prepay_id"]
    order.raw_request = prepay["raw_request"]
    order.raw_response = prepay["raw_response"]
    await db.flush()

    return {
        "order_id": str(order.id),
        "provider": data.provider,
        "plan": data.plan,
        "amount_cents": amount_cents,
        "currency": "CNY",
        "out_trade_no": out_trade_no,
        "prepay_id": order.prepay_id,
        "payment_params": prepay["payment_params"],
    }


@router.post("/wechat/notify")
async def wechat_payment_notify(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    try:
        notification = payment_service.parse_payment_notification(body, request.headers)
    except PaymentNotificationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_payment_notification",
                "message": str(exc),
            },
        ) from exc

    out_trade_no = str(notification.get("out_trade_no") or "")
    if not out_trade_no:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_out_trade_no",
                "message": "WeChat Pay notification did not include out_trade_no",
            },
        )

    result = await db.execute(
        select(PaymentOrder).where(PaymentOrder.out_trade_no == out_trade_no)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "payment_order_not_found",
                "message": "Payment order was not found",
            },
        )

    trade_state = str(notification.get("trade_state") or "")
    order.raw_notify = notification
    order.transaction_id = (
        str(notification.get("transaction_id") or "") or order.transaction_id
    )
    if trade_state == "SUCCESS":
        now = datetime.now(timezone.utc)
        order.status = "paid"
        order.paid_at = order.paid_at or now
        user = await db.get(User, order.user_id)
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "payment_user_not_found",
                    "message": "Payment order user was not found",
                },
            )
        activate_paid_subscription(
            user=user,
            plan=order.plan,  # type: ignore[arg-type]
            provider=order.provider,
            now=now,
        )
    elif trade_state in {"CLOSED", "REVOKED", "PAYERROR"}:
        order.status = "failed"

    await db.flush()
    return {"code": "SUCCESS", "message": "成功"}


@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_plan = (user.settings or {}).get("subscription_plan", "free")
    if current_plan == "free":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "subscription_not_active",
                "message": "Current user has no paid subscription to cancel",
            },
        )

    user.settings = merge_user_settings(
        user.settings,
        {
            "subscription_cancel_at_period_end": True,
            "subscription_canceled_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await db.flush()
    return await get_subscription_overview(user=user, db=db)
