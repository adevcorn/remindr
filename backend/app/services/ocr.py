"""OCR service using Google Cloud Vision API."""

import asyncio
import base64
from typing import Optional

from google.cloud import vision


class OCRService:
    """Service for extracting text from images."""

    def __init__(self):
        """Initialize Google Cloud Vision client lazily."""
        self._client = None

    @property
    def client(self):
        """Lazy-load the Google Cloud Vision client."""
        if self._client is None:
            self._client = vision.ImageAnnotatorClient()
        return self._client

    async def extract_text(self, image_data: bytes) -> tuple[Optional[str], float]:
        """
        Extract text from image using OCR.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (extracted_text, confidence_score)
        """

        def _extract_text_blocking():
            """Blocking I/O operation for OCR."""
            image = vision.Image(content=image_data)

            try:
                # Use document_text_detection for better handwriting support
                response = self.client.document_text_detection(image=image)

                if response.error.message:
                    raise Exception(f"OCR API error: {response.error.message}")

                if not response.full_text_annotation:
                    return None, 0.0

                text = response.full_text_annotation.text

                # Calculate average confidence from all detected words
                confidence = 0.0
                word_count = 0

                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        for paragraph in block.paragraphs:
                            for word in paragraph.words:
                                confidence += word.confidence
                                word_count += 1

                avg_confidence = confidence / word_count if word_count > 0 else 0.0

                return text.strip(), avg_confidence

            except Exception as e:
                raise Exception(f"OCR failed: {str(e)}")

        # Run blocking call in thread pool
        return await asyncio.to_thread(_extract_text_blocking)


# Singleton instance
ocr_service = OCRService()
