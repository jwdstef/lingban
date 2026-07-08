import unittest
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.services.proactive_service import ProactiveService


@dataclass
class FakeDiary:
    user_id: uuid.UUID
    date: datetime
    dominant_emotion: str
    triggers: list[str]


@dataclass
class FakeUser:
    id: uuid.UUID


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, scalars):
        self._scalars = scalars

    def scalars(self):
        return FakeScalars(self._scalars)


class FakeDb:
    def __init__(self, result):
        self._result = result

    async def execute(self, statement):
        return self._result


class ProactiveServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_emotion_trigger_supports_english_diary_values(self):
        user = FakeUser(id=uuid.uuid4())
        diaries = [
            FakeDiary(
                user_id=user.id,
                date=datetime(2026, 7, 7),
                dominant_emotion="anxious",
                triggers=["deadline pressure"],
            ),
            FakeDiary(
                user_id=user.id,
                date=datetime(2026, 7, 6),
                dominant_emotion="tired",
                triggers=["slept late"],
            ),
        ]
        db = FakeDb(FakeResult(diaries))

        trigger = await ProactiveService()._check_emotion_trigger(user, db)

        self.assertIsNotNone(trigger)
        trigger_type, context = trigger
        self.assertEqual(trigger_type, "emotion")
        self.assertEqual(context["emotion"], "anxious")
        self.assertEqual(context["days"], 2)
        self.assertCountEqual(
            context["triggers"],
            ["deadline pressure", "slept late"],
        )


if __name__ == "__main__":
    unittest.main()
