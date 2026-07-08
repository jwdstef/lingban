"""角色管理接口 - 列表、详情、选择"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.character import Character, UserCharacterRelation
from app.models.user import User
from app.routers.relationship import RelationResponse, serialize_relation
from app.services.relationship_service import relationship_service

router = APIRouter()


# ── Schemas ──

class CharacterResponse(BaseModel):
    id: str
    name: str
    source: str
    description: str
    avatar_url: str
    color: int
    personality: dict

    model_config = {"from_attributes": True}


class CharacterWithRelationResponse(CharacterResponse):
    """角色信息 + 用户关系"""
    relation: dict | None = None  # 包含 level/label/intimacy/consecutive_days


class SelectCharacterRequest(BaseModel):
    character_id: str


# ── 角色列表 ──

@router.get("", response_model=list[CharacterResponse])
async def list_characters(
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """获取所有可用角色（无需登录也可访问）"""
    result = await db.execute(select(Character).order_by(Character.created_at))
    characters = result.scalars().all()
    return [
        CharacterResponse(
            id=c.id,
            name=c.name,
            source=c.source,
            description=c.description,
            avatar_url=c.avatar_url,
            color=c.color,
            personality=c.personality,
        )
        for c in characters
    ]


# ── 角色列表（含关系信息）──

@router.get("/with-relation", response_model=list[CharacterWithRelationResponse])
async def list_characters_with_relation(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取角色列表，包含用户关系信息（需登录）"""
    # 查询所有角色
    result = await db.execute(select(Character).order_by(Character.created_at))
    characters = result.scalars().all()

    # 查询用户与所有角色的关系
    relation_result = await db.execute(
        select(UserCharacterRelation).where(UserCharacterRelation.user_id == user.id)
    )
    relations = {r.character_id: r for r in relation_result.scalars().all()}

    response = []
    for c in characters:
        relation = relations.get(c.id)
        relation_data = None
        if relation:
            relation_data = {
                "level": relation.level,
                "label": relation.label,
                "intimacy": relation.intimacy,
                "consecutive_days": relation.consecutive_days,
                "first_chat_at": relation.first_chat_at,
                "last_chat_at": relation.last_chat_at,
            }
        response.append(
            CharacterWithRelationResponse(
                id=c.id,
                name=c.name,
                source=c.source,
                description=c.description,
                avatar_url=c.avatar_url,
                color=c.color,
                personality=c.personality,
                relation=relation_data,
            )
        )
    return response


# ── 选择角色 ──

@router.post("/select")
async def select_character(
    data: SelectCharacterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """选择当前角色（引导页完成后调用）"""
    # 验证角色存在
    result = await db.execute(select(Character).where(Character.id == data.character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 更新用户选择的角色
    user.selected_character_id = data.character_id

    # 初始化关系（如果还没有）
    await relationship_service.get_or_create(user.id, data.character_id, db)

    await db.flush()

    return {
        "status": "ok",
        "selected_character_id": data.character_id,
        "character_name": character.name,
    }


# ── 获取当前角色 ──

@router.get("/current/selected")
async def get_selected_character(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户当前选择的角色"""
    if not user.selected_character_id:
        return {"selected": False, "character": None}

    result = await db.execute(
        select(Character).where(Character.id == user.selected_character_id)
    )
    character = result.scalar_one_or_none()
    if not character:
        return {"selected": False, "character": None}

    return {
        "selected": True,
        "character": {
            "id": character.id,
            "name": character.name,
            "source": character.source,
            "description": character.description,
            "avatar_url": character.avatar_url,
            "color": character.color,
        },
    }


# ── 角色详情 ──

@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取角色详情"""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="角色不存在")

    return CharacterResponse(
        id=character.id,
        name=character.name,
        source=character.source,
        description=character.description,
        avatar_url=character.avatar_url,
        color=character.color,
        personality=character.personality,
    )


# ── 关系查询 ──

@router.get("/{character_id}/relation", response_model=RelationResponse)
@router.get("/{character_id}/relationship", response_model=RelationResponse)
async def get_relation(
    character_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户与角色的关系信息"""
    relation = await relationship_service.get_or_create(user.id, character_id, db)
    return serialize_relation(character_id, relation)
