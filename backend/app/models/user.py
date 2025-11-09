"""User and authentication models."""

from datetime import datetime

from app.db.base import Base
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func


class User(Base):
    """User account with OAuth credentials."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        String, unique=True, nullable=False, index=True
    )  # Unique identifier
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)

    # OAuth credentials (encrypted in production)
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expiry = Column(DateTime(timezone=True), nullable=True)
    google_scopes = Column(Text, nullable=True)  # Space-separated scopes

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class Session(Base):
    """User session tokens."""

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)

    # Session metadata
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
