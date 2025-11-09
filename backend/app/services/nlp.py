"""NLP service for intent classification and entity extraction.

Optimized for <500ms inference using lightweight models and async processing.
"""
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re
import asyncio
from functools import lru_cache
import numpy as np
from app.models.capture import DraftType


class NLPService:
    """Service for AI-powered intent classification and entity extraction.
    
    Performance optimizations:
    - Uses sentence-transformers/all-MiniLM-L6-v2 (80MB, ~100-200ms)
    - Async inference with asyncio.to_thread for non-blocking
    - Semantic similarity + rule-based classification
    - Cached embeddings for common patterns
    - Target: <500ms total inference time
    """

    def __init__(self):
        """Initialize lightweight NLP models."""
        # Use efficient sentence transformer (80-100MB, ~100-200ms inference)
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Pre-compute embeddings for intent patterns (cached)
        self.task_patterns = [
            "buy groceries", "call the dentist", "submit report",
            "finish homework", "write email", "review document",
            "prepare presentation", "update code", "fix bug"
        ]
        
        self.event_patterns = [
            "meeting tomorrow", "conference next week", "lunch with",
            "doctor appointment", "flight to", "birthday party",
            "team standup", "presentation at", "call scheduled"
        ]
        
        self.note_patterns = [
            "remember that", "don't forget", "note to self",
            "keep in mind", "important info", "reference"
        ]
        
        # Pre-compute pattern embeddings (done once at startup)
        self.task_embeddings = self.model.encode(self.task_patterns, convert_to_tensor=True)
        self.event_embeddings = self.model.encode(self.event_patterns, convert_to_tensor=True)
        self.note_embeddings = self.model.encode(self.note_patterns, convert_to_tensor=True)
        
        # Confidence threshold for auto-filing (from PRD)
        self.auto_file_threshold = 0.85

    async def classify_and_extract(
        self,
        text: str
    ) -> tuple[DraftType, float, Dict[str, Any]]:
        """
        Classify intent and extract entities from text.
        
        Optimized for <500ms total time:
        - Async embedding generation (~100-200ms)
        - Parallel entity extraction (~50-100ms)
        - Rule-based confidence boosting (~10ms)

        Args:
            text: Input text to analyze

        Returns:
            Tuple of (draft_type, confidence, extracted_entities)
        """
        # Run classification and entity extraction in parallel
        classification_task = self._classify_intent(text)
        entity_extraction_task = self._extract_entities_async(text)
        
        # Await both concurrently
        (draft_type, base_confidence), entities = await asyncio.gather(
            classification_task,
            entity_extraction_task
        )
        
        # Boost confidence based on extracted entities
        confidence = self._adjust_confidence(
            base_confidence, draft_type, entities, text
        )
        
        return draft_type, confidence, entities
    
    async def _classify_intent(self, text: str) -> tuple[DraftType, float]:
        """
        Classify text intent using semantic similarity + rule-based.
        
        Uses lightweight sentence-transformers for fast inference.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (draft_type, confidence_score)
        """
        # Generate embedding asynchronously (non-blocking)
        text_embedding = await asyncio.to_thread(
            self.model.encode, text, convert_to_tensor=True
        )
        
        # Compute cosine similarity with pattern embeddings
        from sentence_transformers import util
        
        task_scores = util.pytorch_cos_sim(text_embedding, self.task_embeddings)[0]
        event_scores = util.pytorch_cos_sim(text_embedding, self.event_embeddings)[0]
        note_scores = util.pytorch_cos_sim(text_embedding, self.note_embeddings)[0]
        
        # Get max similarity for each category
        task_similarity = float(task_scores.max())
        event_similarity = float(event_scores.max())
        note_similarity = float(note_scores.max())
        
        # Rule-based boosting for clear indicators
        text_lower = text.lower()
        
        # Event indicators (meetings, appointments, time-based)
        event_keywords = [
            "meeting", "appointment", "call", "conference", "lunch", "dinner",
            "party", "event", "scheduled", "at ", "tomorrow at", "today at"
        ]
        has_event_keyword = any(kw in text_lower for kw in event_keywords)
        has_time = self._has_time_pattern(text)
        
        if has_event_keyword or has_time:
            event_similarity += 0.2  # Boost event score
        
        # Task indicators (action verbs, TODO-like)
        task_keywords = [
            "buy", "call", "send", "write", "submit", "finish", "complete",
            "review", "prepare", "update", "fix", "create", "schedule", "book"
        ]
        has_task_keyword = any(kw in text_lower for kw in task_keywords)
        
        if has_task_keyword and not has_time:
            task_similarity += 0.15  # Boost task score
        
        # Note indicators (passive, reminder-like)
        note_keywords = ["remember", "note", "don't forget", "keep in mind"]
        has_note_keyword = any(kw in text_lower for kw in note_keywords)
        
        if has_note_keyword:
            note_similarity += 0.1
        
        # Determine winner
        max_score = max(task_similarity, event_similarity, note_similarity)
        
        if max_score == event_similarity:
            draft_type = DraftType.EVENT
            confidence = min(event_similarity, 1.0)
        elif max_score == task_similarity:
            draft_type = DraftType.TASK
            confidence = min(task_similarity, 1.0)
        else:
            draft_type = DraftType.NOTE
            confidence = min(note_similarity, 1.0)
        
        # Normalize confidence to 0.0-1.0 range
        # Cosine similarity is -1 to 1, but we're seeing 0-1 range
        confidence = max(0.0, min(1.0, confidence))
        
        return draft_type, confidence
    
    def _has_time_pattern(self, text: str) -> bool:
        """Check if text contains time patterns."""
        time_pattern = r'(?:at|@)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?'
        return bool(re.search(time_pattern, text.lower()))
    
    async def _extract_entities_async(self, text: str) -> Dict[str, Any]:
        """Extract entities asynchronously."""
        # Run entity extraction in thread pool (CPU-bound regex operations)
        return await asyncio.to_thread(self._extract_entities, text)
    
    def _adjust_confidence(
        self,
        base_confidence: float,
        draft_type: DraftType,
        entities: Dict[str, Any],
        text: str
    ) -> float:
        """
        Adjust confidence based on extracted entities and text quality.
        
        Boosts confidence when:
        - Task has priority or due date
        - Event has start_time and location
        - Text is clear and well-formed
        
        Args:
            base_confidence: Initial confidence score
            draft_type: Classified draft type
            entities: Extracted entities
            text: Original input text
            
        Returns:
            Adjusted confidence score (0.0-1.0)
        """
        confidence = base_confidence
        
        # Boost for tasks with clear deadline
        if draft_type == DraftType.TASK:
            if entities.get("due_date"):
                confidence += 0.05
            if entities.get("priority") in ["high", "low"]:
                confidence += 0.03
        
        # Boost for events with time and location
        elif draft_type == DraftType.EVENT:
            if entities.get("start_time"):
                confidence += 0.05
            if entities.get("location"):
                confidence += 0.03
        
        # Penalize very short or unclear text
        if len(text.split()) < 3:
            confidence -= 0.1
        
        # Cap at 1.0
        return max(0.0, min(1.0, confidence))

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract structured entities from text.

        Args:
            text: Input text

        Returns:
            Dictionary of extracted entities
        """
        entities: Dict[str, Any] = {
            "title": text,  # Default to full text
            "description": None,
            "due_date": None,
            "start_time": None,
            "end_time": None,
            "priority": None,
            "location": None,
            "tags": []
        }
        
        # Extract date/time patterns
        date_time = self._extract_datetime(text)
        if date_time:
            if date_time["date"]:
                entities["due_date"] = date_time["date"]
            if date_time["start_time"]:
                entities["start_time"] = date_time["start_time"]
            if date_time["end_time"]:
                entities["end_time"] = date_time["end_time"]
        
        # Extract priority
        priority = self._extract_priority(text)
        if priority:
            entities["priority"] = priority
        
        # Extract location (simple pattern matching)
        location = self._extract_location(text)
        if location:
            entities["location"] = location
        
        # Extract tags (hashtags)
        tags = self._extract_tags(text)
        if tags:
            entities["tags"] = tags
        
        # Clean up title (remove extracted datetime/priority phrases)
        entities["title"] = self._clean_title(text, date_time, priority)
        
        return entities

    def _extract_datetime(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract date and time from text using pattern matching."""
        now = datetime.now()
        result: Dict[str, Any] = {"date": None, "start_time": None, "end_time": None}
        
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
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract hashtags from text."""
        # Find all hashtags (#tag)
        tag_pattern = r'#(\w+)'
        matches = re.findall(tag_pattern, text)
        return matches if matches else []

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
        
        # Remove hashtags (already extracted as tags)
        cleaned = re.sub(r'#\w+', '', cleaned)
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned.strip()


# Singleton instance
nlp_service = NLPService()
