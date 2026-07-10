import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.ai_service import AIService
from app.services.memory_service import MemoryService


class LocalAIFallbackTest(unittest.TestCase):
    def test_local_reply_uses_character_voice(self):
        service = AIService()

        reply = service._build_local_reply(
            character_id="yinyue",
            messages=[{"role": "user", "content": "今天加班到很晚，有点累"}],
            memories=[],
        )

        self.assertIn("今天加班到很晚", reply)
        self.assertIn("本姑娘", reply)

    def test_local_memory_extraction_without_openai_key(self):
        service = MemoryService()
        conversation = [
            {"role": "user", "content": "我最近睡得很晚，工作压力有点大"},
            {"role": "assistant", "content": "别硬撑。"},
        ]

        with patch("app.services.memory_service.settings.openai_api_key", ""):
            memories = asyncio.run(service._extract_memories_with_ai(conversation))

        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["category"], "emotion")
        self.assertIn("工作压力", memories[0]["content"])

    def test_chat_memory_recall_timeout_returns_empty_memories(self):
        service = AIService()

        async def slow_recall(**kwargs):
            await asyncio.sleep(0.05)
            return ["should-time-out"]

        with patch(
            "app.services.ai_service.settings.ai_memory_recall_timeout_ms",
            1,
        ), patch.object(service, "_recall_memories", side_effect=slow_recall):
            memories = asyncio.run(
                service._recall_memories_for_chat(
                    user_id="user-id",
                    character_id="yinyue",
                    query="hello",
                    db=None,
                    request_id="test",
                )
            )

        self.assertEqual(memories, [])

    def test_stream_chat_truncates_long_upstream_response(self):
        service = AIService()

        class FakeStream:
            def __init__(self):
                self.closed = False
                self._chunks = iter(("hello", " world"))

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    content = next(self._chunks)
                except StopIteration:
                    raise StopAsyncIteration
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            delta=SimpleNamespace(content=content),
                        )
                    ]
                )

            async def close(self):
                self.closed = True

        fake_stream = FakeStream()

        async def collect_chunks():
            with patch("app.services.ai_service.settings.openai_api_key", "key"), patch(
                "app.services.ai_service.settings.ai_chat_response_char_limit",
                5,
            ), patch.object(
                service,
                "_get_character",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(system_prompt="prompt"),
            ), patch.object(
                service,
                "_get_relationship",
                new_callable=AsyncMock,
                return_value=None,
            ), patch.object(
                service,
                "_get_user_settings",
                new_callable=AsyncMock,
                return_value={},
            ), patch.object(
                service,
                "_recall_memories_for_chat",
                new_callable=AsyncMock,
                return_value=[],
            ), patch.object(
                service,
                "_create_chat_stream",
                new_callable=AsyncMock,
                return_value=fake_stream,
            ):
                chunks = []
                async for chunk in service.stream_chat(
                    character_id="yinyue",
                    user_id="user-id",
                    messages=[{"role": "user", "content": "hello"}],
                    db=None,
                    request_id="test",
                ):
                    chunks.append(chunk)
                return chunks

        chunks = asyncio.run(collect_chunks())

        self.assertEqual("".join(chunks), "hello")
        self.assertTrue(fake_stream.closed)


if __name__ == "__main__":
    unittest.main()
