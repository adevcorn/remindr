"""Tests for NLP service."""
import pytest
from app.services.nlp import nlp_service
from app.models.capture import DraftType


@pytest.mark.asyncio
async def test_classify_task():
    """Test classifying a task."""
    text = "Buy groceries tomorrow at 5pm"
    
    draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
    
    assert draft_type == DraftType.TASK
    assert confidence > 0.0
    assert entities["title"] is not None
    assert "buy" in entities["title"].lower() or "groceries" in entities["title"].lower()


@pytest.mark.asyncio
async def test_classify_event():
    """Test classifying an event."""
    text = "Meeting with John tomorrow at 3pm in Conference Room A"
    
    draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
    
    assert draft_type == DraftType.EVENT
    assert confidence > 0.0
    assert entities["title"] is not None
    assert entities["start_time"] is not None


@pytest.mark.asyncio
async def test_classify_note():
    """Test classifying a note."""
    text = "Remember that Paris is the capital of France"
    
    draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
    
    assert draft_type == DraftType.NOTE
    assert confidence > 0.0
    assert entities["title"] is not None


@pytest.mark.asyncio
async def test_extract_due_date():
    """Test extracting due date from text."""
    text = "Complete report by Friday"
    
    _, _, entities = await nlp_service.classify_and_extract(text)
    
    # Should extract a due date (may vary based on current date)
    assert entities["due_date"] is not None or entities["start_time"] is not None


@pytest.mark.asyncio
async def test_extract_priority():
    """Test extracting priority from text."""
    text = "URGENT: Fix production bug immediately"
    
    _, _, entities = await nlp_service.classify_and_extract(text)
    
    assert entities["priority"] in ["low", "medium", "high"]
    # Urgent should result in high priority
    assert entities["priority"] == "high"


@pytest.mark.asyncio
async def test_empty_text():
    """Test handling of empty text."""
    text = ""
    
    with pytest.raises(Exception):
        await nlp_service.classify_and_extract(text)
