"""NLP service for intent classification and entity extraction."""
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import re
from app.models.capture import DraftType


class NLPService:
    """Service for AI-powered intent classification and entity extraction."""

    def __init__(self):
        """Initialize NLP models."""
        # Use a pre-trained model for intent classification
        # In production, this would be fine-tuned on task/event data
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
        # Intent categories
        self.candidate_labels = ["task", "event", "note", "reminder"]

    async def classify_and_extract(
        self,
        text: str
    ) -> tuple[DraftType, float, Dict[str, Any]]:
        """
        Classify intent and extract entities from text.

        Args:
            text: Input text to analyze

        Returns:
            Tuple of (draft_type, confidence, extracted_entities)
        """
        # Classify intent
        classification = self.classifier(text, self.candidate_labels)
        intent = classification["labels"][0]
        confidence = classification["scores"][0]
        
        # Map intent to DraftType
        if intent in ["event", "reminder"]:
            draft_type = DraftType.EVENT
        elif intent == "task":
            draft_type = DraftType.TASK
        else:
            draft_type = DraftType.NOTE
        
        # Extract entities
        entities = self._extract_entities(text)
        
        return draft_type, confidence, entities

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract structured entities from text.

        Args:
            text: Input text

        Returns:
            Dictionary of extracted entities
        """
        entities = {
            "title": text,  # Default to full text
            "description": None,
            "due_date": None,
            "start_time": None,
            "end_time": None,
            "priority": None,
            "location": None
        }
        
        # Extract date/time patterns
        date_time = self._extract_datetime(text)
        if date_time:
            entities["due_date"] = date_time["date"]
            entities["start_time"] = date_time["start_time"]
            entities["end_time"] = date_time["end_time"]
        
        # Extract priority
        priority = self._extract_priority(text)
        if priority:
            entities["priority"] = priority
        
        # Extract location (simple pattern matching)
        location = self._extract_location(text)
        if location:
            entities["location"] = location
        
        # Clean up title (remove extracted datetime/priority phrases)
        entities["title"] = self._clean_title(text, date_time, priority)
        
        return entities

    def _extract_datetime(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract date and time from text using pattern matching."""
        now = datetime.now()
        result = {"date": None, "start_time": None, "end_time": None}
        
        # Relative dates
        if "tomorrow" in text.lower():
            result["date"] = now + timedelta(days=1)
        elif "today" in text.lower():
            result["date"] = now
        elif "next week" in text.lower():
            result["date"] = now + timedelta(weeks=1)
        
        # Day of week
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if day in text.lower():
                # Calculate next occurrence of this day
                days_ahead = i - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                result["date"] = now + timedelta(days=days_ahead)
                break
        
        # Time patterns (e.g., "at 14:00", "at 2pm", "at 8:30am")
        time_pattern = r'(?:at|@)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
        time_match = re.search(time_pattern, text.lower())
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3)
            
            if period == "pm" and hour < 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0
            
            if result["date"]:
                result["start_time"] = result["date"].replace(hour=hour, minute=minute)
            else:
                result["start_time"] = now.replace(hour=hour, minute=minute)
        
        return result if any(result.values()) else None

    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from text."""
        text_lower = text.lower()
        if any(word in text_lower for word in ["urgent", "important", "critical", "asap"]):
            return "high"
        elif any(word in text_lower for word in ["low priority", "whenever", "someday"]):
            return "low"
        return "medium"

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text using simple patterns."""
        # Pattern: "at [location]" or "in [location]"
        location_pattern = r'(?:at|in)\s+([A-Z][a-zA-Z\s]+?)(?:\s+(?:tomorrow|today|on|at|\d)|\.|$)'
        match = re.search(location_pattern, text)
        if match:
            return match.group(1).strip()
        return None

    def _clean_title(
        self,
        text: str,
        date_time: Optional[Dict[str, Any]],
        priority: Optional[str]
    ) -> str:
        """Clean up title by removing extracted information."""
        cleaned = text
        
        # Remove date/time phrases
        for phrase in ["tomorrow", "today", "next week", "monday", "tuesday", "wednesday",
                      "thursday", "friday", "saturday", "sunday"]:
            cleaned = re.sub(rf'\b{phrase}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove time patterns
        cleaned = re.sub(r'(?:at|@)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?', '', cleaned, flags=re.IGNORECASE)
        
        # Remove priority keywords
        for phrase in ["urgent", "important", "critical", "asap", "low priority"]:
            cleaned = re.sub(rf'\b{phrase}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()


# Singleton instance
nlp_service = NLPService()
