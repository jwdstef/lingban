"""Emotion diary APIs."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import EmotionDiary
from app.models.user import User

router = APIRouter()


class EmotionDiaryResponse(BaseModel):
    id: str
    date: datetime
    dominant_emotion: str | None
    intensity: float | None
    triggers: list[str]
    created_at: datetime


class EmotionDiaryListResponse(BaseModel):
    records: list[EmotionDiaryResponse]
    total: int
    has_more: bool


class EmotionTrendPoint(BaseModel):
    date: datetime
    dominant_emotion: str | None
    intensity: float | None


class EmotionTrendResponse(BaseModel):
    days: int
    points: list[EmotionTrendPoint]
    emotion_counts: dict[str, int]
    average_intensity: float


def _serialize_diary(record: EmotionDiary) -> EmotionDiaryResponse:
    return EmotionDiaryResponse(
        id=str(record.id),
        date=record.date,
        dominant_emotion=record.dominant_emotion,
        intensity=record.intensity,
        triggers=[
            str(trigger)
            for trigger in (record.triggers if isinstance(record.triggers, list) else [])
            if str(trigger).strip()
        ],
        created_at=record.created_at,
    )


def _start_date_for_days(days: int) -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = datetime(now.year, now.month, now.day)
    return today - timedelta(days=days - 1)


@router.get("/diary", response_model=EmotionDiaryListResponse)
async def get_emotion_diary(
    limit: int = Query(default=30, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(
        select(func.count())
        .select_from(EmotionDiary)
        .where(EmotionDiary.user_id == user.id)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(EmotionDiary)
        .where(EmotionDiary.user_id == user.id)
        .order_by(EmotionDiary.date.desc(), EmotionDiary.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    records = result.scalars().all()

    return EmotionDiaryListResponse(
        records=[_serialize_diary(record) for record in records],
        total=total,
        has_more=offset + limit < total,
    )


@router.get("/trend", response_model=EmotionTrendResponse)
async def get_emotion_trend(
    days: int = Query(default=14, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmotionDiary)
        .where(
            EmotionDiary.user_id == user.id,
            EmotionDiary.date >= _start_date_for_days(days),
        )
        .order_by(EmotionDiary.date.asc())
    )
    records = result.scalars().all()

    emotion_counts: dict[str, int] = {}
    intensity_values: list[float] = []
    points: list[EmotionTrendPoint] = []
    for record in records:
        emotion = record.dominant_emotion
        if emotion:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        if record.intensity is not None:
            intensity_values.append(float(record.intensity))
        points.append(
            EmotionTrendPoint(
                date=record.date,
                dominant_emotion=record.dominant_emotion,
                intensity=record.intensity,
            )
        )

    average = (
        round(sum(intensity_values) / len(intensity_values), 2)
        if intensity_values
        else 0.0
    )

    return EmotionTrendResponse(
        days=days,
        points=points,
        emotion_counts=emotion_counts,
        average_intensity=average,
    )
