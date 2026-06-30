"""主动关怀服务 - 触发器检查 + 消息生成"""

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import UserCharacterRelation
from app.models.chat import ChatMessage
from app.models.memory import EmotionDiary
from app.models.user import User
from app.services.ai_service import ai_service
from app.services.push_service import push_gateway


class ProactiveService:
    """主动关怀服务"""

    # 沉默触发阈值（小时）
    SILENCE_THRESHOLD_HOURS = 24

    async def check_and_trigger(
        self,
        user: User,
        character_id: str,
        db: AsyncSession,
    ) -> bool:
        """检查是否触发主动关怀，返回是否触发"""
        if not user.selected_character_id:
            return False

        # 获取关系信息
        relation_result = await db.execute(
            select(UserCharacterRelation).where(
                UserCharacterRelation.user_id == user.id,
                UserCharacterRelation.character_id == character_id,
            )
        )
        relation = relation_result.scalar_one_or_none()
        if not relation:
            return False

        # 检查各种触发条件
        triggers = await self._check_triggers(user, character_id, relation, db)

        if not triggers:
            return False

        # 选择最合适的触发器
        trigger_type, trigger_context = triggers[0]

        # 生成关怀消息
        content = await self._generate_message(
            character_id=character_id,
            trigger_type=trigger_type,
            context=trigger_context,
            db=db,
        )

        if not content:
            return False

        # 发送推送
        await push_gateway.send(
            user_id=user.id,
            character_id=character_id,
            trigger_type=trigger_type,
            content=content,
            db=db,
        )

        return True

    async def _check_triggers(
        self,
        user: User,
        character_id: str,
        relation: UserCharacterRelation,
        db: AsyncSession,
    ) -> list[tuple[str, dict]]:
        """检查所有触发条件，返回触发的列表 [(trigger_type, context), ...]"""
        triggers = []
        now = datetime.now(timezone.utc)

        # 1. 时间触发 - 早安/晚安
        time_trigger = self._check_time_trigger(user, now)
        if time_trigger:
            triggers.append(time_trigger)

        # 2. 沉默触发 - 长时间未互动
        silence_trigger = self._check_silence_trigger(relation, now)
        if silence_trigger:
            triggers.append(silence_trigger)

        # 3. 情绪触发 - 最近情绪低落
        emotion_trigger = await self._check_emotion_trigger(user, db)
        if emotion_trigger:
            triggers.append(emotion_trigger)

        return triggers

    def _check_time_trigger(
        self, user: User, now: datetime
    ) -> tuple[str, dict] | None:
        """检查时间触发"""
        settings_data = user.settings or {}
        morning_time = settings_data.get("morning_time", "08:00")
        night_time = settings_data.get("night_time", "22:00")

        current_time = f"{now.hour:02d}:{now.minute:02d}"

        # 早安触发（±30分钟窗口）
        if self._is_in_time_window(current_time, morning_time, 30):
            return ("time_morning", {"time": current_time})

        # 晚安触发（±30分钟窗口）
        if self._is_in_time_window(current_time, night_time, 30):
            return ("time_night", {"time": current_time})

        return None

    def _is_in_time_window(self, current: str, target: str, window_minutes: int) -> bool:
        """检查当前时间是否在目标时间的窗口内"""
        current_parts = current.split(":")
        current_minutes = int(current_parts[0]) * 60 + int(current_parts[1])

        target_parts = target.split(":")
        target_minutes = int(target_parts[0]) * 60 + int(target_parts[1])

        return abs(current_minutes - target_minutes) <= window_minutes

    def _check_silence_trigger(
        self, relation: UserCharacterRelation, now: datetime
    ) -> tuple[str, dict] | None:
        """检查沉默触发"""
        if not relation.last_chat_at:
            # 从未聊天，不触发沉默关怀
            return None

        # 计算距离上次聊天的时间
        if relation.last_chat_at.tzinfo is None:
            last_chat = relation.last_chat_at.replace(tzinfo=timezone.utc)
        else:
            last_chat = relation.last_chat_at

        hours_since_chat = (now - last_chat).total_seconds() / 3600

        if hours_since_chat >= self.SILENCE_THRESHOLD_HOURS:
            return ("silence", {"hours": int(hours_since_chat)})

        return None

    async def _check_emotion_trigger(
        self, user: User, db: AsyncSession
    ) -> tuple[str, dict] | None:
        """检查情绪触发"""
        # 查询最近的情绪日记
        result = await db.execute(
            select(EmotionDiary)
            .where(EmotionDiary.user_id == user.id)
            .order_by(EmotionDiary.date.desc())
            .limit(3)
        )
        diaries = result.scalars().all()

        if not diaries:
            return None

        # 检查是否有持续负面情绪
        negative_emotions = ["焦虑", "悲伤", "愤怒", "孤独", "疲惫"]
        negative_count = 0
        recent_triggers = []

        for diary in diaries:
            if diary.dominant_emotion in negative_emotions:
                negative_count += 1
                recent_triggers.extend(diary.triggers or [])

        # 连续 2 天负面情绪触发
        if negative_count >= 2:
            return ("emotion", {
                "emotion": diaries[0].dominant_emotion,
                "days": negative_count,
                "triggers": list(set(recent_triggers))[:3],
            })

        return None

    async def _generate_message(
        self,
        character_id: str,
        trigger_type: str,
        context: dict,
        db: AsyncSession,
    ) -> str | None:
        """生成关怀消息内容"""
        # 根据触发类型构建提示
        prompts = {
            "time_morning": "现在是早上，给用户发一条早安问候，用你的角色风格。要简短自然，像朋友一样。",
            "time_night": "现在是晚上，给用户发一条晚安问候，用你的角色风格。要简短自然，关心对方早点休息。",
            "silence": f"用户已经 {context.get('hours', 24)} 小时没和你聊天了，主动关心一下，用你的角色风格。不要太刻意，自然一点。",
            "emotion": f"用户最近情绪不太好（{context.get('emotion', '低落')}），已经持续 {context.get('days', 2)} 天了。用你的角色风格关心一下，要温暖但不要过度。",
        }

        hint = prompts.get(trigger_type)
        if not hint:
            return None

        # 调用 AI 生成消息
        try:
            messages = [{"role": "user", "content": hint}]
            full_response = ""

            async for chunk in ai_service.stream_chat(
                character_id=character_id,
                user_id=uuid.uuid4(),  # 临时 user_id，仅用于生成
                messages=messages,
                db=db,
            ):
                full_response += chunk

            # 限制消息长度
            if len(full_response) > 100:
                full_response = full_response[:100] + "..."

            return full_response
        except Exception as e:
            print(f"[ProactiveService] 生成消息失败: {e}")
            return None


# 单例
proactive_service = ProactiveService()
