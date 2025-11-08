"""Integration tests for authentication flows."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, Session as UserSession
from app.core.auth import create_user_session


@pytest.fixture
def client():
    """Test client for API calls."""
    return TestClient(app)


@pytest.fixture
def mock_google_id_token():
    """Mock Google ID token verification."""
    with patch('app.api.endpoints.auth.id_token.verify_oauth2_token') as mock:
        yield mock


class TestGoogleTokenAuthentication:
    """Test Google ID token authentication flow."""
    
    def test_authenticate_with_valid_token(self, client, mock_google_id_token, db: Session):
        """Test successful authentication with valid Google ID token."""
        # Mock successful token verification
        mock_google_id_token.return_value = {
            'iss': 'accounts.google.com',
            'sub': 'google_user_123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        response = client.post(
            '/api/v1/auth/google-token',
            json={'id_token': 'valid_test_token'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'session_token' in data
        assert data['email'] == 'test@example.com'
        assert data['name'] == 'Test User'
        assert data['user_id'] == 'google_user_123'
        
        # Verify user was created in database
        user = db.query(User).filter(User.email == 'test@example.com').first()
        assert user is not None
        assert user.user_id == 'google_user_123'
    
    def test_authenticate_existing_user(self, client, mock_google_id_token, db: Session):
        """Test authentication with existing user updates last_login."""
        # Create existing user
        existing_user = User(
            user_id='google_user_123',
            email='test@example.com',
            name='Old Name',
            last_login_at=datetime.utcnow() - timedelta(days=7)
        )
        db.add(existing_user)
        db.commit()
        old_login_time = existing_user.last_login_at
        
        # Mock token verification
        mock_google_id_token.return_value = {
            'iss': 'accounts.google.com',
            'sub': 'google_user_123',
            'email': 'test@example.com',
            'name': 'New Name'
        }
        
        response = client.post(
            '/api/v1/auth/google-token',
            json={'id_token': 'valid_test_token'}
        )
        
        assert response.status_code == 200
        
        # Verify user was updated
        db.refresh(existing_user)
        assert existing_user.last_login_at > old_login_time
    
    def test_authenticate_with_invalid_token(self, client, mock_google_id_token):
        """Test authentication fails with invalid token."""
        mock_google_id_token.side_effect = ValueError('Invalid token')
        
        response = client.post(
            '/api/v1/auth/google-token',
            json={'id_token': 'invalid_token'}
        )
        
        assert response.status_code == 401
        assert 'Invalid ID token' in response.json()['detail']
    
    def test_authenticate_with_invalid_issuer(self, client, mock_google_id_token):
        """Test authentication fails with wrong issuer."""
        mock_google_id_token.return_value = {
            'iss': 'malicious.com',
            'sub': 'fake_user',
            'email': 'fake@example.com'
        }
        
        response = client.post(
            '/api/v1/auth/google-token',
            json={'id_token': 'token_from_wrong_issuer'}
        )
        
        assert response.status_code == 401
    
    def test_authenticate_without_email(self, client, mock_google_id_token):
        """Test authentication fails without email in token."""
        mock_google_id_token.return_value = {
            'iss': 'accounts.google.com',
            'sub': 'google_user_123',
            # Missing email
        }
        
        response = client.post(
            '/api/v1/auth/google-token',
            json={'id_token': 'token_without_email'}
        )
        
        assert response.status_code == 400
        assert 'Failed to get user info' in response.json()['detail']


class TestSessionManagement:
    """Test session token management."""
    
    def test_session_token_stored(self, client, db: Session):
        """Test that session token is stored in database."""
        # Create user
        user = User(
            user_id='test_user_123',
            email='test@example.com',
            name='Test User'
        )
        db.add(user)
        db.commit()
        
        # Create session
        token = create_user_session(db, user.user_id)
        
        # Verify session exists
        session = db.query(UserSession).filter(
            UserSession.session_token == token
        ).first()
        assert session is not None
        assert session.user_id == user.user_id
        assert session.expires_at > datetime.utcnow()
    
    def test_me_endpoint_with_valid_token(self, client, db: Session):
        """Test /me endpoint returns user info with valid token."""
        # Create user and session
        user = User(
            user_id='test_user_123',
            email='test@example.com',
            name='Test User'
        )
        db.add(user)
        db.commit()
        
        token = create_user_session(db, user.user_id)
        
        response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == 'test@example.com'
        assert data['user_id'] == 'test_user_123'
    
    def test_me_endpoint_with_expired_token(self, client, db: Session):
        """Test /me endpoint returns 401 with expired token."""
        # Create user
        user = User(
            user_id='test_user_123',
            email='test@example.com'
        )
        db.add(user)
        db.commit()
        
        # Create expired session
        session = UserSession(
            session_token='expired_token',
            user_id=user.user_id,
            expires_at=datetime.utcnow() - timedelta(hours=1),
            last_accessed_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.add(session)
        db.commit()
        
        response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': 'Bearer expired_token'}
        )
        
        assert response.status_code == 401
        assert 'expired' in response.json()['detail'].lower()
    
    def test_logout_revokes_session(self, client, db: Session):
        """Test logout endpoint revokes session."""
        # Create user and session
        user = User(
            user_id='test_user_123',
            email='test@example.com'
        )
        db.add(user)
        db.commit()
        
        token = create_user_session(db, user.user_id)
        
        # Logout
        response = client.post(
            '/api/v1/auth/logout',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        
        # Verify session is deleted
        session = db.query(UserSession).filter(
            UserSession.session_token == token
        ).first()
        assert session is None
    
    def test_401_on_missing_token(self, client):
        """Test protected endpoints return 401 without token."""
        response = client.get('/api/v1/auth/me')
        assert response.status_code == 401


class TestTokenExpiry:
    """Test token expiry behavior."""
    
    def test_session_expires_after_30_days(self, db: Session):
        """Test session token expires after configured period."""
        user = User(
            user_id='test_user_123',
            email='test@example.com'
        )
        db.add(user)
        db.commit()
        
        # Create session with 30-day expiry (default)
        token = create_user_session(db, user.user_id, expires_hours=24 * 30)
        
        session = db.query(UserSession).filter(
            UserSession.session_token == token
        ).first()
        
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        # Allow 1 minute tolerance for test execution time
        assert abs((session.expires_at - expected_expiry).total_seconds()) < 60
    
    def test_last_accessed_updates(self, client, db: Session):
        """Test last_accessed_at updates on each request."""
        # Create user and session
        user = User(
            user_id='test_user_123',
            email='test@example.com'
        )
        db.add(user)
        db.commit()
        
        token = create_user_session(db, user.user_id)
        
        session = db.query(UserSession).filter(
            UserSession.session_token == token
        ).first()
        old_accessed = session.last_accessed_at
        
        # Make authenticated request
        response = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        assert response.status_code == 200
        
        # Verify last_accessed was updated
        db.refresh(session)
        assert session.last_accessed_at > old_accessed
