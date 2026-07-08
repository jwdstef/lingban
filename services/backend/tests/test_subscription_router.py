import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.models.payment import PaymentOrder
from app.routers.subscription import (
    CreateSubscriptionRequest,
    cancel_subscription,
    create_subscription,
    get_subscription,
    wechat_payment_notify,
)


@dataclass
class FakeUser:
    id: uuid.UUID
    settings: dict = field(default_factory=dict)


class FakeResult:
    def __init__(self, scalar_value=0, scalar_one_value=None):
        self._scalar_value = scalar_value
        self._scalar_one_value = scalar_one_value

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_one_value


class FakeDb:
    def __init__(self, *scalar_values, scalar_one_values=None, users=None):
        self._scalar_values = list(scalar_values)
        self._scalar_one_values = list(scalar_one_values or [])
        self.users = users or {}
        self.added = []
        self.flushed = False

    def add(self, item):
        self.added.append(item)

    async def execute(self, statement):
        value = self._scalar_values.pop(0) if self._scalar_values else 0
        scalar_one_value = (
            self._scalar_one_values.pop(0) if self._scalar_one_values else None
        )
        return FakeResult(value, scalar_one_value)

    async def get(self, model, item_id):
        return self.users.get(item_id)

    async def flush(self):
        self.flushed = True
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc)


class FakeRequest:
    headers = {
        "Wechatpay-Timestamp": "1780000000",
        "Wechatpay-Nonce": "notify-nonce",
        "Wechatpay-Signature": "signature",
    }

    async def body(self):
        return b'{"resource":{"ciphertext":"encrypted"}}'


class SubscriptionRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_subscription_returns_current_plan_and_quota(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(2)

        response = await get_subscription(user=user, db=db)

        self.assertEqual(response["plan"], "free")
        self.assertEqual(response["quota"]["chat_daily"]["used"], 2)
        self.assertEqual(response["quota"]["chat_daily"]["remaining"], 18)
        self.assertTrue(any(plan["id"] == "basic" for plan in response["plans"]))

    async def test_create_subscription_requires_configured_payment_provider(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with patch(
            "app.routers.subscription.payment_service.is_configured",
            return_value=False,
        ):
            with self.assertRaises(HTTPException) as ctx:
                await create_subscription(
                    data=CreateSubscriptionRequest(plan="basic"),
                    user=user,
                    db=db,
                )

        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("payment", str(ctx.exception.detail).lower())
        self.assertFalse(db.flushed)

    async def test_create_subscription_creates_wechat_order(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with patch(
            "app.routers.subscription.payment_service.is_configured",
            return_value=True,
        ), patch(
            "app.routers.subscription.payment_service.create_app_prepay_order",
            new_callable=AsyncMock,
            return_value={
                "prepay_id": "wx-prepay-id",
                "payment_params": {"prepayid": "wx-prepay-id"},
                "raw_request": {"out_trade_no": "LB202607080001"},
                "raw_response": {"prepay_id": "wx-prepay-id"},
            },
        ) as create_order, patch(
            "app.routers.subscription.generate_out_trade_no",
            return_value="LB202607080001",
        ):
            response = await create_subscription(
                data=CreateSubscriptionRequest(plan="basic"),
                user=user,
                db=db,
            )

        self.assertTrue(db.flushed)
        self.assertEqual(len(db.added), 1)
        order = db.added[0]
        self.assertIsInstance(order, PaymentOrder)
        self.assertEqual(order.user_id, user.id)
        self.assertEqual(order.plan, "basic")
        self.assertEqual(order.amount_cents, 2900)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.prepay_id, "wx-prepay-id")
        create_order.assert_called_once()
        self.assertEqual(response["out_trade_no"], "LB202607080001")
        self.assertEqual(response["payment_params"]["prepayid"], "wx-prepay-id")

    async def test_wechat_notify_marks_order_paid_and_activates_subscription(self):
        user = FakeUser(id=uuid.uuid4(), settings={})
        order = PaymentOrder(
            id=uuid.uuid4(),
            user_id=user.id,
            plan="basic",
            provider="wechat",
            out_trade_no="LB202607080001",
            amount_cents=2900,
            currency="CNY",
            status="pending",
        )
        db = FakeDb(scalar_one_values=[order], users={user.id: user})

        with patch(
            "app.routers.subscription.payment_service.parse_payment_notification",
            return_value={
                "out_trade_no": "LB202607080001",
                "trade_state": "SUCCESS",
                "transaction_id": "4200000000000000001",
            },
        ):
            response = await wechat_payment_notify(request=FakeRequest(), db=db)

        self.assertEqual(response["code"], "SUCCESS")
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.transaction_id, "4200000000000000001")
        self.assertEqual(user.settings["subscription_plan"], "basic")
        self.assertEqual(user.settings["subscription_provider"], "wechat")
        self.assertFalse(user.settings["subscription_cancel_at_period_end"])
        self.assertIn("subscription_expires_at", user.settings)
        self.assertTrue(db.flushed)

    async def test_cancel_subscription_marks_paid_plan_cancel_at_period_end(self):
        user = FakeUser(
            id=uuid.uuid4(),
            settings={
                "subscription_plan": "basic",
                "subscription_expires_at": "2026-08-07T00:00:00+00:00",
            },
        )
        db = FakeDb(4)

        response = await cancel_subscription(user=user, db=db)

        self.assertTrue(db.flushed)
        self.assertTrue(user.settings["subscription_cancel_at_period_end"])
        self.assertIn("subscription_canceled_at", user.settings)
        self.assertEqual(response["plan"], "basic")
        self.assertEqual(response["status"], "cancel_at_period_end")


if __name__ == "__main__":
    unittest.main()
