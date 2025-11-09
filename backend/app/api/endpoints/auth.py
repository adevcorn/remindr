"""
Authentication endpoints for OAuth flow.

This module implements a two-phase authentication flow:

**Phase 1: Sign In with Google (ID Token Flow)**
1. Mobile app handles Google Sign-In client-side (using Google Sign-In SDK)
2. Mobile app receives ID token from Google
3. Mobile app sends ID token to backend /auth/google-token endpoint
4. Backend verifies ID token with Google's servers
5. Backend creates/updates user and returns session token
6. Mobile app uses session token for all subsequent API calls

**Phase 2: Connect Google Services (OAuth Token Flow)**
1. User initiates "Connect Google Services" from mobile app
2. Mobile app calls /auth/connect-google to get OAuth authorization URL
3. Mobile app opens OAuth URL in webview/browser
4. User grants Calendar & Tasks permissions
5. Google redirects to callback with authorization code
6. Backend exchanges code for access/refresh tokens
7. Backend stores tokens in user record
8. Google sync is now enabled

Session tokens expire after 30 days (configurable). OAuth tokens are
refreshed automatically when expired using the refresh token.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google.auth.transport import requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import create_user_session, get_current_user_id, revoke_session
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

router = APIRouter()

# In-memory state store (use Redis in production)
# Format: {state: {"expiry": timestamp, "user_id": user_id}}
# For connect flow, we need to track which user initiated the OAuth
_oauth_states: dict[str, dict] = {}

# OAuth 2.0 scopes for Google Tasks and Calendar
SCOPES = [
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
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


class GoogleTokenRequest(BaseModel):
    """Request schema for Google ID token authentication."""

    id_token: str


class GoogleConnectionStatus(BaseModel):
    """Response schema for Google connection status."""

    connected: bool
    email: Optional[str] = None
    has_tasks_scope: bool = False
    has_calendar_scope: bool = False


class ConnectGoogleResponse(BaseModel):
    """Response schema for connect Google endpoint."""

    authorization_url: str
    state: str


def get_oauth_flow() -> Flow:
    """Create OAuth 2.0 flow."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }

    flow = Flow.from_client_config(
        client_config, scopes=SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    return flow


@router.post("/google-token", response_model=AuthResponse)
async def authenticate_with_google_token(
    token_request: GoogleTokenRequest, db: Session = Depends(get_db)
):
    """
    Authenticate user with Google ID token (mobile-friendly flow).

    This endpoint accepts an ID token from Google Sign-In (client-side)
    and verifies it with Google's servers. On success, it creates or updates
    the user record and returns a session token.

    Flow:
    1. Mobile app uses Google Sign-In SDK to authenticate
    2. Mobile app receives ID token from Google
    3. Mobile app sends ID token to this endpoint
    4. Backend verifies token with Google
    5. Backend creates/updates user and session
    6. Backend returns session token for future API calls
    """
    try:
        # Verify the ID token with Google
        idinfo = id_token.verify_oauth2_token(
            token_request.id_token, requests.Request(), settings.GOOGLE_CLIENT_ID
        )

        # Verify the issuer
        if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
            raise ValueError("Invalid token issuer")

        # Extract user information from verified token
        google_user_id = idinfo["sub"]
        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email or not google_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from token",
            )

        # Create or update user
        user = db.query(User).filter(User.email == email).first()

        if not user:
            user = User(
                user_id=google_user_id,
                email=email,
                name=name,
                # Note: We don't get access/refresh tokens in this flow
                # Google Tasks/Calendar sync will need to be handled separately
                # or we can request additional scopes when needed
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
        else:
            # Update existing user
            user.last_login_at = datetime.utcnow()
            if name and not user.name:
                user.name = name

        db.commit()
        db.refresh(user)

        # Create session (30-day expiry)
        session_token = create_user_session(db, user.user_id, expires_hours=24 * 30)

        return AuthResponse(
            session_token=session_token,
            user_id=user.user_id,
            email=user.email,
            name=user.name,
        )

    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid ID token: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@router.get("/login")
async def login():
    """
    Initiate OAuth 2.0 flow (legacy web-based flow).
    Redirects to Google's consent screen.

    Note: Mobile apps should use /connect-google instead for a better UX.
    """
    flow = get_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Force consent to get refresh token
    )

    # Store state with 5-minute expiry for CSRF protection
    _oauth_states[state] = {
        "expiry": datetime.utcnow() + timedelta(minutes=5),
        "user_id": None,  # No user context for login flow
    }

    # Clean up expired states
    _cleanup_expired_states()

    return {"authorization_url": authorization_url, "state": state}


@router.get("/callback")
async def oauth_callback(
    code: str, state: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    OAuth 2.0 callback handler.
    Exchanges authorization code for tokens and stores them for the user.

    This endpoint handles two flows:
    1. Login flow (/login): Creates new session
    2. Connect flow (/connect-google): Updates existing user's tokens
    """
    try:
        # Validate state parameter for CSRF protection
        if not state or state not in _oauth_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing state parameter",
            )

        # Check if state is expired
        state_data = _oauth_states[state]
        if state_data["expiry"] < datetime.utcnow():
            del _oauth_states[state]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State parameter expired",
            )

        user_id = state_data.get("user_id")

        # Remove state after validation (one-time use)
        del _oauth_states[state]

        # Exchange authorization code for tokens
        flow = get_oauth_flow()
        flow.fetch_token(code=code)

        credentials = flow.credentials

        # Get user info from Google
        user_info_service = build("oauth2", "v2", credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()

        email = user_info.get("email")
        google_user_id = user_info.get("id")
        name = user_info.get("name")

        if not email or not google_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google",
            )

        # Determine if this is a connect flow (user_id provided) or login flow
        if user_id:
            # Connect flow: Update existing user's tokens
            user = db.query(User).filter(User.user_id == user_id).first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            # Verify email matches (security check)
            if user.email != email:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email mismatch - cannot connect different Google account",
                )

            # Update tokens
            user.google_access_token = credentials.token
            if credentials.refresh_token:
                user.google_refresh_token = credentials.refresh_token
            user.google_token_expiry = credentials.expiry
            user.google_scopes = " ".join(SCOPES)

            db.commit()
            db.refresh(user)

            # Return success for connect flow (no session token needed)
            return {
                "success": True,
                "message": "Google services connected successfully",
                "email": email,
            }
        else:
            # Login flow: Create or update user and return session
            user = db.query(User).filter(User.email == email).first()

            if not user:
                user = User(
                    user_id=google_user_id,
                    email=email,
                    name=name,
                    google_access_token=credentials.token,
                    google_refresh_token=credentials.refresh_token,
                    google_token_expiry=credentials.expiry,
                    google_scopes=" ".join(SCOPES),
                    last_login_at=datetime.utcnow(),
                )
                db.add(user)
            else:
                # Update existing user credentials
                user.google_access_token = credentials.token
                if credentials.refresh_token:
                    user.google_refresh_token = credentials.refresh_token
                user.google_token_expiry = credentials.expiry
                user.google_scopes = " ".join(SCOPES)
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
                name=user.name,
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
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
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Get current authenticated user info.
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {
        "user_id": user.user_id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


@router.get("/connect-google", response_model=ConnectGoogleResponse)
async def connect_google_services(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Initiate OAuth flow to connect Google Tasks/Calendar for an authenticated user.

    This endpoint is called after the user has already signed in via the ID token flow.
    It initiates a separate OAuth flow specifically to obtain access/refresh tokens
    for Google Tasks and Calendar APIs.

    Flow:
    1. User is already authenticated (has valid session token)
    2. Mobile app calls this endpoint to get OAuth URL
    3. Mobile app opens OAuth URL in webview/browser
    4. User grants Calendar & Tasks permissions
    5. Google redirects to /callback with authorization code
    6. Backend exchanges code for tokens and stores them
    """
    # Verify user exists
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Create OAuth flow
    flow = get_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # Force consent to get refresh token
    )

    # Store state with user_id for validation in callback
    _oauth_states[state] = {
        "expiry": datetime.utcnow() + timedelta(minutes=5),
        "user_id": user_id,
    }

    # Clean up expired states
    _cleanup_expired_states()

    return ConnectGoogleResponse(authorization_url=authorization_url, state=state)


@router.get("/google-connection-status", response_model=GoogleConnectionStatus)
async def get_google_connection_status(
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    """
    Check if user has connected Google services (Tasks & Calendar).

    Returns connection status and which scopes are granted.
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user has valid tokens
    connected = bool(user.google_access_token and user.google_refresh_token)

    # Parse scopes to check which services are connected
    scopes = user.google_scopes.split() if user.google_scopes else []
    has_tasks_scope = "https://www.googleapis.com/auth/tasks" in scopes
    has_calendar_scope = "https://www.googleapis.com/auth/calendar" in scopes

    return GoogleConnectionStatus(
        connected=connected,
        email=user.email if connected else None,
        has_tasks_scope=has_tasks_scope,
        has_calendar_scope=has_calendar_scope,
    )


def _cleanup_expired_states():
    """Remove expired OAuth states from memory."""
    now = datetime.utcnow()
    expired = [state for state, data in _oauth_states.items() if data["expiry"] < now]
    for state in expired:
        del _oauth_states[state]
