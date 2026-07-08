"""聊天接口 - SSE 流式对话 + 历史记录"""

import base64
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.chat import ChatMessage
from app.models.user import User
from app.services.ai_service import ai_service
from app.services.emotion_service import detect_emotion_signal, record_emotion_from_text
from app.services.memory_service import memory_service
from app.services.relationship_service import relationship_service
from app.services.safety_service import create_event_for_message
from app.services.subscription_service import SubscriptionLimitError, subscription_service
from app.services.tasks import extract_memory
from app.services.tts_service import TTSGenerationError, tts_service
from app.services.voice_service import VoiceTranscriptionError, voice_service

router = APIRouter()


# ── Schemas ──

class SendMessageRequest(BaseModel):
    content: str
    message_type: str = "text"  # text / voice


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    message_type: str
    is_proactive: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    has_more: bool
    total: int


class VoiceMessageResponse(BaseModel):
    transcript: str
    reply: str
    user_message_id: str
    assistant_message_id: str
    tts_status: str = "not_requested"
    tts_audio_base64: str | None = None
    tts_content_type: str | None = None
    tts_format: str | None = None


# ── 聊天历史 ──

@router.get("/{character_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    character_id: str,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天历史（按时间正序返回）"""
    query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.character_id == character_id)
        .order_by(ChatMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    count_query = (
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.character_id == character_id)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                message_type=m.message_type,
                is_proactive=m.is_proactive,
                created_at=m.created_at,
            )
            for m in reversed(messages)
        ],
        has_more=offset + limit < total,
        total=total,
    )


# ── SSE 流式对话 ──

@router.post("/{character_id}/message")
async def send_message(
    character_id: str,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息并获取 AI 回复（SSE 流式）"""
    try:
        await subscription_service.ensure_chat_quota(user=user, db=db)
    except SubscriptionLimitError as exc:
        raise _subscription_limit_http_error(exc) from exc

    # 1. 保存用户消息
    user_msg = ChatMessage(
        user_id=user.id,
        character_id=character_id,
        role="user",
        content=data.content,
        message_type=data.message_type,
    )
    db.add(user_msg)
    await db.flush()
    await create_event_for_message(db, user_msg)
    user_msg_id = user_msg.id

    # 2. 获取最近 20 条对话上下文
    recent_query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.character_id == character_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    result = await db.execute(recent_query)
    recent_messages = list(reversed(result.scalars().all()))

    # 构建 Claude messages 格式
    claude_messages = [
        {"role": m.role, "content": m.content}
        for m in recent_messages
    ]

    # 3. SSE 流式生成
    async def generate():
        full_response = ""
        msg_count = len([m for m in recent_messages if m.role == "user"])

        async for chunk in ai_service.stream_chat(
            character_id=character_id,
            user_id=user.id,
            messages=claude_messages,
            db=db,
        ):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # 4. 保存 AI 回复
        ai_msg = ChatMessage(
            user_id=user.id,
            character_id=character_id,
            role="assistant",
            content=full_response,
        )
        db.add(ai_msg)
        await db.flush()

        # 5. Update relationship and emotion diary.
        has_emotion = _detect_emotion(data.content)
        if has_emotion:
            await record_emotion_from_text(
                user_id=user.id,
                text=data.content,
                db=db,
            )
        await relationship_service.on_chat(
            user_id=user.id,
            character_id=character_id,
            message_count=msg_count,
            has_emotion=has_emotion,
            db=db,
        )

        await db.commit()

        # 6. 异步触发记忆提取
        extract_memory.delay(
            str(user.id),
            character_id,
            [{"role": "user", "content": data.content}, {"role": "assistant", "content": full_response}],
            str(user_msg_id),
        )

        # 7. 发送消息 ID + 完成信号
        yield f"data: {json.dumps({'message_id': str(ai_msg.id)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 不缓冲
        },
    )


# ── 删除消息 ──

@router.post("/{character_id}/voice", response_model=VoiceMessageResponse)
async def send_voice_message(
    character_id: str,
    audio: UploadFile = File(...),
    transcript: str | None = Form(default=None),
    include_tts: bool = Form(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a voice message, transcribe it, and process it through chat."""
    try:
        await subscription_service.ensure_chat_quota(user=user, db=db)
    except SubscriptionLimitError as exc:
        raise _subscription_limit_http_error(exc) from exc

    audio_bytes = await audio.read()
    try:
        transcript_text = await voice_service.transcribe(
            audio_bytes=audio_bytes,
            filename=audio.filename or "voice.webm",
            content_type=audio.content_type,
            transcript_fallback=transcript,
        )
    except VoiceTranscriptionError as exc:
        detail = str(exc)
        status_code = 400 if "empty" in detail.lower() or "large" in detail.lower() else 503
        raise HTTPException(status_code=status_code, detail=detail) from exc

    user_msg = ChatMessage(
        user_id=user.id,
        character_id=character_id,
        role="user",
        content=transcript_text,
        message_type="voice",
    )
    db.add(user_msg)
    await db.flush()
    await create_event_for_message(db, user_msg)
    user_msg_id = user_msg.id

    recent_query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.character_id == character_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    result = await db.execute(recent_query)
    recent_messages = list(reversed(result.scalars().all()))
    claude_messages = [
        {"role": m.role, "content": m.content}
        for m in recent_messages
    ]
    msg_count = len([m for m in recent_messages if m.role == "user"])

    full_response = ""
    async for chunk in ai_service.stream_chat(
        character_id=character_id,
        user_id=user.id,
        messages=claude_messages,
        db=db,
    ):
        full_response += chunk

    ai_msg = ChatMessage(
        user_id=user.id,
        character_id=character_id,
        role="assistant",
        content=full_response,
    )
    db.add(ai_msg)
    await db.flush()

    has_emotion = _detect_emotion(transcript_text)
    if has_emotion:
        await record_emotion_from_text(
            user_id=user.id,
            text=transcript_text,
            db=db,
        )
    await relationship_service.on_chat(
        user_id=user.id,
        character_id=character_id,
        message_count=msg_count,
        has_emotion=has_emotion,
        db=db,
    )

    await db.commit()

    extract_memory.delay(
        str(user.id),
        character_id,
        [{"role": "user", "content": transcript_text}, {"role": "assistant", "content": full_response}],
        str(user_msg_id),
    )

    tts_status = "not_requested"
    tts_audio_base64 = None
    tts_content_type = None
    tts_format = None
    if include_tts:
        if not tts_service.is_configured():
            tts_status = "disabled"
        else:
            try:
                tts_audio = await tts_service.synthesize(full_response)
                tts_status = "generated"
                tts_audio_base64 = base64.b64encode(tts_audio.audio_bytes).decode("ascii")
                tts_content_type = tts_audio.content_type
                tts_format = tts_audio.format
            except TTSGenerationError:
                tts_status = "failed"

    return VoiceMessageResponse(
        transcript=transcript_text,
        reply=full_response,
        user_message_id=str(user_msg.id),
        assistant_message_id=str(ai_msg.id),
        tts_status=tts_status,
        tts_audio_base64=tts_audio_base64,
        tts_content_type=tts_content_type,
        tts_format=tts_format,
    )


@router.delete("/{character_id}/message/{message_id}")
async def delete_message(
    character_id: str,
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除聊天消息"""
    result = await db.execute(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.user_id == user.id,
            ChatMessage.character_id == character_id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    await db.delete(message)
    await db.commit()
    return {"status": "ok"}


# ── 清空对话 ──

@router.delete("/{character_id}/history")
async def clear_chat_history(
    character_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空与某角色的全部对话"""
    from sqlalchemy import delete

    await db.execute(
        delete(ChatMessage).where(
            ChatMessage.user_id == user.id,
            ChatMessage.character_id == character_id,
        )
    )
    await db.commit()
    return {"status": "ok"}


# ── Helpers ──

def _detect_emotion(text: str) -> bool:
    return detect_emotion_signal(text) is not None
    """简单情绪检测（MVP 阶段用规则，后续用 AI）"""
    emotion_keywords = [
        "难过", "伤心", "焦虑", "压力", "累", "烦", "崩溃", "绝望",
        "开心", "高兴", "兴奋", "幸福", "感动", "温暖",
        "害怕", "恐惧", "愤怒", "生气", "委屈", "孤独", "寂寞",
    ]
    return any(kw in text for kw in emotion_keywords)


def _subscription_limit_http_error(exc: SubscriptionLimitError) -> HTTPException:
    return HTTPException(
        status_code=402,
        detail={
            "code": "subscription_limit_reached",
            "message": "今天的对话额度用完啦，明天再来",
            "quota": exc.quota,
        },
    )
