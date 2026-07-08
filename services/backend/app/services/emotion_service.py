"""Emotion detection and diary recording for MVP chat flows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import EmotionDiary


@dataclass(frozen=True)
class EmotionSignal:
    emotion: str
    intensity: float
    trigger: str


_EMOTION_PATTERNS: list[tuple[str, float, tuple[str, ...]]] = [
    (
        "anxious",
        0.78,
        (
            "焦虑",
            "压力",
            "紧张",
            "担心",
            "慌",
            "不安",
            "anxious",
            "anxiety",
            "stress",
            "stressed",
            "worried",
            "panic",
            "nervous",
        ),
    ),
    (
        "sad",
        0.72,
        (
            "难过",
            "伤心",
            "低落",
            "崩溃",
            "绝望",
            "想哭",
            "心情不好",
            "sad",
            "down",
            "depressed",
            "upset",
            "cry",
        ),
    ),
    (
        "tired",
        0.66,
        (
            "累",
            "疲惫",
            "困",
            "失眠",
            "睡不着",
            "耗尽",
            "tired",
            "exhausted",
            "burned out",
            "burnout",
            "can't sleep",
            "insomnia",
        ),
    ),
    (
        "angry",
        0.7,
        (
            "生气",
            "愤怒",
            "烦",
            "火大",
            "angry",
            "mad",
            "furious",
            "annoyed",
        ),
    ),
    (
        "lonely",
        0.7,
        ("孤独", "寂寞", "没人陪", "lonely", "alone"),
    ),
    (
        "happy",
        0.58,
        (
            "开心",
            "高兴",
            "兴奋",
            "幸福",
            "期待",
            "快乐",
            "不错",
            "happy",
            "glad",
            "excited",
            "great",
            "good",
            "joy",
        ),
    ),
    (
        "calm",
        0.46,
        ("平静", "放松", "安心", "calm", "relaxed"),
    ),
]


def _normalize_trigger(text: str) -> str:
    return " ".join(text.strip().split())[:120]


def _day_bounds(occurred_at: datetime) -> tuple[datetime, datetime]:
    if occurred_at.tzinfo is not None:
        occurred_at = occurred_at.astimezone(timezone.utc).replace(tzinfo=None)
    day_start = datetime(occurred_at.year, occurred_at.month, occurred_at.day)
    return day_start, day_start + timedelta(days=1)


def detect_emotion_signal(text: str) -> EmotionSignal | None:
    normalized = _normalize_trigger(text)
    if not normalized:
        return None

    lowered = normalized.lower()
    matches: list[EmotionSignal] = []
    for emotion, intensity, keywords in _EMOTION_PATTERNS:
        if any(keyword.lower() in lowered for keyword in keywords):
            matches.append(
                EmotionSignal(
                    emotion=emotion,
                    intensity=intensity,
                    trigger=normalized,
                )
            )

    if not matches:
        return None
    return max(matches, key=lambda signal: signal.intensity)


def _merge_triggers(new_trigger: str, existing_triggers: object) -> list[str]:
    merged: list[str] = []
    for trigger in [new_trigger, *(existing_triggers if isinstance(existing_triggers, list) else [])]:
        trigger_text = str(trigger).strip()
        if trigger_text and trigger_text not in merged:
            merged.append(trigger_text)
    return merged[:8]


async def record_emotion_from_text(
    user_id: uuid.UUID,
    text: str,
    db: AsyncSession,
    occurred_at: datetime | None = None,
) -> EmotionDiary | None:
    signal = detect_emotion_signal(text)
    if signal is None:
        return None

    day_start, day_end = _day_bounds(occurred_at or datetime.now(timezone.utc))
    result = await db.execute(
        select(EmotionDiary).where(
            EmotionDiary.user_id == user_id,
            EmotionDiary.date >= day_start,
            EmotionDiary.date < day_end,
        )
    )
    diary = result.scalar_one_or_none()

    if diary is None:
        diary = EmotionDiary(
            user_id=user_id,
            date=day_start,
            dominant_emotion=signal.emotion,
            intensity=signal.intensity,
            triggers=[signal.trigger],
        )
        db.add(diary)
    else:
        existing_intensity = diary.intensity or 0
        if signal.intensity >= existing_intensity:
            diary.dominant_emotion = signal.emotion
            diary.intensity = signal.intensity
        diary.triggers = _merge_triggers(signal.trigger, diary.triggers)

    await db.flush()
    return diary
