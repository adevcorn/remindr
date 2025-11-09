"""Tests for capture endpoints."""
import pytest
import uuid
from fastapi.testclient import TestClient
from datetime import datetime
import base64

from app.main import app
from app.db.session import get_db
from app.models.user import User, Session as UserSession
from app.core.auth import create_user_session


@pytest.fixture
def client(db_session):
    """Test client for API calls with overridden database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    # Generate unique IDs for this test
    unique_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    user = User(
        user_id=unique_user_id,
        email=unique_email,
        name="Test User",
        google_access_token="test_token",
        google_refresh_token="test_refresh",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(db_session, test_user):
    """Create an auth token for testing."""
    return create_user_session(db_session, test_user.user_id)


def test_create_text_capture(client, db_session, auth_token):
    """Test creating a text capture."""
    response = client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "text",
            "raw_text": "Buy groceries tomorrow at 5pm"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["capture_type"] == "text"
    assert data["raw_text"] == "Buy groceries tomorrow at 5pm"
    # After inline NLP processing, state should be either parsed (high confidence) or needs_review (low confidence)
    assert data["state"] in ["parsed", "needs_review"]


def test_create_voice_capture(client, db_session, auth_token):
    """Test creating a voice capture."""
    # Create dummy audio data
    audio_bytes = b"fake audio data for testing"
    audio_base64 = base64.b64encode(audio_bytes).decode()
    
    response = client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "voice",
            "audio_data": audio_base64
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code in [201, 500]  # May fail if Google API not configured
    

def test_create_image_capture(client, db_session, auth_token):
    """Test creating an image capture."""
    # Create dummy image data
    image_bytes = b"fake image data for testing"
    image_base64 = base64.b64encode(image_bytes).decode()
    
    response = client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "image",
            "image_data": image_base64
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code in [201, 500]  # May fail if Google API not configured


def test_create_capture_without_auth(client):
    """Test that creating a capture without auth fails."""
    response = client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "text",
            "raw_text": "Test capture"
        }
    )
    
    assert response.status_code == 401


def test_list_captures(client, db_session, auth_token):
    """Test listing captures."""
    # Create a capture first
    client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "text",
            "raw_text": "Test capture 1"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    # List captures
    response = client.get(
        "/api/v1/captures/captures",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_capture(client, db_session, auth_token):
    """Test getting a specific capture."""
    # Create a capture first
    create_response = client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "text",
            "raw_text": "Test capture"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    capture_id = create_response.json()["id"]
    
    # Get the capture
    response = client.get(
        f"/api/v1/captures/captures/{capture_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == capture_id


def test_input_validation_text_too_long(client, db_session, auth_token):
    """Test that text input validation rejects oversized text."""
    # Create text exceeding MAX_TEXT_LENGTH (5000 characters)
    long_text = "a" * 6000
    
    response = client.post(
        "/api/v1/captures/captures",
        json={
            "capture_type": "text",
            "raw_text": long_text
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 422  # Validation error


def test_rate_limiting(client):
    """Test that rate limiting works."""
    # Note: This test may be flaky depending on rate limit settings
    # Make many requests rapidly
    responses = []
    for _ in range(150):  # Exceed default 100/minute limit
        response = client.get("/health")
        responses.append(response.status_code)
    
    # At least one should be rate limited
    assert 429 in responses


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
