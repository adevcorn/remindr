"""Google Tasks and Calendar sync service."""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from app.models.capture import DraftType


class GoogleSyncService:
    """Service for syncing with Google Tasks and Calendar."""

    def __init__(self):
        """Initialize Google API clients."""
        pass  # Clients are created per-user with their credentials

    def _get_tasks_service(self, credentials: Credentials):
        """Get Google Tasks API service."""
        return build('tasks', 'v1', credentials=credentials)

    def _get_calendar_service(self, credentials: Credentials):
        """Get Google Calendar API service."""
        return build('calendar', 'v3', credentials=credentials)

    async def sync_task(
        self,
        credentials: Credentials,
        title: str,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        task_list_id: str = "@default"
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Sync a task to Google Tasks.

        Args:
            credentials: User's Google OAuth credentials
            title: Task title
            description: Task description
            due_date: Task due date
            task_list_id: Google Tasks list ID

        Returns:
            Tuple of (task_id, error_message)
        """
        def _sync_task_blocking():
            """Blocking I/O operation to sync task."""
            try:
                service = self._get_tasks_service(credentials)
                
                task_body = {
                    'title': title,
                    'notes': description or '',
                    'status': 'needsAction'
                }
                
                if due_date:
                    # Google Tasks expects RFC 3339 timestamp
                    task_body['due'] = due_date.isoformat()
                
                result = service.tasks().insert(
                    tasklist=task_list_id,
                    body=task_body
                ).execute()
                
                return result.get('id'), None

            except HttpError as e:
                error_msg = f"Google Tasks API error: {e.resp.status} - {e.error_details}"
                return None, error_msg
            except Exception as e:
                return None, str(e)
        
        # Run blocking call in thread pool
        return await asyncio.to_thread(_sync_task_blocking)

    async def sync_event(
        self,
        credentials: Credentials,
        title: str,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        calendar_id: str = "primary"
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Sync an event to Google Calendar.

        Args:
            credentials: User's Google OAuth credentials
            title: Event title
            description: Event description
            start_time: Event start time
            end_time: Event end time
            location: Event location
            calendar_id: Google Calendar ID

        Returns:
            Tuple of (event_id, error_message)
        """
        def _sync_event_blocking():
            """Blocking I/O operation to sync event."""
            try:
                service = self._get_calendar_service(credentials)
                
                # Default to 1-hour event if times not specified
                event_start = start_time or datetime.now()
                event_end = end_time or event_start.replace(hour=event_start.hour + 1)
                
                event_body = {
                    'summary': title,
                    'description': description or '',
                    'start': {
                        'dateTime': event_start.isoformat(),
                        'timeZone': 'UTC'
                    },
                    'end': {
                        'dateTime': event_end.isoformat(),
                        'timeZone': 'UTC'
                    }
                }
                
                if location:
                    event_body['location'] = location
                
                result = service.events().insert(
                    calendarId=calendar_id,
                    body=event_body
                ).execute()
                
                return result.get('id'), None

            except HttpError as e:
                error_msg = f"Google Calendar API error: {e.resp.status} - {e.error_details}"
                return None, error_msg
            except Exception as e:
                return None, str(e)
        
        # Run blocking call in thread pool
        return await asyncio.to_thread(_sync_event_blocking)

    async def update_task(
        self,
        credentials: Credentials,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[datetime] = None,
        status: Optional[str] = None,
        task_list_id: str = "@default"
    ) -> Optional[str]:
        """
        Update a task in Google Tasks.

        Returns:
            Error message if failed, None if successful
        """
        def _update_task_blocking():
            """Blocking I/O operation to update task."""
            try:
                service = self._get_tasks_service(credentials)
                
                # Get existing task first
                task = service.tasks().get(
                    tasklist=task_list_id,
                    task=task_id
                ).execute()
                
                # Update fields
                if title:
                    task['title'] = title
                if description:
                    task['notes'] = description
                if due_date:
                    task['due'] = due_date.isoformat()
                if status:
                    task['status'] = status
                
                service.tasks().update(
                    tasklist=task_list_id,
                    task=task_id,
                    body=task
                ).execute()
                
                return None

            except Exception as e:
                return str(e)
        
        # Run blocking call in thread pool
        return await asyncio.to_thread(_update_task_blocking)

    async def delete_task(
        self,
        credentials: Credentials,
        task_id: str,
        task_list_id: str = "@default"
    ) -> Optional[str]:
        """
        Delete a task from Google Tasks.

        Returns:
            Error message if failed, None if successful
        """
        def _delete_task_blocking():
            """Blocking I/O operation to delete task."""
            try:
                service = self._get_tasks_service(credentials)
                service.tasks().delete(
                    tasklist=task_list_id,
                    task=task_id
                ).execute()
                return None
            except Exception as e:
                return str(e)
        
        # Run blocking call in thread pool
        return await asyncio.to_thread(_delete_task_blocking)


# Singleton instance
google_sync_service = GoogleSyncService()
