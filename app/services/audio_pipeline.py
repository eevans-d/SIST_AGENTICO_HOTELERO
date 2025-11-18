"""
# Audio pipeline: quality checks, retrying transcription, streaming TTS orchestration,
# and unified generate_audio_response that chooses provider with fallback.
# Designed to be test-friendly via dependency injection.
"""
import asyncio
import math
import random
from typing import Optional, Dict, Any, Callable

DEFAULT_RETRY_ATTEMPTS = 4
BASE_BACKOFF = 0.5  # seconds
MAX_BACKOFF = 8.0

class AudioQualityError(Exception):
    pass

class AudioPipeline:
    def __init__(self, audio_processor=None, tts_manager=None, logger=None):
        # audio_processor must implement transcribe(media_url, tenant_id) or transcribe_bytes
        self.audio_processor = audio_processor
        self.tts_manager = tts_manager
        self.logger = logger or __import__("logging").getLogger(__name__)    

    async def _sleep_backoff(self, attempt: int):
        backoff = min(MAX_BACKOFF, BASE_BACKOFF * (2 ** (attempt - 1)))
        # jitter
        backoff = backoff * (0.8 + random.random() * 0.4)
        await asyncio.sleep(backoff)

    async def transcribe_with_retry(self, media_url: str, tenant_id: Optional[str] = None, attempts: int = DEFAULT_RETRY_ATTEMPTS) -> Dict[str, Any]:
        """
        Retry wrapper for transcription with exponential backoff.
        Returns dict: {"text": str, "confidence": float, "language": str}
        """
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                # allow audio_processor to accept tenant_id
                transcribe_fn = getattr(self.audio_processor, "transcribe", None)
                if transcribe_fn is None:
                    # fallback to transcribe_whatsapp_audio or similar
                    transcribe_fn = getattr(self.audio_processor, "transcribe_whatsapp_audio", None)
                if transcribe_fn is None:
                    raise RuntimeError("No transcription function available")
                result = transcribe_fn(media_url, tenant_id=tenant_id) if not asyncio.iscoroutinefunction(transcribe_fn) else await transcribe_fn(media_url, tenant_id=tenant_id)
                return result or {}
            except Exception as e:
                last_exc = e
                self.logger.warning("transcribe_attempt_failed", attempt=attempt, error=str(e), tenant_id=tenant_id)
                if attempt < attempts:
                    await self._sleep_backoff(attempt)
                else:
                    self.logger.error("transcribe_all_attempts_failed", tenant_id=tenant_id, error=str(last_exc))
                    raise last_exc

    def validate_audio_quality(self, audio_info: Dict[str, Any]) -> None:
        """
        audio_info should contain keys: duration_seconds, sample_rate, channels, format, rms or similar
        Raises AudioQualityError if below thresholds.
        """
        duration = audio_info.get("duration_seconds", 0)
        fmt = (audio_info.get("format") or "").lower()
        rms = audio_info.get("rms", None)  # root-mean-square amplitude (proxy SNR)
        if duration < 0.2:
            raise AudioQualityError("audio_too_short")
        if duration > 600:  # safety cap
            raise AudioQualityError("audio_too_long")
        if fmt not in ("wav", "mp3", "m4a", "ogg", "opus"):
            raise AudioQualityError("unsupported_format")
        if rms is not None and rms < 0.001:
            raise AudioQualityError("low_snr")

    async def generate_audio_response(self, text: str, tenant_id: Optional[str] = None, voice: Optional[str] = None, content_type: Optional[str] = None, stream_threshold: int = 30) -> Optional[bytes]:
        """
        Choose best TTS provider via tts_manager and return bytes.
        If text > stream_threshold seconds estimate, request streaming/chunked output.
        """
        # estimate seconds roughly by words -> seconds (at 150 wpm => 2.5 wps)
        words = len(text.split())
        est_seconds = words / 2.5
        use_stream = est_seconds > stream_threshold

        if not self.tts_manager:
            self.logger.debug("tts_manager_missing", tenant_id=tenant_id)
            return None

        # Providers should implement generate(text, voice, stream=False, tenant_id=None)
        try:
            if use_stream and hasattr(self.tts_manager, "generate_stream"):
                # collect streamed chunks
                chunks = []
                async for c in self.tts_manager.generate_stream(text, voice=voice, tenant_id=tenant_id):
                    chunks.append(c)
                return b"".join(chunks) if chunks else None
            return await self.tts_manager.generate(text, voice=voice, tenant_id=tenant_id)
        except Exception as e:
            self.logger.error("tts_generation_failed", error=str(e), tenant_id=tenant_id)
            return None
