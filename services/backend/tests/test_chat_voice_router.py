import unittest
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.routers.chat import send_voice_message
from app.services.subscription_service import SubscriptionLimitError
from app.services.tts_service import TTSAudio


@dataclass
class FakeUser:
    id: uuid.UUID


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, scalars=None):
        self._scalars = scalars or []

    def scalars(self):
        return FakeScalars(self._scalars)


class FakeDb:
    def __init__(self):
        self.added = []
        self.flushed = False
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid.uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime(2026, 7, 7, 9, 0, tzinfo=timezone.utc)

    async def execute(self, statement):
        return FakeResult(scalars=list(self.added))

    async def commit(self):
        self.committed = True


class FakeUpload:
    filename = "voice.webm"
    content_type = "audio/webm"

    async def read(self):
        return b"voice-bytes"


async def fake_stream_chat(**kwargs):
    yield "voice "
    yield "reply"


class ChatVoiceRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_voice_message_transcribes_and_persists_chat(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with patch(
            "app.routers.chat.subscription_service.ensure_chat_quota",
            new_callable=AsyncMock,
            return_value={"limit": 20, "used": 0, "remaining": 20},
        ) as ensure_quota, patch(
            "app.routers.chat.voice_service.transcribe",
            new_callable=AsyncMock,
            return_value="I feel anxious in this voice note.",
        ) as transcribe, patch(
            "app.routers.chat.ai_service.stream_chat",
            side_effect=fake_stream_chat,
        ), patch(
            "app.routers.chat.relationship_service.on_chat",
            new_callable=AsyncMock,
        ) as on_chat, patch(
            "app.routers.chat.record_emotion_from_text",
            new_callable=AsyncMock,
        ) as record_emotion, patch(
            "app.routers.chat.extract_memory.delay",
        ) as extract_memory:
            response = await send_voice_message(
                character_id="yinyue",
                audio=FakeUpload(),
                transcript="I feel anxious in this voice note.",
                include_tts=False,
                user=user,
                db=db,
            )

        self.assertEqual(response.transcript, "I feel anxious in this voice note.")
        self.assertEqual(response.reply, "voice reply")
        self.assertEqual(db.added[0].message_type, "voice")
        self.assertEqual(db.added[1].role, "assistant")
        self.assertTrue(db.committed)
        transcribe.assert_awaited_once()
        ensure_quota.assert_awaited_once()
        on_chat.assert_awaited_once()
        record_emotion.assert_awaited_once()
        extract_memory.assert_called_once()
        self.assertEqual(response.tts_status, "not_requested")
        self.assertIsNone(response.tts_audio_base64)

    async def test_send_voice_message_can_include_tts_audio(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with patch(
            "app.routers.chat.subscription_service.ensure_chat_quota",
            new_callable=AsyncMock,
            return_value={"limit": 20, "used": 0, "remaining": 20},
        ), patch(
            "app.routers.chat.voice_service.transcribe",
            new_callable=AsyncMock,
            return_value="I feel calm in this voice note.",
        ), patch(
            "app.routers.chat.ai_service.stream_chat",
            side_effect=fake_stream_chat,
        ), patch(
            "app.routers.chat.relationship_service.on_chat",
            new_callable=AsyncMock,
        ), patch(
            "app.routers.chat.record_emotion_from_text",
            new_callable=AsyncMock,
        ), patch(
            "app.routers.chat.extract_memory.delay",
        ), patch(
            "app.routers.chat.tts_service.is_configured",
            return_value=True,
        ), patch(
            "app.routers.chat.tts_service.synthesize",
            new_callable=AsyncMock,
            return_value=TTSAudio(
                audio_bytes=b"mp3-bytes",
                content_type="audio/mpeg",
                format="mp3",
            ),
        ) as synthesize:
            response = await send_voice_message(
                character_id="yinyue",
                audio=FakeUpload(),
                transcript="I feel calm in this voice note.",
                include_tts=True,
                user=user,
                db=db,
            )

        synthesize.assert_awaited_once_with("voice reply")
        self.assertEqual(response.tts_status, "generated")
        self.assertEqual(response.tts_audio_base64, "bXAzLWJ5dGVz")
        self.assertEqual(response.tts_content_type, "audio/mpeg")
        self.assertEqual(response.tts_format, "mp3")

    async def test_send_voice_message_reports_disabled_tts_when_not_configured(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with patch(
            "app.routers.chat.subscription_service.ensure_chat_quota",
            new_callable=AsyncMock,
            return_value={"limit": 20, "used": 0, "remaining": 20},
        ), patch(
            "app.routers.chat.voice_service.transcribe",
            new_callable=AsyncMock,
            return_value="I feel calm in this voice note.",
        ), patch(
            "app.routers.chat.ai_service.stream_chat",
            side_effect=fake_stream_chat,
        ), patch(
            "app.routers.chat.relationship_service.on_chat",
            new_callable=AsyncMock,
        ), patch(
            "app.routers.chat.record_emotion_from_text",
            new_callable=AsyncMock,
        ), patch(
            "app.routers.chat.extract_memory.delay",
        ), patch(
            "app.routers.chat.tts_service.is_configured",
            return_value=False,
        ), patch(
            "app.routers.chat.tts_service.synthesize",
            new_callable=AsyncMock,
        ) as synthesize:
            response = await send_voice_message(
                character_id="yinyue",
                audio=FakeUpload(),
                transcript="I feel calm in this voice note.",
                include_tts=True,
                user=user,
                db=db,
            )

        synthesize.assert_not_awaited()
        self.assertEqual(response.tts_status, "disabled")
        self.assertIsNone(response.tts_audio_base64)

    async def test_send_voice_message_blocks_when_subscription_quota_is_used_up(self):
        user = FakeUser(id=uuid.uuid4())
        db = FakeDb()

        with patch(
            "app.routers.chat.subscription_service.ensure_chat_quota",
            new_callable=AsyncMock,
            side_effect=SubscriptionLimitError(
                {"limit": 20, "used": 20, "remaining": 0}
            ),
        ), patch(
            "app.routers.chat.voice_service.transcribe",
            new_callable=AsyncMock,
        ) as transcribe:
            with self.assertRaises(HTTPException) as ctx:
                await send_voice_message(
                    character_id="yinyue",
                    audio=FakeUpload(),
                    transcript="I should not be transcribed.",
                    include_tts=False,
                    user=user,
                    db=db,
                )

        self.assertEqual(ctx.exception.status_code, 402)
        self.assertEqual(ctx.exception.detail["code"], "subscription_limit_reached")
        transcribe.assert_not_awaited()
        self.assertEqual(db.added, [])


if __name__ == "__main__":
    unittest.main()
