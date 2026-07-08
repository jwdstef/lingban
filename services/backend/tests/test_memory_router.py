import unittest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException

from app.routers.memory import (
    UpdateMemoryToggleRequest,
    UpdateMemoryRequest,
    get_memories,
    toggle_memory,
    update_memory,
)


@dataclass
class FakeMemory:
    id: uuid.UUID
    category: str
    content: str
    importance: int
    emotion_tags: list[str]
    recall_count: int
    created_at: datetime
    embedding: list[float] | None = None
    is_active: bool = True


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
    def __init__(self, scalar_value=None, scalars=None, rows=None, rowcount=0):
        self._scalar_value = scalar_value
        self._scalars = scalars or []
        self._rows = rows or []
        self.rowcount = rowcount

    def scalar(self):
        return self._scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalars(self):
        return FakeScalars(self._scalars)

    def fetchall(self):
        return self._rows


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


def make_memory(**overrides):
    values = {
        "id": uuid.uuid4(),
        "category": "daily",
        "content": "User likes late-night ramen after work.",
        "importance": 6,
        "emotion_tags": ["comfort"],
        "recall_count": 0,
        "created_at": datetime(2026, 7, 7, 9, 30, tzinfo=timezone.utc),
        "embedding": [0.1, 0.2],
        "is_active": True,
    }
    values.update(overrides)
    return FakeMemory(**values)


class MemoryRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_memories_filters_by_search_query(self):
        memory = make_memory()
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(
            FakeResult(scalars=[memory]),
            FakeResult(scalar_value=1),
            FakeResult(rows=[("daily", 1)]),
        )

        response = await get_memories(
            character_id="yinyue",
            category=None,
            search="ramen",
            limit=50,
            offset=0,
            user=user,
            db=db,
        )

        self.assertEqual(response.total, 1)
        self.assertEqual(response.memories[0].content, memory.content)
        list_sql = str(db.statements[0])
        self.assertIn("memories.content", list_sql)
        self.assertIn("LIKE", list_sql.upper())

    async def test_update_memory_edits_fields_and_clears_stale_embedding(self):
        memory = make_memory()
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=memory))

        response = await update_memory(
            character_id="yinyue",
            memory_id=str(memory.id),
            data=UpdateMemoryRequest(
                content="User now prefers warm soup after late work.",
                category="preference",
                importance=8,
                emotion_tags=["comfort", "tired"],
            ),
            user=user,
            db=db,
        )

        self.assertEqual(memory.content, "User now prefers warm soup after late work.")
        self.assertEqual(memory.category, "preference")
        self.assertEqual(memory.importance, 8)
        self.assertEqual(memory.emotion_tags, ["comfort", "tired"])
        self.assertIsNone(memory.embedding)
        self.assertTrue(db.flushed)
        self.assertEqual(response.content, memory.content)

    async def test_update_memory_rejects_empty_payload(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with self.assertRaises(HTTPException) as ctx:
            await update_memory(
                character_id="yinyue",
                memory_id=str(uuid.uuid4()),
                data=UpdateMemoryRequest(),
                user=user,
                db=db,
            )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_update_memory_returns_404_for_missing_memory(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb(FakeResult(scalar_value=None))

        with self.assertRaises(HTTPException) as ctx:
            await update_memory(
                character_id="yinyue",
                memory_id=str(uuid.uuid4()),
                data=UpdateMemoryRequest(content="Corrected content"),
                user=user,
                db=db,
            )

        self.assertEqual(ctx.exception.status_code, 404)

    async def test_toggle_memory_updates_current_user_setting(self):
        user = FakeUser(id=uuid.uuid4(), settings={"proactive_level": "medium"})
        db = FakeDb()

        response = await toggle_memory(
            data=UpdateMemoryToggleRequest(memory_enabled=False),
            user=user,
            db=db,
        )

        self.assertFalse(user.settings["memory_enabled"])
        self.assertIn("memory_disabled_at", user.settings)
        self.assertEqual(response["settings"]["proactive_level"], "medium")
        self.assertTrue(db.flushed)


if __name__ == "__main__":
    unittest.main()
