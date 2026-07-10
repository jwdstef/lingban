"""记忆管理服务 - 多路并发召回 + RRF 融合 + 分层来源防自污染

核心设计：
- 分层来源：human_original / user_new / ai_generated，不同权重参与融合
- 多路召回：按 category 分路并发检索，RRF 融合
- RRF 公式：rrf = Σ 1/(k + rank_i)，配合 source_weight × recency × warmth
"""

import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone

import httpx
from openai import AsyncOpenAI
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.memory import Memory
from app.models.user import User

logger = logging.getLogger(__name__)


# ── 来源策略（分层防自污染）──

# 只有真人原始聊天允许参与 persona / 风格蒸馏
PERSONA_SOURCES = frozenset({"human_original"})

# 允许参与运行时连续性检索
CONTINUITY_SOURCES = frozenset({"user_new", "ai_generated", "human_original"})


def is_persona_eligible(source: str) -> bool:
    """该 source 是否允许参与 persona / 风格蒸馏。"""
    return source in PERSONA_SOURCES


def source_weight(source: str) -> float:
    """不同来源在融合时的权重 —— 防污染核心。"""
    if source in {"human_original"}:
        return settings.history_source_weight
    if source == "ai_generated":
        return settings.ai_generated_source_weight
    if source == "user_new":
        return settings.user_new_source_weight
    return settings.history_source_weight


def recency_weight(timestamp_ms: int, now_ms: int) -> float:
    """时间衰减权重：半衰期 recency_half_life_days，最大 boost recency_max_boost。"""
    if timestamp_ms <= 0 or now_ms <= 0:
        return 1.0
    age_days = max(0, (now_ms - timestamp_ms) / (1000 * 86400))
    half_life = settings.recency_half_life_days
    if half_life <= 0:
        return 1.0
    decay = math.pow(0.5, age_days / half_life)
    boost = 1.0 + (1.0 - decay) * settings.recency_max_boost
    return boost


# ── 暖度词检测 ──

_WARMTH_KEYWORDS = (
    "陪", "抱抱", "晚安", "加油", "想你", "心疼", "别怕", "我在",
    "没事", "乖", "暖", "甜", "可爱", "幸福", "开心",
)


def compute_warmth(text_content: str) -> float:
    """基于关键词启发式计算暖度评分（0-1）。"""
    hits = sum(1 for kw in _WARMTH_KEYWORDS if kw in text_content)
    return min(1.0, hits / 4.0)


# ── 数据结构 ──

class ScoredMemory:
    """带分数的记忆结果。"""

    def __init__(
        self,
        memory: Memory,
        score: float,
        rank: int,
        kind: str,
        similarity: float = 0.0,
    ):
        self.memory = memory
        self.score = score
        self.rank = rank
        self.kind = kind  # "preference" / "emotion" / "daily" / "fact" / "event" / "person"
        self.similarity = similarity


class MemoryService:
    """记忆管理服务 - 多路并发召回 + RRF 融合"""

    def __init__(self):
        self._openai = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._embedding_dim = settings.embedding_dimensions

    async def extract_and_store(
        self,
        user_id: uuid.UUID,
        character_id: str,
        conversation: list[dict],
        source_message_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> list[Memory]:
        """从对话中提取记忆并存储（带来源标记）。"""
        if not await self._memory_enabled(user_id, db):
            return []

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
                source="human_original",  # AI 提取的记忆标记为真人原始
                recall_count=0,
                is_active=True,
            )
            db.add(memory)
            await db.flush()

            if embedding:
                await self._write_embedding(db, memory.id, embedding)

            memories.append(memory)

        await db.commit()
        return memories

    async def store_chat_turn(
        self,
        user_id: uuid.UUID,
        character_id: str,
        user_text: str,
        assistant_text: str,
        db: AsyncSession,
    ) -> int:
        """存储一轮对话（分层来源标记）。

        - 用户输入：source=user_new
        - AI 回复：source=ai_generated
        """
        count = 0

        # 用户输入
        if user_text.strip():
            user_embedding = await self._get_embedding(user_text)
            user_memory = Memory(
                user_id=user_id,
                character_id=character_id,
                category="daily",
                content=user_text.strip(),
                importance=5,
                emotion_tags=[],
                source="user_new",
                recall_count=0,
                is_active=True,
            )
            db.add(user_memory)
            await db.flush()
            if user_embedding:
                await self._write_embedding(db, user_memory.id, user_embedding)
            count += 1

        # AI 回复
        if assistant_text.strip():
            ai_embedding = await self._get_embedding(assistant_text)
            ai_memory = Memory(
                user_id=user_id,
                character_id=character_id,
                category="fact",
                content=assistant_text.strip(),
                importance=3,
                emotion_tags=[],
                source="ai_generated",
                recall_count=0,
                is_active=True,
            )
            db.add(ai_memory)
            await db.flush()
            if ai_embedding:
                await self._write_embedding(db, ai_memory.id, ai_embedding)
            count += 1

        await db.commit()
        return count

    # ── 多路并发召回 + RRF 融合 ──

    async def recall_memories_hybrid(
        self,
        user_id: uuid.UUID,
        character_id: str,
        query: str,
        db: AsyncSession,
        top_k: int | None = None,
    ) -> list[ScoredMemory]:
        """多路并发召回 + RRF 融合。

        按 category 分路检索：
        - preference 路（用户偏好）
        - emotion 路（情绪记忆）
        - daily 路（日常事实）
        - fact/event/person 路（其他事实）

        每路独立 rank，然后 RRF 融合，配合 source_weight × recency × warmth。
        """
        final_k = top_k or settings.memory_recall_top_k
        overfetch = max(1, settings.retrieval_overfetch)
        per_path_k = final_k * overfetch

        # 获取查询向量
        query_embedding = await self._get_embedding(query)
        if not query_embedding:
            return await self._recall_fallback(user_id, character_id, db, final_k)

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        # 多路并发召回
        tasks = {
            "preference": self._search_by_category(
                user_id, character_id, query_embedding, db, "preference", per_path_k
            ),
            "emotion": self._search_by_category(
                user_id, character_id, query_embedding, db, "emotion", per_path_k
            ),
            "daily": self._search_by_category(
                user_id, character_id, query_embedding, db, "daily", per_path_k
            ),
            "fact_event_person": self._search_by_categories(
                user_id, character_id, query_embedding, db,
                ["fact", "event", "person"], per_path_k
            ),
        }

        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True,
        )

        # 收集各路结果
        path_results: dict[str, list[tuple[Memory, float]]] = {}
        for path_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("recall path %s failed: %s", path_name, result)
                path_results[path_name] = []
            else:
                path_results[path_name] = result

        # RRF 融合
        return self._rrf_fuse(path_results, now_ms, final_k)

    async def _search_by_category(
        self,
        user_id: uuid.UUID,
        character_id: str,
        query_embedding: list[float],
        db: AsyncSession,
        category: str,
        top_k: int,
    ) -> list[tuple[Memory, float]]:
        """按单个 category 做向量检索。"""
        return await self._vector_search(
            user_id, character_id, query_embedding, db, top_k,
            extra_where="AND category = :category",
            params={"category": category},
        )

    async def _search_by_categories(
        self,
        user_id: uuid.UUID,
        character_id: str,
        query_embedding: list[float],
        db: AsyncSession,
        categories: list[str],
        top_k: int,
    ) -> list[tuple[Memory, float]]:
        """按多个 category 做向量检索。"""
        cat_list = ", ".join(f"'{c}'" for c in categories)
        return await self._vector_search(
            user_id, character_id, query_embedding, db, top_k,
            extra_where=f"AND category IN ({cat_list})",
            params={},
        )

    async def _vector_search(
        self,
        user_id: uuid.UUID,
        character_id: str,
        query_embedding: list[float],
        db: AsyncSession,
        top_k: int,
        *,
        extra_where: str = "",
        params: dict | None = None,
    ) -> list[tuple[Memory, float]]:
        """pgvector 向量检索。"""
        dim = self._embedding_dim
        base_sql = f"""
            SELECT id, user_id, character_id, category, content, importance,
                   emotion_tags, source_message_id, source, recall_count, is_active,
                   created_at, updated_at,
                   1 - (embedding <=> CAST(:query_embedding AS vector({dim}))) AS similarity
            FROM memories
            WHERE user_id = :user_id
              AND character_id = :character_id
              AND is_active = true
              AND embedding IS NOT NULL
              {extra_where}
            ORDER BY embedding <=> CAST(:query_embedding AS vector({dim}))
            LIMIT :top_k
        """
        query_params = {
            "query_embedding": self._format_vector(query_embedding),
            "user_id": str(user_id),
            "character_id": character_id,
            "top_k": top_k,
        }
        if params:
            query_params.update(params)

        result = await db.execute(text(base_sql), query_params)
        rows = result.fetchall()

        memories = []
        for row in rows:
            m = Memory(
                id=row[0], user_id=row[1], character_id=row[2],
                category=row[3], content=row[4], importance=row[5],
                emotion_tags=row[6], source_message_id=row[7],
                source=row[8] if len(row) > 8 else "human_original",
                recall_count=row[9] if len(row) > 9 else 0,
                is_active=row[10] if len(row) > 10 else True,
                created_at=row[11], updated_at=row[12],
            )
            similarity = float(row[13]) if len(row) > 13 else 0.0
            memories.append((m, similarity))

        return memories

    def _rrf_fuse(
        self,
        path_results: dict[str, list[tuple[Memory, float]]],
        now_ms: int,
        final_k: int,
    ) -> list[ScoredMemory]:
        """RRF 融合多路结果。

        公式：
            rrf = Σ 1/(k + rank_i)  ← 同一 memory 多路命中时得分相加
            final = rrf × source_weight × recency × (1 + warmth × warmth_boost)
        """
        k = settings.rrf_k
        aggregated: dict[str, dict] = {}

        for path_name, results in path_results.items():
            for rank, (memory, similarity) in enumerate(results, 1):
                mid = str(memory.id)
                if mid not in aggregated:
                    aggregated[mid] = {
                        "memory": memory,
                        "rrf": 0.0,
                        "ranks": [],
                        "kinds": set(),
                        "best_similarity": 0.0,
                    }
                agg = aggregated[mid]
                agg["rrf"] += 1.0 / (k + rank)
                agg["ranks"].append(rank)
                agg["kinds"].add(memory.category)
                agg["best_similarity"] = max(agg["best_similarity"], similarity)

        # 计算最终分数
        fused: list[ScoredMemory] = []
        for entry in aggregated.values():
            memory: Memory = entry["memory"]
            rrf = entry["rrf"]

            # source weight（防自污染核心）
            src = getattr(memory, "source", "human_original") or "human_original"
            src_w = source_weight(src)

            # 如果 ai_generated 长期累积未开启，跳过
            if src == "ai_generated" and not settings.ai_generated_long_term_enabled:
                continue

            # recency
            created_ts = int(memory.created_at.timestamp() * 1000) if memory.created_at else 0
            rec_w = recency_weight(created_ts, now_ms)

            # warmth
            warmth = compute_warmth(memory.content)
            warm_factor = 1.0 + warmth * settings.warmth_boost

            # 最终分数
            final_score = rrf * src_w * rec_w * warm_factor

            kind = sorted(entry["kinds"])[0] if entry["kinds"] else "unknown"
            fused.append(ScoredMemory(
                memory=memory,
                score=final_score,
                rank=0,
                kind=kind,
                similarity=entry["best_similarity"],
            ))

        # 按分数降序排列
        fused.sort(key=lambda x: x.score, reverse=True)

        # 重新分配 rank
        result = fused[:final_k]
        for i, sm in enumerate(result):
            sm.rank = i + 1

        return result

    async def _recall_fallback(
        self,
        user_id: uuid.UUID,
        character_id: str,
        db: AsyncSession,
        top_k: int,
    ) -> list[ScoredMemory]:
        """Fallback: 按重要度+时间召回（无 embedding 时）。"""
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
        memories = list(result.scalars().all())
        return [
            ScoredMemory(memory=m, score=float(m.importance), rank=i + 1, kind=m.category)
            for i, m in enumerate(memories)
        ]

    # ── 兼容旧接口 ──

    async def recall_memories(
        self,
        user_id: uuid.UUID,
        character_id: str,
        query: str,
        db: AsyncSession,
        top_k: int = 5,
    ) -> list[Memory]:
        """语义召回记忆（兼容旧接口，内部使用混合召回）。"""
        scored = await self.recall_memories_hybrid(
            user_id, character_id, query, db, top_k
        )
        # 更新召回计数
        memory_ids = [str(sm.memory.id) for sm in scored]
        if memory_ids:
            await db.execute(
                update(Memory)
                .where(Memory.id.in_(memory_ids))
                .values(recall_count=Memory.recall_count + 1)
            )
            await db.commit()
        return [sm.memory for sm in scored]

    # ── 工具方法 ──

    async def _memory_enabled(self, user_id: uuid.UUID, db: AsyncSession) -> bool:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        return (user.settings or {}).get("memory_enabled", True) is not False

    async def backfill_missing_embeddings(
        self,
        db: AsyncSession,
        user_id: uuid.UUID | None = None,
        character_id: str | None = None,
        limit: int = 100,
    ) -> int:
        """Fill embeddings for active memories that were created before embedding was configured."""
        where_clauses = [
            Memory.is_active == True,
            Memory.embedding.is_(None),
        ]
        if user_id:
            where_clauses.append(Memory.user_id == user_id)
        if character_id:
            where_clauses.append(Memory.character_id == character_id)

        result = await db.execute(
            select(Memory.id, Memory.content)
            .where(*where_clauses)
            .order_by(Memory.created_at.asc())
            .limit(limit)
        )

        updated = 0
        for memory_id, content in result.all():
            embedding = await self._get_embedding(content)
            if not embedding:
                continue
            await self._write_embedding(db, memory_id, embedding)
            updated += 1

        if updated:
            await db.flush()
        return updated

    async def _extract_memories_with_ai(
        self, conversation: list[dict]
    ) -> list[dict]:
        """用 AI 从对话中提取结构化记忆"""
        user_messages = [m["content"] for m in conversation if m["role"] == "user"]
        if not user_messages:
            return []

        user_text = "\n".join(user_messages)

        if not settings.openai_api_key.strip():
            return self._extract_memories_locally(user_messages)

        try:
            response = await self._openai.chat.completions.create(
                model=settings.openai_chat_model,
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
            if not settings.embedding_api_key.strip():
                return None

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.embedding_base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.embedding_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": text,
                        "model": settings.embedding_model,
                    },
                )
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                if len(embedding) > self._embedding_dim:
                    embedding = embedding[: self._embedding_dim]
                elif len(embedding) < self._embedding_dim:
                    embedding.extend([0.0] * (self._embedding_dim - len(embedding)))
                return embedding
        except Exception:
            return None

    def _format_vector(self, vector: list[float]) -> str:
        return "[" + ",".join(str(v) for v in vector) + "]"

    async def _write_embedding(
        self,
        db: AsyncSession,
        memory_id: uuid.UUID,
        embedding: list[float],
    ) -> None:
        await db.execute(
            text(f"""
                UPDATE memories
                SET embedding = CAST(:embedding AS vector({self._embedding_dim})),
                    updated_at = now()
                WHERE id = :id
            """),
            {"embedding": self._format_vector(embedding), "id": str(memory_id)},
        )

    def _extract_memories_locally(self, user_messages: list[str]) -> list[dict]:
        """Rule-based memory extraction for local development without OpenAI."""
        memories = []
        for text_value in user_messages[-3:]:
            content = text_value.strip()
            if len(content) < 4:
                continue

            category = "daily"
            importance = 5
            emotion_tags: list[str] = []

            if any(word in content for word in ("压力", "焦虑", "难过", "累", "崩溃", "孤独")):
                category = "emotion"
                importance = 7
                if "压力" in content:
                    emotion_tags.append("压力")
                if "焦虑" in content:
                    emotion_tags.append("焦虑")
                if "累" in content:
                    emotion_tags.append("疲惫")
            elif any(word in content for word in ("喜欢", "讨厌", "想吃", "偏好")):
                category = "preference"
                importance = 6
            elif any(word in content for word in ("朋友", "同事", "妈妈", "爸爸", "家人")):
                category = "person"
                importance = 6

            memories.append({
                "category": category,
                "content": f"用户提到：{content}",
                "importance": importance,
                "emotion_tags": emotion_tags,
            })

        return memories


# 单例
memory_service = MemoryService()
