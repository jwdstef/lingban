import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.routers.admin import (
    _mask_secret,
    _serialize_audit_log,
    _serialize_chat_message,
    _serialize_proactive_message,
    _serialize_push_delivery,
    _serialize_safety_event,
)


@dataclass
class FakeChatMessage:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    character_id: str = "yinyue"
    role: str = "user"
    content: str = "I feel unsafe"
    message_type: str = "text"
    emotion_tags: list[str] = field(default_factory=lambda: ["crisis"])
    is_proactive: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc)
    )


@dataclass
class FakeProactiveMessage:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    character_id: str = "yinyue"
    trigger_type: str = "silence"
    content: str = "Are you doing okay?"
    delivered: bool = True
    replied: bool = False
    push_status: str = "sent"
    push_error: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc)
    )


@dataclass
class FakePushDelivery:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    push_token_id: uuid.UUID | None = field(default_factory=uuid.uuid4)
    proactive_message_id: uuid.UUID | None = field(default_factory=uuid.uuid4)
    provider: str = "jpush"
    notification_type: str = "proactive"
    title: str = "Yinyue"
    body: str = "Are you doing okay?"
    deep_link: str | None = "lingban://chat/yinyue"
    status: str = "clicked"
    provider_message_id: str | None = "provider-1"
    failure_reason: str | None = None
    sent_at: datetime | None = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc)
    )
    clicked_at: datetime | None = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 31, tzinfo=timezone.utc)
    )
    created_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc)
    )


@dataclass
class FakeSafetyEvent:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    character_id: str = "yinyue"
    source: str = "chat_message"
    source_message_id: uuid.UUID | None = field(default_factory=uuid.uuid4)
    event_type: str = "self_harm"
    severity: str = "critical"
    status: str = "pending_review"
    content_excerpt: str = "I do not want to live"
    matched_terms: list[str] = field(default_factory=lambda: ["do not want to live"])
    review_note: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc)
    )


@dataclass
class FakeAuditLog:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    actor_type: str = "admin"
    actor_id: str | None = "admin-ui"
    action: str = "safety_event.reviewed"
    target_type: str = "safety_event"
    target_id: str | None = field(default_factory=lambda: str(uuid.uuid4()))
    event_metadata: dict = field(default_factory=lambda: {"status": "resolved"})
    created_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, 9, 35, tzinfo=timezone.utc)
    )


class AdminRouterSerializerTest(unittest.TestCase):
    def test_mask_secret_keeps_only_edges(self):
        self.assertEqual(_mask_secret("abcdef1234567890", visible=4), "abcd...7890")
        self.assertIsNone(_mask_secret(None))

    def test_serialize_chat_message_for_audit_table(self):
        message = FakeChatMessage()

        data = _serialize_chat_message(message)

        self.assertEqual(data["id"], str(message.id))
        self.assertEqual(data["short_id"], str(message.id)[:8])
        self.assertEqual(data["role"], "user")
        self.assertEqual(data["emotion_tags"], ["crisis"])

    def test_serialize_proactive_message_for_operations_table(self):
        message = FakeProactiveMessage()

        data = _serialize_proactive_message(message)

        self.assertEqual(data["trigger_type"], "silence")
        self.assertEqual(data["push_status"], "sent")
        self.assertTrue(data["delivered"])
        self.assertFalse(data["replied"])

    def test_serialize_push_delivery_omits_raw_token(self):
        delivery = FakePushDelivery()

        data = _serialize_push_delivery(delivery)

        self.assertEqual(data["provider"], "jpush")
        self.assertEqual(data["status"], "clicked")
        self.assertNotIn("token", data)
        self.assertEqual(data["push_token_id"], str(delivery.push_token_id))

    def test_serialize_safety_event_marks_pending_review(self):
        event = FakeSafetyEvent()

        data = _serialize_safety_event(event)

        self.assertEqual(data["id"], str(event.id))
        self.assertEqual(data["short_id"], str(event.id)[:8])
        self.assertEqual(data["source_message_id"], str(event.source_message_id))
        self.assertEqual(data["event_type"], "self_harm")
        self.assertEqual(data["severity"], "critical")
        self.assertEqual(data["status"], "pending_review")
        self.assertEqual(data["content"], "I do not want to live")
        self.assertEqual(data["matched_terms"], ["do not want to live"])

    def test_serialize_audit_log_for_operations_table(self):
        log = FakeAuditLog()

        data = _serialize_audit_log(log)

        self.assertEqual(data["id"], str(log.id))
        self.assertEqual(data["action"], "safety_event.reviewed")
        self.assertEqual(data["metadata"], {"status": "resolved"})


if __name__ == "__main__":
    unittest.main()
