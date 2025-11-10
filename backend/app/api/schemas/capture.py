"""Pydantic schemas for capture API."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.capture import CaptureState, CaptureType, DraftType

# Size limits (in characters for base64 strings)
MAX_TEXT_LENGTH = 5000
MAX_AUDIO_SIZE = 10_000_000  # ~7.5MB of audio (base64 encoded)
MAX_IMAGE_SIZE = 15_000_000  # ~11MB of image (base64 encoded)


class CaptureCreate(BaseModel):
    """Schema for creating a new capture."""

    capture_type: CaptureType
    raw_text: Optional[str] = Field(None, max_length=MAX_TEXT_LENGTH)
    audio_data: Optional[str] = Field(
        None, max_length=MAX_AUDIO_SIZE
    )  # Base64 encoded audio
    image_data: Optional[str] = Field(
        None, max_length=MAX_IMAGE_SIZE
    )  # Base64 encoded image

    @field_validator("raw_text")
    @classmethod
    def validate_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Text cannot be empty")
        return v

    @field_validator("audio_data")
    @classmethod
    def validate_audio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Audio data cannot be empty")
        return v

    @field_validator("image_data")
    @classmethod
    def validate_image(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Image data cannot be empty")
        return v


class CaptureResponse(BaseModel):
    """Schema for capture response."""

    id: int
    user_id: str
    capture_type: CaptureType
    state: CaptureState
    raw_text: Optional[str]
    ai_confidence: Optional[float]
    error_message: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class DraftResponse(BaseModel):
    """Schema for draft response."""

    id: int
    capture_id: int
    user_id: str
    draft_type: DraftType
    ai_confidence: float
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: Optional[str]
    location: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    is_confirmed: bool
    sync_state: CaptureState
    created_at: datetime

    class Config:
        from_attributes = True


class DraftConfirm(BaseModel):
    """Schema for confirming a draft."""

    draft_id: int
    title: Optional[str] = Field(None, max_length=500)  # Allow user to edit
    description: Optional[str] = Field(None, max_length=5000)
    due_date: Optional[datetime] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")


class SyncStatus(BaseModel):
    """Schema for sync status response."""

    draft_id: int
    sync_state: CaptureState
    google_task_id: Optional[str]
    google_event_id: Optional[str]
    synced_at: Optional[datetime]
    error_message: Optional[str]
