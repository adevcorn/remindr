"""Speech-to-text service using Google Cloud Speech API."""

import asyncio
import base64
from typing import Optional

from app.core.config import settings
from google.cloud import speech_v1
from google.cloud.speech_v1 import types


class SpeechToTextService:
    """Service for converting speech to text."""

    def __init__(self):
        """Initialize Google Cloud Speech client."""
        self.client = speech_v1.SpeechClient()

    async def transcribe_audio(
        self, audio_data: bytes, language_code: str = "en-US"
    ) -> tuple[Optional[str], float]:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes
            language_code: Language code (default: en-US)

        Returns:
            Tuple of (transcribed_text, confidence_score)
        """

        def _transcribe_blocking():
            """Blocking I/O operation for speech recognition."""
            audio = types.RecognitionAudio(content=audio_data)
            config = types.RecognitionConfig(
                encoding=types.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="latest_long",
            )

            try:
                response = self.client.recognize(config=config, audio=audio)

                if not response.results:
                    return None, 0.0

                # Get the first result with highest confidence
                result = response.results[0]
                if not result.alternatives:
                    return None, 0.0

                alternative = result.alternatives[0]
                return alternative.transcript, alternative.confidence

            except Exception as e:
                raise Exception(f"Speech-to-text failed: {str(e)}")

        # Run blocking call in thread pool
        return await asyncio.to_thread(_transcribe_blocking)


# Singleton instance
speech_service = SpeechToTextService()
