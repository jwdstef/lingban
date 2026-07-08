import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.memory_service import MemoryService


class FakeResult:
    def __init__(self, item):
        self._item = item

    def scalar_one_or_none(self):
        return self._item


class FakeDb:
    async def execute(self, statement):
        return FakeResult(
            SimpleNamespace(settings={"memory_enabled": False})
        )


class MemoryServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_extract_and_store_skips_when_user_disabled_memory(self):
        service = MemoryService()
        service._extract_memories_with_ai = AsyncMock(return_value=[{"content": "x"}])

        memories = await service.extract_and_store(
            user_id=uuid.uuid4(),
            character_id="yinyue",
            conversation=[{"role": "user", "content": "remember this"}],
            source_message_id=None,
            db=FakeDb(),
        )

        self.assertEqual(memories, [])
        service._extract_memories_with_ai.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
