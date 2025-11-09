"""Tests for Connect Google Services flow."""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.db.session import get_db
from app.models.user import User
from app.core.auth import create_user_session


@pytest.fixture
def client(db_session):
    """Test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # db_session cleanup is handled by conftest fixture
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_with_session(db_session):
    """Create test user with valid session."""
    # Generate unique user ID and email for each test
    unique_id = str(uuid.uuid4())[:8]
    
    # Create user without OAuth tokens
    user = User(
        user_id=f"test_user_connect_{unique_id}",
        email=f"test_connect_{unique_id}@example.com",
        name="Test User Connect",
        last_login_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create session
    session_token = create_user_session(db_session, user.user_id)
    
    # Extract attributes before session rollback
    user_data = {
        "user_id": user.user_id,
        "email": user.email,
        "session_token": session_token
    }
    
    return user_data


def test_connect_google_requires_authentication(client):
    """Test that /connect-google requires valid session token."""
    response = client.get("/api/v1/auth/connect-google")
    
    assert response.status_code == 401


def test_connect_google_returns_oauth_url(client, test_user_with_session):
    """Test that /connect-google returns OAuth authorization URL."""
    headers = {
        "Authorization": f"Bearer {test_user_with_session['session_token']}"
    }
    
    response = client.get("/api/v1/auth/connect-google", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "authorization_url" in data
    assert "state" in data
    assert "accounts.google.com" in data["authorization_url"]
    assert "oauth2/auth" in data["authorization_url"]


def test_google_connection_status_not_connected(client, test_user_with_session):
    """Test connection status for user without OAuth tokens."""
    headers = {
        "Authorization": f"Bearer {test_user_with_session['session_token']}"
    }
    
    response = client.get("/api/v1/auth/google-connection-status", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["connected"] is False
    assert data["email"] is None
    assert data["has_tasks_scope"] is False
    assert data["has_calendar_scope"] is False


def test_google_connection_status_connected(client, db_session):
    """Test connection status for user with OAuth tokens."""
    # Generate unique user ID and email
    unique_id = str(uuid.uuid4())[:8]
    
    # Create user with OAuth tokens
    user = User(
        user_id=f"test_user_connected_{unique_id}",
        email=f"connected_{unique_id}@example.com",
        name="Connected User",
        google_access_token="test_access_token",
        google_refresh_token="test_refresh_token",
        google_scopes="https://www.googleapis.com/auth/tasks https://www.googleapis.com/auth/calendar",
        last_login_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    
    session_token = create_user_session(db_session, user.user_id)
    
    headers = {
        "Authorization": f"Bearer {session_token}"
    }
    
    response = client.get("/api/v1/auth/google-connection-status", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["connected"] is True
    assert data["email"] == f"connected_{unique_id}@example.com"
    assert data["has_tasks_scope"] is True
    assert data["has_calendar_scope"] is True


@patch('app.api.endpoints.auth.Flow')
@patch('app.api.endpoints.auth.build')
def test_callback_connect_flow(mock_build, mock_flow_class, client, db_session, test_user_with_session):
    """Test OAuth callback for connect flow (with user_id in state)."""
    # Mock OAuth flow
    mock_flow = MagicMock()
    mock_credentials = MagicMock()
    mock_credentials.token = "new_access_token"
    mock_credentials.refresh_token = "new_refresh_token"
    mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)
    mock_flow.credentials = mock_credentials
    
    # Mock authorization_url method to return (url, state) tuple
    test_state = "test_oauth_state_12345"
    mock_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?client_id=test",
        test_state
    )
    
    mock_flow_class.from_client_config.return_value = mock_flow
    
    # Mock Google userinfo API
    mock_service = MagicMock()
    mock_userinfo = MagicMock()
    mock_userinfo.get.return_value.execute.return_value = {
        "id": test_user_with_session["user_id"],
        "email": test_user_with_session["email"],
        "name": "Test User"
    }
    mock_service.userinfo.return_value = mock_userinfo
    mock_build.return_value = mock_service
    
    # First, initiate connect flow to get state
    headers = {
        "Authorization": f"Bearer {test_user_with_session['session_token']}"
    }
    connect_response = client.get("/api/v1/auth/connect-google", headers=headers)
    state = connect_response.json()["state"]
    
    # Now call callback with state
    response = client.get(
        f"/api/v1/auth/callback?code=test_auth_code&state={state}"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # For connect flow, should return success message
    assert data["success"] is True
    assert data["message"] == "Google services connected successfully"
    assert data["email"] == test_user_with_session["email"]
    
    # Verify user tokens were updated
    user = db_session.query(User).filter(User.user_id == test_user_with_session["user_id"]).first()
    
    assert user.google_access_token == "new_access_token"
    assert user.google_refresh_token == "new_refresh_token"
    assert user.google_scopes is not None


def test_callback_connect_flow_email_mismatch(client, db_session):
    """Test callback rejects connect flow if email doesn't match."""
    # Generate unique user ID and email
    unique_id = str(uuid.uuid4())[:8]
    
    # Create user
    user = User(
        user_id=f"test_user_mismatch_{unique_id}",
        email=f"original_{unique_id}@example.com",
        name="Test User",
        last_login_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    
    session_token = create_user_session(db_session, user.user_id)
    
    # Initiate connect flow
    headers = {"Authorization": f"Bearer {session_token}"}
    connect_response = client.get("/api/v1/auth/connect-google", headers=headers)
    state = connect_response.json()["state"]
    
    # Mock OAuth with different email
    with patch('app.api.endpoints.auth.Flow') as mock_flow_class, \
         patch('app.api.endpoints.auth.build') as mock_build:
        
        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.token = "access_token"
        mock_credentials.refresh_token = "refresh_token"
        mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)
        mock_flow.credentials = mock_credentials
        mock_flow_class.from_client_config.return_value = mock_flow
        
        mock_service = MagicMock()
        mock_userinfo = MagicMock()
        mock_userinfo.get.return_value.execute.return_value = {
            "id": "different_user_id",
            "email": "different@example.com",  # Different email!
            "name": "Different User"
        }
        mock_service.userinfo.return_value = mock_userinfo
        mock_build.return_value = mock_service
        
        response = client.get(
            f"/api/v1/auth/callback?code=test_code&state={state}"
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403
        assert "Email mismatch" in response.json()["detail"]


def test_callback_invalid_state(client):
    """Test callback rejects invalid state parameter."""
    response = client.get(
        "/api/v1/auth/callback?code=test_code&state=invalid_state"
    )
    
    assert response.status_code == 400
    assert "Invalid or missing state" in response.json()["detail"]


def test_callback_expired_state(client, test_user_with_session):
    """Test callback rejects expired state."""
    # Manually add expired state
    from app.api.endpoints.auth import _oauth_states
    
    expired_state = "expired_state_token"
    _oauth_states[expired_state] = {
        "expiry": datetime.utcnow() - timedelta(minutes=10),  # Expired
        "user_id": test_user_with_session["user_id"]
    }
    
    response = client.get(
        f"/api/v1/auth/callback?code=test_code&state={expired_state}"
    )
    
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()
