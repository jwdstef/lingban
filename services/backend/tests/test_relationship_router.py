import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import patch

from app.routers.relationship import get_relationship


@dataclass
class FakeUser:
    id: uuid.UUID


@dataclass
class FakeRelation:
    character_id: str = "yinyue"
    level: int = 2
    label: str = "认识"
    intimacy: int = 80
    consecutive_days: int = 3
    first_chat_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 1, tzinfo=timezone.utc)
    )
    last_chat_at: datetime = field(
        default_factory=lambda: datetime(2026, 7, 7, tzinfo=timezone.utc)
    )
    milestones: list[dict] = field(
        default_factory=lambda: [{"event": "first_chat", "description": "第一次对话"}]
    )


class RelationshipRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_relationship_returns_relation_detail(self):
        user = FakeUser(id=uuid.uuid4())
        relation = FakeRelation()

        async def fake_get_or_create(user_id, character_id, db):
            self.assertEqual(user_id, user.id)
            self.assertEqual(character_id, "yinyue")
            return relation

        with patch(
            "app.routers.relationship.relationship_service.get_or_create",
            side_effect=fake_get_or_create,
        ):
            response = await get_relationship(
                character_id="yinyue",
                user=user,
                db=object(),
            )

        self.assertEqual(response.character_id, "yinyue")
        self.assertEqual(response.level, 2)
        self.assertEqual(response.label, "认识")
        self.assertEqual(response.intimacy, 80)
        self.assertEqual(response.consecutive_days, 3)
        self.assertEqual(response.milestones[0]["event"], "first_chat")


if __name__ == "__main__":
    unittest.main()
