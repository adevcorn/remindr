"""Database models for captures and drafts."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class CaptureType(str, enum.Enum):
    """Type of user capture input."""
    VOICE = "voice"
    TEXT = "text"
    IMAGE = "image"


class CaptureState(str, enum.Enum):
    """State of capture processing."""
    QUEUED = "queued"
    PROCESSING = "processing"
    PARSED = "parsed"
    CONFIRMED = "confirmed"
    SYNCING = "syncing"
    SYNCED = "synced"
    ERROR = "error"
    NEEDS_REVIEW = "needs_review"


class DraftType(str, enum.Enum):
    """Type of draft item."""
    TASK = "task"
    EVENT = "event"
    NOTE = "note"


class Capture(Base):
    """User capture input (voice, text, or image)."""
    __tablename__ = "captures"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    capture_type = Column(Enum(CaptureType), nullable=False)
    state = Column(Enum(CaptureState), default=CaptureState.QUEUED, nullable=False)
    
    # Raw input data
    raw_text = Column(Text, nullable=True)  # For text capture or transcribed voice
    audio_url = Column(String, nullable=True)  # Cloud storage URL for audio
    image_url = Column(String, nullable=True)  # Cloud storage URL for image
    
    # Processing metadata
    ai_confidence = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class Draft(Base):
    """AI-parsed structured draft (task or event)."""
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, index=True)
    capture_id = Column(Integer, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    
    # Classification
    draft_type = Column(Enum(DraftType), nullable=False)
    ai_confidence = Column(Float, nullable=False)
    
    # Extracted fields
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    priority = Column(String, nullable=True)  # high, medium, low
    location = Column(String, nullable=True)
    
    # Event-specific fields
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Sync state
    is_confirmed = Column(Boolean, default=False)
    google_task_id = Column(String, nullable=True)
    google_event_id = Column(String, nullable=True)
    sync_state = Column(Enum(CaptureState), default=CaptureState.PARSED)
    
    # Metadata
    extracted_entities = Column(JSONB, nullable=True)  # Full NLP output
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    synced_at = Column(DateTime(timezone=True), nullable=True)
