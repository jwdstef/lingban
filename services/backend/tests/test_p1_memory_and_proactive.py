import uuid
import unittest

from app.core.config import settings
from app.models.memory import Memory
from app.services import proactive_service as proactive_module
from app.services.memory_service import MemoryService


class ProactiveCareContextTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_message_uses_real_user_id_for_memory_context(self):
        service = proactive_module.ProactiveService()
        expected_user_id = uuid.uuid4()
        captured = {}

        class FakeAIService:
            async def stream_chat(self, character_id, user_id, messages, db):
                captured["character_id"] = character_id
                captured["user_id"] = user_id
                captured["messages"] = messages
                yield "记得你最近提到的项目，今天也别硬撑。"

        original_ai_service = proactive_module.ai_service
        proactive_module.ai_service = FakeAIService()
        try:
            content = await service._generate_message(
                user_id=expected_user_id,
                character_id="yinyue",
                trigger_type="silence",
                context={"hours": 26},
                db=object(),
            )
        finally:
            proactive_module.ai_service = original_ai_service

        self.assertEqual(captured["user_id"], expected_user_id)
        self.assertEqual(captured["character_id"], "yinyue")
        self.assertIn("26", captured["messages"][0]["content"])
        self.assertEqual(content, "记得你最近提到的项目，今天也别硬撑。")


class MemoryEmbeddingTest(unittest.IsolatedAsyncioTestCase):
    def test_memory_model_vector_dimension_matches_settings(self):
        self.assertEqual(Memory.__table__.c.embedding.type.dim, settings.embedding_dimensions)

    async def test_backfill_missing_embeddings_writes_vectors(self):
        service = MemoryService()
        service._embedding_dim = 4

        memory_id = uuid.uuid4()
        writes = []

        async def fake_get_embedding(text):
            self.assertEqual(text, "用户最近工作压力很大")
            return [0.1, 0.2, 0.3, 0.4]

        service._get_embedding = fake_get_embedding

        class RowResult:
            def all(self):
                return [(memory_id, "用户最近工作压力很大")]

        class FakeDb:
            async def execute(self, statement, params=None):
                if params is not None:
                    writes.append((str(statement), params))
                    return None
                return RowResult()

            async def flush(self):
                writes.append(("flush", None))

        updated = await service.backfill_missing_embeddings(FakeDb(), limit=10)

        self.assertEqual(updated, 1)
        self.assertEqual(writes[0][1]["id"], str(memory_id))
        self.assertEqual(writes[0][1]["embedding"], "[0.1,0.2,0.3,0.4]")
        self.assertIn("vector(4)", writes[0][0])
        self.assertEqual(writes[-1], ("flush", None))


if __name__ == "__main__":
    unittest.main()
