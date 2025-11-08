"""Celery tasks for background processing."""
from celery import Celery
from sqlalchemy.orm import Session
from typing import Optional
from google.oauth2.credentials import Credentials

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.capture import Draft, CaptureState, DraftType
from app.services.google_sync import google_sync_service

# Initialize Celery
celery_app = Celery(
    "remindr",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(
    bind=True,
    max_retries=settings.SYNC_RETRY_MAX_ATTEMPTS,
    default_retry_delay=60
)
def sync_draft_to_google(self, draft_id: int, user_credentials: dict):
    """
    Sync a confirmed draft to Google Tasks or Calendar.
    
    Args:
        draft_id: ID of the draft to sync
        user_credentials: User's Google OAuth credentials as dict
    """
    db: Session = SessionLocal()
    
    try:
        # Get draft
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            return {"error": "Draft not found"}
        
        # Update state to syncing
        draft.sync_state = CaptureState.SYNCING
        db.commit()
        
        # Create credentials object
        credentials = Credentials.from_authorized_user_info(user_credentials)
        
        # Sync based on type
        if draft.draft_type == DraftType.TASK:
            task_id, error = google_sync_service.sync_task(
                credentials=credentials,
                title=draft.title,
                description=draft.description,
                due_date=draft.due_date
            )
            
            if error:
                raise Exception(error)
            
            draft.google_task_id = task_id
            
        elif draft.draft_type == DraftType.EVENT:
            event_id, error = google_sync_service.sync_event(
                credentials=credentials,
                title=draft.title,
                description=draft.description,
                start_time=draft.start_time,
                end_time=draft.end_time,
                location=draft.location
            )
            
            if error:
                raise Exception(error)
            
            draft.google_event_id = event_id
        
        # Update state to synced
        draft.sync_state = CaptureState.SYNCED
        from datetime import datetime
        draft.synced_at = datetime.utcnow()
        db.commit()
        
        return {
            "draft_id": draft_id,
            "status": "synced",
            "google_task_id": draft.google_task_id,
            "google_event_id": draft.google_event_id
        }
        
    except Exception as e:
        # Update error state
        draft.sync_state = CaptureState.ERROR
        db.commit()
        
        # Retry with exponential backoff
        backoff = settings.SYNC_RETRY_BACKOFF_BASE ** self.request.retries
        raise self.retry(exc=e, countdown=backoff * 60)
        
    finally:
        db.close()


@celery_app.task
def process_offline_queue(user_id: str, user_credentials: dict):
    """
    Process all pending drafts for a user when they come online.
    
    Args:
        user_id: User ID
        user_credentials: User's Google OAuth credentials
    """
    db: Session = SessionLocal()
    
    try:
        # Get all confirmed but unsynced drafts
        drafts = db.query(Draft).filter(
            Draft.user_id == user_id,
            Draft.is_confirmed == True,
            Draft.sync_state.in_([CaptureState.CONFIRMED, CaptureState.ERROR])
        ).all()
        
        # Queue each draft for syncing
        for draft in drafts:
            sync_draft_to_google.delay(draft.id, user_credentials)
        
        return {
            "user_id": user_id,
            "queued_count": len(drafts)
        }
        
    finally:
        db.close()
