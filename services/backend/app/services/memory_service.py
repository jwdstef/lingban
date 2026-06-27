from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory


class MemoryService:
    """记忆管理服务 - 从对话中提取和召回记忆"""

    async def extract_memories(
        self,
        user_id: str,
        character_id: str,
        message_content: str,
        db: AsyncSession,
    ) -> list[Memory]:
        """从对话中提取记忆（MVP 阶段使用规则，后续用 AI 提取）"""
        # TODO: 使用 AI 分析对话内容，提取结构化记忆
        # TODO: 将记忆向量化存入 Qdrant
        memories = []
        return memories

    async def recall_memories(
        self,
        user_id: str,
        character_id: str,
        query: str,
        db: AsyncSession,
        top_k: int = 5,
    ) -> list[Memory]:
        """召回相关记忆（语义检索）"""
        # TODO: 使用 Qdrant 向量检索相关记忆
        # TODO: 结合时间衰减和重要度排序
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


memory_service = MemoryService()
