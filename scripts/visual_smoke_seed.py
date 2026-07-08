"""Seed deterministic records for the Flutter visual smoke test."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from cleanup_test_users import configure_backend_path


async def seed_visual_data(email: str, character_id: str) -> dict[str, str | int]:
    configure_backend_path()

    from sqlalchemy import select

    from app.core.database import async_session, engine
    from app.models.memory import EmotionDiary, Memory, ProactiveMessage
    from app.models.user import User

    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            raise RuntimeError(f"user not found: {email}")

        user.selected_character_id = character_id

        care = ProactiveMessage(
            user_id=user.id,
            character_id=character_id,
            trigger_type="time_night",
            content="You mentioned sleeping late recently. I am just checking in.",
            delivered=True,
            replied=False,
            push_status="sent",
            created_at=datetime.now(timezone.utc),
        )
        db.add(care)

        memories = [
            Memory(
                user_id=user.id,
                character_id=character_id,
                category="daily",
                content="User has been working late and wants gentler evening check-ins.",
                importance=7,
                emotion_tags=["tired"],
                is_active=True,
            ),
            Memory(
                user_id=user.id,
                character_id=character_id,
                category="emotion",
                content="User feels calmer when the companion remembers small routines.",
                importance=6,
                emotion_tags=["calm"],
                is_active=True,
            ),
        ]
        db.add_all(memories)

        today = datetime.now(timezone.utc).replace(tzinfo=None)
        day_start = datetime(today.year, today.month, today.day)
        diaries = [
            EmotionDiary(
                user_id=user.id,
                date=day_start - timedelta(days=3),
                dominant_emotion="tired",
                intensity=0.58,
                triggers=["Worked late and felt worn down."],
            ),
            EmotionDiary(
                user_id=user.id,
                date=day_start - timedelta(days=2),
                dominant_emotion="anxious",
                intensity=0.76,
                triggers=["Worried about the next milestone."],
            ),
            EmotionDiary(
                user_id=user.id,
                date=day_start - timedelta(days=1),
                dominant_emotion="calm",
                intensity=0.42,
                triggers=["Felt calmer after a quiet evening routine."],
            ),
            EmotionDiary(
                user_id=user.id,
                date=day_start,
                dominant_emotion="happy",
                intensity=0.62,
                triggers=["Shared a small win with the companion."],
            ),
        ]
        db.add_all(diaries)
        await db.commit()

        result = {
            "user_id": str(user.id),
            "care_message_id": str(care.id),
            "memory_count": len(memories),
            "emotion_diary_count": len(diaries),
        }

    await engine.dispose()
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--character-id", default="yinyue")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(seed_visual_data(args.email, args.character_id))
    print(result)


if __name__ == "__main__":
    main()
