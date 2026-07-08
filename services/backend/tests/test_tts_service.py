import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.tts_service import TTSGenerationError, TTSService


class TTSServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_synthesize_requires_provider_config(self):
        service = TTSService()

        with patch("app.services.tts_service.settings.fish_audio_api_key", ""):
            with self.assertRaises(TTSGenerationError) as ctx:
                await service.synthesize("hello")

        self.assertIn("TTS provider", str(ctx.exception))

    async def test_synthesize_rejects_empty_text(self):
        service = TTSService()

        with self.assertRaises(TTSGenerationError) as ctx:
            await service.synthesize("   ")

        self.assertIn("empty", str(ctx.exception).lower())

    async def test_synthesize_posts_to_fish_audio(self):
        service = TTSService()
        calls = {}

        class FakeResponse:
            headers = {"content-type": "audio/mpeg"}
            content = b"mp3-bytes"

            def raise_for_status(self):
                return None

        class FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, url, headers, json):
                calls["url"] = url
                calls["headers"] = headers
                calls["json"] = json
                return FakeResponse()

        with patch("app.services.tts_service.settings.fish_audio_api_key", "fish-key"):
            with patch(
                "app.services.tts_service.settings.fish_audio_reference_id",
                "voice-ref",
            ):
                with patch(
                    "app.services.tts_service.settings.fish_audio_base_url",
                    "https://fish.example",
                ):
                    with patch(
                        "app.services.tts_service.settings.fish_audio_tts_model",
                        "s2-pro",
                    ):
                        with patch(
                            "app.services.tts_service.httpx.AsyncClient",
                            return_value=FakeClient(),
                        ):
                            audio = await service.synthesize("  hello   there  ")

        self.assertEqual(audio.audio_bytes, b"mp3-bytes")
        self.assertEqual(audio.content_type, "audio/mpeg")
        self.assertEqual(audio.format, "mp3")
        self.assertEqual(calls["url"], "https://fish.example/v1/tts")
        self.assertEqual(calls["headers"]["Authorization"], "Bearer fish-key")
        self.assertEqual(calls["headers"]["model"], "s2-pro")
        self.assertEqual(calls["json"]["text"], "hello there")
        self.assertEqual(calls["json"]["reference_id"], "voice-ref")
        self.assertEqual(calls["json"]["format"], "mp3")


if __name__ == "__main__":
    unittest.main()
