"""Pydantic schemas for capture API."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.capture import CaptureType, CaptureState, DraftType


class CaptureCreate(BaseModel):
    """Schema for creating a new capture."""
    capture_type: CaptureType
    raw_text: Optional[str] = None
    audio_data: Optional[str] = None  # Base64 encoded audio
    image_data: Optional[str] = None  # Base64 encoded image


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
    title: Optional[str] = None  # Allow user to edit
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None


class SyncStatus(BaseModel):
    """Schema for sync status response."""
    draft_id: int
    sync_state: CaptureState
    google_task_id: Optional[str]
    google_event_id: Optional[str]
    synced_at: Optional[datetime]
    error_message: Optional[str]
