"""关系成长服务 - 亲密度计算、等级提升"""

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import UserCharacterRelation


# 关系等级定义
RELATIONSHIP_LEVELS = [
    (1, "陌生", 0, 50),
    (2, "认识", 51, 150),
    (3, "熟悉", 151, 350),
    (4, "亲密", 351, 600),
    (5, "挚友", 601, 1000),
]

# 亲密度增长规则
INTIMACY_RULES = {
    "first_chat_today": 5,       # 每日首次对话
    "effective_exchange": 2,     # 每轮有效对话（>3 次往返）
    "deep_sharing": 10,          # 深度倾诉（情绪相关）
    "consecutive_3days": 15,     # 连续 3 天互动
    "reply_proactive": 3,        # 回复主动消息
}

# 衰减规则
DECAY_RULES = {
    "inactive_7days": -20,       # 7 天未互动
}


class RelationshipService:
    """关系成长服务"""

    async def get_or_create(
        self,
        user_id: uuid.UUID,
        character_id: str,
        db: AsyncSession,
    ) -> UserCharacterRelation:
        """获取或创建关系记录"""
        result = await db.execute(
            select(UserCharacterRelation).where(
                UserCharacterRelation.user_id == user_id,
                UserCharacterRelation.character_id == character_id,
            )
        )
        relation = result.scalar_one_or_none()

        if not relation:
            relation = UserCharacterRelation(
                user_id=user_id,
                character_id=character_id,
                level=1,
                label="陌生",
                intimacy=0,
                milestones=[],
                consecutive_days=0,
            )
            db.add(relation)
            await db.flush()

        return relation

    async def on_chat(
        self,
        user_id: uuid.UUID,
        character_id: str,
        message_count: int,
        has_emotion: bool,
        db: AsyncSession,
    ) -> UserCharacterRelation:
        """用户发送消息后更新关系"""
        relation = await self.get_or_create(user_id, character_id, db)
        now = datetime.now(timezone.utc)

        # 记录首次聊天时间
        if not relation.first_chat_at:
            relation.first_chat_at = now
            relation.milestones = relation.milestones + [
                {"event": "first_chat", "date": now.isoformat(), "description": "第一次对话"}
            ]

        # 每日首次对话奖励
        is_first_chat_today = (
            not relation.last_chat_at
            or relation.last_chat_at.date() < now.date()
        )
        if is_first_chat_today:
            relation.intimacy += INTIMACY_RULES["first_chat_today"]

            # 连续天数计算
            if relation.last_chat_at:
                days_diff = (now.date() - relation.last_chat_at.date()).days
                if days_diff == 1:
                    relation.consecutive_days += 1
                elif days_diff > 1:
                    relation.consecutive_days = 1
            else:
                relation.consecutive_days = 1

            # 连续 3 天奖励
            if relation.consecutive_days == 3:
                relation.intimacy += INTIMACY_RULES["consecutive_3days"]
                relation.milestones = relation.milestones + [
                    {
                        "event": "consecutive_3days",
                        "date": now.isoformat(),
                        "description": f"连续互动 {relation.consecutive_days} 天",
                    }
                ]

        # 有效对话奖励（每轮 >3 次往返）
        if message_count > 3:
            relation.intimacy += INTIMACY_RULES["effective_exchange"]

        # 深度倾诉奖励
        if has_emotion:
            relation.intimacy += INTIMACY_RULES["deep_sharing"]

        # 更新最后聊天时间
        relation.last_chat_at = now

        # 更新关系等级
        self._update_level(relation, now)

        # 亲密度上限
        relation.intimacy = min(relation.intimacy, 1000)

        await db.flush()
        return relation

    async def on_reply_proactive(
        self,
        user_id: uuid.UUID,
        character_id: str,
        db: AsyncSession,
    ) -> None:
        """用户回复主动消息后更新关系"""
        relation = await self.get_or_create(user_id, character_id, db)
        relation.intimacy += INTIMACY_RULES["reply_proactive"]
        relation.intimacy = min(relation.intimacy, 1000)
        self._update_level(relation, datetime.now(timezone.utc))
        await db.flush()

    async def apply_decay(self, db: AsyncSession) -> int:
        """对长时间未互动的用户应用亲密度衰减"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        result = await db.execute(
            select(UserCharacterRelation).where(
                UserCharacterRelation.last_chat_at < cutoff,
                UserCharacterRelation.intimacy > 0,
            )
        )
        relations = result.scalars().all()
        count = 0
        for relation in relations:
            relation.intimacy = max(0, relation.intimacy + DECAY_RULES["inactive_7days"])
            relation.consecutive_days = 0
            self._update_level(relation, datetime.now(timezone.utc))
            count += 1

        if count > 0:
            await db.flush()
        return count

    def _update_level(self, relation: UserCharacterRelation, now: datetime) -> None:
        """根据亲密度更新关系等级"""
        old_level = relation.level
        for level, label, min_intimacy, max_intimacy in RELATIONSHIP_LEVELS:
            if min_intimacy <= relation.intimacy <= max_intimacy:
                relation.level = level
                relation.label = label
                break

        # 等级提升时记录里程碑
        if relation.level > old_level:
            relation.milestones = relation.milestones + [
                {
                    "event": "level_up",
                    "date": now.isoformat(),
                    "description": f"关系提升到 Lv.{relation.level} {relation.label}",
                }
            ]


# 单例
relationship_service = RelationshipService()
