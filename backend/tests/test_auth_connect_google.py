"""Tests for Connect Google Services flow."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.core.auth import create_user_session

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_connect_google.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Setup and teardown test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user_with_session():
    """Create test user with valid session."""
    db = TestingSessionLocal()
    
    # Create user without OAuth tokens
    user = User(
        user_id="test_user_123",
        email="test@example.com",
        name="Test User",
        last_login_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create session
    session_token = create_user_session(db, user.user_id)
    
    db.close()
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "session_token": session_token
    }


def test_connect_google_requires_authentication():
    """Test that /connect-google requires valid session token."""
    response = client.get("/api/v1/auth/connect-google")
    
    assert response.status_code == 401


def test_connect_google_returns_oauth_url(test_user_with_session):
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


def test_google_connection_status_not_connected(test_user_with_session):
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


def test_google_connection_status_connected():
    """Test connection status for user with OAuth tokens."""
    db = TestingSessionLocal()
    
    # Create user with OAuth tokens
    user = User(
        user_id="test_user_connected",
        email="connected@example.com",
        name="Connected User",
        google_access_token="test_access_token",
        google_refresh_token="test_refresh_token",
        google_scopes="https://www.googleapis.com/auth/tasks https://www.googleapis.com/auth/calendar",
        last_login_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    
    session_token = create_user_session(db, user.user_id)
    db.close()
    
    headers = {
        "Authorization": f"Bearer {session_token}"
    }
    
    response = client.get("/api/v1/auth/google-connection-status", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["connected"] is True
    assert data["email"] == "connected@example.com"
    assert data["has_tasks_scope"] is True
    assert data["has_calendar_scope"] is True


@patch('app.api.endpoints.auth.Flow')
@patch('app.api.endpoints.auth.build')
def test_callback_connect_flow(mock_build, mock_flow_class, test_user_with_session):
    """Test OAuth callback for connect flow (with user_id in state)."""
    # Mock OAuth flow
    mock_flow = MagicMock()
    mock_credentials = MagicMock()
    mock_credentials.token = "new_access_token"
    mock_credentials.refresh_token = "new_refresh_token"
    mock_credentials.expiry = datetime.utcnow() + timedelta(hours=1)
    mock_flow.credentials = mock_credentials
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
    db = TestingSessionLocal()
    user = db.query(User).filter(User.user_id == test_user_with_session["user_id"]).first()
    
    assert user.google_access_token == "new_access_token"
    assert user.google_refresh_token == "new_refresh_token"
    assert user.google_scopes is not None
    
    db.close()


def test_callback_connect_flow_email_mismatch():
    """Test callback rejects connect flow if email doesn't match."""
    db = TestingSessionLocal()
    
    # Create user
    user = User(
        user_id="test_user_mismatch",
        email="original@example.com",
        name="Test User",
        last_login_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    
    session_token = create_user_session(db, user.user_id)
    db.close()
    
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


def test_callback_invalid_state():
    """Test callback rejects invalid state parameter."""
    response = client.get(
        "/api/v1/auth/callback?code=test_code&state=invalid_state"
    )
    
    assert response.status_code == 400
    assert "Invalid or missing state" in response.json()["detail"]


def test_callback_expired_state(test_user_with_session):
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
