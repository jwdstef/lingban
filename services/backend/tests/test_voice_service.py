import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from app.services.voice_service import VoiceTranscriptionError, VoiceService


class VoiceServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_transcribe_uses_transcript_fallback_for_local_smoke(self):
        service = VoiceService()

        transcript = await service.transcribe(
            audio_bytes=b"not-real-audio",
            filename="voice.txt",
            content_type="text/plain",
            transcript_fallback="  I feel anxious after work.  ",
        )

        self.assertEqual(transcript, "I feel anxious after work.")

    async def test_transcribe_rejects_empty_audio_without_fallback(self):
        service = VoiceService()

        with self.assertRaises(VoiceTranscriptionError):
            await service.transcribe(
                audio_bytes=b"",
                filename="empty.webm",
                content_type="audio/webm",
            )

    async def test_transcribe_requires_asr_provider_without_fallback(self):
        service = VoiceService()

        with patch("app.services.voice_service.settings.fish_audio_api_key", ""):
            with patch("app.services.voice_service.settings.openai_api_key", ""):
                with self.assertRaises(VoiceTranscriptionError) as ctx:
                    await service.transcribe(
                        audio_bytes=b"audio-bytes",
                        filename="voice.webm",
                        content_type="audio/webm",
                    )

        self.assertIn("ASR", str(ctx.exception))

    async def test_transcribe_posts_to_fish_audio_when_configured(self):
        service = VoiceService()
        calls = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "text": " 今天好多了 ",
                    "duration": 1.2,
                    "segments": [],
                }

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers, data, files):
                calls["url"] = url
                calls["headers"] = headers
                calls["data"] = data
                calls["files"] = files
                return FakeResponse()

        with patch("app.services.voice_service.settings.fish_audio_api_key", "fish-key"):
            with patch(
                "app.services.voice_service.settings.fish_audio_base_url",
                "https://fish.example",
            ):
                with patch(
                    "app.services.voice_service.settings.fish_audio_asr_language",
                    "zh",
                ):
                    with patch(
                        "app.services.voice_service.settings.fish_audio_asr_ignore_timestamps",
                        True,
                    ):
                        with patch(
                            "app.services.voice_service.httpx.AsyncClient",
                            return_value=FakeClient(),
                        ):
                            transcript = await service.transcribe(
                                audio_bytes=b"audio-bytes",
                                filename="voice.wav",
                                content_type="audio/wav",
                            )

        self.assertEqual(transcript, "今天好多了")
        self.assertEqual(calls["url"], "https://fish.example/v1/asr")
        self.assertEqual(calls["headers"]["Authorization"], "Bearer fish-key")
        self.assertEqual(calls["data"]["language"], "zh")
        self.assertEqual(calls["data"]["ignore_timestamps"], "true")
        self.assertEqual(calls["files"]["audio"][0], "voice.wav")
        self.assertEqual(calls["files"]["audio"][1], b"audio-bytes")
        self.assertEqual(calls["files"]["audio"][2], "audio/wav")

    async def test_transcribe_falls_back_to_openai_when_fish_audio_fails(self):
        service = VoiceService()
        calls = {"fish": 0}

        class FailingFishClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers, data, files):
                calls["fish"] += 1
                raise httpx.ConnectError("fish unavailable")

        async def fake_create(model, file, response_format):
            calls["openai_model"] = model
            return "openai fallback transcript"

        fake_openai_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=fake_create),
            ),
        )

        with patch("app.services.voice_service.settings.fish_audio_api_key", "fish-key"):
            with patch("app.services.voice_service.settings.openai_api_key", "openai-key"):
                with patch(
                    "app.services.voice_service.settings.openai_audio_transcription_model",
                    "whisper-like",
                ):
                    with patch(
                        "app.services.voice_service.httpx.AsyncClient",
                        return_value=FailingFishClient(),
                    ):
                        with patch(
                            "app.services.voice_service.AsyncOpenAI",
                            return_value=fake_openai_client,
                        ):
                            transcript = await service.transcribe(
                                audio_bytes=b"audio-bytes",
                                filename="voice.webm",
                                content_type="audio/webm",
                            )

        self.assertEqual(transcript, "openai fallback transcript")
        self.assertEqual(calls["fish"], 1)
        self.assertEqual(calls["openai_model"], "whisper-like")

    async def test_transcribe_reports_provider_error_when_all_asr_attempts_fail(self):
        service = VoiceService()

        class FailingFishClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers, data, files):
                raise httpx.ConnectError("fish unavailable")

        with patch("app.services.voice_service.settings.fish_audio_api_key", "fish-key"):
            with patch("app.services.voice_service.settings.openai_api_key", ""):
                with patch(
                    "app.services.voice_service.httpx.AsyncClient",
                    return_value=FailingFishClient(),
                ):
                    with self.assertRaises(VoiceTranscriptionError) as ctx:
                        await service.transcribe(
                            audio_bytes=b"audio-bytes",
                            filename="voice.webm",
                            content_type="audio/webm",
                        )

        self.assertIn("Fish Audio ASR", str(ctx.exception))

    async def test_transcribe_uses_configured_openai_asr_model(self):
        service = VoiceService()
        calls = {}

        async def fake_create(model, file, response_format):
            calls["model"] = model
            calls["filename"] = file.name
            calls["response_format"] = response_format
            return "calm today"

        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=fake_create),
            ),
        )

        with patch("app.services.voice_service.settings.fish_audio_api_key", ""):
            with patch("app.services.voice_service.settings.openai_api_key", "test-key"):
                with patch(
                    "app.services.voice_service.settings.openai_audio_transcription_model",
                    "custom-asr",
                ):
                    with patch(
                        "app.services.voice_service.AsyncOpenAI",
                        return_value=fake_client,
                    ):
                        transcript = await service.transcribe(
                            audio_bytes=b"audio-bytes",
                            filename="voice.wav",
                            content_type="audio/wav",
                        )

        self.assertEqual(transcript, "calm today")
        self.assertEqual(calls["model"], "custom-asr")
        self.assertEqual(calls["filename"], "voice.wav")
        self.assertEqual(calls["response_format"], "text")


if __name__ == "__main__":
    unittest.main()
