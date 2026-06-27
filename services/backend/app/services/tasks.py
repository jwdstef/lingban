from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "lingban",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    beat_schedule={
        # 主动关怀定时任务
        "morning_greeting": {
            "task": "app.services.tasks.proactive_morning_greeting",
            "schedule": 3600.0,  # 每小时检查一次
        },
    },
)


@celery_app.task
def proactive_morning_greeting():
    """早安问候 - 检查需要发送早安消息的用户"""
    # TODO: 查询活跃用户，根据角色性格生成个性化问候
    # TODO: 考虑天气、日历、用户习惯等因素
    pass


@celery_app.task
def proactive_evening_checkin():
    """晚间关怀 - 检查用户状态"""
    # TODO: 检查用户今日互动情况，决定是否发送关怀消息
    pass


@celery_app.task
def proactive_sleep_reminder():
    """深夜劝睡 - 检测用户是否还在活跃"""
    # TODO: 检查用户最后活跃时间，深夜时发送劝睡消息
    pass


@celery_app.task
def extract_memory_from_conversation(user_id: str, character_id: str, message_id: str):
    """异步提取对话中的记忆"""
    # TODO: 调用 memory_service 提取记忆并存入向量库
    pass
