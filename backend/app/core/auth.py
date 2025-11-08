"""Authentication and authorization utilities."""
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import secrets

from app.db.session import get_db
from app.models.user import User, Session as UserSession
from app.core.config import settings

security = HTTPBearer(auto_error=False)


def create_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def create_user_session(db: Session, user_id: str, expires_hours: int = 24 * 30) -> str:
    """Create a new session for a user."""
    session_token = create_session_token()
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
    
    session = UserSession(
        session_token=session_token,
        user_id=user_id,
        expires_at=expires_at,
        last_accessed_at=datetime.utcnow()
    )
    
    db.add(session)
    db.commit()
    
    return session_token


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> str:
    """
    Get the current authenticated user's ID from the session token.
    
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    session_token = credentials.credentials
    
    # Look up session
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check expiration
    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last accessed time
    session.last_accessed_at = datetime.utcnow()
    db.commit()
    
    return session.user_id


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user object.
    
    Raises:
        HTTPException: 401 if user not found
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def revoke_session(db: Session, session_token: str) -> bool:
    """Revoke a session token."""
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token
    ).first()
    
    if session:
        db.delete(session)
        db.commit()
        return True
    
    return False
