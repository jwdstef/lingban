import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.services.subscription_service import (
    SubscriptionLimitError,
    get_effective_subscription,
    get_subscription_overview,
    subscription_service,
)


@dataclass
class FakeUser:
    id: uuid.UUID
    settings: dict = field(default_factory=dict)


class FakeResult:
    def __init__(self, scalar_value=0):
        self._scalar_value = scalar_value

    def scalar(self):
        return self._scalar_value


class FakeDb:
    def __init__(self, *scalar_values):
        self._scalar_values = list(scalar_values)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        value = self._scalar_values.pop(0) if self._scalar_values else 0
        return FakeResult(value)


class SubscriptionServiceTest(unittest.IsolatedAsyncioTestCase):
    def test_expired_paid_plan_falls_back_to_free_quota(self):
        user = FakeUser(
            id=uuid.uuid4(),
            settings={
                "subscription_plan": "basic",
                "subscription_expires_at": "2026-07-01T00:00:00+00:00",
            },
        )

        subscription = get_effective_subscription(
            user,
            now=datetime(2026, 7, 7, tzinfo=timezone.utc),
        )

        self.assertEqual(subscription.plan, "free")
        self.assertEqual(subscription.status, "expired")
        self.assertEqual(subscription.previous_plan, "basic")
        self.assertEqual(subscription.chat_daily_limit, 20)

    async def test_overview_reports_daily_chat_quota(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(3)

        overview = await get_subscription_overview(
            user=user,
            db=db,
            now=datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(overview["plan"], "free")
        self.assertEqual(overview["status"], "active")
        self.assertEqual(overview["quota"]["chat_daily"]["limit"], 20)
        self.assertEqual(overview["quota"]["chat_daily"]["used"], 3)
        self.assertEqual(overview["quota"]["chat_daily"]["remaining"], 17)
        self.assertEqual(
            overview["quota"]["chat_daily"]["reset_at"],
            "2026-07-08T00:00:00+00:00",
        )

    async def test_free_chat_quota_blocks_when_exhausted(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(20)

        with self.assertRaises(SubscriptionLimitError) as ctx:
            await subscription_service.ensure_chat_quota(
                user=user,
                db=db,
                now=datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(ctx.exception.quota["remaining"], 0)

    async def test_paid_plan_uses_paid_quota(self):
        user = FakeUser(
            id=uuid.uuid4(),
            settings={
                "subscription_plan": "basic",
                "subscription_expires_at": (
                    datetime(2026, 8, 7, tzinfo=timezone.utc).isoformat()
                ),
            },
        )
        db = FakeDb(30)

        quota = await subscription_service.ensure_chat_quota(
            user=user,
            db=db,
            now=datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(quota["limit"], 200)
        self.assertEqual(quota["used"], 30)
        self.assertEqual(quota["remaining"], 170)


if __name__ == "__main__":
    unittest.main()
