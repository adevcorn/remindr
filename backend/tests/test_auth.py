"""Tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.core.auth import create_user_session

# Test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
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


@pytest.fixture
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(bind=engine)


def test_login_endpoint():
    """Test OAuth login endpoint returns authorization URL."""
    response = client.get("/api/v1/auth/login")
    
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "state" in data
    assert "https://accounts.google.com/o/oauth2/auth" in data["authorization_url"]


def test_get_current_user_without_auth():
    """Test that getting current user without auth fails."""
    response = client.get("/api/v1/auth/me")
    
    assert response.status_code == 401


def test_get_current_user_with_auth(test_db):
    """Test getting current user info with valid auth."""
    # Create a test user
    user = User(
        user_id="test_user_123",
        email="test@example.com",
        name="Test User",
    )
    test_db.add(user)
    test_db.commit()
    
    # Create session
    token = create_user_session(test_db, user.user_id)
    
    # Get user info
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user_123"
    assert data["email"] == "test@example.com"


def test_logout(test_db):
    """Test logout endpoint."""
    # Create a test user and session
    user = User(
        user_id="test_user_123",
        email="test@example.com",
        name="Test User",
    )
    test_db.add(user)
    test_db.commit()
    
    token = create_user_session(test_db, user.user_id)
    
    # Logout
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    
    # Verify token is now invalid
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_session_expiry(test_db):
    """Test that expired sessions are rejected."""
    from datetime import datetime, timedelta
    from app.models.user import Session as UserSession
    
    # Create user and expired session
    user = User(
        user_id="test_user_123",
        email="test@example.com",
    )
    test_db.add(user)
    test_db.commit()
    
    expired_session = UserSession(
        session_token="expired_token",
        user_id=user.user_id,
        expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    )
    test_db.add(expired_session)
    test_db.commit()
    
    # Try to use expired token
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer expired_token"}
    )
    
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
