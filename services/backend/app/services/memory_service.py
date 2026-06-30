"""记忆管理服务 - 提取、存储、召回"""

import uuid
from datetime import datetime, timezone

from openai import AsyncOpenAI
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.memory import Memory


class MemoryService:
    """记忆管理服务"""

    def __init__(self):
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_and_store(
        self,
        user_id: uuid.UUID,
        character_id: str,
        conversation: list[dict],
        source_message_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> list[Memory]:
        """从对话中提取记忆并存储"""
        # 1. 用 AI 提取结构化记忆
        extracted = await self._extract_memories_with_ai(conversation)

        # 2. 向量化并存储
        memories = []
        for item in extracted:
            embedding = await self._get_embedding(item["content"])

            memory = Memory(
                user_id=user_id,
                character_id=character_id,
                category=item["category"],
                content=item["content"],
                importance=item.get("importance", 5),
                emotion_tags=item.get("emotion_tags", []),
                source_message_id=source_message_id,
                recall_count=0,
                is_active=True,
            )
            db.add(memory)
            await db.flush()

            # 写入 pgvector embedding
            if embedding:
                await db.execute(
                    text("""
                        UPDATE memories 
                        SET embedding = CAST(:embedding AS vector(1536))
                        WHERE id = :id
                    """),
                    {"embedding": self._format_vector(embedding), "id": str(memory.id)},
                )

            memories.append(memory)

        await db.commit()
        return memories

    async def recall_memories(
        self,
        user_id: uuid.UUID,
        character_id: str,
        query: str,
        db: AsyncSession,
        top_k: int = 5,
    ) -> list[Memory]:
        """语义召回记忆（pgvector）"""
        # 获取查询向量
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            # fallback: 按重要度+时间排序
            return await self._recall_by_importance(user_id, character_id, db, top_k)

        # pgvector 语义检索
        result = await db.execute(
            text("""
                SELECT id, user_id, character_id, category, content, importance,
                       emotion_tags, source_message_id, recall_count, is_active,
                       created_at, updated_at,
                       1 - (embedding <=> CAST(:query_embedding AS vector(1536))) AS similarity
                FROM memories
                WHERE user_id = :user_id
                  AND character_id = :character_id
                  AND is_active = true
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_embedding AS vector(1536))
                LIMIT :top_k
            """),
            {
                "query_embedding": self._format_vector(query_embedding),
                "user_id": str(user_id),
                "character_id": character_id,
                "top_k": top_k,
            },
        )
        rows = result.fetchall()

        # 更新召回计数
        memory_ids = [str(row[0]) for row in rows]
        if memory_ids:
            await db.execute(
                update(Memory)
                .where(Memory.id.in_(memory_ids))
                .values(recall_count=Memory.recall_count + 1)
            )
            await db.commit()

        # 转换为 Memory 对象
        memories = []
        for row in rows:
            m = Memory(
                id=row[0],
                user_id=row[1],
                character_id=row[2],
                category=row[3],
                content=row[4],
                importance=row[5],
                emotion_tags=row[6],
                source_message_id=row[7],
                recall_count=row[8],
                is_active=row[9],
                created_at=row[10],
                updated_at=row[11],
            )
            memories.append(m)

        return memories

    async def _recall_by_importance(
        self,
        user_id: uuid.UUID,
        character_id: str,
        db: AsyncSession,
        top_k: int,
    ) -> list[Memory]:
        """Fallback: 按重要度+时间召回"""
        result = await db.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.character_id == character_id,
                Memory.is_active == True,
            )
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def _extract_memories_with_ai(
        self, conversation: list[dict]
    ) -> list[dict]:
        """用 AI 从对话中提取结构化记忆"""
        # 只提取用户消息中的信息
        user_messages = [m["content"] for m in conversation if m["role"] == "user"]
        if not user_messages:
            return []

        user_text = "\n".join(user_messages)

        try:
            response = await self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """你是一个记忆提取助手。从用户对话中提取值得长期记住的信息。

返回 JSON 数组，每个元素包含：
- category: 分类（daily/emotion/preference/event/person/fact）
- content: 记忆内容（一句话概括）
- importance: 重要度 1-10
- emotion_tags: 情感标签数组

只提取有长期价值的信息，忽略无意义的寒暄。如果没有值得提取的记忆，返回空数组 []。

示例输出：
[
  {"category": "daily", "content": "用户今天加班到很晚，看起来很疲惫", "importance": 6, "emotion_tags": ["疲惫"]},
  {"category": "preference", "content": "用户喜欢深夜聊天", "importance": 5, "emotion_tags": []}
]""",
                    },
                    {"role": "user", "content": user_text},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            import json
            content = response.choices[0].message.content
            data = json.loads(content)
            return data.get("memories", data) if isinstance(data, dict) else data

        except Exception:
            return []

    async def _get_embedding(self, text: str) -> list[float] | None:
        """获取文本 embedding"""
        try:
            response = await self._openai.embeddings.create(
                model=settings.embedding_model,
                input=text,
                dimensions=settings.embedding_dimensions,
            )
            return response.data[0].embedding
        except Exception:
            return None

    def _format_vector(self, vector: list[float]) -> str:
        """格式化向量为 pgvector 字符串"""
        return "[" + ",".join(str(v) for v in vector) + "]"


# 单例
memory_service = MemoryService()
