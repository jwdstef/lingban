import unittest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.routers.care import (
    UpdateCareFrequencyRequest,
    UpdateDndRequest,
    _parse_message_id,
    _serialize_message,
    list_care_messages,
    mark_care_message_clicked,
    mark_care_message_replied,
    update_care_dnd,
    update_care_frequency,
)


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


@dataclass
class FakeUser:
    id: uuid.UUID
    settings: dict | None = None


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, scalar_value=None, scalars=None):
        self._scalar_value = scalar_value
        self._scalars = scalars or []

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return FakeScalars(self._scalars)


class FakeDb:
    def __init__(self, *results):
        self._results = list(results)
        self.statements = []
        self.flushed = False

    async def execute(self, statement):
        self.statements.append(statement)
        return self._results.pop(0)

    async def flush(self):
        self.flushed = True


def make_message(**overrides):
    values = {
        "id": uuid.uuid4(),
        "character_id": "yinyue",
        "trigger_type": "silence",
        "content": "Checking in.",
        "delivered": False,
        "replied": False,
        "push_status": "sent",
        "push_error": None,
        "created_at": datetime(2026, 7, 7, 8, 30, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return FakeCareMessage(**values)


class CareRouterTest(unittest.IsolatedAsyncioTestCase):
    def test_serialize_message_returns_mobile_contract(self):
        message = make_message(delivered=True)

        response = _serialize_message(message)

        self.assertEqual(response.id, str(message.id))
        self.assertEqual(response.character_id, "yinyue")
        self.assertEqual(response.trigger_type, "silence")
        self.assertEqual(response.content, "Checking in.")
        self.assertTrue(response.delivered)
        self.assertFalse(response.replied)
        self.assertEqual(response.push_status, "sent")
        self.assertIsNone(response.push_error)
        self.assertEqual(response.created_at, message.created_at)

    def test_parse_message_id_rejects_invalid_uuid(self):
        with self.assertRaises(HTTPException) as ctx:
            _parse_message_id("not-a-uuid")

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_list_messages_returns_paginated_character_messages(self):
        message = make_message()
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=1), FakeResult(scalars=[message]))

        response = await list_care_messages(
            limit=20,
            offset=0,
            character_id="yinyue",
            user=user,
            db=db,
        )

        self.assertEqual(response.total, 1)
        self.assertFalse(response.has_more)
        self.assertEqual(len(response.messages), 1)
        self.assertEqual(response.messages[0].id, str(message.id))
        self.assertIn("AND proactive_messages.character_id", str(db.statements[0]))

    async def test_update_frequency_persists_proactive_level(self):
        user = FakeUser(id=uuid.uuid4(), settings={"dnd_enabled": True})
        db = FakeDb()

        response = await update_care_frequency(
            UpdateCareFrequencyRequest(proactive_level="quiet"),
            user=user,
            db=db,
        )

        self.assertEqual(response["settings"]["proactive_level"], "quiet")
        self.assertTrue(response["settings"]["dnd_enabled"])
        self.assertTrue(db.flushed)

    async def test_update_dnd_persists_window(self):
        user = FakeUser(id=uuid.uuid4(), settings={"proactive_level": "high"})
        db = FakeDb()

        response = await update_care_dnd(
            UpdateDndRequest(
                dnd_enabled=True,
                dnd_start="22:30",
                dnd_end="07:45",
            ),
            user=user,
            db=db,
        )

        self.assertEqual(response["settings"]["dnd_start"], "22:30")
        self.assertEqual(response["settings"]["dnd_end"], "07:45")
        self.assertEqual(response["settings"]["proactive_level"], "high")
        self.assertTrue(db.flushed)

    async def test_mark_clicked_updates_status(self):
        message = make_message(delivered=False, push_status="sent")
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=message))

        response = await mark_care_message_clicked(str(message.id), user=user, db=db)

        self.assertTrue(message.delivered)
        self.assertEqual(message.push_status, "clicked")
        self.assertTrue(db.flushed)
        self.assertEqual(response.push_status, "clicked")

    async def test_mark_clicked_returns_404_for_missing_message(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=None))

        with self.assertRaises(HTTPException) as ctx:
            await mark_care_message_clicked(str(uuid.uuid4()), user=user, db=db)

        self.assertEqual(ctx.exception.status_code, 404)

    async def test_mark_replied_updates_message_and_relationship(self):
        message = make_message(replied=False)
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=message))

        with patch(
            "app.routers.care.relationship_service.on_reply_proactive",
            new_callable=AsyncMock,
        ) as on_reply_proactive:
            response = await mark_care_message_replied(
                str(message.id),
                user=user,
                db=db,
            )

        self.assertTrue(message.replied)
        self.assertTrue(db.flushed)
        self.assertTrue(response.replied)
        on_reply_proactive.assert_awaited_once_with(user.id, "yinyue", db)

    async def test_mark_replied_does_not_double_count_relationship(self):
        message = make_message(replied=True)
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=message))

        with patch(
            "app.routers.care.relationship_service.on_reply_proactive",
            new_callable=AsyncMock,
        ) as on_reply_proactive:
            await mark_care_message_replied(str(message.id), user=user, db=db)

        on_reply_proactive.assert_not_awaited()

    async def test_mark_replied_returns_404_for_missing_message(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=None))

        with self.assertRaises(HTTPException) as ctx:
            await mark_care_message_replied(str(uuid.uuid4()), user=user, db=db)

        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
