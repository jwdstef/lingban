# AI Companion 整改核查报告

日期：2026-07-09

## 审查结论

结论：未完全修改完成。

本次整改已经解决了部分表层问题：移动端删除了旧的硬编码“她正在惦记的事”列表，聊天顶栏和情绪条不再写死“银月/醒着”等文案；后端 embedding API 已配置并实测可返回 4096 维向量，数据库当前 `memories.embedding` 实际类型也是 `vector(4096)`。

但核心体验仍未闭环：已有记忆未向量化，主动关怀生成没有使用真实用户记忆和关系上下文，Fish Audio TTS 当前未配置，新增测试脚本不是自动化验收。

## 变更范围

- `apps/mobile/lib/features/home/home_page.dart`
- `apps/mobile/lib/features/chat/chat_page.dart`
- `services/backend/app/core/config.py`
- `services/backend/app/services/memory_service.py`
- `services/backend/alembic/versions/001_initial_schema.py`
- `services/backend/test_full_flow.py`

## 核查结果

### 已完成

- 原硬编码惦记列表已移除：`周三汇报`、`最近睡得晚`、`想吃火锅`、`和老板的第 5 次改需求` 不再出现在移动端源码中。
- 首页“惦记的事”改为读取记忆接口，并在无数据时隐藏。
- 聊天顶栏固定状态改为读取关系接口后展示关系状态。
- embedding provider 改为 SiliconFlow，模型为 `Qwen/Qwen3-VL-Embedding-8B`，维度为 4096。
- 当前环境实测 embedding API 可用，返回 4096 维向量。
- 当前连接数据库中 `memories.embedding` 实际类型为 `vector(4096)`。
- `flutter analyze` 通过，无静态分析错误。
- 后端相关 Python 文件通过 `py_compile`。

### 未完成或存在风险

#### P1 主动关怀仍没有真实“由头”

`services/backend/app/services/proactive_service.py` 生成主动关怀时传入的是临时随机 `user_id=uuid.uuid4()`，导致 `ai_service.stream_chat()` 无法召回当前用户真实关系和记忆。主动消息能生成，但更像泛化关怀，不是“基于真实事件想起你”。

#### P1 记忆系统尚未端到端证明跑通

当前环境 embedding API 和 schema 可用，但数据库已有 2 条记忆中 0 条有 embedding。聊天接口会派发 Celery `extract_memory.delay(...)`，但本次没有自动化测试证明 worker 正常消费、提取、写入向量、召回。

#### P1 语音体验未完整完成

ASR 服务有 Fish Audio 和 OpenAI 降级路径，但当前环境未配置 Fish Audio API key。TTS 服务必须依赖 Fish Audio API key 和 reference id，当前二者均未配置，因此 AI 语音回复会返回 disabled，PRD 中“高质量语音”仍未验收通过。

#### P2 测试不足

新增 `services/backend/test_full_flow.py` 是手工冒烟脚本，没有断言、没有隔离测试数据、没有 CI 集成，也没有验证 embedding 写入、语义召回、主动关怀真实由头、TTS 音频生成。

#### P2 前端重复请求风险

`apps/mobile/lib/features/chat/chat_page.dart` 在两个 `FutureBuilder` 中直接调用 `_fetchRelation()`，每次 rebuild 都会创建新请求。`apps/mobile/lib/features/home/home_page.dart` 的 `_fetchThinkingItems()` 也未进入既有 Future 缓存机制，可能重复拉取记忆。

#### P2 历史迁移修改方式有发布风险

直接修改 `001_initial_schema.py` 只对新库有效。当前连接库已经是 `vector(4096)`，但若其他环境曾跑过旧的 `vector(1536)` 初始迁移，需要新增 Alembic 升级迁移，而不是只改历史迁移。

## 验证命令

- `python -m py_compile services/backend/app/services/memory_service.py services/backend/app/routers/memory.py services/backend/app/core/config.py services/backend/app/services/voice_service.py services/backend/app/services/tts_service.py`
- `flutter analyze`
- 只读数据库检查：`memories.embedding` 为 `vector(4096)`，当前记忆统计为 0/2 条带 embedding。
- 小样本 embedding 调用：成功返回 4096 维向量。

## 建议

1. 主动关怀生成传入真实 `user.id`，并把触发原因、相关记忆、最近对话摘要写入 prompt，同时在 `ProactiveMessage` 中保存 reason/source memory。
2. 新增 migration：将旧环境的 `vector(1536)` 升级为 `vector(4096)`，并补一个历史记忆 backfill embedding 任务。
3. 把 `test_full_flow.py` 改成带断言的 pytest/e2e 测试，至少断言记忆数量、embedding 非空、语义召回能命中、主动关怀内容带真实上下文。
4. 配置并验证 Fish Audio TTS reference id；或明确 MVP 暂时降级为“语音输入 + 文字回复”，不要在验收中标记高质量语音已完成。
5. 前端缓存新增 Future，避免关系和记忆接口在 rebuild 时重复请求。
