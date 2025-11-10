"""Tests for Google sync service."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from google.oauth2.credentials import Credentials

from app.services.google_sync import google_sync_service


@pytest.fixture
def mock_credentials():
    """Create mock Google OAuth credentials."""
    return Credentials(
        token="mock_access_token",
        refresh_token="mock_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="mock_client_id",
        client_secret="mock_client_secret"
    )


@pytest.mark.asyncio
async def test_sync_task_success(mock_credentials):
    """Test successful task sync to Google Tasks."""
    with patch('app.services.google_sync.build') as mock_build:
        # Mock the Google Tasks API response
        mock_service = MagicMock()
        mock_service.tasks().insert().execute.return_value = {'id': 'task_123'}
        mock_build.return_value = mock_service
        
        task_id, error = await google_sync_service.sync_task(
            credentials=mock_credentials,
            title="Test Task",
            description="Test Description",
            due_date=datetime(2025, 11, 10, 17, 0, 0)
        )
        
        assert task_id == "task_123"
        assert error is None


@pytest.mark.asyncio
async def test_sync_event_success(mock_credentials):
    """Test successful event sync to Google Calendar."""
    with patch('app.services.google_sync.build') as mock_build:
        # Mock the Google Calendar API response
        mock_service = MagicMock()
        mock_service.events().insert().execute.return_value = {'id': 'event_456'}
        mock_build.return_value = mock_service
        
        event_id, error = await google_sync_service.sync_event(
            credentials=mock_credentials,
            title="Test Meeting",
            description="Test Description",
            start_time=datetime(2025, 11, 10, 14, 0, 0),
            end_time=datetime(2025, 11, 10, 15, 0, 0),
            location="Conference Room A"
        )
        
        assert event_id == "event_456"
        assert error is None


@pytest.mark.asyncio
async def test_sync_task_api_error(mock_credentials):
    """Test handling of Google Tasks API error."""
    from googleapiclient.errors import HttpError
    
    with patch('app.services.google_sync.build') as mock_build:
        # Mock API error
        mock_service = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 429
        error = HttpError(mock_response, b'Rate limit exceeded')
        error.error_details = 'Rate limit exceeded'
        mock_service.tasks().insert().execute.side_effect = error
        mock_build.return_value = mock_service
        
        task_id, error_msg = await google_sync_service.sync_task(
            credentials=mock_credentials,
            title="Test Task"
        )
        
        assert task_id is None
        assert error_msg is not None
        assert "429" in error_msg


@pytest.mark.asyncio
async def test_update_task(mock_credentials):
    """Test updating an existing task."""
    with patch('app.services.google_sync.build') as mock_build:
        # Mock the Google Tasks API
        mock_service = MagicMock()
        mock_service.tasks().get().execute.return_value = {
            'id': 'task_123',
            'title': 'Old Title'
        }
        mock_service.tasks().update().execute.return_value = {'id': 'task_123'}
        mock_build.return_value = mock_service
        
        error = await google_sync_service.update_task(
            credentials=mock_credentials,
            task_id="task_123",
            title="New Title",
            status="completed"
        )
        
        assert error is None


@pytest.mark.asyncio
async def test_delete_task(mock_credentials):
    """Test deleting a task."""
    with patch('app.services.google_sync.build') as mock_build:
        # Mock the Google Tasks API
        mock_service = MagicMock()
        mock_service.tasks().delete().execute.return_value = {}
        mock_build.return_value = mock_service
        
        error = await google_sync_service.delete_task(
            credentials=mock_credentials,
            task_id="task_123"
        )
        
        assert error is None
