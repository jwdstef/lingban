"""Run an end-to-end API smoke test against a running backend.

The script uses HTTP for product flows and the backend SQLAlchemy session only
for deterministic setup/cleanup of smoke-only data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from cleanup_test_users import cleanup_test_users, configure_backend_path


PASSWORD = "CodexSmokeTest123!"
ADULT_BIRTH_DATE = "1990-01-01"
CHARACTER_ID = "yinyue"
ADMIN_TOKEN = os.environ.get("ADMIN_API_TOKEN", "dev-admin-token")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_status(response: httpx.Response, expected: int = 200) -> httpx.Response:
    if response.status_code != expected:
        raise AssertionError(
            f"{response.request.method} {response.request.url} returned "
            f"{response.status_code}: {response.text}"
        )
    return response


async def insert_care_message(email: str, character_id: str) -> str:
    configure_backend_path()

    from sqlalchemy import select

    from app.core.database import async_session, engine
    from app.models.memory import ProactiveMessage
    from app.models.user import User

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            require(user is not None, f"user not found in database: {email}")

            message = ProactiveMessage(
                user_id=user.id,
                character_id=character_id,
                trigger_type="time_night",
                content="It is late. I am checking whether you are doing okay.",
                delivered=False,
                replied=False,
                push_status="pending",
                created_at=datetime.now(timezone.utc),
            )
            db.add(message)
            await db.flush()
            message_id = str(message.id)
            await db.commit()
            return message_id
    finally:
        await engine.dispose()


async def trigger_push_delivery(email: str, character_id: str) -> dict[str, Any]:
    configure_backend_path()

    from sqlalchemy import select

    from app.core.database import async_session, engine
    from app.models.push import PushDelivery
    from app.models.user import User
    from app.services.push_service import push_gateway

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            require(user is not None, f"user not found in database: {email}")
            user.settings = {
                **(user.settings or {}),
                "push_enabled": True,
                "dnd_enabled": False,
                "proactive_level": "high",
            }
            await db.flush()

            message = await push_gateway.send(
                user_id=user.id,
                character_id=character_id,
                trigger_type="time_morning",
                content="Smoke test proactive push.",
                db=db,
            )
            result = await db.execute(
                select(PushDelivery).where(
                    PushDelivery.proactive_message_id == message.id
                )
            )
            deliveries = result.scalars().all()
            payload = {
                "message_id": str(message.id),
                "message_status": message.push_status,
                "delivery_ids": [str(delivery.id) for delivery in deliveries],
                "delivery_statuses": [delivery.status for delivery in deliveries],
            }
            await db.commit()
            return payload
    finally:
        await engine.dispose()


async def insert_memory(email: str, character_id: str, content: str) -> str:
    configure_backend_path()

    from sqlalchemy import select

    from app.core.database import async_session, engine
    from app.models.memory import Memory
    from app.models.user import User

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            require(user is not None, f"user not found in database: {email}")

            memory = Memory(
                user_id=user.id,
                character_id=character_id,
                category="daily",
                content=content,
                importance=5,
                emotion_tags=["smoke"],
                is_active=True,
            )
            db.add(memory)
            await db.flush()
            memory_id = str(memory.id)
            await db.commit()
            return memory_id
    finally:
        await engine.dispose()


async def insert_chat_message(
    email: str,
    character_id: str,
    content: str,
    role: str = "user",
) -> str:
    configure_backend_path()

    from sqlalchemy import select

    from app.core.database import async_session, engine
    from app.models.chat import ChatMessage
    from app.models.user import User
    from app.services.safety_service import create_event_for_message

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            require(user is not None, f"user not found in database: {email}")

            message = ChatMessage(
                user_id=user.id,
                character_id=character_id,
                role=role,
                content=content,
                message_type="text",
                emotion_tags=["smoke", "crisis"],
            )
            db.add(message)
            await db.flush()
            await create_event_for_message(db, message)
            message_id = str(message.id)
            await db.commit()
            return message_id
    finally:
        await engine.dispose()


async def insert_emotion_diary(email: str) -> str:
    configure_backend_path()

    from sqlalchemy import select

    from app.core.database import async_session, engine
    from app.models.memory import EmotionDiary
    from app.models.user import User

    try:
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            require(user is not None, f"user not found in database: {email}")

            today = datetime.now(timezone.utc).replace(tzinfo=None)
            day_start = datetime(today.year, today.month, today.day)
            diary = EmotionDiary(
                user_id=user.id,
                date=day_start - timedelta(days=2),
                dominant_emotion="anxious",
                intensity=0.74,
                triggers=["Smoke test seeded deadline anxiety."],
            )
            db.add(diary)
            await db.flush()
            diary_id = str(diary.id)
            await db.commit()
            return diary_id
    finally:
        await engine.dispose()


def parse_sse_events(response: httpx.Response) -> list[str]:
    events: list[str] = []
    for line in response.iter_lines():
        if not line:
            continue
        if line.startswith("data: "):
            events.append(line[len("data: ") :])
    return events


def run_smoke(base_url: str) -> dict[str, Any]:
    email = f"codex-api-{int(time.time())}-{uuid.uuid4().hex[:8]}@example.test"
    delete_email = f"codex-api-delete-{int(time.time())}-{uuid.uuid4().hex[:8]}@example.test"
    headers: dict[str, str] = {}
    summary: dict[str, Any] = {"email": email, "checks": []}

    try:
        with httpx.Client(base_url=base_url.rstrip("/"), timeout=60.0) as client:
            health = require_status(client.get("/health")).json()
            require(health.get("status") == "ok", "health status is not ok")
            summary["checks"].append("health")

            register = require_status(
                client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": email,
                        "nickname": "Codex API Smoke",
                        "password": PASSWORD,
                        "birth_date": ADULT_BIRTH_DATE,
                    },
                )
            ).json()
            token = register["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            summary["checks"].append("register")

            login = require_status(
                client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": PASSWORD},
                )
            ).json()
            require(login["access_token"], "login did not return a token")
            summary["checks"].append("login")

            me = require_status(client.get("/api/v1/auth/me", headers=headers)).json()
            require(me["email"] == email, "profile email mismatch")
            summary["user_id"] = me["id"]
            summary["checks"].append("me")

            characters = require_status(client.get("/api/v1/characters")).json()
            by_id = {character["id"]: character for character in characters}
            for character_id in ("yinyue", "babata", "heihaung"):
                require(character_id in by_id, f"missing character {character_id}")
            require(
                by_id[CHARACTER_ID]["color"] > 2_147_483_647,
                "yinyue color was not persisted as a 64-bit ARGB value",
            )
            summary["checks"].append("characters")

            require_status(
                client.post(
                    "/api/v1/characters/select",
                    headers=headers,
                    json={"character_id": CHARACTER_ID},
                )
            )
            current = require_status(
                client.get("/api/v1/characters/current/selected", headers=headers)
            ).json()
            require(current["selected"] is True, "selected character not marked")
            require(
                current["character"]["id"] == CHARACTER_ID,
                "selected character id mismatch",
            )
            summary["checks"].append("select_character")

            relation_before = require_status(
                client.get(
                    f"/api/v1/characters/{CHARACTER_ID}/relation",
                    headers=headers,
                )
            ).json()
            intimacy_before = relation_before["intimacy"]
            relationship = require_status(
                client.get(
                    f"/api/v1/relationship/{CHARACTER_ID}",
                    headers=headers,
                )
            ).json()
            character_relationship = require_status(
                client.get(
                    f"/api/v1/characters/{CHARACTER_ID}/relationship",
                    headers=headers,
                )
            ).json()
            require(
                relationship["character_id"] == CHARACTER_ID,
                "relationship route returned wrong character",
            )
            require(
                relationship["intimacy"] == intimacy_before,
                "relationship route intimacy mismatch",
            )
            require(
                character_relationship["intimacy"] == intimacy_before,
                "character relationship route intimacy mismatch",
            )
            summary["checks"].append("relation_before")
            summary["checks"].append("relationship_compat")

            settings_before = require_status(
                client.get("/api/v1/settings", headers=headers)
            ).json()
            require(
                "push_enabled" in settings_before,
                "settings defaults are missing push_enabled",
            )
            settings_after = require_status(
                client.put(
                    "/api/v1/settings",
                    headers=headers,
                    json={"settings": {"proactive_level": "high"}},
                )
            ).json()
            require(
                settings_after["settings"]["proactive_level"] == "high",
                "settings update did not persist",
            )
            summary["checks"].append("settings")

            subscription = require_status(
                client.get("/api/v1/subscription", headers=headers)
            ).json()
            require(subscription["plan"] == "free", "new user should start on free plan")
            require(
                subscription["quota"]["chat_daily"]["limit"] >= 1,
                "subscription did not return chat quota",
            )
            require(
                any(plan["id"] == "basic" for plan in subscription["plans"]),
                "subscription plan catalog missing basic plan",
            )
            summary["checks"].append("subscription")

            memory_off = require_status(
                client.put(
                    "/api/v1/memory/toggle",
                    headers=headers,
                    json={"memory_enabled": False},
                )
            ).json()
            require(
                memory_off["settings"]["memory_enabled"] is False,
                "memory toggle did not disable memory",
            )
            memory_on = require_status(
                client.put(
                    "/api/v1/memory/toggle",
                    headers=headers,
                    json={"memory_enabled": True},
                )
            ).json()
            require(
                memory_on["settings"]["memory_enabled"] is True,
                "memory toggle did not re-enable memory",
            )
            summary["checks"].append("memory_toggle")

            push_token = require_status(
                client.post(
                    "/api/v1/push/tokens",
                    headers=headers,
                    json={
                        "platform": "jpush",
                        "token": f"smoke-token-{uuid.uuid4().hex}",
                        "permission_status": "granted",
                        "device_id": "codex-smoke-device",
                        "app_version": "smoke",
                    },
                )
            ).json()
            require(push_token["provider"] == "jpush", "push provider mismatch")
            require(push_token["push_enabled"] is True, "push token did not enable push")
            push_token_2 = require_status(
                client.post(
                    "/api/v1/push/tokens",
                    headers=headers,
                    json={
                        "platform": "fcm",
                        "token": f"smoke-token-{uuid.uuid4().hex}",
                        "permission_status": "granted",
                        "device_id": "codex-smoke-device-2",
                        "app_version": "smoke",
                    },
                )
            ).json()
            require(
                push_token_2["token_id"] != push_token["token_id"],
                "push multi-device registration reused the same token row",
            )

            unauthorized_admin = client.get("/api/v1/admin/dashboard/stats")
            require(
                unauthorized_admin.status_code == 401,
                "admin dashboard should reject missing token",
            )
            admin_headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            require_status(
                client.post("/api/v1/admin/auth/verify", headers=admin_headers)
            )
            admin_stats = require_status(
                client.get("/api/v1/admin/dashboard/stats", headers=admin_headers)
            ).json()
            require("total_users" in admin_stats, "admin stats missing total_users")
            summary["checks"].append("admin_auth")

            frequency = require_status(
                client.put(
                    "/api/v1/care/frequency",
                    headers=headers,
                    json={"proactive_level": "quiet"},
                )
            ).json()
            require(
                frequency["settings"]["proactive_level"] == "quiet",
                "care frequency update did not persist",
            )
            dnd = require_status(
                client.put(
                    "/api/v1/care/dnd",
                    headers=headers,
                    json={
                        "dnd_enabled": True,
                        "dnd_start": "22:30",
                        "dnd_end": "07:45",
                    },
                )
            ).json()
            require(
                dnd["settings"]["dnd_start"] == "22:30"
                and dnd["settings"]["dnd_end"] == "07:45",
                "care DND update did not persist",
            )
            summary["checks"].append("care_frequency_dnd")

            old_memory = f"codex-old-memory-{uuid.uuid4().hex[:8]}"
            new_memory = f"codex-new-memory-{uuid.uuid4().hex[:8]}"
            memory_id = asyncio.run(insert_memory(email, CHARACTER_ID, old_memory))

            memory_search = require_status(
                client.get(
                    f"/api/v1/memory/{CHARACTER_ID}",
                    headers=headers,
                    params={"query": old_memory},
                )
            ).json()
            require(memory_search["total"] == 1, "memory search did not find seed memory")
            require(
                memory_search["memories"][0]["id"] == memory_id,
                "memory search returned the wrong memory",
            )

            updated_memory = require_status(
                client.put(
                    f"/api/v1/memory/{CHARACTER_ID}/{memory_id}",
                    headers=headers,
                    json={
                        "content": new_memory,
                        "category": "preference",
                        "importance": 8,
                        "emotion_tags": ["updated", "smoke"],
                    },
                )
            ).json()
            require(updated_memory["content"] == new_memory, "memory content was not edited")
            require(updated_memory["category"] == "preference", "memory category was not edited")
            require(updated_memory["importance"] == 8, "memory importance was not edited")
            require(
                updated_memory["emotion_tags"] == ["updated", "smoke"],
                "memory emotion tags were not edited",
            )

            old_search_after_update = require_status(
                client.get(
                    f"/api/v1/memory/{CHARACTER_ID}",
                    headers=headers,
                    params={"query": old_memory},
                )
            ).json()
            require(
                old_search_after_update["total"] == 0,
                "old memory content still appeared after edit",
            )

            new_search_after_update = require_status(
                client.get(
                    f"/api/v1/memory/{CHARACTER_ID}",
                    headers=headers,
                    params={"query": new_memory},
                )
            ).json()
            require(
                new_search_after_update["total"] == 1,
                "new memory content did not appear after edit",
            )
            summary["checks"].append("memory_search_edit")

            emotion_id = asyncio.run(insert_emotion_diary(email))
            diary = require_status(
                client.get("/api/v1/emotion/diary", headers=headers)
            ).json()
            require(diary["total"] == 1, "emotion diary did not return seed record")
            require(
                diary["records"][0]["id"] == emotion_id,
                "emotion diary returned the wrong record",
            )
            trend = require_status(
                client.get(
                    "/api/v1/emotion/trend",
                    headers=headers,
                    params={"days": 14},
                )
            ).json()
            require(
                any(point["dominant_emotion"] == "anxious" for point in trend["points"]),
                "emotion trend did not include seed record",
            )
            require(
                trend["emotion_counts"].get("anxious") == 1,
                "emotion trend counts are wrong",
            )
            summary["checks"].append("emotion_diary_trend")

            push_delivery = asyncio.run(trigger_push_delivery(email, CHARACTER_ID))
            require(
                push_delivery["message_status"] == "sent",
                "PushGateway did not mark proactive push as sent",
            )
            require(
                len(push_delivery["delivery_ids"]) == 2,
                "PushGateway did not create one delivery per registered device",
            )
            require(
                push_delivery["delivery_statuses"] == ["sent", "sent"],
                "PushGateway deliveries were not marked sent",
            )
            push_clicked = require_status(
                client.post(
                    "/api/v1/push/click",
                    headers=headers,
                    json={
                        "delivery_id": push_delivery["delivery_ids"][0],
                        "deep_link": f"lingban://chat/{CHARACTER_ID}",
                    },
                )
            ).json()
            require(
                push_clicked["delivery_id"] == push_delivery["delivery_ids"][0],
                "push click returned the wrong delivery",
            )
            require(
                push_clicked["proactive_message_id"] == push_delivery["message_id"],
                "push click returned the wrong proactive message",
            )
            require(push_clicked["delivered"] is True, "push click did not mark delivered")
            require(
                push_clicked["push_status"] == "clicked",
                "push click did not mark message clicked",
            )
            summary["checks"].append("push_token_click")

            care_message_id = asyncio.run(insert_care_message(email, CHARACTER_ID))
            care_list = require_status(
                client.get(
                    "/api/v1/care/messages",
                    headers=headers,
                    params={"character_id": CHARACTER_ID, "limit": 5},
                )
            ).json()
            require(
                any(message["id"] == care_message_id for message in care_list["messages"]),
                "seeded care message not returned",
            )
            clicked = require_status(
                client.post(
                    f"/api/v1/care/messages/{care_message_id}/click",
                    headers=headers,
                )
            ).json()
            require(clicked["delivered"] is True, "care click did not mark delivered")
            replied = require_status(
                client.post(
                    f"/api/v1/care/messages/{care_message_id}/reply",
                    headers=headers,
                )
            ).json()
            require(replied["replied"] is True, "care reply did not mark replied")
            relation_after_reply = require_status(
                client.get(
                    f"/api/v1/characters/{CHARACTER_ID}/relation",
                    headers=headers,
                )
            ).json()
            require(
                relation_after_reply["intimacy"] == intimacy_before + 3,
                "care reply should add exactly 3 intimacy",
            )
            require_status(
                client.post(
                    f"/api/v1/care/messages/{care_message_id}/reply",
                    headers=headers,
                )
            )
            relation_after_duplicate = require_status(
                client.get(
                    f"/api/v1/characters/{CHARACTER_ID}/relation",
                    headers=headers,
                )
            ).json()
            require(
                relation_after_duplicate["intimacy"]
                == relation_after_reply["intimacy"],
                "duplicate care reply changed intimacy",
            )
            summary["checks"].append("care_click_reply")

            with client.stream(
                "POST",
                f"/api/v1/chat/{CHARACTER_ID}/message",
                headers=headers,
                json={"content": "I worked late today and feel tired."},
            ) as stream:
                require_status(stream)
                events = parse_sse_events(stream)

            require(events, "chat SSE returned no events")
            require(events[-1] == "[DONE]", "chat SSE did not end with [DONE]")
            message_events = [
                json.loads(event)
                for event in events
                if event.startswith("{") and "message_id" in event
            ]
            require(message_events, "chat SSE did not include assistant message_id")
            summary["checks"].append("chat_sse")

            voice_transcript = "I am anxious but recording this as a voice note."
            voice = require_status(
                client.post(
                    f"/api/v1/chat/{CHARACTER_ID}/voice",
                    headers=headers,
                    data={"transcript": voice_transcript},
                    files={
                        "audio": (
                            "voice-smoke.txt",
                            voice_transcript.encode("utf-8"),
                            "text/plain",
                        )
                    },
                )
            ).json()
            require(
                voice["transcript"] == voice_transcript,
                "voice transcript fallback was not used",
            )
            require(voice["reply"], "voice message did not return an AI reply")
            require(
                voice.get("tts_status") == "not_requested",
                "voice message should not request TTS by default",
            )
            summary["checks"].append("chat_voice")

            diary_after_chat = require_status(
                client.get("/api/v1/emotion/diary", headers=headers)
            ).json()
            require(
                any(
                    any("feel tired" in trigger for trigger in record["triggers"])
                    for record in diary_after_chat["records"]
                ),
                "chat emotion was not recorded in diary",
            )
            require(
                any(
                    any("voice note" in trigger for trigger in record["triggers"])
                    for record in diary_after_chat["records"]
                ),
                "voice emotion was not recorded in diary",
            )
            summary["checks"].append("emotion_diary_record")

            history = require_status(
                client.get(
                    f"/api/v1/chat/{CHARACTER_ID}/history",
                    headers=headers,
                )
            ).json()
            require(history["total"] >= 2, "chat history did not persist both messages")
            require(
                any(
                    message["message_type"] == "voice"
                    and message["content"] == voice_transcript
                    for message in history["messages"]
                ),
                "chat history did not persist the voice message",
            )
            summary["checks"].append("chat_history")

            safety_message_id = asyncio.run(
                insert_chat_message(
                    email,
                    CHARACTER_ID,
                    "我不想活了，这是一条安全复核 smoke 消息。",
                )
            )
            admin_user_detail = require_status(
                client.get(
                    f"/api/v1/admin/users/{summary['user_id']}",
                    headers=admin_headers,
                )
            ).json()
            require(
                admin_user_detail["metrics"]["chat_messages"] >= 1,
                "admin user detail missing chat metrics",
            )
            require(
                admin_user_detail["push_tokens"][0]["token_preview"],
                "admin user detail missing push token preview",
            )

            admin_messages = require_status(
                client.get(
                    "/api/v1/admin/messages",
                    headers=admin_headers,
                    params={"user_id": summary["user_id"], "page_size": 5},
                )
            ).json()
            require(
                any(item["id"] == safety_message_id for item in admin_messages["items"]),
                "admin chat audit did not include seeded safety chat",
            )

            admin_care = require_status(
                client.get(
                    "/api/v1/admin/care/messages",
                    headers=admin_headers,
                    params={"user_id": summary["user_id"], "page_size": 5},
                )
            ).json()
            require(
                any(item["id"] == care_message_id for item in admin_care["items"]),
                "admin care records did not include seeded care message",
            )

            admin_push = require_status(
                client.get(
                    "/api/v1/admin/push/deliveries",
                    headers=admin_headers,
                    params={"user_id": summary["user_id"], "page_size": 5},
                )
            ).json()
            require(
                any(
                    item["id"] == push_delivery["delivery_ids"][0]
                    for item in admin_push["items"]
                ),
                "admin push deliveries did not include generated delivery",
            )

            admin_safety = require_status(
                client.get(
                    "/api/v1/admin/safety/events",
                    headers=admin_headers,
                    params={"user_id": summary["user_id"], "page_size": 5},
                )
            ).json()
            safety_event = next(
                (
                    item
                    for item in admin_safety["items"]
                    if item.get("source_message_id") == safety_message_id
                ),
                None,
            )
            require(
                safety_event is not None,
                "admin safety events did not include seeded risk message",
            )
            require(
                safety_event["event_type"] == "self_harm",
                "admin safety event type mismatch",
            )
            reviewed_safety = require_status(
                client.post(
                    f"/api/v1/admin/safety/events/{safety_event['id']}/review",
                    headers=admin_headers,
                    json={
                        "status": "in_review",
                        "note": "Smoke test review",
                        "reviewed_by": "api-smoke",
                    },
                )
            ).json()
            require(
                reviewed_safety["status"] == "in_review",
                "admin safety review did not update status",
            )
            audit_logs = require_status(
                client.get(
                    "/api/v1/admin/audit/logs",
                    headers=admin_headers,
                    params={
                        "target_type": "safety_event",
                        "target_id": safety_event["id"],
                        "page_size": 10,
                    },
                )
            ).json()
            require(
                any(
                    item["action"] == "safety_event.reviewed"
                    and item["metadata"].get("status") == "in_review"
                    for item in audit_logs["items"]
                ),
                "audit logs did not include safety review",
            )
            summary["checks"].append("admin_operations")
            summary["checks"].append("safety_review_audit")

            export = require_status(
                client.get("/api/v1/data/export", headers=headers)
            ).json()
            require(export["user"]["email"] == email, "data export returned wrong user")
            require("password_hash" not in export["user"], "data export leaked password hash")
            require("push_token" not in export["user"], "data export leaked push token")
            require(
                any(memory["id"] == memory_id for memory in export["memories"]),
                "data export did not include memory data",
            )
            require(
                len(export["push_tokens"]) == 2,
                "data export did not include both push token metadata rows",
            )
            require(
                all("token" not in token for token in export["push_tokens"]),
                "data export leaked raw push token",
            )
            require(
                len(export["push_deliveries"]) >= 2,
                "data export did not include push delivery records",
            )
            require(
                "payment_orders" in export,
                "data export did not include payment order metadata",
            )
            summary["checks"].append("data_export")

            delete_register = require_status(
                client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": delete_email,
                        "nickname": "Delete Me",
                        "password": PASSWORD,
                        "birth_date": ADULT_BIRTH_DATE,
                    },
                )
            ).json()
            delete_headers = {"Authorization": f"Bearer {delete_register['access_token']}"}
            bad_delete = client.post(
                "/api/v1/data/delete-account",
                headers=delete_headers,
                json={"confirm": "WRONG"},
            )
            require(
                bad_delete.status_code == 400,
                "delete account should require explicit confirmation",
            )
            delete_response = require_status(
                client.post(
                    "/api/v1/data/delete-account",
                    headers=delete_headers,
                    json={"confirm": "DELETE", "reason": "smoke"},
                )
            ).json()
            require(
                delete_response["status"] == "pending_deletion",
                "delete account did not mark pending deletion",
            )
            require(
                "scheduled_deletion_at" in delete_response,
                "delete account did not return scheduled deletion date",
            )
            summary["checks"].append("data_delete_account")

        return summary
    finally:
        asyncio.run(cleanup_test_users((email, delete_email)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Running backend base URL.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_smoke(args.base_url)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
