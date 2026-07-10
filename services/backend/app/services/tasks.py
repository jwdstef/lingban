"""Celery 任务 - 配置 + 定义"""

import asyncio
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.user import User

# ── Celery 配置 ──

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
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

# 定时任务调度
celery_app.conf.beat_schedule = {
    "check-proactive-care": {
        "task": "app.services.tasks.check_proactive_care",
        "schedule": crontab(minute=0),
    },
    "apply-intimacy-decay": {
        "task": "app.services.tasks.apply_intimacy_decay",
        "schedule": crontab(hour=2, minute=0),
    },
    "cleanup-expired-data": {
        "task": "app.services.tasks.cleanup_expired_data",
        "schedule": crontab(hour=3, minute=0),
    },
}


# ── 工具函数 ──

def run_async(coro):
    """在同步 Celery 任务中运行异步协程"""
    return asyncio.run(coro)


# ── 定时任务 ──

@celery_app.task(name="app.services.tasks.check_proactive_care")
def check_proactive_care():
    """定时检查主动关怀触发（每小时执行）"""
    print(f"[{datetime.now()}] 开始检查主动关怀...")

    async def _check():
        from app.services.proactive_service import proactive_service

        async with async_session() as db:
            result = await db.execute(
                select(User).where(
                    User.selected_character_id.isnot(None),
                    User.push_token.isnot(None),
                )
            )
            users = result.scalars().all()

            triggered_count = 0
            for user in users:
                try:
                    triggered = await proactive_service.check_and_trigger(
                        user=user,
                        character_id=user.selected_character_id,
                        db=db,
                    )
                    if triggered:
                        triggered_count += 1
                except Exception as e:
                    print(f"[ProactiveCare] 用户 {user.id} 检查失败: {e}")

            await db.commit()
            print(f"[{datetime.now()}] 主动关怀检查完成，触发 {triggered_count} 条")

    run_async(_check())


@celery_app.task(name="app.services.tasks.apply_intimacy_decay")
def apply_intimacy_decay():
    """定时执行亲密度衰减（每天凌晨 2 点）"""
    print(f"[{datetime.now()}] 开始执行亲密度衰减...")

    async def _decay():
        from app.services.relationship_service import relationship_service

        async with async_session() as db:
            count = await relationship_service.apply_decay(db)
            await db.commit()
            print(f"[{datetime.now()}] 亲密度衰减完成，处理 {count} 条关系")

    run_async(_decay())


@celery_app.task(name="app.services.tasks.cleanup_expired_data")
def cleanup_expired_data():
    """定时清理过期数据（每天凌晨 3 点）"""
    print(f"[{datetime.now()}] 开始清理过期数据...")

    async def _cleanup():
        from app.services.data_retention_service import cleanup_due_deleted_accounts

        async with async_session() as db:
            deleted_accounts = await cleanup_due_deleted_accounts(db)
            await db.commit()
            print(
                f"[{datetime.now()}] 过期数据清理完成，永久删除账号 {deleted_accounts} 个"
            )

    run_async(_cleanup())


# ── 异步任务 ──

@celery_app.task(name="app.services.tasks.extract_memory")
def extract_memory(
    user_id: str,
    character_id: str,
    conversation: list[dict],
    source_message_id: str | None = None,
):
    """异步提取记忆（对话后触发）"""
    print(f"[{datetime.now()}] 开始提取记忆：user={user_id}, character={character_id}")

    async def _extract():
        import uuid
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from app.core.config import settings
        from app.services.memory_service import memory_service

        # 为每个任务创建新的引擎和会话，避免事件循环问题
        engine = create_async_engine(settings.database_url)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_maker() as db:
            try:
                memories = await memory_service.extract_and_store(
                    user_id=uuid.UUID(user_id),
                    character_id=character_id,
                    conversation=conversation,
                    source_message_id=uuid.UUID(source_message_id) if source_message_id else None,
                    db=db,
                )
                print(f"[{datetime.now()}] 记忆提取完成，提取 {len(memories)} 条")
            except Exception as e:
                print(f"[ExtractMemory] 记忆提取失败：{e}")
            finally:
                await engine.dispose()

    run_async(_extract())


@celery_app.task(name="app.services.tasks.backfill_memory_embeddings")
def backfill_memory_embeddings(
    user_id: str | None = None,
    character_id: str | None = None,
    limit: int = 100,
):
    """Backfill pgvector embeddings for existing active memories."""
    print(
        f"[{datetime.now()}] 开始补齐记忆向量 user={user_id}, "
        f"character={character_id}, limit={limit}"
    )

    async def _backfill():
        import uuid
        from app.services.memory_service import memory_service

        async with async_session() as db:
            try:
                updated = await memory_service.backfill_missing_embeddings(
                    db=db,
                    user_id=uuid.UUID(user_id) if user_id else None,
                    character_id=character_id,
                    limit=limit,
                )
                await db.commit()
                print(f"[{datetime.now()}] 记忆向量补齐完成，更新 {updated} 条")
                return updated
            except Exception as e:
                await db.rollback()
                print(f"[BackfillMemoryEmbeddings] 记忆向量补齐失败: {e}")
                raise

    return run_async(_backfill())
