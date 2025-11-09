"""Capture API endpoints."""

import base64
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas.capture import (
    CaptureCreate,
    CaptureResponse,
    DraftConfirm,
    DraftResponse,
    SyncStatus,
)
from app.core.auth import get_current_user_credentials, get_current_user_id
from app.core.config import settings
from app.db.session import get_db
from app.models.capture import Capture, CaptureState, CaptureType, Draft
from app.services.nlp import nlp_service
from app.services.ocr import ocr_service
from app.services.speech_to_text import speech_service
from app.services.tasks import sync_draft_to_google_with_retry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/captures", response_model=CaptureResponse, status_code=status.HTTP_201_CREATED
)
async def create_capture(
    capture: CaptureCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Create a new capture (voice, text, or image).
    Processes capture immediately and returns response < 3s.
    Background sync happens asynchronously without blocking.
    """
    # Create capture record
    db_capture = Capture(
        user_id=user_id,
        capture_type=capture.capture_type,
        state=CaptureState.QUEUED,
        raw_text=capture.raw_text,
    )

    db.add(db_capture)
    db.commit()
    db.refresh(db_capture)

    # Process asynchronously based on type
    try:
        if capture.capture_type == CaptureType.VOICE and capture.audio_data:
            # Decode base64 audio
            audio_bytes = base64.b64decode(capture.audio_data)
            text, confidence = await speech_service.transcribe_audio(audio_bytes)

            db_capture.raw_text = text
            db_capture.ai_confidence = confidence
            db_capture.state = CaptureState.PROCESSING

        elif capture.capture_type == CaptureType.IMAGE and capture.image_data:
            # Decode base64 image
            image_bytes = base64.b64decode(capture.image_data)
            text, confidence = await ocr_service.extract_text(image_bytes)

            db_capture.raw_text = text
            db_capture.ai_confidence = confidence
            db_capture.state = CaptureState.PROCESSING

        elif capture.capture_type == CaptureType.TEXT:
            db_capture.state = CaptureState.PROCESSING

        db_capture.processed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_capture)

        # Run NLP classification if we have text
        # This is fast (< 500ms) so we do it inline
        if db_capture.raw_text:
            await process_capture_nlp(db_capture.id, db)

    except Exception as e:
        db_capture.state = CaptureState.ERROR
        db_capture.error_message = str(e)
        db.commit()
        logger.exception(f"Failed to process capture {db_capture.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process capture: {str(e)}",
        )

    return db_capture


async def process_capture_nlp(capture_id: int, db: Session):
    """Process capture with NLP to create draft."""
    capture = db.query(Capture).filter(Capture.id == capture_id).first()
    if not capture or not capture.raw_text:
        return

    try:
        # Classify and extract entities
        draft_type, confidence, entities = await nlp_service.classify_and_extract(
            capture.raw_text
        )

        # Create draft
        draft = Draft(
            capture_id=capture.id,
            user_id=capture.user_id,
            draft_type=draft_type,
            ai_confidence=confidence,
            title=entities["title"],
            description=entities["description"],
            due_date=entities["due_date"],
            priority=entities["priority"],
            location=entities["location"],
            start_time=entities["start_time"],
            end_time=entities["end_time"],
            extracted_entities=entities,
        )

        db.add(draft)
        capture.state = CaptureState.PARSED

        # Auto-confirm if confidence is high enough
        if confidence >= settings.AI_CONFIDENCE_THRESHOLD:
            draft.is_confirmed = True
            draft.sync_state = CaptureState.CONFIRMED
        else:
            capture.state = CaptureState.NEEDS_REVIEW

        db.commit()

    except Exception as e:
        capture.state = CaptureState.ERROR
        capture.error_message = f"NLP processing failed: {str(e)}"
        db.commit()
        logger.exception(f"NLP processing failed for capture {capture_id}: {e}")


@router.get("/captures", response_model=List[CaptureResponse])
async def list_captures(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all captures for the user."""
    captures = (
        db.query(Capture)
        .filter(Capture.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return captures


@router.get("/captures/{capture_id}", response_model=CaptureResponse)
async def get_capture(
    capture_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific capture."""
    capture = (
        db.query(Capture)
        .filter(Capture.id == capture_id, Capture.user_id == user_id)
        .first()
    )

    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capture not found"
        )

    return capture


@router.get("/drafts", response_model=List[DraftResponse])
async def list_drafts(
    skip: int = 0,
    limit: int = 100,
    needs_review_only: bool = False,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all drafts for the user."""
    query = db.query(Draft).filter(Draft.user_id == user_id)

    if needs_review_only:
        query = query.filter(Draft.is_confirmed == False)

    drafts = query.offset(skip).limit(limit).all()
    return drafts


@router.post("/drafts/{draft_id}/confirm", response_model=DraftResponse)
async def confirm_draft(
    draft_id: int,
    confirm: DraftConfirm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    user_credentials: dict = Depends(get_current_user_credentials),
):
    """
    Confirm and optionally edit a draft.
    Immediately queues Google sync in background without blocking response.
    """
    draft = (
        db.query(Draft).filter(Draft.id == draft_id, Draft.user_id == user_id).first()
    )

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found"
        )

    # Update draft with user edits
    if confirm.title:
        draft.title = confirm.title
    if confirm.description:
        draft.description = confirm.description
    if confirm.due_date:
        draft.due_date = confirm.due_date
    if confirm.priority:
        draft.priority = confirm.priority

    draft.is_confirmed = True
    draft.sync_state = CaptureState.CONFIRMED

    db.commit()
    db.refresh(draft)

    # Queue Google sync in background (non-blocking)
    # Uses FastAPI BackgroundTasks instead of Celery - removes 1-3s overhead
    background_tasks.add_task(
        sync_draft_to_google_with_retry,
        draft_id=draft.id,
        user_credentials=user_credentials,
        retry_count=0,
    )

    logger.info(f"Draft {draft_id} confirmed, Google sync queued in background")

    return draft


@router.post("/sync/offline-queue")
async def sync_offline_queue(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    user_credentials: dict = Depends(get_current_user_credentials),
):
    """
    Sync all pending drafts for user (offline queue processing).
    Returns immediately, syncs happen in background.
    """
    # Get all confirmed but unsynced drafts
    drafts = (
        db.query(Draft)
        .filter(
            Draft.user_id == user_id,
            Draft.is_confirmed == True,
            Draft.sync_state.in_([CaptureState.CONFIRMED, CaptureState.ERROR]),
        )
        .all()
    )

    draft_ids = [draft.id for draft in drafts]

    # Queue each draft for background sync
    for draft_id in draft_ids:
        background_tasks.add_task(
            sync_draft_to_google_with_retry,
            draft_id=draft_id,
            user_credentials=user_credentials,
            retry_count=0,
        )

    logger.info(
        f"Queued {len(draft_ids)} drafts for background sync for user {user_id}"
    )

    return {
        "user_id": user_id,
        "queued_count": len(draft_ids),
        "draft_ids": draft_ids,
        "status": "queued",
    }
