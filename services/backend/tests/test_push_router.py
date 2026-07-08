import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import HTTPException

from app.routers.push import (
    PushClickRequest,
    RegisterPushTokenRequest,
    record_push_click,
    register_push_token,
)


@dataclass
class FakeUser:
    id: uuid.UUID
    push_token: str | None = None
    push_platform: str | None = None
    settings: dict = field(default_factory=dict)


@dataclass
class FakeMessage:
    id: uuid.UUID
    user_id: uuid.UUID
    push_status: str = "sent"
    delivered: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FakeDelivery:
    id: uuid.UUID
    user_id: uuid.UUID
    proactive_message_id: uuid.UUID
    status: str = "sent"
    clicked_at: datetime | None = None


class FakeResult:
    def __init__(self, item):
        self._item = item

    def scalar_one_or_none(self):
        return self._item


class FakeDb:
    def __init__(self, *items):
        self.items = list(items)
        self.added = []
        self.flushed = False

    def add(self, item):
        self.added.append(item)

    async def execute(self, statement):
        item = self.items.pop(0) if self.items else None
        return FakeResult(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()
        self.flushed = True


class PushRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_register_push_token_updates_current_user(self):
        user = FakeUser(id=uuid.uuid4(), settings={"proactive_level": "medium"})
        db = FakeDb()

        response = await register_push_token(
            RegisterPushTokenRequest(
                platform="jpush",
                token="push-token-123",
                permission_status="granted",
                device_id="device-a",
                app_version="1.0.0",
            ),
            user=user,
            db=db,
        )

        self.assertTrue(db.flushed)
        self.assertEqual(user.push_token, "push-token-123")
        self.assertEqual(user.push_platform, "jpush")
        self.assertTrue(user.settings["push_enabled"])
        self.assertEqual(user.settings["push_permission_status"], "granted")
        self.assertEqual(user.settings["push_device_id"], "device-a")
        self.assertEqual(len(db.added), 1)
        self.assertTrue(db.added[0].is_active)
        self.assertNotEqual(response.token_id, "None")
        self.assertEqual(response.provider, "jpush")
        self.assertTrue(response.push_enabled)

    async def test_register_push_token_disables_push_when_permission_denied(self):
        user = FakeUser(id=uuid.uuid4(), settings={"push_enabled": True})
        db = FakeDb()

        response = await register_push_token(
            RegisterPushTokenRequest(
                platform="apns",
                token="push-token-456",
                permission_status="denied",
            ),
            user=user,
            db=db,
        )

        self.assertFalse(user.settings["push_enabled"])
        self.assertEqual(len(db.added), 1)
        self.assertFalse(db.added[0].is_active)
        self.assertEqual(user.settings["push_permission_status"], "denied")
        self.assertFalse(response.push_enabled)

    async def test_record_push_click_marks_related_message_clicked_by_proactive_id(self):
        user_id = uuid.uuid4()
        message = FakeMessage(id=uuid.uuid4(), user_id=user_id)
        db = FakeDb(message)

        response = await record_push_click(
            PushClickRequest(
                proactive_message_id=str(message.id),
                deep_link="lingban://chat/yinyue",
            ),
            user=FakeUser(id=user_id),
            db=db,
        )

        self.assertTrue(db.flushed)
        self.assertEqual(message.push_status, "clicked")
        self.assertTrue(message.delivered)
        self.assertEqual(response.proactive_message_id, str(message.id))
        self.assertEqual(response.push_status, "clicked")

    async def test_record_push_click_marks_delivery_clicked(self):
        user_id = uuid.uuid4()
        message = FakeMessage(id=uuid.uuid4(), user_id=user_id)
        delivery = FakeDelivery(
            id=uuid.uuid4(),
            user_id=user_id,
            proactive_message_id=message.id,
        )
        db = FakeDb(delivery, message)

        response = await record_push_click(
            PushClickRequest(delivery_id=str(delivery.id)),
            user=FakeUser(id=user_id),
            db=db,
        )

        self.assertEqual(delivery.status, "clicked")
        self.assertIsNotNone(delivery.clicked_at)
        self.assertEqual(response.delivery_id, str(delivery.id))
        self.assertEqual(response.proactive_message_id, str(message.id))

    async def test_record_push_click_requires_message_id(self):
        with self.assertRaises(HTTPException) as ctx:
            await record_push_click(
                PushClickRequest(),
                user=FakeUser(id=uuid.uuid4()),
                db=FakeDb(),
            )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_record_push_click_returns_404_when_message_missing(self):
        with self.assertRaises(HTTPException) as ctx:
            await record_push_click(
                PushClickRequest(delivery_id=str(uuid.uuid4())),
                user=FakeUser(id=uuid.uuid4()),
                db=FakeDb(None),
            )

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
