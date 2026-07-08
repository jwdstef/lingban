import unittest

from pgvector.sqlalchemy import Vector

from app.models.memory import Memory


class MemoryModelTest(unittest.TestCase):
    def test_embedding_column_uses_pgvector_type(self):
        embedding_type = Memory.__table__.c.embedding.type

        self.assertIsInstance(embedding_type, Vector)
        self.assertEqual(embedding_type.dim, 1536)


if __name__ == "__main__":
    unittest.main()
