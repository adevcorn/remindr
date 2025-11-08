"""OCR service using Google Cloud Vision API."""
import base64
from google.cloud import vision
from typing import Optional


class OCRService:
    """Service for extracting text from images."""

    def __init__(self):
        """Initialize Google Cloud Vision client."""
        self.client = vision.ImageAnnotatorClient()

    async def extract_text(self, image_data: bytes) -> tuple[Optional[str], float]:
        """
        Extract text from image using OCR.

        Args:
            image_data: Raw image bytes

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
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


# Singleton instance
ocr_service = OCRService()
