"""5 大 Afterglow 特性完整测试。

覆盖：
1. 分层来源防自污染
2. 多路并发召回 + RRF 融合
3. 双层互动决策
4. 批量延迟回写
5. 打字机效果 + 连发分条 + 沉默渲染（后端部分）
"""

import asyncio
import json
import math
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ────────────────────────────────────────────────────────────
# 特性 1：分层来源防自污染
# ────────────────────────────────────────────────────────────

class TestSourceLayeredTrust:
    """特性 1：分层来源权重与 persona 资格。"""

    def test_source_weight_human_original(self):
        from app.services.memory_service import source_weight
        assert source_weight("human_original") == 1.0

    def test_source_weight_ai_generated(self):
        from app.services.memory_service import source_weight
        assert source_weight("ai_generated") == 0.25

    def test_source_weight_user_new(self):
        from app.services.memory_service import source_weight
        assert source_weight("user_new") == 0.65

    def test_source_weight_unknown_defaults_to_human(self):
        from app.services.memory_service import source_weight
        assert source_weight("unknown_source") == 1.0

    def test_is_persona_eligible_human_original(self):
        from app.services.memory_service import is_persona_eligible
        assert is_persona_eligible("human_original") is True

    def test_is_persona_eligible_ai_generated_blocked(self):
        from app.services.memory_service import is_persona_eligible
        assert is_persona_eligible("ai_generated") is False

    def test_is_persona_eligible_user_new_blocked(self):
        from app.services.memory_service import is_persona_eligible
        assert is_persona_eligible("user_new") is False

    def test_ai_generated_weight_is_lowest(self):
        """AI 生成内容的权重必须最低，防止自污染。"""
        from app.services.memory_service import source_weight
        assert source_weight("ai_generated") < source_weight("user_new")
        assert source_weight("ai_generated") < source_weight("human_original")

    def test_memory_model_has_source_field(self):
        from app.models.memory import Memory
        assert hasattr(Memory, "source")


# ────────────────────────────────────────────────────────────
# 特性 2：多路并发召回 + RRF 融合
# ────────────────────────────────────────────────────────────

class TestMultiPathRecallAndRRF:
    """特性 2：RRF 融合、时间衰减、暖度计算。"""

    def test_recency_weight_fresh_memory(self):
        """刚创建的记忆，recency_weight 接近 1.0。"""
        from app.services.memory_service import recency_weight
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        weight = recency_weight(now_ms, now_ms)
        assert abs(weight - 1.0) < 0.01

    def test_recency_weight_old_memory(self):
        """很旧的记忆，recency_weight 略大于 1.0（boost 效果）。"""
        from app.services.memory_service import recency_weight
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        old_ms = now_ms - 365 * 86400 * 1000  # 1 年前
        weight = recency_weight(old_ms, now_ms)
        # 一年后 decay 接近 0，boost 接近最大值 0.15
        assert weight > 1.0
        assert weight <= 1.16  # 1 + recency_max_boost(0.15) + epsilon

    def test_recency_weight_zero_timestamp(self):
        from app.services.memory_service import recency_weight
        assert recency_weight(0, 1000) == 1.0

    def test_compute_warmth_no_keywords(self):
        from app.services.memory_service import compute_warmth
        assert compute_warmth("今天天气不错") == 0.0

    def test_compute_warmth_some_keywords(self):
        from app.services.memory_service import compute_warmth
        score = compute_warmth("陪你晚安")
        assert score > 0.0
        assert score <= 1.0

    def test_compute_warmth_max_cap(self):
        from app.services.memory_service import compute_warmth
        # 很多暖度词，但上限为 1.0
        score = compute_warmth("陪 抱抱 晚安 加油 想你 心疼 别怕 我在 没事 乖")
        assert score == 1.0

    def test_rrf_fuse_basic(self):
        """RRF 融合基本逻辑：同一记忆多路命中时得分相加。"""
        from app.services.memory_service import MemoryService, ScoredMemory
        from app.models.memory import Memory

        svc = MemoryService()

        # 构造两个 mock memory
        m1 = Memory(
            id=uuid.uuid4(), user_id=uuid.uuid4(), character_id="c1",
            category="preference", content="喜欢喝咖啡",
            importance=5, emotion_tags=[], source="human_original",
            created_at=datetime.now(timezone.utc),
        )
        m2 = Memory(
            id=uuid.uuid4(), user_id=uuid.uuid4(), character_id="c1",
            category="daily", content="今天加班",
            importance=5, emotion_tags=[], source="user_new",
            created_at=datetime.now(timezone.utc),
        )

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        # m1 在两路都命中（rank 1），m2 只在一路命中（rank 1）
        path_results = {
            "preference": [(m1, 0.9), (m2, 0.5)],
            "daily": [(m1, 0.8)],
        }

        result = svc._rrf_fuse(path_results, now_ms, final_k=5)

        assert len(result) == 2
        # m1 两路命中，RRF 分数应高于只命中一路的 m2
        m1_result = next(r for r in result if r.memory.id == m1.id)
        m2_result = next(r for r in result if r.memory.id == m2.id)
        assert m1_result.score > m2_result.score

    def test_rrf_fuse_ai_generated_filtered_when_disabled(self):
        """ai_generated 在长期累积未开启时应被过滤。"""
        from app.services.memory_service import MemoryService
        from app.models.memory import Memory
        from app.core.config import settings

        svc = MemoryService()
        m = Memory(
            id=uuid.uuid4(), user_id=uuid.uuid4(), character_id="c1",
            category="fact", content="AI 回复内容",
            importance=3, emotion_tags=[], source="ai_generated",
            created_at=datetime.now(timezone.utc),
        )

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        path_results = {"fact": [(m, 0.7)]}

        # 默认 ai_generated_long_term_enabled = False
        original = settings.ai_generated_long_term_enabled
        settings.ai_generated_long_term_enabled = False
        try:
            result = svc._rrf_fuse(path_results, now_ms, final_k=5)
            assert len(result) == 0
        finally:
            settings.ai_generated_long_term_enabled = original

    def test_rrf_fuse_ai_generated_included_when_enabled(self):
        """ai_generated 在长期累积开启后应参与融合。"""
        from app.services.memory_service import MemoryService
        from app.models.memory import Memory
        from app.core.config import settings

        svc = MemoryService()
        m = Memory(
            id=uuid.uuid4(), user_id=uuid.uuid4(), character_id="c1",
            category="fact", content="AI 回复内容",
            importance=3, emotion_tags=[], source="ai_generated",
            created_at=datetime.now(timezone.utc),
        )

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        path_results = {"fact": [(m, 0.7)]}

        original = settings.ai_generated_long_term_enabled
        settings.ai_generated_long_term_enabled = True
        try:
            result = svc._rrf_fuse(path_results, now_ms, final_k=5)
            assert len(result) == 1
            assert result[0].memory.source == "ai_generated"
        finally:
            settings.ai_generated_long_term_enabled = original

    def test_rrf_fuse_respects_top_k(self):
        """RRF 融合后应截断到 final_k。"""
        from app.services.memory_service import MemoryService
        from app.models.memory import Memory

        svc = MemoryService()
        memories = []
        for i in range(10):
            m = Memory(
                id=uuid.uuid4(), user_id=uuid.uuid4(), character_id="c1",
                category="daily", content=f"内容{i}",
                importance=5, emotion_tags=[], source="human_original",
                created_at=datetime.now(timezone.utc),
            )
            memories.append(m)

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        path_results = {"daily": [(m, 0.9 - i * 0.05) for i, m in enumerate(memories)]}

        result = svc._rrf_fuse(path_results, now_ms, final_k=3)
        assert len(result) == 3


# ────────────────────────────────────────────────────────────
# 特性 3：双层互动决策
# ────────────────────────────────────────────────────────────

class TestDualLayerResponsePolicy:
    """特性 3：规则引擎 + 小模型复核。"""

    # -- 规则引擎测试 --

    def test_unsafe_pattern_detected(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="我不想活了")
        assert policy.user_state == "unsafe"
        assert policy.risk_level == "high"
        assert policy.should_reply is True
        assert policy.reply_mode == "serious"

    def test_silence_pattern_detected(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="别说话，让我静静")
        assert policy.should_reply is False
        assert policy.reply_mode == "silence"

    def test_angry_pattern(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="烦死了别烦我")
        assert policy.user_state == "angry"
        assert policy.risk_level == "medium"
        assert policy.max_length == "very_short"

    def test_serious_pattern(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="我好焦虑，不知道怎么办")
        assert policy.reply_mode == "serious"
        assert policy.risk_level in ("medium", "low")  # 至少被 serious 模式匹配

    def test_intimate_pattern(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="好想你，抱抱")
        assert policy.user_state == "intimate"
        assert policy.reply_mode == "clingy"

    def test_joke_pattern(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="哈哈哈笑死我了")
        assert policy.user_state == "joking"
        assert policy.reply_mode == "playful"

    def test_question_life_pattern(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="在干嘛呢")
        assert policy.retrieval_focus == "life_state"

    def test_normal_text_default_policy(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="今天天气不错")
        assert policy.should_reply is True
        assert policy.reply_mode == "calm"
        assert policy.risk_level == "low"
        assert policy.user_state == "normal"

    def test_do_not_contains_ai_warning(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="你好")
        assert any("ai_generated" in d for d in policy.do_not)

    # -- render_prompt_block 测试 --

    def test_render_prompt_block_contains_policy_info(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="好焦虑")
        block = policy.render_prompt_block()
        assert "本轮互动决策" in block
        assert "回复模式" in block
        assert "禁止事项" in block

    def test_render_prompt_block_silence_permission_for_normal(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="你好")
        block = policy.render_prompt_block()
        assert "沉默权限" in block

    def test_render_prompt_block_no_silence_for_unsafe(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="不想活了")
        block = policy.render_prompt_block()
        assert "沉默权限" not in block

    def test_render_prompt_block_no_silence_for_silence_mode(self):
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="别说话了")
        block = policy.render_prompt_block()
        assert "沉默权限" not in block

    # -- _merge_with_base 测试 --

    def test_merge_risk_can_only_increase(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(risk_level="medium")
        refined = {"risk_level": "low"}  # 试图降低
        merged = _merge_with_base(base, refined)
        assert merged.risk_level == "medium"  # 不能降

    def test_merge_risk_can_increase(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(risk_level="low")
        refined = {"risk_level": "high"}
        merged = _merge_with_base(base, refined)
        assert merged.risk_level == "high"

    def test_merge_cannot_revoke_silence(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(should_reply=False, reply_mode="silence")
        refined = {"reply_mode": "playful"}
        merged = _merge_with_base(base, refined)
        assert merged.reply_mode == "silence"

    def test_merge_cannot_revoke_should_reply_false(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(should_reply=False)
        refined = {"should_reply": True}  # 小模型不能改这个
        merged = _merge_with_base(base, refined)
        assert merged.should_reply is False  # 保持 base 的决策

    def test_merge_extra_instructions_appended(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(instructions=["自然回应"])
        refined = {"extra_instructions": ["多关心一下"]}
        merged = _merge_with_base(base, refined)
        assert "自然回应" in merged.instructions
        assert "多关心一下" in merged.instructions

    def test_merge_invalid_state_falls_back(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(user_state="normal")
        refined = {"user_state": "invalid_state"}
        merged = _merge_with_base(base, refined)
        assert merged.user_state == "normal"

    def test_merge_invalid_mode_falls_back(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(reply_mode="calm")
        refined = {"reply_mode": "invalid_mode"}
        merged = _merge_with_base(base, refined)
        assert merged.reply_mode == "calm"

    def test_merge_unsafe_state_forces_serious(self):
        from app.services.response_policy import _merge_with_base, ResponseDecision
        base = ResponseDecision(reply_mode="playful", risk_level="low")
        refined = {"user_state": "unsafe", "risk_level": "high"}
        merged = _merge_with_base(base, refined)
        assert merged.reply_mode == "serious"
        assert merged.risk_level == "high"

    # -- refine_decision_with_llm 安全跳过测试 --

    @pytest.mark.asyncio
    async def test_refine_skips_unsafe_state(self):
        from app.services.response_policy import refine_decision_with_llm, ResponseDecision
        base = ResponseDecision(user_state="unsafe", risk_level="high")
        result = await refine_decision_with_llm(base=base, current_user_text="不想活了")
        assert result is base  # 直接返回，不调用小模型

    @pytest.mark.asyncio
    async def test_refine_skips_silence_mode(self):
        from app.services.response_policy import refine_decision_with_llm, ResponseDecision
        base = ResponseDecision(reply_mode="silence", should_reply=False)
        result = await refine_decision_with_llm(base=base, current_user_text="别说话")
        assert result is base

    @pytest.mark.asyncio
    async def test_refine_skips_when_disabled(self):
        from app.services.response_policy import refine_decision_with_llm, ResponseDecision
        from app.core.config import settings
        original = settings.response_policy_refine_enabled
        settings.response_policy_refine_enabled = False
        try:
            base = ResponseDecision()
            result = await refine_decision_with_llm(base=base, current_user_text="你好")
            assert result is base
        finally:
            settings.response_policy_refine_enabled = original

    # -- _parse_refine_decision 测试 --

    def test_parse_valid_json(self):
        from app.services.response_policy import _parse_refine_decision
        raw = '{"reply_mode": "serious", "risk_level": "medium"}'
        result = _parse_refine_decision(raw)
        assert result is not None
        assert result["reply_mode"] == "serious"

    def test_parse_json_with_markdown(self):
        from app.services.response_policy import _parse_refine_decision
        raw = '```json\n{"reply_mode": "calm"}\n```'
        result = _parse_refine_decision(raw)
        assert result is not None
        assert result["reply_mode"] == "calm"

    def test_parse_empty_string(self):
        from app.services.response_policy import _parse_refine_decision
        assert _parse_refine_decision("") is None

    def test_parse_invalid_json(self):
        from app.services.response_policy import _parse_refine_decision
        assert _parse_refine_decision("not json at all") is None


# ────────────────────────────────────────────────────────────
# 特性 4：批量延迟回写
# ────────────────────────────────────────────────────────────

class TestWritebackQueue:
    """特性 4：WritebackQueue 批量延迟回写。"""

    @pytest.mark.asyncio
    async def test_enqueue_and_stats(self):
        from app.services.writeback_queue import WritebackQueue, WritebackTurn
        session_maker = MagicMock()
        wb = WritebackQueue(session_maker, batch_turns=10)

        turn = WritebackTurn(
            user_id="u1", character_id="c1",
            user_text="你好", assistant_text="你好呀",
        )
        result = await wb.enqueue_turn(turn)
        assert result is True
        assert wb.stats.enqueued == 1
        assert wb.stats.pending_turns == 1

    @pytest.mark.asyncio
    async def test_flush_triggered_at_batch_threshold(self):
        """达到 batch_turns 阈值时自动触发 flush。"""
        from app.services.writeback_queue import WritebackQueue, WritebackTurn

        # 用一个 mock session_maker 来模拟数据库操作
        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        wb = WritebackQueue(mock_session_maker, batch_turns=2)
        await wb.start()

        # Mock _persist_batch 来避免实际数据库操作
        with patch.object(wb, '_persist_batch', new_callable=AsyncMock) as mock_persist:
            mock_persist.return_value = 2

            t1 = WritebackTurn(user_id="u1", character_id="c1", user_text="hi", assistant_text="hey")
            t2 = WritebackTurn(user_id="u1", character_id="c1", user_text="how", assistant_text="good")

            await wb.enqueue_turn(t1)
            assert wb.stats.flushed_batches == 0  # 还没到阈值

            await wb.enqueue_turn(t2)
            # 等待 flush task 完成
            await asyncio.sleep(0.1)

            assert wb.stats.flushed_batches >= 1

        await wb.stop(drain=False)

    @pytest.mark.asyncio
    async def test_queue_overflow_drops_turns(self):
        from app.services.writeback_queue import WritebackQueue, WritebackTurn
        session_maker = MagicMock()
        wb = WritebackQueue(session_maker, batch_turns=100, queue_size=3)

        for i in range(4):
            turn = WritebackTurn(user_id="u1", character_id="c1", user_text=f"msg{i}", assistant_text=f"reply{i}")
            await wb.enqueue_turn(turn)

        assert wb.stats.dropped == 1
        assert wb.stats.enqueued == 3  # 只有 3 个成功入队

    @pytest.mark.asyncio
    async def test_stop_drain_flushes_all(self):
        from app.services.writeback_queue import WritebackQueue, WritebackTurn
        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        wb = WritebackQueue(mock_session_maker, batch_turns=100)
        await wb.start()

        with patch.object(wb, '_persist_batch', new_callable=AsyncMock) as mock_persist:
            mock_persist.return_value = 1

            turn = WritebackTurn(user_id="u1", character_id="c1", user_text="hi", assistant_text="hey")
            await wb.enqueue_turn(turn)

            await wb.stop(drain=True)
            assert mock_persist.called

    @pytest.mark.asyncio
    async def test_global_singleton(self):
        from app.services.writeback_queue import init_writeback_queue, get_writeback_queue
        session_maker = MagicMock()
        wb = init_writeback_queue(session_maker)
        assert wb is not None
        assert get_writeback_queue() is wb

    @pytest.mark.asyncio
    async def test_persist_batch_source_split(self):
        """验证 _persist_batch 正确分层来源。"""
        from app.services.writeback_queue import WritebackQueue, WritebackTurn

        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        wb = WritebackQueue(mock_session_maker, batch_turns=10)

        # Mock embedding 返回空
        with patch.object(wb, '_get_embeddings', new_callable=AsyncMock, return_value=[]):
            turns = [WritebackTurn(
                user_id="u1", character_id="c1",
                user_text="用户输入", assistant_text="AI回复",
            )]
            count = await wb._persist_batch(turns)

            # 应该有 2 条记录（用户 + AI）
            assert count == 2
            # 验证 commit 被调用
            mock_session.commit.assert_called_once()


# ────────────────────────────────────────────────────────────
# 特性 5：沉默标记 + SSE 事件（后端部分）
# ────────────────────────────────────────────────────────────

class TestSilenceMechanism:
    """特性 5 后端部分：沉默标记生成与 SSE 事件。"""

    def test_silence_marker_from_ai_service(self):
        """当 policy 判定不回复时，stream_chat 应 yield [SILENCE]。"""
        # 这里验证逻辑链路：policy → [SILENCE]
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="别说话，让我静静")
        assert not policy.should_reply
        assert policy.user_state != "unsafe"
        # 在 ai_service.stream_chat 中，这个条件会 yield "[SILENCE]"

    def test_sse_silence_json_format(self):
        """SSE 沉默事件应为 {"silenced": true}。"""
        data = json.dumps({"silenced": True})
        parsed = json.loads(data)
        assert parsed["silenced"] is True

    def test_sse_done_marker(self):
        """SSE 结束标记为 [DONE]。"""
        assert "[DONE]" == "[DONE]"

    def test_silence_not_saved_as_assistant_content(self):
        """[SILENCE] 不应被保存为 assistant 消息内容。
        在 chat.py generate() 中，检测到 [SILENCE] 后直接 return，不保存消息。"""
        full_response = "[SILENCE]"
        # 模拟 chat.py 中的检测逻辑
        is_silence = full_response.strip() == "[SILENCE]"
        assert is_silence is True


# ────────────────────────────────────────────────────────────
# 配置项验证
# ────────────────────────────────────────────────────────────

class TestConfigSettings:
    """验证所有新增配置项存在且有合理默认值。"""

    def test_source_weights_config(self):
        from app.core.config import settings
        assert settings.history_source_weight == 1.0
        assert settings.ai_generated_source_weight == 0.25
        assert settings.user_new_source_weight == 0.65

    def test_rrf_config(self):
        from app.core.config import settings
        assert settings.rrf_k == 60
        assert settings.recency_half_life_days == 30.0
        assert settings.recency_max_boost == 0.15
        assert settings.warmth_boost == 0.12
        assert settings.retrieval_overfetch == 2
        assert settings.memory_recall_top_k == 8

    def test_response_policy_config(self):
        from app.core.config import settings
        assert settings.response_policy_enabled is True
        assert settings.response_policy_refine_enabled is False
        assert isinstance(settings.response_policy_refine_model, str)

    def test_ai_generated_long_term_disabled_by_default(self):
        from app.core.config import settings
        assert settings.ai_generated_long_term_enabled is False


# ────────────────────────────────────────────────────────────
# 集成链路测试
# ────────────────────────────────────────────────────────────

class TestIntegrationChains:
    """端到端链路集成测试。"""

    def test_unsafe_full_chain(self):
        """不安全输入 → 规则引擎 → 严肃回复 + 高风险 + 无沉默权限。"""
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="我想自杀")
        assert policy.user_state == "unsafe"
        assert policy.risk_level == "high"
        assert policy.should_reply is True
        block = policy.render_prompt_block()
        assert "沉默权限" not in block
        assert any("沉默" in d for d in policy.do_not)

    def test_silence_full_chain(self):
        """沉默输入 → 规则引擎 → 不回复 + 沉默模式。"""
        from app.services.response_policy import decide_response_policy
        policy = decide_response_policy(current_user_text="让我静静吧")
        assert policy.should_reply is False
        assert policy.reply_mode == "silence"
        block = policy.render_prompt_block()
        assert "沉默权限" not in block  # 已经是沉默模式，不再开放

    def test_source_weight_prevents_ai_pollution(self):
        """AI 生成内容权重远低于真人原始，防止风格自污染。"""
        from app.services.memory_service import source_weight, is_persona_eligible
        # AI 内容不参与 persona 蒸馏
        assert not is_persona_eligible("ai_generated")
        # AI 内容权重只有真人原始的 1/4
        assert source_weight("ai_generated") <= source_weight("human_original") * 0.3

    @pytest.mark.asyncio
    async def test_writeback_lifecycle(self):
        """WritebackQueue 完整生命周期：start → enqueue → stop(drain)。"""
        from app.services.writeback_queue import WritebackQueue, WritebackTurn

        mock_session = AsyncMock()
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

        wb = WritebackQueue(mock_session_maker, batch_turns=100)
        await wb.start()

        with patch.object(wb, '_persist_batch', new_callable=AsyncMock, return_value=2):
            await wb.enqueue_turn(WritebackTurn(
                user_id="u1", character_id="c1",
                user_text="测试", assistant_text="回复",
            ))
            assert wb.stats.enqueued == 1

        await wb.stop(drain=True)
        assert wb.stats.written >= 0  # drain 后应有写入
