"""Voice message transcription service."""

from __future__ import annotations

from io import BytesIO

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


class VoiceTranscriptionError(RuntimeError):
    pass


class VoiceService:
    max_audio_bytes = 10 * 1024 * 1024

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str | None,
        transcript_fallback: str | None = None,
    ) -> str:
        fallback = self._normalize(transcript_fallback or "")
        if fallback:
            return fallback

        if not audio_bytes:
            raise VoiceTranscriptionError("Voice audio is empty")
        if len(audio_bytes) > self.max_audio_bytes:
            raise VoiceTranscriptionError("Voice audio is too large")

        provider_errors: list[str] = []
        if settings.fish_audio_api_key.strip():
            try:
                return await self._transcribe_with_fish_audio(
                    audio_bytes=audio_bytes,
                    filename=filename,
                    content_type=content_type,
                )
            except VoiceTranscriptionError as exc:
                provider_errors.append(f"Fish Audio ASR: {exc}")

        if settings.openai_api_key.strip():
            try:
                return await self._transcribe_with_openai(
                    audio_bytes=audio_bytes,
                    filename=filename,
                )
            except VoiceTranscriptionError as exc:
                provider_errors.append(f"OpenAI ASR: {exc}")

        if provider_errors:
            raise VoiceTranscriptionError("; ".join(provider_errors))
        raise VoiceTranscriptionError("ASR provider is not configured")

    async def _transcribe_with_fish_audio(
        self,
        audio_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> str:
        url = f"{settings.fish_audio_base_url.rstrip('/')}/v1/asr"
        headers = {"Authorization": f"Bearer {settings.fish_audio_api_key}"}
        data = {
            "ignore_timestamps": str(settings.fish_audio_asr_ignore_timestamps).lower()
        }
        language = settings.fish_audio_asr_language.strip()
        if language:
            data["language"] = language
        files = {
            "audio": (
                filename or "voice.webm",
                audio_bytes,
                content_type or "application/octet-stream",
            )
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    files=files,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise VoiceTranscriptionError(
                f"provider returned {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise VoiceTranscriptionError(f"request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise VoiceTranscriptionError("provider returned invalid JSON") from exc

        text = payload.get("text", "") if isinstance(payload, dict) else ""
        transcript = self._normalize(str(text))
        if not transcript:
            raise VoiceTranscriptionError("provider returned empty transcript")
        return transcript

    async def _transcribe_with_openai(
        self,
        audio_bytes: bytes,
        filename: str,
    ) -> str:
        if not settings.openai_api_key.strip():
            raise VoiceTranscriptionError("ASR provider is not configured")

        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        audio_file = BytesIO(audio_bytes)
        audio_file.name = filename or "voice.webm"

        try:
            result = await client.audio.transcriptions.create(
                model=settings.openai_audio_transcription_model,
                file=audio_file,
                response_format="text",
            )
        except Exception as exc:
            raise VoiceTranscriptionError(f"ASR transcription failed: {exc}") from exc

        if isinstance(result, str):
            text = result
        else:
            text = getattr(result, "text", "")

        transcript = self._normalize(text)
        if not transcript:
            raise VoiceTranscriptionError("ASR returned empty transcript")
        return transcript

    def _normalize(self, text: str) -> str:
        return " ".join(text.strip().split())[:4000]


voice_service = VoiceService()
