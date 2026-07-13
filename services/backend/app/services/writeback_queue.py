"""批量延迟回写队列。

聊天完成后把 (user_message, assistant_message) 加到内存缓存，不立刻向量化。
- 当某个 conversation 累积 >= writeback_batch_turns 轮时，触发该会话的 flush
- 后台 ticker 定时巡检，把不活跃的会话强制 flush
- stop(drain=True) 时 flush 所有未持久化轮次（服务退出不丢数据）

好处：每 N 轮才调一次 embedding API（而非每轮 2 次），大幅降低 API 成本。
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WritebackTurn:
    """一轮对话的回写请求。"""
    user_id: str
    character_id: str
    user_text: str
    assistant_text: str


@dataclass
class WritebackStats:
    """运行时指标。"""
    enqueued: int = 0
    written: int = 0
    flushed_batches: int = 0
    dropped: int = 0
    failed: int = 0
    paused: bool = False
    pending_turns: int = 0


@dataclass
class _ConversationBuffer:
    """单个 conversation 的待 flush 缓冲。"""
    turns: list[WritebackTurn] = field(default_factory=list)
    last_enqueue_ts: float = 0.0


class WritebackQueue:
    """批量延迟回写队列。

    使用方式：
        wb = WritebackQueue(session_maker)
        await wb.start()
        await wb.enqueue_turn(turn)
        ...
        await wb.stop(drain=True)
    """

    def __init__(
        self,
        session_maker: async_sessionmaker,
        *,
        batch_turns: int = 8,
        flush_interval_seconds: float = 60.0,
        queue_size: int = 200,
    ):
        self._session_maker = session_maker
        self._batch_turns = batch_turns
        self._flush_interval = flush_interval_seconds
        self._queue_size = queue_size
        self._pending: dict[str, _ConversationBuffer] = {}
        self._lock = asyncio.Lock()
        self._ticker_task: asyncio.Task | None = None
        self._flush_tasks: set[asyncio.Task] = set()
        self._stopping = asyncio.Event()
        self.stats = WritebackStats()

    async def start(self) -> None:
        if self._ticker_task is not None:
            return
        self._stopping.clear()
        self._ticker_task = asyncio.create_task(self._ticker_loop(), name="writeback-ticker")
        logger.info("writeback_queue.started batch_turns=%d flush_interval=%.1fs",
                     self._batch_turns, self._flush_interval)

    async def stop(self, *, drain: bool = True) -> None:
        if self._ticker_task is None:
            return
        self._stopping.set()
        self._ticker_task.cancel()
        try:
            await self._ticker_task
        except asyncio.CancelledError:
            pass
        self._ticker_task = None

        if self._flush_tasks:
            await asyncio.gather(*self._flush_tasks, return_exceptions=True)

        if drain:
            await self.flush_all()
        logger.info("writeback_queue.stopped stats=%s", self.stats)

    async def enqueue_turn(self, turn: WritebackTurn) -> bool:
        """把一轮对话加入待 flush 缓冲。"""
        conv_key = f"{turn.user_id}:{turn.character_id}"

        total = sum(len(b.turns) for b in self._pending.values())
        if total >= self._queue_size:
            self.stats.dropped += 1
            logger.warning("writeback 总缓冲超限（%d 轮），丢弃一轮", total)
            return False

        async with self._lock:
            buf = self._pending.setdefault(conv_key, _ConversationBuffer())
            buf.turns.append(turn)
            buf.last_enqueue_ts = time.monotonic()
            self.stats.enqueued += 1
            self.stats.pending_turns = sum(len(b.turns) for b in self._pending.values())
            should_flush = len(buf.turns) >= self._batch_turns

        if should_flush:
            task = asyncio.create_task(self._flush_conversation(conv_key))
            self._flush_tasks.add(task)
            task.add_done_callback(self._flush_tasks.discard)
        return True

    async def flush_all(self) -> None:
        """强制 flush 所有 pending。"""
        async with self._lock:
            conv_keys = list(self._pending.keys())
        for key in conv_keys:
            await self._flush_conversation(key)

    async def _ticker_loop(self) -> None:
        """周期性巡检，对超过 flush_interval 未活动的会话强制 flush。"""
        interval = max(1.0, self._flush_interval / 4)
        try:
            while not self._stopping.is_set():
                await asyncio.sleep(interval)
                threshold = self._flush_interval
                now = time.monotonic()
                async with self._lock:
                    candidates = [
                        key for key, buf in self._pending.items()
                        if buf.turns and (now - buf.last_enqueue_ts) >= threshold
                    ]
                for key in candidates:
                    await self._flush_conversation(key)
        except asyncio.CancelledError:
            raise

    async def _flush_conversation(self, conv_key: str) -> None:
        """把某个 conversation 的所有 pending 轮次批量持久化。"""
        async with self._lock:
            buf = self._pending.get(conv_key)
            if buf is None or not buf.turns:
                return
            turns = buf.turns
            buf.turns = []
            self.stats.pending_turns = sum(len(b.turns) for b in self._pending.values())

        try:
            written = await self._persist_batch(turns)
            self.stats.flushed_batches += 1
            self.stats.written += written
            logger.info("writeback flushed conv=%s turns=%d", conv_key, written)
        except Exception:
            self.stats.failed += len(turns)
            logger.warning("writeback flush 失败（%s），丢弃 %d 轮",
                          conv_key, len(turns), exc_info=True)

    async def _persist_batch(self, turns: list[WritebackTurn]) -> int:
        """批量向量化 + 写库。

        分层策略：
        - 用户输入：source=user_new（用户近况事实，不参与风格蒸馏）
        - AI 回复：source=ai_generated（仅用于连续性检索）

        中断续跑：
        - content_fingerprint 基于 user/character/source/content 确定性生成
        - 写库前先查已存在指纹，只处理未入库部分
        """
        from app.services.memory_service import content_fingerprint, memory_service

        items: list[tuple[str, str, str, str, WritebackTurn]] = []
        # (text, role, source, fingerprint, turn)
        for t in turns:
            user_text = t.user_text.strip()
            if user_text:
                fp = content_fingerprint(
                    user_id=t.user_id,
                    character_id=t.character_id,
                    source="user_new",
                    content=user_text,
                )
                items.append((user_text, "user", "user_new", fp, t))
            assistant_text = t.assistant_text.strip()
            if assistant_text:
                fp = content_fingerprint(
                    user_id=t.user_id,
                    character_id=t.character_id,
                    source="ai_generated",
                    content=assistant_text,
                )
                items.append((assistant_text, "assistant", "ai_generated", fp, t))

        if not items:
            return 0

        # 按会话分组做 fingerprint 去重
        pending_by_conv: dict[str, list[tuple[str, str, str, str, WritebackTurn]]] = {}
        for item in items:
            turn = item[4]
            conv_key = f"{turn.user_id}:{turn.character_id}"
            pending_by_conv.setdefault(conv_key, []).append(item)

        written = 0
        async with self._session_maker() as db:
            for conv_key, conv_items in pending_by_conv.items():
                user_id, character_id = conv_key.split(":", 1)
                fingerprints = [item[3] for item in conv_items]
                existing = await memory_service.filter_existing_fingerprints(
                    db,
                    user_id=user_id,
                    character_id=character_id,
                    fingerprints=fingerprints,
                )
                pending = [item for item in conv_items if item[3] not in existing]
                if not pending:
                    continue

                texts = [item[0] for item in pending]
                vectors = await self._get_embeddings(texts)
                for i, (text_content, role, source, fingerprint, turn) in enumerate(pending):
                    embedding = vectors[i] if i < len(vectors) else None
                    await self._insert_memory(
                        db,
                        text_content,
                        role,
                        source,
                        embedding,
                        turn,
                        fingerprint=fingerprint,
                    )
                    written += 1

            await db.commit()
        return written

    async def _insert_memory(
        self,
        db: AsyncSession,
        content: str,
        role: str,
        source: str,
        embedding: list[float] | None,
        turn: WritebackTurn,
        *,
        fingerprint: str | None = None,
    ) -> None:
        """插入一条记忆。"""
        memory_id = uuid.uuid4()
        await db.execute(
            text("""
                INSERT INTO memories (id, user_id, character_id, category, content,
                                      importance, emotion_tags, source, content_fingerprint,
                                      is_active, recall_count, created_at, updated_at)
                VALUES (:id, :user_id, :character_id, :category, :content,
                        :importance, :emotion_tags, :source, :content_fingerprint,
                        true, 0, now(), now())
            """),
            {
                "id": str(memory_id),
                "user_id": turn.user_id,
                "character_id": turn.character_id,
                "category": "daily" if role == "user" else "fact",
                "content": content,
                "importance": 5,
                "emotion_tags": "[]",
                "source": source,
                "content_fingerprint": fingerprint,
            },
        )

        if embedding:
            await self._write_embedding(db, memory_id, embedding)

    async def _write_embedding(
        self,
        db: AsyncSession,
        memory_id: uuid.UUID,
        embedding: list[float],
    ) -> None:
        """写入 pgvector embedding。"""
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
        dim = settings.embedding_dimensions
        await db.execute(
            text(f"""
                UPDATE memories
                SET embedding = CAST(:embedding AS vector({dim})),
                    updated_at = now()
                WHERE id = :id
            """),
            {"embedding": vector_str, "id": str(memory_id)},
        )

    async def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """批量获取 embedding。"""
        if not settings.embedding_api_key.strip():
            return [None] * len(texts)

        dim = settings.embedding_dimensions
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.embedding_base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.embedding_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"input": texts, "model": settings.embedding_model},
                )
                response.raise_for_status()
                data = response.json()
                embeddings = [d["embedding"] for d in data.get("data", [])]
                # 截断或补零到目标维度
                result = []
                for emb in embeddings:
                    if len(emb) > dim:
                        emb = emb[:dim]
                    elif len(emb) < dim:
                        emb.extend([0.0] * (dim - len(emb)))
                    result.append(emb)
                return result
        except Exception:
            logger.warning("批量 embedding 失败，使用空向量兜底", exc_info=True)
            return [[] for _ in texts]


# ── 全局单例 ──

_writeback_queue: WritebackQueue | None = None


def get_writeback_queue() -> WritebackQueue | None:
    return _writeback_queue


def init_writeback_queue(session_maker: async_sessionmaker) -> WritebackQueue:
    global _writeback_queue
    _writeback_queue = WritebackQueue(session_maker)
    return _writeback_queue
