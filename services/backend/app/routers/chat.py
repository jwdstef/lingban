from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.chat import ChatMessage
from app.models.user import User
from app.schemas.chat import SendMessageRequest, ChatMessageResponse, ChatHistoryResponse
from app.services.ai_service import ai_service

router = APIRouter()


@router.get("/{character_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    character_id: str,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取聊天历史"""
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


@router.post("/{character_id}/message")
async def send_message(
    character_id: str,
    data: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息并获取 AI 回复（SSE 流式）"""
    # 保存用户消息
    user_msg = ChatMessage(
        user_id=user.id,
        character_id=character_id,
        role="user",
        content=data.content,
        message_type=data.message_type,
    )
    db.add(user_msg)
    await db.flush()

    # 获取最近对话上下文
    recent_query = (
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.character_id == character_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
    )
    result = await db.execute(recent_query)
    recent_messages = list(reversed(result.scalars().all()))

    # SSE 流式返回 AI 回复
    async def generate():
        full_response = ""
        async for chunk in ai_service.stream_chat(
            character_id=character_id,
            messages=[
                {"role": m.role, "content": m.content} for m in recent_messages
            ],
            user_id=str(user.id),
        ):
            full_response += chunk
            yield f"data: {chunk}\n\n"

        # 保存 AI 回复
        ai_msg = ChatMessage(
            user_id=user.id,
            character_id=character_id,
            role="assistant",
            content=full_response,
        )
        db.add(ai_msg)
        await db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
