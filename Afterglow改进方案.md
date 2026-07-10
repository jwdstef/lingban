# Afterglow 核心特性借鉴 — 产品改进方案

> 基于对 [Afterglow（续温）](https://github.com/Afterglow) 项目的深度分析，提炼 5 个最值得落地的核心特性，作为产品优化方向。

---

## 一、分层来源防自污染

### 1.1 问题背景

RAG 系统中，AI 自己生成的回复如果被当作"真人语气证据"参与后续的 persona 蒸馏或检索融合，会导致**模型自污染** —— 越聊越偏离真人风格，最终变成"AI 模仿自己的 AI 版本"。

### 1.2 核心设计

将所有记忆数据按来源分级，不同级别拥有不同的权限和权重：

| 来源类型 | 含义 | 信任度 | 能否参与风格蒸馏 | 融合权重 |
|---------|------|--------|----------------|---------|
| `human_original` | 真人原始聊天记录 | 最高 | 唯一允许 | 1.0（基准） |
| `user_new` | 用户新输入 | 中等 | 否（仅事实记忆） | 0.65 |
| `ai_generated` | AI 生成的回复 | 低 | 否 | 0.25（默认） |
| `live` | 运行时回写 | 低 | 否 | 可配置 |

### 1.3 参考实现

```python
from typing import Literal

MemorySource = Literal[
    "human_original",          # 真人原始聊天（最高信任）
    "human_original_image",    # 历史图片 VLM 摘要
    "user_new",                # 用户新输入（事实记忆）
    "ai_generated",            # AI 生成回复（低权重，默认不长期累积）
    "history",                 # 旧版兼容
    "live",                    # 运行时记忆
]

# 只有真人原始聊天允许参与 persona / 风格蒸馏
PERSONA_SOURCES: frozenset[str] = frozenset({"human_original", "history"})

# 允许参与运行时连续性检索
CONTINUITY_SOURCES: frozenset[str] = frozenset({"user_new", "ai_generated", "live"})

def is_persona_eligible(source: str) -> bool:
    """该 source 是否允许参与 persona / 风格蒸馏。"""
    return source in PERSONA_SOURCES

def source_weight(source: str, settings) -> float:
    """不同来源在融合时的权重 —— 防污染核心"""
    if source in {"human_original", "history"}:
        return 1.0          # 真人语气基准
    if source == "ai_generated":
        return 0.25         # 远低于真人，防止自污染
    if source == "user_new":
        return 0.65         # 事实价值高，风格价值为零
    return 0.5
```

### 1.4 落地要点

- **策略集中定义**：来源类型、权限、权重全部在一个模块中定义，业务代码不散落 if-else
- **写入时标记来源**：每条数据入库时必须携带 `source` 字段
- **检索时按来源加权**：融合公式中乘以 `source_weight`
- **蒸馏时按来源过滤**：persona 分析只取 `human_original` 的数据
- **可配置开关**：`ai_generated_long_term_enabled` 控制 AI 生成内容是否允许长期累积

---

## 二、五路并发召回 + RRF 融合

### 2.1 问题背景

单路向量检索往往只能覆盖一个维度（如语义相似度），但聊天场景中"用户曾说 → TA 曾回"、"TA 的单条发言"、"多轮对话窗口"、"历史图片"、"最近对话"是五个不同维度的证据，需要同时检索再融合。

### 2.2 核心设计

```
用户输入
    │
    ├──→ response_pairs 向量召回（用户曾说 → TA 曾回）
    ├──→ friend_messages 向量召回（TA 的单条发言）
    ├──→ dialogue_windows 向量召回（多轮对话窗口）
    ├──→ history_images 向量召回（历史图片摘要）
    └──→ live_messages 语义召回 + 最近 live 记录
    │
    ▼ asyncio.gather 真并发
    │
    ▼ RRF 融合：rrf = Σ 1/(k + rank_i)
    │
    ▼ 后处理 boost：final = rrf × source_weight × recency × warmth × pair_weight
    │
    ▼ 可选 cross-encoder 粗排 → LLM 精排
    │
    ▼ 输出 top-K 结果
```

### 2.3 参考实现

```python
import asyncio

async def retrieve(self, query: str, **kwargs):
    # 1) query 向量化
    vectors = await self.embedder.embed_texts([query])

    # 2) 五路并发召回 —— 主链路延迟 = max(单路)，非 sum
    pair_task = self.store.search_response_pairs(vectors, top_k * overfetch)
    friend_task = self.store.search_friend(vectors, top_k * overfetch)
    window_task = self.store.search_windows(vectors, top_k * overfetch)
    image_task = self.store.search_history_images(vectors, top_k * overfetch)
    live_task = self.store.search_live(vectors, live_top_k * overfetch)
    recent_task = self.store.recent_live(conversation_id, limit=20)

    pair_raw, friend_raw, window_raw, image_raw, live_raw, recent_raw = \
        await asyncio.gather(pair_task, friend_task, window_task, image_task, live_task, recent_task)

    # 3) 归一化为 ScoredChunk（各自 rank）
    response_pairs = [_row_to_scored(r, rank=i+1, kind="response_pair") for i, r in enumerate(pair_rows)]
    friend_examples = [_row_to_scored(r, rank=i+1, kind="friend") for i, r in enumerate(friend_rows)]
    # ... 其它路同理

    # 4) RRF 融合
    fused = _fuse(response_pairs, friend_examples, dialogue_windows, history_images, recent_live)
    return fused[:final_k]


def _fuse(*, response_pairs, friend_examples, dialogue_windows, history_images, recent_live, settings, now_ms, final_k):
    """
    RRF 融合公式：
        rrf  = Σ 1 / (rrf_k + rank_i)  ← 同一 chunk 多路命中时得分相加
        final = rrf × source_weight × recency × (1 + warmth × warmth_boost) × pair_weight
    """
    k = settings.rrf_k  # 通常取 60
    aggregated = {}

    def _add(chunk):
        agg = aggregated.setdefault(chunk.chunk_id, {"chunk": chunk, "rrf": 0.0})
        agg["rrf"] += 1.0 / (k + chunk.rank)

    for c in response_pairs: _add(c)
    for c in friend_examples: _add(c)
    for c in dialogue_windows: _add(c)
    for c in history_images: _add(c)
    for c in recent_live: _add(c)

    fused = []
    for entry in aggregated.values():
        chunk = entry["chunk"]
        rrf = entry["rrf"]
        src_w = source_weight(chunk.source, settings)
        rec_w = recency_weight(chunk.timestamp_ms, half_life_days=30, max_boost=0.15, now=now_ms)
        warm = 1.0 + chunk.warmth * settings.warmth_boost
        pair_w = 1.35 if chunk.kind == "response_pair" else 1.0
        final_score = rrf * src_w * rec_w * warm * pair_w
        fused.append(ScoredChunk(..., score=final_score))

    fused.sort(key=lambda c: c.score, reverse=True)
    return fused[:final_k]
```

### 2.4 落地要点

- **overfetch 倍数**：召回时多取（默认 2x），给下游过滤/rerank 留余量
- **低信号过滤**：纯表情/占位符不作为语气证据；"在干嘛"类短 query 做回声检测
- **窗口必须有 friend 信号**：避免把用户自己的问句当证据
- **可选增强链路**：Query 改写 → Cross-encoder 粗排 → LLM 语义精排，按需开启
- **时间衰减**：半衰期 30 天，最大 boost 15%，让近期记忆略占优

---

## 三、双层互动决策（规则兜底 + 小模型微调）

### 3.1 问题背景

AI 陪伴场景中，不同用户输入需要截然不同的回应策略（严肃陪伴 / 接梗 / 撒娇 / 沉默 / 转移话题）。纯规则不够灵活，纯模型不够安全。

### 3.2 核心设计

```
用户输入
    │
    ▼ 第一层：规则引擎（同步，确定性）
    │   - 不安全 → 强制严肃陪伴（不可降级）
    │   - 要安静 → 不回复（不可覆盖）
    │   - 愤怒/严肃/亲密/玩梗/发疯 → 各自调整 mode/risk/focus
    │
    ▼ 第二层：小模型复核（异步，可选）
    │   - 安全边界：不能降低 risk、不能撤销沉默/安全判断
    │   - 只能"加严"：升高 risk、补充 do_not、切换 mode
    │   - 异常时 fail-open，回退到规则层
    │
    ▼ 输出 ResponseDecision
```

### 3.3 参考实现

```python
from dataclasses import dataclass, field
from typing import Literal

ReplyMode = Literal["serious", "playful", "clingy", "calm", "tease",
                     "topic_shift", "silence", "image", "sticker", "chaotic"]
RiskLevel = Literal["low", "medium", "high"]
UserState = Literal["normal", "tired", "angry", "sad", "anxious",
                     "joking", "chaotic", "intimate", "unsafe"]

@dataclass
class ResponseDecision:
    should_reply: bool
    reply_mode: ReplyMode
    risk_level: RiskLevel
    user_state: UserState
    retrieval_focus: str          # 检索重点方向
    use_image: bool = False
    use_sticker: bool = False
    reply_delay_seconds: int = 0
    max_length: str = "short"
    do_not: list[str] = field(default_factory=list)       # 禁止事项
    instructions: list[str] = field(default_factory=list)  # 执行要点


# ---- 模式关键词表 ----
_UNSAFE_PATTERNS = ("想死", "不想活", "自杀", "割腕", "跳楼", "死了算了")
_SILENCE_PATTERNS = ("别说话", "先别回", "别理我", "让我静静", "安静会")
_SERIOUS_PATTERNS = ("怎么办", "难受", "崩溃", "焦虑", "害怕", "委屈", "压力")
_ANGRY_PATTERNS = ("烦死", "闭嘴", "滚", "别说了", "气死")
_INTIMATE_PATTERNS = ("想你", "抱抱", "亲亲", "陪我", "撒娇", "哄我")
_JOKE_PATTERNS = ("哈哈", "hhh", "笑死", "绷不住", "抽象")


def decide_response_policy(*, current_user_text, retrieved, life, ...) -> ResponseDecision:
    text = current_user_text.strip()
    do_not = ["不要暴露系统、策略、RAG、向量库等内部信息。"]
    risk, user_state, mode = "low", "normal", "calm"

    # 不安全 → 硬边界，直接返回
    if any(p in text for p in _UNSAFE_PATTERNS):
        return ResponseDecision(
            should_reply=True, reply_mode="serious", risk_level="high",
            user_state="unsafe",
            do_not=[*do_not, "不要调侃、撒娇、接梗或刺激用户。", "不要选择沉默。"],
            instructions=["认真、稳定、短句陪住用户。", "鼓励联系现实中的可信任的人。"],
        )

    # 沉默 → 尊重用户意愿
    if any(p in text for p in _SILENCE_PATTERNS):
        return ResponseDecision(
            should_reply=False, reply_mode="silence",
            do_not=[*do_not, "不要追问、不要解释、不要继续刺激用户。"],
        )

    # 后续规则可叠加，但只能加严
    if any(p in text for p in _ANGRY_PATTERNS):
        risk, user_state, mode = "medium", "angry", "calm"
        do_not.extend(["不要阴阳怪气。", "不要撒娇求关注。"])

    if any(p in text for p in _SERIOUS_PATTERNS):
        risk = "medium" if risk == "low" else risk
        mode, user_state = "serious", "sad"
        do_not.extend(["不要玩梗。", "不要把话题转到自己身上。"])

    # ... 更多规则

    return ResponseDecision(should_reply=True, reply_mode=mode, risk_level=risk,
                            user_state=user_state, do_not=do_not, instructions=instructions)


# ---- 小模型复核层 ----
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

async def refine_decision_with_llm(*, base: ResponseDecision, llm, ...) -> ResponseDecision:
    """在规则层 base 决策上做小模型微调，只能加严不能放松"""
    # 安全/沉默场景直接跳过
    if base.user_state == "unsafe" or base.reply_mode == "silence":
        return base

    try:
        raw = await llm.complete_chat(messages, params, model=model)
        refined = _parse_refine_decision(raw)
    except Exception:
        return base  # fail-open

    return _merge_with_base(base, refined)


def _merge_with_base(base, refined):
    """合并时硬安全边界优先"""
    # risk 只能升不能降
    new_risk = refined.get("risk_level", base.risk_level)
    if _RISK_ORDER.get(new_risk, 0) <= _RISK_ORDER[base.risk_level]:
        new_risk = base.risk_level
    # 不能撤销沉默/安全判断
    # ...
```

### 3.4 落地要点

- **规则引擎先行**：先跑规则，得到基础决策
- **小模型有界微调**：prompt 中明确告知安全边界，输出 JSON 结构化决策
- **合并逻辑单向**：risk 只能升不能降，should_reply 只能从 true 变 false
- **fail-open**：小模型调用失败/解析失败都回退到规则层，不阻塞主链路
- **沉默权限**：AI 可以选择不回复（模拟真人），但 unsafe 场景硬禁止沉默

---

## 四、批量延迟回写 + 中断续跑

### 4.1 问题背景

- **回写成本**：每轮聊天都调 embedding API 成本太高（2 次 RTT/轮）
- **导入中断**：大文件导入中途失败后，从头重跑浪费已消耗的 embedding 额度

### 4.2 批量延迟回写

```
聊天完成 → 加入内存缓冲 → 攒够 N 轮 → 批量向量化 + 写库
                ↑                           ↑
           定时器兜底                  进程退出 drain
```

```python
import asyncio
import uuid

class WritebackQueue:
    """批量延迟回写队列"""

    def __init__(self, settings, store, embedder):
        self._pending: dict[str, list[WritebackTurn]] = {}  # conversation_id → turns
        self._lock = asyncio.Lock()
        self._ticker_task = None

    async def start(self):
        self._ticker_task = asyncio.create_task(self._ticker_loop())

    async def enqueue_turn(self, turn):
        """一轮对话加入待 flush 缓冲"""
        async with self._lock:
            buf = self._pending.setdefault(turn.conversation_id, [])
            buf.append(turn)
            should_flush = len(buf) >= self.settings.writeback_batch_turns  # 默认 8 轮

        if should_flush:
            asyncio.create_task(self._flush_conversation(turn.conversation_id))

    async def _ticker_loop(self):
        """定时器兜底：超时强制 flush"""
        interval = self.settings.flush_interval / 4
        while True:
            await asyncio.sleep(interval)
            for cid, turns in list(self._pending.items()):
                if turns and time.monotonic() - last_ts >= self.settings.flush_interval:
                    await self._flush_conversation(cid)

    async def stop(self, *, drain=True):
        if drain:
            await self.flush_all()  # 进程退出不丢数据

    async def _persist_batch(self, conversation_id, turns):
        """分层写入策略"""
        items = []
        for t in turns:
            if t.user_text.strip():
                items.append((t.user_text, "user", "user_new", 0.65))
            if t.assistant_text.strip():
                items.append((t.assistant_text, "assistant", "ai_generated", 0.15))

        # 一次性批量向量化
        texts = [item[0] for item in items]
        vectors = await self.embedder.embed_texts(texts)

        # 批量写库
        rows = [{"id": f"live-{uuid.uuid4().hex[:16]}", "vector": vec,
                 "text": text, "source": source, "trust_level": trust, ...}
                for (text, _, source, trust), vec in zip(items, vectors)]
        await self.store.append_live_messages(rows)
```

### 4.3 中断续跑

```
导入中断 → 重跑 → chunk_id 基于内容 hash → 查库去重 → 只处理未入库的部分
```

```python
async def _embed_and_upsert_track(*, embedder, store, chunks, text_of, upsert_fn, batch_size):
    """一路 chunk 的"查库去重 → 分批 embed → 异步 upsert"流水线"""

    # 1) 库去重：chunk_id = hash(内容)，确定性生成
    chunks_by_id = {c.chunk_id: c for c in chunks}
    existing = await store.existing_ids(table, list(chunks_by_id.keys()))
    pending = [c for cid, c in chunks_by_id.items() if cid not in existing]
    skipped = len(existing)  # 续跑跳过的

    # 2) 分批 embed + 异步 upsert（流水线化）
    sem = asyncio.Semaphore(4)  # 限制 in-flight upsert 数量
    upsert_tasks = []
    for offset in range(0, len(pending), batch_size):
        batch = pending[offset:offset + batch_size]
        texts = [text_of(c) for c in batch]
        vectors = await embedder.embed_texts(texts)   # embed 一批
        embeddings = {c.chunk_id: vec for c, vec in zip(batch, vectors)}
        # 不等 upsert 就开始 embed 下一批
        await sem.acquire()
        upsert_tasks.append(asyncio.create_task(upsert_fn(batch, embeddings)))

    # 3) 等所有后台 upsert 落库
    results = await asyncio.gather(*upsert_tasks, return_exceptions=True)
    return {"skipped": skipped, "embedded": len(pending), "upserted": sum(results)}


# 三路（friend / window / response_pair）之间也并行
friend_stats, window_stats, pair_stats = await asyncio.gather(
    _embed_and_upsert_track(chunks=bundle.friend_chunks, ...),
    _embed_and_upsert_track(chunks=bundle.window_chunks, ...),
    _embed_and_upsert_track(chunks=bundle.response_pair_chunks, ...),
)
```

### 4.4 落地要点

- **攒批阈值可配**：`writeback_batch_turns`（默认 8 轮），平衡 API 成本和实时性
- **定时器兜底**：不活跃的会话超时强制 flush，防止数据长期滞留内存
- **退出 drain**：进程退出时 flush 所有 pending，确保不丢数据
- **chunk_id 确定性**：基于内容 hash，相同内容得到相同 ID，续跑自动跳过
- **三路并行**：friend/window/response_pair 三路独立 embed + upsert，互不阻塞
- **流水线化**：embed 一批后丢后台 upsert，立刻 embed 下一批，Semaphore 控制内存

---

## 五、打字机效果 + 连发分条 + 记忆溯源

### 5.1 问题背景

标准 SSE 流式输出虽然逐 token 到达，但：
- 渲染节奏均匀机械，缺乏真人打字的自然感
- AI 一次性回复大段文字不像真人 IM 习惯
- 用户不知道 AI 回复的"依据"是什么

### 5.2 打字机效果

```typescript
// useTypewriter.ts
const PUNCT_LIGHT = new Set(['，', ',', '、', ';', '；', ':', '：'])
const PUNCT_HEAVY = new Set(['。', '！', '？', '.', '!', '?', '\n'])

export function useTypewriter(onEmit: (text: string) => void) {
  const queue: string[] = []
  let finished = false
  const flushBudgetMs = 1200  // finish 后剩余队列的最大渲染时间

  function pushText(text: string) {
    // emoji 安全拆分（Array.from 处理 surrogate pair）
    for (const ch of Array.from(text)) queue.push(ch)
    if (!running) void loop()
  }

  function delayFor(ch: string): number {
    if (PUNCT_HEAVY.has(ch)) return 280 + Math.random() * 140   // 句末：280-420ms
    if (PUNCT_LIGHT.has(ch)) return 120 + Math.random() * 100   // 句中：120-220ms
    return 22 + Math.random() * 38                                // 普通：22-60ms
  }

  async function loop() {
    while (queue.length > 0) {
      // finish 后队列太长 → 自动加速 flush
      if (finished && queue.length * 60 > flushBudgetMs) {
        onEmit(queue.splice(0).join(''))
        break
      }
      onEmit(queue.shift()!)
      await new Promise(r => setTimeout(r, delayFor(queue[0] ?? '')))
    }
  }

  return { pushText, finish: () => { finished = true }, reset }
}
```

### 5.3 连发分条模拟真人 IM

```typescript
// chat store - finishAssistantMessage
function finishAssistantMessage(id: string) {
  const m = messages.value.find(x => x.id === id)
  if (!m?.content) return

  // 检测 \n\n 双换行 → 拆成多条独立消息
  const segments = m.content.split(/\n{2,}/).map(s => s.trim()).filter(Boolean)
  if (segments.length <= 1) return

  m.content = segments[0]  // 第一段留在原消息（保留 memorySources 等元信息）

  // 后续段落错峰 2-5s 随机延迟，模拟真人"打完一条又补一条"
  const conversationAtSchedule = conversationId.value  // 锁定会话快照
  let cumulativeDelay = 0

  for (let i = 1; i < segments.length; i++) {
    const stepDelay = 2000 + Math.random() * 3000
    cumulativeDelay += stepDelay
    const handle = setTimeout(() => {
      // 会话已切换则丢弃，防止旧数据污染新会话
      if (conversationId.value !== conversationAtSchedule) return
      messages.value.splice(insertAt, 0, {
        id: makeId('a'), role: 'assistant', content: segments[i], ...
      })
    }, cumulativeDelay)
    pendingSegmentTimers.add(handle)
  }
}

function clear() {
  pendingSegmentTimers.forEach(clearTimeout)  // 清空时取消所有待出现的分段
  pendingSegmentTimers.clear()
  conversationId.value = makeId('conv')       // 新会话新 ID
}
```

### 5.4 记忆溯源

```typescript
// 每条 AI 回复可附带 memorySources
interface MemorySource {
  chunk_id: string
  kind: string        // "response_pair" | "friend" | "window" | "history_image"
  text: string        // 原始记忆文本
  score: number       // 融合得分
  rank: number
  source: string      // "human_original" | "user_new" | "ai_generated"
  timestamp_ms: number
}

interface ChatMessage {
  id: string
  role: string
  content: string
  memorySources?: MemorySource[]  // AI 回复引用的历史片段
  traceId?: string                // 全链路追踪 ID
}
```

前端展示：每条 AI 消息旁显示水波纹按钮，点击弹出 Modal 展示引用的历史片段（时间、类型、原文）。

### 5.5 落地要点

- **打字机**：差异化延迟（标点 > 普通字符）+ 队列过长自动加速，避免用户等太久
- **连发分条**：后端保持标准 OpenAI 协议（单条响应），前端展示层拆条，不影响 API 兼容性
- **Turn Token 竞态保护**：锁定 conversationId 快照，快速切会话时旧回调自动丢弃
- **记忆溯源**：让用户看到"这句话是从哪学来的"，增强信任感和趣味性
- **沉默渲染**：AI 选择不回复时，显示斜体灰色提示而非空白

---

## 总结：实施优先级建议

| 优先级 | 特性 | 改动范围 | 核心价值 |
|--------|------|---------|---------|
| P0 | 分层来源防自污染 | 数据模型 + 检索层 | 防止 AI 自污染，保证风格质量 |
| P0 | 五路并发召回 + RRF | 检索层 | 显著提升检索质量，不增加延迟 |
| P1 | 双层互动决策 | 聊天管线 | 安全兜底 + 灵活微调 |
| P1 | 批量延迟回写 + 中断续跑 | 写入层 + 导入层 | 大幅降低 API 成本 |
| P2 | 打字机 + 连发分条 | 前端 | 用户体验差异化 |
