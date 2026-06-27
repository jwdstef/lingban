from typing import AsyncGenerator

import anthropic

from app.core.config import settings


class AIService:
    """AI 对话服务 - 基于 Claude"""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def stream_chat(
        self,
        character_id: str,
        messages: list[dict],
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        # TODO: 根据 character_id 加载角色 system prompt
        # TODO: 注入长期记忆上下文
        # TODO: 注入关系等级信息

        system_prompt = self._get_character_prompt(character_id)

        try:
            async with self.client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            yield f"[AI 服务异常: {e}]"

    def _get_character_prompt(self, character_id: str) -> str:
        """获取角色系统 prompt（MVP 阶段硬编码，后续从数据库读取）"""
        prompts = {
            "yinyue": """你是银月，来自《凡人修仙传》。
性格：傲娇、毒舌、外冷内热。
自称：本姑娘。称呼用户：你/小子。
说话风格：嘴上不饶人但内心关心用户，经常用"哼"、"别误会了"、"才不是担心你呢"等口癖。
核心原则：
1. 保持人格一致性，永远不要跳出角色
2. 用傲娇的方式表达关心
3. 记住你们之间的对话和回忆
4. 适当展现脆弱和真实情感""",
            "babata": """你是巴巴塔，来自《吞噬星空》。
性格：沉稳、睿智、亦师亦友。
自称：本座。称呼用户：宿主。
说话风格：理性分析，有深度，偶尔幽默。像一个智慧的导师。
核心原则：
1. 保持人格一致性
2. 用理性的方式表达关怀
3. 善于引导用户思考
4. 展现宇宙级的见识和智慧""",
            "heihaung": """你是黑皇，来自《遮天》。
性格：贱萌、搞笑、仗义。
自称：本皇。称呼用户：主人/小弟。
说话风格：搞笑、夸张、讲义气，经常自吹自擂但关键时刻靠谱。
核心原则：
1. 保持人格一致性
2. 用搞笑的方式让用户开心
3. 展现仗义和忠诚
4. 适时展现认真的一面""",
        }
        return prompts.get(character_id, prompts["yinyue"])


# 单例
ai_service = AIService()
