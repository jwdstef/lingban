import unittest

from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.models.memory import Memory


class MemoryModelTest(unittest.TestCase):
    def test_embedding_column_uses_pgvector_type(self):
        embedding_type = Memory.__table__.c.embedding.type

        self.assertIsInstance(embedding_type, Vector)
        self.assertEqual(embedding_type.dim, settings.embedding_dimensions)


if __name__ == "__main__":
    unittest.main()
