"""Delete temporary smoke-test users and their dependent rows.

Run from the repository root:
    python scripts/cleanup_test_users.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "services" / "backend"

DEFAULT_PATTERNS = (
    "codex-api-%@example.test",
    "codex-ui-%@example.test",
    "codex-memory-%@example.test",
)


def configure_backend_path() -> None:
    """Make backend modules and its local .env visible to this script."""
    load_dotenv(BACKEND_DIR / ".env", override=False)
    backend_path = str(BACKEND_DIR)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


async def cleanup_test_users(
    patterns: tuple[str, ...] = DEFAULT_PATTERNS,
    dry_run: bool = False,
) -> int:
    configure_backend_path()

    from sqlalchemy import delete, or_, select

    from app.core.database import async_session, engine
    from app.models.character import UserCharacterRelation
    from app.models.chat import ChatMessage
    from app.models.memory import EmotionDiary, Memory, ProactiveMessage
    from app.models.payment import PaymentOrder
    from app.models.push import PushDelivery, PushToken
    from app.models.safety import AuditLog, SafetyEvent
    from app.models.user import User

    count = 0
    async with async_session() as db:
        filters = [User.email.like(pattern) for pattern in patterns]
        result = await db.execute(select(User).where(or_(*filters)))
        users = list(result.scalars().all())
        user_ids = [user.id for user in users]
        count = len(user_ids)

        if not user_ids or dry_run:
            pass
        else:
            await db.execute(delete(PushDelivery).where(PushDelivery.user_id.in_(user_ids)))
            await db.execute(delete(PushToken).where(PushToken.user_id.in_(user_ids)))

            safety_result = await db.execute(
                select(SafetyEvent.id).where(SafetyEvent.user_id.in_(user_ids))
            )
            safety_event_ids = [str(event_id) for event_id in safety_result.scalars().all()]
            if safety_event_ids:
                await db.execute(
                    delete(AuditLog).where(
                        AuditLog.target_type == "safety_event",
                        AuditLog.target_id.in_(safety_event_ids),
                    )
                )
            await db.execute(delete(SafetyEvent).where(SafetyEvent.user_id.in_(user_ids)))

            for model in (ProactiveMessage, ChatMessage, Memory, EmotionDiary):
                await db.execute(delete(model).where(model.user_id.in_(user_ids)))

            await db.execute(delete(PaymentOrder).where(PaymentOrder.user_id.in_(user_ids)))
            await db.execute(
                delete(UserCharacterRelation).where(
                    UserCharacterRelation.user_id.in_(user_ids)
                )
            )
            await db.execute(delete(User).where(User.id.in_(user_ids)))
            await db.commit()

    await engine.dispose()
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern",
        action="append",
        dest="patterns",
        help="SQL LIKE pattern for user email. May be provided more than once.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count matching users; do not delete anything.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    patterns = tuple(args.patterns or DEFAULT_PATTERNS)
    count = asyncio.run(cleanup_test_users(patterns, dry_run=args.dry_run))
    action = "matched" if args.dry_run else "deleted"
    print(f"{action} {count} smoke-test user(s)")


if __name__ == "__main__":
    main()
