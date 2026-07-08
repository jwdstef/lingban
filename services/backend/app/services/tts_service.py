"""Text-to-speech service for optional voice replies."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings


class TTSGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class TTSAudio:
    audio_bytes: bytes
    content_type: str
    format: str


class TTSService:
    max_text_chars = 1200

    def is_configured(self) -> bool:
        return bool(
            settings.fish_audio_api_key.strip()
            and settings.fish_audio_reference_id.strip()
        )

    async def synthesize(self, text: str, reference_id: str | None = None) -> TTSAudio:
        normalized_text = self._normalize(text)
        if not normalized_text:
            raise TTSGenerationError("TTS text is empty")
        if not settings.fish_audio_api_key.strip():
            raise TTSGenerationError("TTS provider is not configured")

        voice_reference_id = (reference_id or settings.fish_audio_reference_id).strip()
        if not voice_reference_id:
            raise TTSGenerationError("TTS voice reference is not configured")

        audio_format = (settings.fish_audio_tts_format or "mp3").strip().lower()
        url = f"{settings.fish_audio_base_url.rstrip('/')}/v1/tts"
        headers = {
            "Authorization": f"Bearer {settings.fish_audio_api_key}",
            "Content-Type": "application/json",
            "model": settings.fish_audio_tts_model,
        }
        payload = {
            "text": normalized_text,
            "reference_id": voice_reference_id,
            "format": audio_format,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise TTSGenerationError(
                f"TTS provider returned {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise TTSGenerationError(f"TTS request failed: {exc}") from exc

        if not response.content:
            raise TTSGenerationError("TTS provider returned empty audio")

        return TTSAudio(
            audio_bytes=response.content,
            content_type=response.headers.get("content-type") or self._content_type(audio_format),
            format=audio_format,
        )

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().split())[: self.max_text_chars]

    def _content_type(self, audio_format: str) -> str:
        if audio_format == "wav":
            return "audio/wav"
        if audio_format == "opus":
            return "audio/ogg"
        return "audio/mpeg"


tts_service = TTSService()
