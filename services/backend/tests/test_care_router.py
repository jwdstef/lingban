import unittest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from inspect import signature

from fastapi import HTTPException

from app.routers.care import _parse_message_id, _serialize_message, list_care_messages


@dataclass
class FakeCareMessage:
    id: uuid.UUID
    character_id: str
    trigger_type: str
    content: str
    delivered: bool
    replied: bool
    push_status: str
    push_error: str | None
    created_at: datetime


class CareRouterTest(unittest.TestCase):
    def test_serialize_message_returns_mobile_contract(self):
        message_id = uuid.uuid4()
        created_at = datetime(2026, 7, 7, 8, 30, tzinfo=timezone.utc)
        message = FakeCareMessage(
            id=message_id,
            character_id="yinyue",
            trigger_type="silence",
            content="Checking in.",
            delivered=True,
            replied=False,
            push_status="sent",
            push_error=None,
            created_at=created_at,
        )

        response = _serialize_message(message)

        self.assertEqual(response.id, str(message_id))
        self.assertEqual(response.character_id, "yinyue")
        self.assertEqual(response.trigger_type, "silence")
        self.assertEqual(response.content, "Checking in.")
        self.assertTrue(response.delivered)
        self.assertFalse(response.replied)
        self.assertEqual(response.push_status, "sent")
        self.assertIsNone(response.push_error)
        self.assertEqual(response.created_at, created_at)

    def test_parse_message_id_rejects_invalid_uuid(self):
        with self.assertRaises(HTTPException) as ctx:
            _parse_message_id("not-a-uuid")

        self.assertEqual(ctx.exception.status_code, 400)

    def test_list_messages_accepts_character_filter(self):
        params = signature(list_care_messages).parameters

        self.assertIn("character_id", params)


if __name__ == "__main__":
    unittest.main()
