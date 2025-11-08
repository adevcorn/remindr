"""Authentication endpoints for OAuth flow."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Optional
import json
import secrets

from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.core.auth import create_user_session, get_current_user_id, revoke_session
from pydantic import BaseModel

router = APIRouter()

# In-memory state store (use Redis in production)
# Format: {state: expiry_timestamp}
_oauth_states: dict[str, datetime] = {}

# OAuth 2.0 scopes for Google Tasks and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]


class AuthResponse(BaseModel):
    """Auth response schema."""
    session_token: str
    user_id: str
    email: str
    name: Optional[str] = None


class LogoutResponse(BaseModel):
    """Logout response schema."""
    message: str


def get_oauth_flow() -> Flow:
    """Create OAuth 2.0 flow."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    
    return flow


@router.get("/login")
async def login():
    """
    Initiate OAuth 2.0 flow.
    Redirects to Google's consent screen.
    """
    flow = get_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent to get refresh token
    )
    
    # Store state with 5-minute expiry for CSRF protection
    _oauth_states[state] = datetime.utcnow() + timedelta(minutes=5)
    
    # Clean up expired states
    _cleanup_expired_states()
    
    return {
        "authorization_url": authorization_url,
        "state": state
    }


@router.get("/callback")
async def oauth_callback(
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    OAuth 2.0 callback handler.
    Exchanges authorization code for tokens and creates user session.
    """
    try:
        # Validate state parameter for CSRF protection
        if not state or state not in _oauth_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing state parameter"
            )
        
        # Check if state is expired
        if _oauth_states[state] < datetime.utcnow():
            del _oauth_states[state]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State parameter expired"
            )
        
        # Remove state after validation (one-time use)
        del _oauth_states[state]
        
        # Exchange authorization code for tokens
        flow = get_oauth_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Get user info from Google
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        email = user_info.get('email')
        google_user_id = user_info.get('id')
        name = user_info.get('name')
        
        if not email or not google_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        # Create or update user
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            user = User(
                user_id=google_user_id,
                email=email,
                name=name,
                google_access_token=credentials.token,
                google_refresh_token=credentials.refresh_token,
                google_token_expiry=credentials.expiry,
                google_scopes=' '.join(SCOPES),
                last_login_at=datetime.utcnow()
            )
            db.add(user)
        else:
            # Update existing user credentials
            user.google_access_token = credentials.token
            if credentials.refresh_token:
                user.google_refresh_token = credentials.refresh_token
            user.google_token_expiry = credentials.expiry
            user.google_scopes = ' '.join(SCOPES)
            user.last_login_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        # Create session
        session_token = create_user_session(db, user.user_id)
        
        # Return auth response
        return AuthResponse(
            session_token=session_token,
            user_id=user.user_id,
            email=user.email,
            name=user.name
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Logout current user by revoking session.
    """
    from app.models.user import Session as UserSession
    
    # Get all sessions for user and revoke them
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
    
    for session in sessions:
        db.delete(session)
    
    db.commit()
    
    return LogoutResponse(message="Logged out successfully")


@router.get("/me")
async def get_current_user_info(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get current authenticated user info.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at
    }


def _cleanup_expired_states():
    """Remove expired OAuth states from memory."""
    now = datetime.utcnow()
    expired = [state for state, expiry in _oauth_states.items() if expiry < now]
    for state in expired:
        del _oauth_states[state]
