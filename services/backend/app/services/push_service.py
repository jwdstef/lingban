"""推送通知服务 - Push Gateway"""

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.memory import ProactiveMessage
from app.models.user import User


class PushGateway:
    """推送网关 - 统一封装各推送通道"""

    async def send(
        self,
        user_id: uuid.UUID,
        character_id: str,
        trigger_type: str,
        content: str,
        db: AsyncSession,
    ) -> ProactiveMessage:
        """发送主动关怀消息"""
        # 1. 创建消息记录
        message = ProactiveMessage(
            user_id=user_id,
            character_id=character_id,
            trigger_type=trigger_type,
            content=content,
            push_status="pending",
        )
        db.add(message)
        await db.flush()

        # 2. 获取用户推送 Token
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user or not user.push_token:
            message.push_status = "failed"
            message.push_error = "用户未注册推送 Token"
            await db.flush()
            return message

        # 3. 检查免打扰
        if self._is_dnd_time(user):
            message.push_status = "failed"
            message.push_error = "免打扰时段"
            await db.flush()
            return message

        # 4. 检查频控
        if await self._check_rate_limit(user_id, db):
            message.push_status = "failed"
            message.push_error = "超过每日推送限制"
            await db.flush()
            return message

        # 5. 发送推送
        try:
            await self._do_send(
                token=user.push_token,
                platform=user.push_platform,
                title=self._get_title(character_id),
                body=content,
                deep_link=f"lingban://chat/{character_id}",
            )
            message.push_status = "sent"
            message.delivered = True
        except Exception as e:
            message.push_status = "failed"
            message.push_error = str(e)[:500]

        await db.flush()
        return message

    async def _do_send(
        self,
        token: str,
        platform: str | None,
        title: str,
        body: str,
        deep_link: str,
    ) -> None:
        """实际发送推送（根据平台选择通道）"""
        if platform == "apns":
            await self._send_apns(token, title, body, deep_link)
        elif platform == "jpush":
            await self._send_jpush(token, title, body, deep_link)
        elif platform == "fcm":
            await self._send_fcm(token, title, body, deep_link)
        else:
            raise ValueError(f"不支持的推送平台: {platform}")

    async def _send_apns(self, token: str, title: str, body: str, deep_link: str) -> None:
        """发送 APNs 推送"""
        # TODO: 集成实际的 APNs 发送逻辑
        # 使用 aiosns 或 apns2 库
        print(f"[APNs] Sending to {token}: {title} - {body}")

    async def _send_jpush(self, token: str, title: str, body: str, deep_link: str) -> None:
        """发送极光推送"""
        if not settings.jpush_app_key or not settings.jpush_master_secret:
            print(f"[JPUSH] Mock: {title} - {body}")
            return

        try:
            import jpush
            from jpush import common

            jpush_client = jpush.JPush(
                settings.jpush_master_secret,
                settings.jpush_app_key,
            )

            push = jpush_client.create_push()
            push.audience = jpush.audience(jpush.registration_id(token))
            push.notification = jpush.notification(
                android=jpush.android(
                    alert=body,
                    title=title,
                    extras={"deep_link": deep_link},
                ),
                ios=jpush.ios(
                    alert=body,
                    extras={"deep_link": deep_link},
                ),
            )
            push.platform = jpush.all_
            push.send()
        except Exception as e:
            raise RuntimeError(f"极光推送失败: {e}")

    async def _send_fcm(self, token: str, title: str, body: str, deep_link: str) -> None:
        """发送 FCM 推送"""
        # TODO: 集成实际的 FCM 发送逻辑
        print(f"[FCM] Sending to {token}: {title} - {body}")

    def _get_title(self, character_id: str) -> str:
        """获取推送标题"""
        names = {
            "yinyue": "银月",
            "babata": "巴巴塔",
            "heihaung": "黑皇",
        }
        return names.get(character_id, "灵伴")

    def _is_dnd_time(self, user: User) -> bool:
        """检查是否在免打扰时段"""
        settings_data = user.settings or {}
        dnd_enabled = settings_data.get("dnd_enabled", True)
        if not dnd_enabled:
            return False

        dnd_start = settings_data.get("dnd_start", "23:00")
        dnd_end = settings_data.get("dnd_end", "08:00")

        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        start_parts = dnd_start.split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])

        end_parts = dnd_end.split(":")
        end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

        # 跨午夜的情况（如 23:00 - 08:00）
        if start_minutes > end_minutes:
            return current_minutes >= start_minutes or current_minutes < end_minutes
        else:
            return start_minutes <= current_minutes < end_minutes

    async def _check_rate_limit(self, user_id: uuid.UUID, db: AsyncSession) -> bool:
        """检查是否超过每日推送限制"""
        max_per_day = 3  # 每天最多 3 次主动消息

        # 查询今日已发送的主动消息数
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(ProactiveMessage).where(
                ProactiveMessage.user_id == user_id,
                ProactiveMessage.created_at >= today_start,
                ProactiveMessage.push_status == "sent",
            )
        )
        sent_count = len(result.scalars().all())

        return sent_count >= max_per_day

    async def mark_clicked(self, message_id: uuid.UUID, db: AsyncSession) -> None:
        """标记消息已点击"""
        await db.execute(
            update(ProactiveMessage)
            .where(ProactiveMessage.id == message_id)
            .values(push_status="clicked")
        )
        await db.flush()


# 单例
push_gateway = PushGateway()
