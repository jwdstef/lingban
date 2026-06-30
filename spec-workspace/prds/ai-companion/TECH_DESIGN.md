# 灵伴 AI Companion - 技术架构设计文档

> 版本：v1.1 | 日期：2026-06-29 | 状态：MVP 收敛版

---

## 0. MVP 架构原则

本技术设计以 **App 首发 + 验证主动陪伴闭环** 为核心目标。MVP 不追求一次性完成完整 AI 伴侣平台，而是优先验证：用户是否会因为“长期记忆 + 主动关怀”产生持续留存。

### 0.1 MVP 必须优先打通的闭环

```
注册/登录
  → 选择角色
  → 文本/SSE 流式对话
  → 保存对话
  → 提取基础记忆
  → 到达触发条件
  → 生成主动关怀
  → 推送到手机通知栏
  → 用户点击回到聊天
  → 记录回复率/留存指标
```

### 0.2 架构取舍

- **主动关怀前置到 P0**：它是产品差异化，不是体验增强项。
- **MVP 使用 PostgreSQL + pgvector**：减少一个独立向量库的运维复杂度；Qdrant 作为规模化阶段迁移目标。
- **MVP 先做语音消息 + TTS 回复**：实时 WebRTC 语音通话后置，避免首期研发被音视频实时链路拖慢。
- **推送必须产品化设计**：不只调用第三方 SDK，还要有 token 管理、发送记录、点击回流、免打扰、频控和失败原因。
- **管理后台只做 P0 运营能力**：用户查看、角色配置、主动关怀记录、推送/安全事件排查，其他数据看板后置。

---

## 1. 技术选型总览

| 层 | 选型 | 说明 |
|---|------|------|
| **移动端** | Flutter + Dart | 一套代码 iOS + Android，动画引擎强，适合灵体动效 |
| **状态管理** | Riverpod | 编译时安全，适合中大型项目 |
| **路由** | go_router | Flutter 官方推荐，支持深链接（推送跳转） |
| **实时通信** | SSE / WebSocket | MVP 用 SSE 做 AI 流式输出；WebSocket 用于后续 WebRTC 信令 |
| **语音能力** | 语音消息 + ASR + TTS（MVP）/ WebRTC（Phase 2） | MVP 先支持语音消息和 AI 语音回复；实时语音通话后置 |
| **推送** | Push Gateway + APNs + 极光推送（国内 Android）/ FCM（海外） | 后端统一封装推送通道，支持 token、回执、点击、频控 |
| **后端** | FastAPI + Python | 异步性能好，AI 生态强 |
| **异步任务** | Celery + Redis | 主动关怀定时调度、异步记忆提取 |
| **管理后台** | React + Ant Design Pro | 组件成熟，开箱即用 |
| **主数据库** | PostgreSQL 16 + pgvector | 用户、角色、关系、消息、基础向量记忆统一存储 |
| **缓存** | Redis 7 | 会话缓存、Celery Broker、限流 |
| **向量数据库** | pgvector（MVP）/ Qdrant（规模化） | MVP 减少独立服务；记忆规模变大后迁移 Qdrant |
| **对象存储** | 阿里云 OSS / AWS S3 | 语音消息、图片存储 |
| **AI 模型** | Claude (Anthropic) 主力 / GPT-4o 降级 | 情感智能最高，人格一致性好 |
| **TTS** | Fish Audio | 情绪化语音合成 |
| **ASR** | Whisper 自托管 / 云 ASR 兜底 | 语音消息转写 |
| **容器化** | Docker + Docker Compose | 开发环境统一，生产可迁移至 K8s |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          客户端层                                    │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Flutter App  │  │  管理后台     │  │  推送/语音能力             │  │
│  │ (iOS/Android)│  │  (React)     │  │  Push + Voice Message     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
└─────────┼──────────────────┼──────────────────────┼────────────────┘
          │                  │                      │
          │ HTTPS/SSE        │ HTTPS                │ APNs/厂商推送/HTTPS
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API 网关层                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Nginx / Traefik                                            │    │
│  │  - SSL 终止                                                  │    │
│  │  - 负载均衡                                                  │    │
│  │  - 限流                                                      │    │
│  │  - WebSocket 升级                                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        应用服务层                                    │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │  FastAPI 主服务 │  │ Celery Worker │  │  Celery Beat          │   │
│  │               │  │               │  │                       │   │
│  │ - Auth API    │  │ - 主动关怀任务 │  │ - 定时任务调度         │   │
│  │ - Chat API    │  │ - 记忆提取任务 │  │ - 早安问候             │   │
│  │ - Memory API  │  │ - 推送发送任务 │  │ - 沉默关怀             │   │
│  │ - Character   │  │ - 情绪分析任务 │  │ - 深夜劝睡             │   │
│  │ - Settings    │  │               │  │ - 关系成长检查         │   │
│  │ - Push API    │  │               │  │                       │   │
│  │ - SSE 流式    │  │               │  │                       │   │
│  └───────┬───────┘  └───────┬───────┘  └───────────────────────┘   │
│          │                  │                                       │
└──────────┼──────────────────┼───────────────────────────────────────┘
           │                  │
           ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        数据与中间件层                                 │
│                                                                     │
│  ┌────────────────┐  ┌──────────┐  ┌──────────────────────────┐   │
│  │PostgreSQL      │  │  Redis   │  │  OSS / S3                │   │
│  │+ pgvector      │  │          │  │                          │   │
│  │用户/角色/关系   │  │缓存/会话  │  │语音/图片存储              │   │
│  │消息/记忆/向量   │  │Broker    │  │                          │   │
│  │推送记录/设置    │  │          │  │                          │   │
│  └────────────────┘  └──────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        外部服务层                                    │
│                                                                     │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Claude API   │  │Fish Audio│  │ 推送通道  │  │ 天气/日历 API │   │
│  │ (AI 对话)    │  │  (TTS)   │  │ APNs/极光 │  │              │   │
│  └──────────────┘  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

#### 2.2.1 AI 对话流（SSE 流式）

```
用户输入 → Flutter App
    │
    ├─ POST /api/v1/chat/{characterId}/message
    │
    ▼
FastAPI 接收消息
    │
    ├─ 1. 保存用户消息到 PostgreSQL
    ├─ 2. 查询最近 20 条对话上下文
    ├─ 3. 召回相关长期记忆（MVP: pgvector；规模化: Qdrant）
    ├─ 4. 加载角色人格参数 + 关系等级
    ├─ 5. 组装完整 Prompt（system + memory + history + user）
    │
    ▼
Claude API（流式）
    │
    ├─ SSE 逐 token 返回 → FastAPI → Flutter App（实时渲染）
    │
    ├─ 6. 流结束后保存 AI 回复到 PostgreSQL
    ├─ 7. 异步触发记忆提取任务（Celery）
    ├─ 8. 异步触发情绪分析任务（Celery）
    └─ 9. 异步更新关系亲密度（Celery）
```

#### 2.2.2 主动关怀流（MVP P0）

> 借鉴 OpenClaw 的 Heartbeat 心跳机制，改造为多用户云端版本。

```
Celery Beat（定时触发）
    │
    ├─ 每小时执行一次「主动关怀检查」
    │
    ▼
Celery Worker 执行任务
    │
    ├─ 1. 查询活跃用户列表
    ├─ 2. 对每个用户检查：
    │     - 是否在免打扰时段？
    │     - 距上次互动是否超过阈值？
    │     - 今日主动消息是否超过频控？
    │     - 是否命中时间/沉默/基础情绪触发？
    ├─ 3. 命中触发条件 → 调用 AI 生成角色化关怀消息
    ├─ 4. 写入 proactive_messages，状态为 pending
    ├─ 5. 调用 Push Gateway 选择 APNs/极光/FCM 通道发送
    ├─ 6. 记录发送结果、失败原因、点击回流
    └─ 7. 用户点击通知后打开 /chat/{characterId}
```

#### 2.2.3 记忆提取流

> MVP 借鉴 OpenClaw 的 WAL（Write-Ahead Logging）思想，但先用 PostgreSQL + pgvector 实现基础记忆写入、召回和溯源。自动压缩和独立 Qdrant 迁移放到规模化阶段。

```
对话结束（异步触发）
    │
    ▼
Celery Worker - 记忆提取
    │
    ├─ 1. AI 分析对话内容，提取结构化记忆
    │     - 分类：日常/情绪/偏好/事件/人物/事实
    │     - 重要度评分：1-10
    │     - 情感标签
    ├─ 2. 记忆写入 PostgreSQL
    ├─ 3. 记忆文本向量化（embedding）
    ├─ 4. 向量写入 pgvector 字段
    └─ 5. 记录 source_message_id，支持用户查看和删除
```

---

## 3. 核心模块设计

### 3.1 角色人格引擎

#### 3.1.1 人格参数模型

```json
{
  "character_id": "yinyue",
  "name": "银月",
  "personality": {
    "tsundere": 80,
    "sharp_tongued": 70,
    "gentle": 30,
    "active": 60,
    "mature": 70
  },
  "dialogue_style": {
    "self_reference": "本姑娘",
    "user_reference": ["你", "小子"],
    "catchphrases": ["哼", "别误会了", "才不是担心你呢"],
    "taboo_expressions": ["亲爱的", "么么哒"]
  },
  "system_prompt_template": "..."
}
```

#### 3.1.2 Prompt 组装流程

```
最终 Prompt = 
    角色 System Prompt（人格 + 对话风格 + 禁忌）
  + 关系等级上下文（当前关系阶段 + 里程碑事件）
  + 长期记忆召回（Top-K 相关记忆）
  + 用户情感画像（情绪状态 + 近期趋势）
  + 对话历史（最近 N 轮）
  + 当前用户消息
```

#### 3.1.3 三个预制角色配置

| 参数 | 银月 | 巴巴塔 | 黑皇 |
|------|------|--------|------|
| 傲娇度 | 80 | 10 | 20 |
| 毒舌度 | 70 | 20 | 40 |
| 温柔度 | 30 | 60 | 50 |
| 活跃度 | 60 | 40 | 95 |
| 成熟度 | 70 | 90 | 20 |
| 自称 | 本姑娘 | 本座 | 本皇 |
| 称呼用户 | 你/小子 | 宿主 | 主人/小弟 |

### 3.2 长期记忆系统

> 设计灵感来自 OpenClaw：WAL 架构 + 向量检索 + 自动压缩。核心改造：从单用户本地文件 → 多用户云端数据库。

#### 3.2.1 记忆分类体系

| 分类 | 说明 | 示例 |
|------|------|------|
| `daily` | 日常事件 | "用户今天加班到很晚" |
| `emotion` | 情绪事件 | "用户因为项目进度感到焦虑" |
| `preference` | 用户偏好 | "用户喜欢深夜聊天" |
| `event` | 重要事件 | "用户下周有项目汇报" |
| `person` | 人物关系 | "用户提到了同事小王" |
| `fact` | 事实信息 | "用户住在杭州" |

#### 3.2.2 记忆生命周期

```
对话产生 → AI 提取 → 向量化存储 → 语义召回 → 注入 Prompt
                                ↓
                          定期压缩（旧记忆合并为摘要）
                                ↓
                          过期清理（低重要度 + 长时间未被召回）
```

#### 3.2.3 记忆召回策略

```
召回分数 = 语义相似度 × 0.5
         + 时间衰减 × 0.2        // 越近的记忆权重越高
         + 重要度 × 0.2           // 高重要度记忆优先
         + 召回频率加成 × 0.1     // 曾被成功召回的记忆加分
```

#### 3.2.4 记忆压缩策略

- 当某分类下记忆超过 50 条时，触发压缩
- 使用 AI 将 10 条相似记忆合并为 1 条摘要记忆
- 压缩后保留原始向量 ID 的引用，支持溯源

### 3.3 关系成长引擎

#### 3.3.1 关系阶段

| 等级 | 阶段名 | 亲密度范围 | AI 行为变化 |
|------|--------|-----------|------------|
| 1 | 陌生 | 0-50 | 礼貌、保持距离、试探性话题 |
| 2 | 认识 | 51-150 | 开始记住偏好、偶尔调侃 |
| 3 | 熟悉 | 151-350 | 主动关心、使用专属称呼 |
| 4 | 亲密 | 351-600 | 深度倾诉、分享感受、展现脆弱 |
| 5 | 挚友/家人 | 601-1000 | 完全信任、共同回忆、仪式感互动 |

#### 3.3.2 亲密度增长规则

| 行为 | 亲密度增量 |
|------|-----------|
| 每日首次对话 | +5 |
| 每轮有效对话（>3 次往返） | +2 |
| 深度倾诉（情绪相关话题） | +10 |
| 连续 3 天互动 | +15（连续奖励） |
| 主动回复 AI 消息 | +3 |
| 7 天未互动 | -20（自然衰减） |

#### 3.3.3 关系里程碑

系统在以下节点自动记录里程碑并触发仪式感事件：

- 第一次对话
- 第一次深度倾诉
- 关系等级提升
- 连续互动 7/30/100 天
- 用户生日（AI 主动准备惊喜）

### 3.4 情感计算引擎

#### 3.4.1 情绪识别

每次用户消息通过 AI 分析，提取情绪标签：

```json
{
  "emotion": "焦虑",
  "intensity": 0.7,
  "trigger": "工作压力",
  "coping_style": "倾诉型"
}
```

#### 3.4.2 情绪画像

持续积累用户的情感画像：

```json
{
  "dominant_emotions": ["焦虑", "孤独"],
  "happy_triggers": ["聊宠物", "分享美食"],
  "sad_triggers": ["加班", "周末独处"],
  "recovery_patterns": ["听音乐", "散步"],
  "weekly_trend": {
    "mon": 0.6, "tue": 0.5, "wed": 0.7,
    "thu": 0.4, "fri": 0.8, "sat": 0.3, "sun": 0.4
  }
}
```

#### 3.4.3 情绪响应策略

| 用户情绪 | AI 响应策略 |
|---------|-----------|
| 开心 | 一起开心，追问细节，强化正面情绪 |
| 焦虑 | 先倾听共情，不急于给建议，引导放松 |
| 悲伤 | 陪伴为主，允许沉默，适时安慰 |
| 愤怒 | 站在用户一边，帮助宣泄，等平静后再理性分析 |
| 孤独 | 表达"我在"，主动发起话题，建议社交活动 |

### 3.5 主动关怀引擎

> 借鉴 OpenClaw Heartbeat 机制，改造为多用户云端主动关怀系统。MVP 只做“时间触发 + 沉默触发 + 基础情绪触发”，天气、纪念日和复杂预测后置。

#### 3.5.1 触发器类型

| 触发器 | MVP | 说明 | 示例 |
|--------|-----|------|------|
| 时间触发 | P0 | 基于用户设置的早安/晚安时间 | "早，今天也别硬撑。" |
| 沉默触发 | P0 | 用户长时间未互动 | "好几天没聊了，还好吗？" |
| 基础情绪触发 | P0 | 最近对话出现明显低落/焦虑 | "感觉你这两天有点累。" |
| 事件触发 | P1 | 基于记忆中的事件 | "今天汇报加油。" |
| 天气触发 | P1 | 天气变化提醒 | "明天降温，多穿点。" |
| 纪念日触发 | P2 | 关系里程碑/用户生日 | "我们认识 100 天了！" |

#### 3.5.2 打扰控制

```python
# 打扰控制策略
MAX_PROACTIVE_PER_DAY = 3          # 每天最多 3 次主动消息
MIN_INTERVAL_MINUTES = 120         # 两次主动消息间隔至少 2 小时
DND_START = "23:00"                # 免打扰开始
DND_END = "08:00"                  # 免打扰结束
COOLDOWN_AFTER_USER_BUSY = 240     # 用户未回复后冷却 4 小时
MAX_UNREPLIED_STREAK = 2           # 连续 2 次不回复后降频
```

#### 3.5.3 依赖检测防护

```python
# 反沉迷策略
MAX_DAILY_INTERACTION_MINUTES = 120    # 日均互动超过 2 小时触发
CONSECUTIVE_DAYS_CHECK = 7             # 连续 7 天超标时触发
ACTION = "reduce_proactive_frequency"  # 降低主动关怀频率
SUGGEST_REAL_SOCIAL = True             # AI 建议用户联系真实朋友
```

### 3.6 推送通知系统

#### 3.6.1 推送架构

```
业务服务 → Push Gateway → 选择通道 → APNs / 极光 / FCM
              │
              ├─ token 管理：用户、多设备、平台、是否有效
              ├─ 权限状态：允许/拒绝/未询问/系统关闭
              ├─ 发送记录：pending/sent/failed/clicked
              ├─ 频控检查：免打扰、每日上限、冷却时间
              └─ deep link：lingban://chat/{characterId}
```

Push Gateway 是后端内部模块，不直接暴露第三方推送 SDK 给业务服务。主动关怀、语音消息、系统事件都通过统一接口发送，方便后续替换极光、接厂商通道或做成本/送达率分析。

#### 3.6.2 推送类型

| 类型 | 场景 | 通知栏展示 | 点击行为 |
|------|------|-----------|---------|
| 主动关怀 | AI 主动发消息 | "银月：今天辛苦了，要不要聊聊？" | 打开聊天页 |
| 异步回复 | App 不在前台时 AI 回复完成 | "银月回复了你" | 打开聊天页 |
| 语音消息 | AI 发语音 | "银月发来一条语音" | 打开聊天页并播放 |
| 关系事件 | 等级提升 | "你和银月的关系更近了！" | 打开关系页 |

#### 3.6.3 MVP 推送验收

| 能力 | MVP 要求 |
|------|----------|
| Token 注册 | App 获取推送 token 后调用 `/api/v1/push/tokens` 注册 |
| 多设备 | 同一用户允许多个有效 token |
| 权限状态 | 记录用户是否授权推送，未授权时不触发主动关怀推送 |
| 送达记录 | 每次推送必须生成 delivery 记录，包含通道、状态、失败原因 |
| 点击回流 | 通知点击进入指定角色聊天页，并记录 clicked_at |
| 频控 | 发送前检查免打扰、每日上限、冷却时间 |
| 降级 | 推送失败不重复打扰；只记录失败并进入下一轮调度 |

---

## 4. 数据库设计

### 4.1 核心表结构

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- 用户表
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone           VARCHAR(20) UNIQUE,
    email           VARCHAR(255) UNIQUE,
    nickname        VARCHAR(100) NOT NULL,
    avatar_url      VARCHAR(500) DEFAULT '',
    password_hash   VARCHAR(255) NOT NULL,
    selected_character_id VARCHAR(50),
    emotion_profile JSONB DEFAULT '{}',   -- 情感画像
    settings        JSONB DEFAULT '{}',   -- 用户设置
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 角色表
CREATE TABLE characters (
    id              VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    source          VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    avatar_url      VARCHAR(500) DEFAULT '',
    color           INTEGER DEFAULT 0,
    personality     JSONB NOT NULL,       -- 人格参数
    system_prompt   TEXT NOT NULL,        -- 系统 Prompt
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 用户-角色关系表
CREATE TABLE user_character_relations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    character_id    VARCHAR(50) NOT NULL REFERENCES characters(id),
    level           INTEGER DEFAULT 1,
    label           VARCHAR(50) DEFAULT '陌生',
    intimacy        INTEGER DEFAULT 0,
    milestones      JSONB DEFAULT '[]',   -- 关系里程碑
    first_chat_at   TIMESTAMPTZ,
    last_chat_at    TIMESTAMPTZ,
    consecutive_days INTEGER DEFAULT 0,   -- 连续互动天数
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, character_id)
);

-- 聊天消息表
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    character_id    VARCHAR(50) NOT NULL,
    role            VARCHAR(20) NOT NULL,  -- user / assistant / system
    content         TEXT NOT NULL,
    message_type    VARCHAR(20) DEFAULT 'text',  -- text / voice / image
    media_asset_id  UUID,
    emotion_tags    JSONB DEFAULT '[]',
    is_proactive    BOOLEAN DEFAULT FALSE,
    proactive_message_id UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_chat_messages_user_char ON chat_messages(user_id, character_id, created_at DESC);

-- 记忆表
CREATE TABLE memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    character_id    VARCHAR(50) NOT NULL,
    category        VARCHAR(50) NOT NULL,  -- daily/emotion/preference/event/person/fact
    content         TEXT NOT NULL,
    importance      INTEGER DEFAULT 5,     -- 1-10
    emotion_tags    JSONB DEFAULT '[]',
    source_message_id UUID,
    embedding        VECTOR(1536),          -- MVP: pgvector；规模化后可迁移至 Qdrant
    external_vector_id VARCHAR(100),        -- Phase 2+: Qdrant 向量 ID
    recall_count    INTEGER DEFAULT 0,     -- 被召回次数
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_memories_user_char ON memories(user_id, character_id, is_active, created_at DESC);

-- 媒体资源表（语音消息、图片、TTS 音频）
CREATE TABLE media_assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    asset_type      VARCHAR(20) NOT NULL,  -- voice/image/tts
    storage_url     VARCHAR(1000) NOT NULL,
    mime_type       VARCHAR(100),
    duration_ms     INTEGER,
    transcript      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 主动消息记录表
CREATE TABLE proactive_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    character_id    VARCHAR(50) NOT NULL,
    trigger_type    VARCHAR(50) NOT NULL,  -- time/weather/event/emotion/silence/anniversary
    content         TEXT NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending', -- pending/generated/sent/failed/replied
    trigger_context JSONB DEFAULT '{}',
    replied         BOOLEAN DEFAULT FALSE,
    replied_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 推送 token 表（支持多设备）
CREATE TABLE push_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    platform        VARCHAR(20) NOT NULL,   -- ios/android
    provider        VARCHAR(20) NOT NULL,   -- apns/jpush/fcm
    token           VARCHAR(1000) NOT NULL,
    permission_status VARCHAR(20) DEFAULT 'unknown', -- granted/denied/unknown
    device_id       VARCHAR(100),
    app_version     VARCHAR(50),
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider, token)
);

-- 推送发送记录表
CREATE TABLE push_deliveries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    push_token_id   UUID REFERENCES push_tokens(id),
    proactive_message_id UUID REFERENCES proactive_messages(id),
    provider        VARCHAR(20) NOT NULL,
    notification_type VARCHAR(50) NOT NULL, -- proactive/voice/relation/system
    title           VARCHAR(200) NOT NULL,
    body            TEXT NOT NULL,
    deep_link       VARCHAR(500),
    status          VARCHAR(20) DEFAULT 'pending', -- pending/sent/failed/clicked
    provider_message_id VARCHAR(200),
    failure_reason  TEXT,
    sent_at         TIMESTAMPTZ,
    clicked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 情绪日记表
CREATE TABLE emotion_diary (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    date            DATE NOT NULL,
    dominant_emotion VARCHAR(50),
    intensity       FLOAT,
    triggers        JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);
```

### 4.2 索引优化

```sql
-- 聊天消息查询优化（分页加载历史）
CREATE INDEX idx_chat_history ON chat_messages(user_id, character_id, created_at DESC);

-- 记忆召回优化（按分类+重要度）
CREATE INDEX idx_memories_category ON memories(user_id, character_id, category, importance DESC)
    WHERE is_active = TRUE;

-- 主动消息频率控制
CREATE INDEX idx_proactive_today ON proactive_messages(user_id, created_at)
    WHERE created_at > NOW() - INTERVAL '1 day';

-- 推送 token 查询
CREATE INDEX idx_push_tokens_user_active ON push_tokens(user_id, is_active);

-- 推送送达统计
CREATE INDEX idx_push_deliveries_user_status ON push_deliveries(user_id, status, created_at DESC);
```

---

## 5. API 设计

### 5.1 API 总览

| 模块 | 方法 | 路径 | 优先级 | 说明 |
|------|------|------|--------|------|
| **认证** | POST | `/api/v1/auth/register` | P0 | 注册 |
| | POST | `/api/v1/auth/login` | P0 | 登录 |
| | GET | `/api/v1/auth/me` | P0 | 获取当前用户 |
| **角色** | GET | `/api/v1/characters` | P0 | 角色列表 |
| | GET | `/api/v1/characters/{id}` | P0 | 角色详情 |
| | POST | `/api/v1/characters/select` | P0 | 选择角色 |
| **聊天** | GET | `/api/v1/chat/{characterId}/history` | P0 | 聊天历史 |
| | POST | `/api/v1/chat/{characterId}/message` | P0 | 发送文字消息（SSE 流式返回） |
| | POST | `/api/v1/chat/{characterId}/voice` | P0 | 发送语音消息（上传、ASR、进入对话流） |
| **记忆** | GET | `/api/v1/memory/{characterId}` | P0 | 记忆列表 |
| | DELETE | `/api/v1/memory/{characterId}/{memoryId}` | P0 | 删除记忆 |
| **主动关怀** | GET | `/api/v1/care/messages` | P0 | 主动消息列表 |
| | PUT | `/api/v1/care/frequency` | P0 | 调整主动关怀频率 |
| **推送** | POST | `/api/v1/push/tokens` | P0 | 注册/更新推送 Token |
| | POST | `/api/v1/push/click` | P0 | 记录通知点击回流 |
| **设置** | GET | `/api/v1/settings` | P0 | 获取设置 |
| | PUT | `/api/v1/settings` | P0 | 更新设置 |
| **关系** | GET | `/api/v1/relationship/{characterId}` | P1 | 关系详情 |
| **情绪** | GET | `/api/v1/emotion/diary` | P1 | 情绪日记 |
| | GET | `/api/v1/emotion/trend` | P1 | 情绪趋势 |
| **实时通话** | POST | `/api/v1/call/start` | P2 | 建立 WebRTC 通话 |
| | POST | `/api/v1/call/end` | P2 | 结束通话 |

### 5.2 核心 API 详细设计

#### 发送消息（SSE 流式）

```
POST /api/v1/chat/{characterId}/message
Content-Type: application/json

Request:
{
  "content": "今天好累啊",
  "message_type": "text"
}

Response: text/event-stream
data: 哼
data: ，
data: 又加班了？
data: 本姑娘才不是担心你呢...
data: [DONE]
```

#### 注册推送 Token

```http
POST /api/v1/push/tokens
Content-Type: application/json

{
  "platform": "ios",
  "provider": "apns",
  "token": "...",
  "permission_status": "granted",
  "device_id": "...",
  "app_version": "1.0.0"
}
```

#### 记录通知点击

```http
POST /api/v1/push/click
Content-Type: application/json

{
  "delivery_id": "uuid",
  "deep_link": "lingban://chat/yinyue"
}
```

---

## 6. 移动端架构

### 6.1 目录结构

```
apps/mobile/lib/
├── main.dart                          # 入口
├── src/
│   ├── app.dart                       # App 根组件
│   ├── core/
│   │   ├── constants/                 # 常量配置
│   │   ├── router/                    # go_router 路由配置
│   │   ├── theme/                     # 主题（暗色系、品牌色）
│   │   └── widgets/                   # 通用组件
│   ├── features/                      # 按功能模块组织
│   │   ├── auth/                      # 登录注册
│   │   ├── onboarding/               # 引导页（角色选择）
│   │   ├── home/                     # 首页（灵体展示）
│   │   ├── chat/                     # 聊天页
│   │   │   ├── chat_page.dart        # 页面
│   │   │   ├── chat_provider.dart    # Riverpod 状态
│   │   │   ├── chat_service.dart     # SSE 流式通信
│   │   │   └── widgets/             # 消息气泡、输入框等
│   │   ├── voice/                    # 语音消息（录音、上传、播放 TTS）
│   │   ├── care/                     # 主动关怀消息列表、频率设置
│   │   ├── memory/                   # 记忆管理
│   │   ├── settings/                 # 设置
│   │   └── call/                     # 实时语音通话（Phase 2: WebRTC）
│   └── shared/
│       ├── models/                   # 数据模型
│       ├── providers/                # 全局 Provider
│       └── services/                 # API、Auth、Push、Storage 等
```

### 6.2 状态管理（Riverpod）

```dart
// 聊天状态示例
@riverpod
class ChatController extends _$ChatController {
  @override
  Stream<ChatState> build(String characterId) async* {
    // 加载历史消息
    // 监听 SSE 流式响应
    // 管理消息列表状态
  }
  
  Future<void> sendMessage(String content) async { ... }
  Future<void> loadMore() async { ... }
}
```

### 6.3 推送处理流程

```
手机通知栏收到推送
    │
    ├─ 点击通知 → 记录 /api/v1/push/click → go_router 深链接 → /chat/{characterId}
    │
    ├─ App 在前台 → 直接显示消息
    │
    └─ App 在后台 → 恢复后跳转到聊天页
```

### 6.4 端侧 P0 要求

- API base URL 必须支持环境切换，不能写死 `localhost`。
- 登录 token 必须本地安全存储，并由 Dio 拦截器自动注入。
- 推送权限引导必须可跳过，用户拒绝后不阻断聊天主流程。
- 所有推送 deep link 必须能恢复到指定角色聊天页。
- 语音消息先按“录音 → 上传 OSS → ASR → 文本对话 → 可选 TTS 播放”实现。

---

## 7. 后端服务设计

### 7.1 目录结构

```
services/backend/
├── app/
│   ├── main.py                      # FastAPI 入口
│   ├── core/
│   │   ├── config.py                # 配置管理（pydantic-settings）
│   │   ├── database.py              # SQLAlchemy async 数据库
│   │   ├── security.py              # JWT + bcrypt
│   │   └── deps.py                  # 依赖注入
│   ├── models/                      # SQLAlchemy ORM 模型
│   │   ├── user.py
│   │   ├── character.py
│   │   ├── chat.py
│   │   ├── memory.py
│   │   ├── push.py
│   │   ├── proactive.py
│   │   ├── media.py
│   │   └── relationship.py
│   ├── schemas/                     # Pydantic 请求/响应模型
│   ├── routers/                     # API 路由
│   │   ├── auth.py
│   │   ├── characters.py
│   │   ├── chat.py
│   │   ├── memory.py
│   │   ├── push.py
│   │   ├── care.py
│   │   ├── media.py
│   │   ├── relationship.py
│   │   ├── admin.py
│   │   └── settings.py
│   └── services/                    # 业务逻辑层
│       ├── ai_service.py            # AI 对话（Claude 集成）
│       ├── memory_service.py        # 记忆提取与召回
│       ├── relationship_service.py  # 关系成长计算
│       ├── emotion_service.py       # 情绪分析
│       ├── push_service.py          # Push Gateway
│       ├── proactive_service.py     # 主动关怀调度
│       ├── media_service.py         # 语音/图片/TTS 文件处理
│       └── tasks.py                 # Celery 异步任务
├── tests/
├── alembic/                         # 数据库迁移
├── Dockerfile
├── requirements.txt
└── .env.example
```

### 7.2 AI 对话服务

```python
class AIService:
    """AI 对话服务"""
    
    async def stream_chat(self, character_id, messages, user_id, db):
        # 1. 加载角色人格
        character = await self.get_character(character_id)
        
        # 2. 召回长期记忆
        memories = await memory_service.recall_memories(
            user_id=user_id,
            character_id=character_id,
            query=messages[-1]["content"],
            db=db,
        )
        
        # 3. 加载关系上下文
        relationship = await relationship_service.get(user_id, character_id, db)
        
        # 4. 组装 Prompt
        system_prompt = self.assemble_prompt(
            character=character,
            memories=memories,
            relationship=relationship,
        )
        
        # 5. 流式调用 Claude
        async for chunk in self.client.messages.stream(
            model="claude-sonnet-4-20250514",
            system=system_prompt,
            messages=messages,
        ):
            yield chunk
```

### 7.3 Celery 异步任务

```python
# 主动关怀 - 每小时检查
@celery_app.task
def check_proactive_care():
    """检查并发送主动关怀消息"""
    for user in get_active_users():
        if should_send_proactive(user):
            trigger = determine_trigger(user)
            message = generate_proactive_message(user, trigger)
            proactive_message = save_proactive_message(user, trigger, message)
            push_gateway.send_proactive(user.id, proactive_message.id)

# 记忆提取 - 每次对话后异步执行
@celery_app.task
def extract_memories(user_id, character_id, message_ids):
    """从对话中提取记忆"""
    memories = ai_service.extract_memories(messages)
    for memory in memories:
        save_to_db(memory)
        save_embedding_to_pgvector(memory)

# 情绪分析 - 每次对话后异步执行
@celery_app.task
def analyze_emotion(user_id, character_id, message_id):
    """分析用户情绪并更新画像"""
    emotion = ai_service.detect_emotion(message)
    update_emotion_profile(user_id, emotion)
```

---

## 8. 部署架构

### 8.1 开发环境

```bash
# 一键启动所有基础设施
docker-compose up -d postgres redis

# 启动后端
cd services/backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# 启动 Celery
celery -A app.services.tasks worker --loglevel=info
celery -A app.services.tasks beat

# 启动管理后台
cd apps/admin
npm install && npm run dev

# 启动 Flutter
cd apps/mobile
flutter pub get
flutter run
```

### 8.2 生产环境（初期）

```
┌──────────────────────────────────────────────┐
│              阿里云 / 腾讯云                    │
│                                              │
│  ┌─────────────┐                             │
│  │ ECS 实例     │  2C4G（初期足够）            │
│  │             │                             │
│  │ - Nginx     │  SSL + 反向代理              │
│  │ - FastAPI   │  Uvicorn × 2 workers        │
│  │ - Celery    │  1 worker + 1 beat          │
│  └─────────────┘                             │
│                                              │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ RDS PG      │  │ Redis 云版   │           │
│  │ + pgvector  │  │ (托管)       │           │
│  └─────────────┘  └─────────────┘           │
└──────────────────────────────────────────────┘
```

### 8.3 扩展路径

| 阶段 | 用户量 | 架构调整 |
|------|--------|---------|
| MVP | < 1000 | 单机 ECS + 托管 PG/Redis + pgvector |
| Phase 2 | 1K-10K | ECS 扩容 + 读写分离 + 推送通道优化 |
| Phase 3 | 10K+ | 引入 Qdrant/K8s/消息队列拆分/CDN |

---

## 9. 安全设计

### 9.1 认证与授权

- JWT Token 认证，Token 有效期 24 小时
- 密码 bcrypt 加密存储
- API 限流：单用户 60 次/分钟

### 9.2 数据安全

- 对话内容加密存储
- 用户可随时删除所有数据（GDPR 合规）
- 敏感内容过滤（自残/暴力/违法）

### 9.3 AI 安全

- 角色人格锁定：防止 Prompt 注入导致角色跳出
- 内容安全层：AI 输出经过安全过滤后再返回用户
- 危机干预：检测到自残/自杀倾向时，触发干预流程

```python
# 危机干预流程
if emotion == "crisis" and intensity > 0.9:
    # 1. AI 温和回应，表达关心
    # 2. 提供专业求助热线
    # 3. 记录危机事件
    # 4. 通知运营团队（人工介入）
    crisis_hotlines = {
        "全国": "400-161-9995",
        "北京": "010-82951332",
        "生命热线": "400-821-1215",
    }
```

---

## 10. 借鉴 OpenClaw 的设计清单

| OpenClaw 特性 | 灵伴如何借鉴 | 实现方式 |
|--------------|------------|---------|
| **Heartbeat 心跳** | 主动关怀定时检查 | Celery Beat 每小时触发 |
| **MEMORY.md 持久记忆** | 长期记忆系统 | MVP: PostgreSQL + pgvector；规模化: Qdrant |
| **记忆自动压缩** | 旧记忆合并摘要 | Celery 定期任务，AI 合并相似记忆 |
| **向量语义检索** | 记忆召回 | pgvector + embedding 相似度搜索 |
| **SOUL.md 人格定义** | 角色人格系统 | 数据库 JSON 字段 + Prompt 模板 |
| **模型无关设计** | AI 模型可切换 | 抽象 AIService 接口，支持 Claude/GPT 切换 |
| **Observe-Plan-Act** | 对话编排流程 | 观察上下文 → 规划响应策略 → 生成回复 |
| **本地优先（隐私）** | 用户数据控制 | 用户可查看/删除记忆，完全掌控个人数据 |

---

## 11. MVP 开发优先级

### Phase 1：核心验证（4-6 周）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 用户注册/登录 | 手机号 + 密码 |
| P0 | 角色选择 | 3 个预制角色 |
| P0 | AI 对话（SSE 流式） | 文本聊天 + 角色人格 |
| P0 | Push Gateway | token 注册、权限状态、发送记录、点击回流 |
| P0 | 主动关怀最小闭环 | 时间触发 + 沉默触发 + 频控 + 推送 + 回复率统计 |
| P0 | 长期记忆基础版 | 结构化记忆提取 + pgvector 召回 + 用户可删除 |
| P0 | 语音消息基础版 | 录音上传 + ASR 转写 + 可选 TTS 回复 |
| P1 | 关系成长基础版 | 亲密度 + 等级 + 简单里程碑 |
| P1 | 管理后台 P0 | 用户/角色/记忆/主动关怀/推送记录排查 |

### Phase 2：体验完善

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P1 | 主动关怀增强 | 天气/事件/基础纪念日触发 |
| P1 | 情绪日记 | 情绪追踪 |
| P2 | 记忆管理 | 用户查看/编辑/删除 |
| P2 | 实时语音通话 | WebRTC + 信令 + 通话记录 |

### Phase 3：增长

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P2 | Qdrant 迁移 | 当用户量/记忆量达到阈值后拆分向量检索 |
| P2 | 情感画像增强 | 长期趋势分析 |
| P3 | 角色创建器 | UGC 生态 |
| P3 | 角色市场 | 创作者经济 |
