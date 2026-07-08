import unittest
import uuid
from types import SimpleNamespace

from app.models.safety import AuditLog, SafetyEvent
from app.services.safety_service import (
    content_excerpt,
    create_event_for_message,
    detect_risk_terms,
    review_event,
    severity_for_event,
)


class FakeResult:
    def __init__(self, item):
        self._item = item

    def scalar_one_or_none(self):
        return self._item


class FakeDb:
    def __init__(self, results=()):
        self._results = list(results)
        self.added = []

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()

    async def execute(self, statement):
        item = self._results.pop(0) if self._results else None
        return FakeResult(item)


def make_message(content: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        character_id="yinyue",
        content=content,
    )


class SafetyServiceTest(unittest.IsolatedAsyncioTestCase):
    def test_detect_risk_terms_and_severity(self):
        event_type, terms = detect_risk_terms("I think I might kill myself tonight")

        self.assertEqual(event_type, "self_harm")
        self.assertEqual(terms, ["kill myself"])
        self.assertEqual(severity_for_event(event_type), "critical")

    def test_content_excerpt_normalizes_and_truncates(self):
        excerpt = content_excerpt("  one\n two\tthree  ", limit=20)
        truncated = content_excerpt("x" * 20, limit=8)

        self.assertEqual(excerpt, "one two three")
        self.assertLessEqual(len(truncated), 8)
        self.assertTrue(truncated.endswith("..."))

    async def test_create_event_for_message_writes_event_and_audit_log(self):
        message = make_message("I want to kill myself")
        db = FakeDb([None])

        event = await create_event_for_message(db, message)

        self.assertIsInstance(event, SafetyEvent)
        self.assertEqual(event.user_id, message.user_id)
        self.assertEqual(event.source_message_id, message.id)
        self.assertEqual(event.event_type, "self_harm")
        self.assertEqual(event.severity, "critical")
        self.assertEqual(event.status, "pending_review")
        self.assertEqual(event.matched_terms, ["kill myself"])
        audit_logs = [item for item in db.added if isinstance(item, AuditLog)]
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs[0].action, "safety_event.created")
        self.assertEqual(audit_logs[0].target_id, str(event.id))

    async def test_create_event_for_message_returns_existing_duplicate(self):
        message = make_message("I might kill myself")
        existing = SafetyEvent(
            id=uuid.uuid4(),
            user_id=message.user_id,
            character_id=message.character_id,
            source="chat_message",
            source_message_id=message.id,
            event_type="self_harm",
            severity="critical",
            status="pending_review",
            content_excerpt=message.content,
            matched_terms=["kill myself"],
        )
        db = FakeDb([existing])

        event = await create_event_for_message(db, message)

        self.assertIs(event, existing)
        self.assertEqual(db.added, [])

    async def test_review_event_updates_status_and_writes_audit_log(self):
        event = SafetyEvent(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            character_id="yinyue",
            source="chat_message",
            source_message_id=uuid.uuid4(),
            event_type="self_harm",
            severity="critical",
            status="pending_review",
            content_excerpt="I do not want to live",
            matched_terms=["do not want to live"],
        )
        db = FakeDb()

        reviewed = await review_event(
            db,
            event,
            status="resolved",
            reviewed_by="admin-ui",
            note="Handled by human reviewer",
        )

        self.assertIs(reviewed, event)
        self.assertEqual(event.status, "resolved")
        self.assertEqual(event.reviewed_by, "admin-ui")
        self.assertEqual(event.review_note, "Handled by human reviewer")
        self.assertIsNotNone(event.reviewed_at)
        audit_logs = [item for item in db.added if isinstance(item, AuditLog)]
        self.assertEqual(len(audit_logs), 1)
        self.assertEqual(audit_logs[0].action, "safety_event.reviewed")
        self.assertEqual(audit_logs[0].event_metadata["previous_status"], "pending_review")
        self.assertEqual(audit_logs[0].event_metadata["status"], "resolved")

    async def test_review_event_rejects_unknown_status(self):
        event = SafetyEvent(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            event_type="self_harm",
            severity="critical",
            status="pending_review",
            content_excerpt="risk",
            matched_terms=["risk"],
        )

        with self.assertRaises(ValueError):
            await review_event(
                FakeDb(),
                event,
                status="closed",
                reviewed_by="admin-ui",
            )


if __name__ == "__main__":
    unittest.main()
