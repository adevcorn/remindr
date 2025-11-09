"""Background task utilities using native async."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.capture import CaptureState, Draft, DraftType
from app.services.google_sync import google_sync_service
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def sync_draft_to_google_with_retry(
    draft_id: int, user_credentials: dict, retry_count: int = 0
) -> Dict[str, Any]:
    """
    Sync a confirmed draft to Google Tasks or Calendar with exponential backoff retry.

    Args:
        draft_id: ID of the draft to sync
        user_credentials: User's Google OAuth credentials as dict
        retry_count: Current retry attempt (for exponential backoff)

    Returns:
        Dict with sync result and status
    """
    db: Session = SessionLocal()

    try:
        # Get draft
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            logger.error(f"Draft {draft_id} not found")
            return {"error": "Draft not found", "draft_id": draft_id}

        # Update state to syncing
        draft.sync_state = CaptureState.SYNCING
        db.commit()

        # Create credentials object
        credentials = Credentials.from_authorized_user_info(user_credentials)

        # Sync based on type
        task_id = None
        event_id = None
        error = None

        if draft.draft_type == DraftType.TASK:
            task_id, error = await google_sync_service.sync_task(
                credentials=credentials,
                title=draft.title,
                description=draft.description,
                due_date=draft.due_date,
            )

            if not error:
                draft.google_task_id = task_id

        elif draft.draft_type == DraftType.EVENT:
            event_id, error = await google_sync_service.sync_event(
                credentials=credentials,
                title=draft.title,
                description=draft.description,
                start_time=draft.start_time,
                end_time=draft.end_time,
                location=draft.location,
            )

            if not error:
                draft.google_event_id = event_id

        # Handle errors with retry logic
        if error:
            if retry_count < settings.SYNC_RETRY_MAX_ATTEMPTS:
                # Update state to indicate retry pending
                draft.sync_state = CaptureState.ERROR
                draft.error_message = f"Retry {retry_count + 1}/{settings.SYNC_RETRY_MAX_ATTEMPTS}: {error}"
                db.commit()
                db.close()

                # Exponential backoff: 2^retry_count * 60 seconds
                backoff_seconds = (settings.SYNC_RETRY_BACKOFF_BASE**retry_count) * 60
                logger.warning(
                    f"Draft {draft_id} sync failed, retrying in {backoff_seconds}s. "
                    f"Attempt {retry_count + 1}/{settings.SYNC_RETRY_MAX_ATTEMPTS}. Error: {error}"
                )

                # Wait and retry
                await asyncio.sleep(backoff_seconds)
                return await sync_draft_to_google_with_retry(
                    draft_id=draft_id,
                    user_credentials=user_credentials,
                    retry_count=retry_count + 1,
                )
            else:
                # Max retries exceeded
                draft.sync_state = CaptureState.ERROR
                draft.error_message = f"Max retries exceeded: {error}"
                db.commit()
                logger.error(
                    f"Draft {draft_id} sync failed after {retry_count} retries: {error}"
                )
                return {
                    "draft_id": draft_id,
                    "status": "error",
                    "error": error,
                    "retries": retry_count,
                }

        # Update state to synced
        draft.sync_state = CaptureState.SYNCED
        draft.synced_at = datetime.utcnow()
        draft.error_message = None
        db.commit()

        logger.info(
            f"Draft {draft_id} synced successfully (task_id={task_id}, event_id={event_id})"
        )

        return {
            "draft_id": draft_id,
            "status": "synced",
            "google_task_id": task_id,
            "google_event_id": event_id,
            "retries": retry_count,
        }

    except Exception as e:
        logger.exception(f"Unexpected error syncing draft {draft_id}: {e}")

        # Try to update error state if we have a draft
        try:
            draft = db.query(Draft).filter(Draft.id == draft_id).first()
            if draft:
                draft.sync_state = CaptureState.ERROR
                draft.error_message = str(e)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update draft error state: {db_error}")

        return {
            "draft_id": draft_id,
            "status": "error",
            "error": str(e),
            "retries": retry_count,
        }

    finally:
        db.close()


async def process_offline_queue(user_id: str, user_credentials: dict) -> Dict[str, Any]:
    """
    Process all pending drafts for a user when they come online.

    Args:
        user_id: User ID
        user_credentials: User's Google OAuth credentials

    Returns:
        Dict with processing summary
    """
    db: Session = SessionLocal()

    try:
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
        logger.info(
            f"Processing offline queue for user {user_id}: {len(draft_ids)} drafts"
        )

        # Process all drafts concurrently (but not blocking the response)
        # We return immediately and let syncs happen in background
        results = []
        for draft_id in draft_ids:
            # Start sync tasks without awaiting (fire and forget)
            asyncio.create_task(
                sync_draft_to_google_with_retry(
                    draft_id, user_credentials, retry_count=0
                )
            )

        return {
            "user_id": user_id,
            "queued_count": len(draft_ids),
            "draft_ids": draft_ids,
            "status": "processing",
        }

    except Exception as e:
        logger.exception(f"Error processing offline queue for user {user_id}: {e}")
        return {"user_id": user_id, "status": "error", "error": str(e)}

    finally:
        db.close()
