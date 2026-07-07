import asyncio
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
