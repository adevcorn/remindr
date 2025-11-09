"""Test configuration and fixtures."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base

# Test database URL
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session", autouse=True)
def mock_google_services():
    """Mock Google Cloud services to prevent real API calls during tests."""
    # Mock Google Cloud Vision client
    with patch("google.cloud.vision.ImageAnnotatorClient") as mock_vision:
        mock_client = MagicMock()
        mock_vision.return_value = mock_client
        
        # Mock OCR response
        mock_response = MagicMock()
        mock_response.error.message = ""
        mock_response.full_text_annotation.text = "Sample OCR text"
        mock_response.full_text_annotation.pages = []
        mock_client.document_text_detection.return_value = mock_response
        
        yield mock_client
