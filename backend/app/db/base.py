"""Database base configuration."""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here to ensure they are registered with Base
# This is required for Alembic migrations
from app.models.capture import Capture, Draft  # noqa
from app.models.user import User, Session  # noqa
