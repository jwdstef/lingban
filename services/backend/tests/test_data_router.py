import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import HTTPException

from app.routers.data import (
    DeleteAccountRequest,
    delete_account,
    export_user_data,
)


@dataclass
class FakeUser:
    id: uuid.UUID
    phone: str | None = None
    email: str | None = "user@example.test"
    nickname: str = "User"
    avatar_url: str = ""
    password_hash: str = "secret-hash"
    selected_character_id: str | None = "yinyue"
    push_token: str | None = "raw-push-token"
    push_platform: str | None = "jpush"
    emotion_profile: dict = field(default_factory=lambda: {"dominant": "calm"})
    settings: dict = field(default_factory=lambda: {"memory_enabled": True})
    created_at: datetime = field(default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc))


@dataclass
class FakeRow:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    character_id: str = "yinyue"
    role: str = "user"
    content: str = "hello"
    message_type: str = "text"
    is_proactive: bool = False
    category: str = "daily"
    importance: int = 5
    emotion_tags: list[str] = field(default_factory=list)
    source_message_id: uuid.UUID | None = None
    recall_count: int = 0
    is_active: bool = True
    trigger_type: str = "time_morning"
    delivered: bool = True
    replied: bool = False
    push_status: str = "sent"
    push_error: str | None = None
    provider: str = "jpush"
    platform: str = "jpush"
    permission_status: str = "granted"
    device_id: str | None = "device-a"
    app_version: str | None = "1.0.0"
    status: str = "sent"
    plan: str = "basic"
    out_trade_no: str = "LB202607080001"
    prepay_id: str | None = "wx-prepay-id"
    amount_cents: int = 2900
    currency: str = "CNY"
    transaction_id: str | None = "4200000000000000001"
    paid_at: datetime | None = field(default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc))
    notification_type: str = "proactive"
    push_token_id: uuid.UUID | None = None
    proactive_message_id: uuid.UUID | None = None
    title: str = "银月"
    body: str = "hello"
    deep_link: str | None = "lingban://chat/yinyue"
    failure_reason: str | None = None
    sent_at: datetime | None = field(default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc))
    clicked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc))
    date: datetime = field(default_factory=lambda: datetime(2026, 7, 7))
    dominant_emotion: str | None = "calm"
    intensity: float | None = 0.5
    triggers: list[str] = field(default_factory=list)
    level: int = 1
    label: str = "陌生"
    intimacy: int = 0
    milestones: list[str] = field(default_factory=list)
    first_chat_at: datetime | None = None
    last_chat_at: datetime | None = None
    consecutive_days: int = 0


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, items=None):
        self._items = items or []

    def scalars(self):
        return FakeScalars(self._items)


class FakeDb:
    def __init__(self, *result_items):
        self._result_items = list(result_items)
        self.flushed = False
        self.executed = []

    async def execute(self, statement):
        self.executed.append(statement)
        items = self._result_items.pop(0) if self._result_items else []
        return FakeResult(items)

    async def flush(self):
        self.flushed = True


class DataRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_export_user_data_excludes_sensitive_secrets(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(
            [FakeRow()],
            [FakeRow(content="I feel calm")],
            [FakeRow(content="User likes tea")],
            [FakeRow()],
            [FakeRow()],
            [FakeRow()],
            [FakeRow()],
            [FakeRow(status="paid")],
        )

        export = await export_user_data(user=user, db=db)

        self.assertEqual(export["user"]["email"], "user@example.test")
        self.assertNotIn("password_hash", export["user"])
        self.assertNotIn("push_token", export["user"])
        self.assertEqual(len(export["chat_messages"]), 1)
        self.assertEqual(len(export["memories"]), 1)
        self.assertEqual(export["push_tokens"][0]["provider"], "jpush")
        self.assertNotIn("token", export["push_tokens"][0])
        self.assertEqual(export["payment_orders"][0]["out_trade_no"], "LB202607080001")
        self.assertNotIn("raw_notify", export["payment_orders"][0])

    async def test_delete_account_requires_confirmation(self):
        with self.assertRaises(HTTPException) as ctx:
            await delete_account(
                data=DeleteAccountRequest(confirm="WRONG"),
                user=FakeUser(id=uuid.uuid4()),
                db=FakeDb(),
            )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_delete_account_marks_pending_deletion_and_disables_push(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        response = await delete_account(
            data=DeleteAccountRequest(confirm="DELETE", reason="privacy"),
            user=user,
            db=db,
        )

        self.assertTrue(db.flushed)
        self.assertIsNone(user.push_token)
        self.assertIsNone(user.push_platform)
        self.assertEqual(user.settings["account_status"], "pending_deletion")
        self.assertEqual(user.settings["account_deletion_reason"], "privacy")
        self.assertEqual(response["status"], "pending_deletion")
        self.assertIn("scheduled_deletion_at", response)


if __name__ == "__main__":
    unittest.main()
