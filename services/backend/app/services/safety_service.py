from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.safety import AuditLog, SafetyEvent


RISK_RULES: dict[str, list[str]] = {
    "self_harm": [
        "\u81ea\u6740",
        "\u8f7b\u751f",
        "\u4e0d\u60f3\u6d3b",
        "\u4f24\u5bb3\u81ea\u5df1",
        "\u5272\u8155",
        "suicide",
        "self harm",
        "kill myself",
        "do not want to live",
        "don't want to live",
        "end my life",
        "hurt myself",
    ],
    "violence": [
        "\u6740\u4e86\u4ed6",
        "\u6740\u4e86\u5979",
        "\u62a5\u590d\u4ed6\u4eec",
        "hurt them",
        "kill them",
    ],
}

REVIEW_STATUSES = {"pending_review", "in_review", "resolved", "dismissed"}


def detect_risk_terms(text: str) -> tuple[str | None, list[str]]:
    lowered = text.lower()
    for event_type, terms in RISK_RULES.items():
        matches = [term for term in terms if term.lower() in lowered]
        if matches:
            return event_type, matches
    return None, []


def severity_for_event(event_type: str) -> str:
    if event_type == "self_harm":
        return "critical"
    return "high"


def content_excerpt(text: str, limit: int = 500) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return normalized[:limit]
    return f"{normalized[:limit - 3]}..."


async def write_audit_log(
    db: AsyncSession,
    *,
    actor_type: str,
    action: str,
    target_type: str,
    actor_id: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        event_metadata=metadata or {},
    )
    db.add(log)
    await db.flush()
    return log


async def create_event_for_message(
    db: AsyncSession,
    message: ChatMessage,
) -> SafetyEvent | None:
    event_type, matched_terms = detect_risk_terms(message.content)
    if not event_type:
        return None

    if message.id is not None:
        existing = await db.execute(
            select(SafetyEvent).where(SafetyEvent.source_message_id == message.id)
        )
        event = existing.scalar_one_or_none()
        if event:
            return event

    event = SafetyEvent(
        user_id=message.user_id,
        character_id=message.character_id,
        source="chat_message",
        source_message_id=message.id,
        event_type=event_type,
        severity=severity_for_event(event_type),
        status="pending_review",
        content_excerpt=content_excerpt(message.content),
        matched_terms=matched_terms,
    )
    db.add(event)
    await db.flush()
    await write_audit_log(
        db,
        actor_type="system",
        action="safety_event.created",
        target_type="safety_event",
        target_id=str(event.id),
        metadata={
            "source_message_id": str(message.id) if message.id else None,
            "event_type": event_type,
            "matched_terms": matched_terms,
        },
    )
    return event


async def review_event(
    db: AsyncSession,
    event: SafetyEvent,
    *,
    status: str,
    reviewed_by: str,
    note: str | None = None,
) -> SafetyEvent:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Unsupported safety event status: {status}")

    previous_status = event.status
    event.status = status
    event.reviewed_by = reviewed_by
    event.review_note = note
    event.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    await write_audit_log(
        db,
        actor_type="admin",
        actor_id=reviewed_by,
        action="safety_event.reviewed",
        target_type="safety_event",
        target_id=str(event.id),
        metadata={
            "previous_status": previous_status,
            "status": status,
            "note": note,
        },
    )
    return event
