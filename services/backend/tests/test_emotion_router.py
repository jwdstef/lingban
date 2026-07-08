import unittest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.routers.emotion import get_emotion_diary, get_emotion_trend
from app.services.emotion_service import (
    detect_emotion_signal,
    record_emotion_from_text,
)


@dataclass
class FakeDiary:
    id: uuid.UUID
    user_id: uuid.UUID
    date: datetime
    dominant_emotion: str | None
    intensity: float | None
    triggers: list[str]
    created_at: datetime


@dataclass
class FakeUser:
    id: uuid.UUID


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
        self.added = []
        self.flushed = False

    async def execute(self, statement):
        self.statements.append(statement)
        return self._results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True


def make_diary(**overrides):
    values = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "date": datetime(2026, 7, 7),
        "dominant_emotion": "anxious",
        "intensity": 0.72,
        "triggers": ["project deadline"],
        "created_at": datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return FakeDiary(**values)


class EmotionRouterTest(unittest.IsolatedAsyncioTestCase):
    def test_detect_emotion_signal_supports_user_language(self):
        english = detect_emotion_signal("I feel anxious and tired after work.")
        chinese = detect_emotion_signal("今天真的好焦虑，也有点累。")

        self.assertIsNotNone(english)
        self.assertEqual(english.emotion, "anxious")
        self.assertIsNotNone(chinese)
        self.assertEqual(chinese.emotion, "anxious")

    async def test_record_emotion_from_text_creates_daily_entry(self):
        user_id = uuid.uuid4()
        db = FakeDb(FakeResult(scalar_value=None))

        diary = await record_emotion_from_text(
            user_id=user_id,
            text="I feel anxious about the launch.",
            db=db,
            occurred_at=datetime(2026, 7, 7, 21, 15, tzinfo=timezone.utc),
        )

        self.assertIsNotNone(diary)
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.added[0].user_id, user_id)
        self.assertEqual(db.added[0].date, datetime(2026, 7, 7))
        self.assertEqual(db.added[0].dominant_emotion, "anxious")
        self.assertTrue(db.added[0].triggers)
        self.assertTrue(db.flushed)

    async def test_record_emotion_from_text_updates_existing_day(self):
        existing = make_diary(
            dominant_emotion="tired",
            intensity=0.55,
            triggers=["slept late"],
        )
        db = FakeDb(FakeResult(scalar_value=existing))

        diary = await record_emotion_from_text(
            user_id=existing.user_id,
            text="I am really stressed about work.",
            db=db,
            occurred_at=datetime(2026, 7, 7, 22, 0, tzinfo=timezone.utc),
        )

        self.assertIs(diary, existing)
        self.assertEqual(existing.dominant_emotion, "anxious")
        self.assertGreater(existing.intensity, 0.55)
        self.assertEqual(existing.triggers[0], "I am really stressed about work.")
        self.assertIn("slept late", existing.triggers)
        self.assertTrue(db.flushed)

    async def test_get_emotion_diary_lists_user_records(self):
        user = FakeUser(id=uuid.uuid4())
        diary = make_diary(user_id=user.id)
        db = FakeDb(FakeResult(scalar_value=1), FakeResult(scalars=[diary]))

        response = await get_emotion_diary(limit=30, offset=0, user=user, db=db)

        self.assertEqual(response.total, 1)
        self.assertFalse(response.has_more)
        self.assertEqual(response.records[0].id, str(diary.id))
        self.assertEqual(response.records[0].dominant_emotion, "anxious")

    async def test_get_emotion_trend_summarizes_records(self):
        user = FakeUser(id=uuid.uuid4())
        records = [
            make_diary(
                user_id=user.id,
                date=datetime(2026, 7, 6),
                dominant_emotion="happy",
                intensity=0.4,
            ),
            make_diary(
                user_id=user.id,
                date=datetime(2026, 7, 7),
                dominant_emotion="anxious",
                intensity=0.8,
            ),
        ]
        db = FakeDb(FakeResult(scalars=records))

        response = await get_emotion_trend(days=14, user=user, db=db)

        self.assertEqual(response.days, 14)
        self.assertEqual(len(response.points), 2)
        self.assertEqual(response.emotion_counts, {"happy": 1, "anxious": 1})
        self.assertAlmostEqual(response.average_intensity, 0.6)


if __name__ == "__main__":
    unittest.main()
