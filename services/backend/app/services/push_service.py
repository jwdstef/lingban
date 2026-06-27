class PushService:
    """推送通知服务"""

    async def send_push(
        self,
        user_push_token: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """发送推送通知"""
        # TODO: 集成 Firebase/极光推送
        # MVP 阶段先打日志
        print(f"[Push] To: {user_push_token[:20]}... | {title}: {body}")
        return True

    async def send_proactive_message(
        self,
        user_push_token: str,
        character_name: str,
        message: str,
        character_id: str,
    ) -> bool:
        """发送 AI 主动关怀推送"""
        return await self.send_push(
            user_push_token=user_push_token,
            title=character_name,
            body=message,
            data={"type": "proactive", "character_id": character_id},
        )


push_service = PushService()
