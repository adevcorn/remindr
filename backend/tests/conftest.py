"""Test configuration and fixtures."""
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
# Import all models to register them with SQLAlchemy
from app.models.user import User, Session as UserSession
from app.models.capture import Capture, Draft

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
        mock_vision_client = MagicMock()
        mock_vision.return_value = mock_vision_client
        
        # Mock OCR response
        mock_response = MagicMock()
        mock_response.error.message = ""
        mock_response.full_text_annotation.text = "Sample OCR text"
        mock_response.full_text_annotation.pages = []
        mock_vision_client.document_text_detection.return_value = mock_response
        
        # Mock Google Cloud Speech client
        with patch("google.cloud.speech_v1.SpeechClient") as mock_speech:
            mock_speech_client = MagicMock()
            mock_speech.return_value = mock_speech_client
            
            # Mock speech recognition response
            mock_speech_response = MagicMock()
            mock_speech_result = MagicMock()
            mock_speech_alternative = MagicMock()
            mock_speech_alternative.transcript = "Sample transcription"
            mock_speech_alternative.confidence = 0.95
            mock_speech_result.alternatives = [mock_speech_alternative]
            mock_speech_response.results = [mock_speech_result]
            mock_speech_client.recognize.return_value = mock_speech_response
            
            # Mock SentenceTransformer for NLP service
            with patch("sentence_transformers.SentenceTransformer") as mock_st:
                mock_model = MagicMock()
                mock_st.return_value = mock_model
                
                # Mock encode to return dummy tensors
                import numpy as np
                mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
                
                yield {
                    "vision": mock_vision_client,
                    "speech": mock_speech_client,
                    "nlp": mock_model
                }
