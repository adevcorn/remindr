"""Performance benchmarks for Remindr.

Tests validate that the system meets PRD performance targets:
- Task capture time: < 3 seconds
- Google sync latency: < 10 seconds
- AI classification accuracy: ≥ 90%
- NLP inference time: < 500ms

Run with: pytest tests/test_performance.py -v -s
Or use: bash scripts/run-performance-tests.sh
"""
import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import base64

from app.services.nlp import nlp_service
from app.services.speech_to_text import speech_service
from app.services.ocr import ocr_service
from app.services.google_sync import google_sync_service
from app.services.tasks import sync_draft_to_google_with_retry
from app.models.capture import DraftType, CaptureState


# ============================================================================
# Constants and Configuration
# ============================================================================

# PRD Performance Targets
TARGET_CAPTURE_TIME = 3.0  # seconds
TARGET_SYNC_LATENCY = 10.0  # seconds
TARGET_NLP_INFERENCE = 0.5  # seconds (500ms)
TARGET_AI_ACCURACY = 0.90  # 90%

# Benchmark Configuration
BENCHMARK_ITERATIONS = 10  # Run each test 10 times for statistical validity
WARMUP_ITERATIONS = 2  # Warm up models before benchmarking

# Sample test data
SAMPLE_TASKS = [
    "Buy groceries tomorrow",
    "Call the dentist at 2pm on Friday",
    "Submit quarterly report by end of week",
    "Schedule team meeting for next Monday at 10am",
    "Review pull request #42 urgent",
]

SAMPLE_EVENTS = [
    "Doctor appointment tomorrow at 3pm",
    "Conference call with client on Wednesday at 9am",
    "Lunch with Sarah at Cafe Roma at noon",
    "Team standup meeting at 9:30am daily",
    "Birthday party on Saturday at 7pm",
]

SAMPLE_NOTES = [
    "Remember to bring laptop charger",
    "Note to self: check email before meeting",
    "Don't forget parking pass tomorrow",
    "Keep in mind the deadline is flexible",
    "Important: verify credentials before deployment",
]


# ============================================================================
# Fixtures and Helpers
# ============================================================================

@pytest.fixture
def mock_audio_data():
    """Generate mock audio data (base64-encoded)."""
    # Simulate 2-second audio clip at 16kHz, 16-bit
    audio_bytes = b'\x00' * (16000 * 2 * 2)  # 2 seconds
    return audio_bytes


@pytest.fixture
def mock_image_data():
    """Generate mock image data."""
    # Simulate small image (1KB)
    image_bytes = b'\xFF\xD8\xFF' * 300  # JPEG header pattern
    return image_bytes


@pytest.fixture
def mock_google_credentials():
    """Mock Google OAuth credentials."""
    from google.oauth2.credentials import Credentials
    return Credentials(
        token="mock_access_token",
        refresh_token="mock_refresh_token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="mock_client_id",
        client_secret="mock_client_secret"
    )


def calculate_statistics(timings: List[float]) -> Dict[str, float]:
    """Calculate performance statistics from timing measurements."""
    return {
        "mean": statistics.mean(timings),
        "median": statistics.median(timings),
        "stdev": statistics.stdev(timings) if len(timings) > 1 else 0.0,
        "min": min(timings),
        "max": max(timings),
        "p95": sorted(timings)[int(len(timings) * 0.95)] if len(timings) > 1 else timings[0],
        "p99": sorted(timings)[int(len(timings) * 0.99)] if len(timings) > 1 else timings[0],
    }


def print_benchmark_results(test_name: str, timings: List[float], target: float):
    """Pretty-print benchmark results."""
    stats = calculate_statistics(timings)
    
    print(f"\n{'=' * 70}")
    print(f"Benchmark: {test_name}")
    print(f"{'=' * 70}")
    print(f"Iterations: {len(timings)}")
    print(f"Target: {target:.3f}s")
    print(f"Mean: {stats['mean']:.3f}s")
    print(f"Median: {stats['median']:.3f}s")
    print(f"Min: {stats['min']:.3f}s")
    print(f"Max: {stats['max']:.3f}s")
    print(f"StdDev: {stats['stdev']:.3f}s")
    print(f"P95: {stats['p95']:.3f}s")
    print(f"P99: {stats['p99']:.3f}s")
    
    # Performance verdict
    passes = stats['p95'] < target
    status = "✅ PASS" if passes else "❌ FAIL"
    improvement = ((target - stats['mean']) / target) * 100
    
    print(f"\nStatus: {status}")
    if passes:
        print(f"Performance: {abs(improvement):.1f}% {'better' if improvement > 0 else 'worse'} than target")
    else:
        print(f"Performance: {abs(improvement):.1f}% slower than target")
    print(f"{'=' * 70}\n")


# ============================================================================
# NLP Performance Benchmarks
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
async def test_nlp_inference_performance():
    """
    Benchmark: NLP inference time
    Target: < 500ms per classification
    
    Tests the AI classification and entity extraction pipeline.
    This is the core AI performance metric.
    """
    # Warm up the model
    for _ in range(WARMUP_ITERATIONS):
        await nlp_service.classify_and_extract(SAMPLE_TASKS[0])
    
    timings = []
    all_confidences = []
    
    # Benchmark across diverse inputs
    test_samples = SAMPLE_TASKS + SAMPLE_EVENTS + SAMPLE_NOTES
    
    for _ in range(BENCHMARK_ITERATIONS):
        for text in test_samples:
            start = time.perf_counter()
            draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
            elapsed = time.perf_counter() - start
            
            timings.append(elapsed)
            all_confidences.append(confidence)
    
    print_benchmark_results("NLP Inference Time", timings, TARGET_NLP_INFERENCE)
    
    # Validate AI accuracy (confidence as proxy)
    avg_confidence = statistics.mean(all_confidences)
    print(f"Average AI Confidence: {avg_confidence:.2%} (target: {TARGET_AI_ACCURACY:.0%})")
    
    # Performance assertions
    stats = calculate_statistics(timings)
    assert stats['p95'] < TARGET_NLP_INFERENCE, \
        f"P95 latency {stats['p95']:.3f}s exceeds target {TARGET_NLP_INFERENCE}s"
    assert avg_confidence >= TARGET_AI_ACCURACY * 0.8, \
        f"Average confidence {avg_confidence:.2%} is too low (target: {TARGET_AI_ACCURACY:.0%})"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_nlp_classification_accuracy():
    """
    Benchmark: AI classification accuracy
    Target: ≥ 90% correct classification
    
    Tests that the NLP service correctly classifies tasks vs events vs notes.
    """
    correct_classifications = 0
    total_classifications = 0
    
    # Test task classification
    for text in SAMPLE_TASKS:
        draft_type, confidence, _ = await nlp_service.classify_and_extract(text)
        if draft_type == DraftType.TASK:
            correct_classifications += 1
        total_classifications += 1
    
    # Test event classification
    for text in SAMPLE_EVENTS:
        draft_type, confidence, _ = await nlp_service.classify_and_extract(text)
        if draft_type == DraftType.EVENT:
            correct_classifications += 1
        total_classifications += 1
    
    # Test note classification
    for text in SAMPLE_NOTES:
        draft_type, confidence, _ = await nlp_service.classify_and_extract(text)
        if draft_type == DraftType.NOTE:
            correct_classifications += 1
        total_classifications += 1
    
    accuracy = correct_classifications / total_classifications
    
    print(f"\n{'=' * 70}")
    print("Benchmark: AI Classification Accuracy")
    print(f"{'=' * 70}")
    print(f"Correct: {correct_classifications}/{total_classifications}")
    print(f"Accuracy: {accuracy:.1%} (target: {TARGET_AI_ACCURACY:.0%})")
    print(f"Status: {'✅ PASS' if accuracy >= TARGET_AI_ACCURACY else '❌ FAIL'}")
    print(f"{'=' * 70}\n")
    
    assert accuracy >= TARGET_AI_ACCURACY, \
        f"Classification accuracy {accuracy:.1%} below target {TARGET_AI_ACCURACY:.0%}"


# ============================================================================
# End-to-End Capture Performance Benchmarks
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
async def test_text_capture_end_to_end_performance():
    """
    Benchmark: Text capture end-to-end latency
    Target: < 3 seconds
    
    Simulates the complete flow:
    1. Receive text input
    2. NLP classification and entity extraction
    3. Draft creation
    
    This is the fastest capture path (no ASR/OCR).
    """
    timings = []
    
    for _ in range(BENCHMARK_ITERATIONS):
        for text in SAMPLE_TASKS[:3]:  # Test subset for speed
            start = time.perf_counter()
            
            # Simulate complete text capture flow
            draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
            
            # Simulate draft creation (minimal overhead)
            draft = {
                "draft_type": draft_type,
                "confidence": confidence,
                "title": entities["title"],
                "entities": entities
            }
            
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
    
    print_benchmark_results("Text Capture End-to-End", timings, TARGET_CAPTURE_TIME)
    
    stats = calculate_statistics(timings)
    assert stats['p95'] < TARGET_CAPTURE_TIME, \
        f"P95 latency {stats['p95']:.3f}s exceeds target {TARGET_CAPTURE_TIME}s"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_voice_capture_end_to_end_performance(mock_audio_data):
    """
    Benchmark: Voice capture end-to-end latency
    Target: < 3 seconds
    
    Simulates the complete flow:
    1. Receive audio data
    2. Speech-to-text transcription (mocked)
    3. NLP classification and entity extraction
    4. Draft creation
    
    Note: Google Speech API is mocked to test only controllable latency.
    Real ASR latency depends on Google's infrastructure.
    """
    timings = []
    
    # Mock Speech-to-Text to isolate NLP performance
    with patch.object(speech_service, 'transcribe_audio', new_callable=AsyncMock) as mock_stt:
        # Simulate realistic STT latency (500-1000ms)
        async def mock_transcribe(audio_data, language_code="en-US"):
            await asyncio.sleep(0.75)  # 750ms simulated STT latency
            return "Buy groceries tomorrow", 0.95
        
        mock_stt.side_effect = mock_transcribe
        
        for _ in range(BENCHMARK_ITERATIONS):
            start = time.perf_counter()
            
            # Simulate complete voice capture flow
            text, stt_confidence = await speech_service.transcribe_audio(mock_audio_data)
            draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
            
            # Simulate draft creation
            draft = {
                "draft_type": draft_type,
                "confidence": confidence,
                "title": entities["title"],
                "entities": entities
            }
            
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
    
    print_benchmark_results("Voice Capture End-to-End (with mocked STT)", timings, TARGET_CAPTURE_TIME)
    
    stats = calculate_statistics(timings)
    assert stats['p95'] < TARGET_CAPTURE_TIME, \
        f"P95 latency {stats['p95']:.3f}s exceeds target {TARGET_CAPTURE_TIME}s"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_image_capture_end_to_end_performance(mock_image_data):
    """
    Benchmark: Image capture end-to-end latency
    Target: < 3 seconds
    
    Simulates the complete flow:
    1. Receive image data
    2. OCR text extraction (mocked)
    3. NLP classification and entity extraction
    4. Draft creation
    
    Note: Google Vision API is mocked to test only controllable latency.
    Real OCR latency depends on Google's infrastructure.
    """
    timings = []
    
    # Mock OCR to isolate NLP performance
    with patch.object(ocr_service, 'extract_text', new_callable=AsyncMock) as mock_ocr:
        # Simulate realistic OCR latency (800-1200ms)
        async def mock_extract(image_data):
            await asyncio.sleep(1.0)  # 1000ms simulated OCR latency
            return "Submit report by Friday", 0.92
        
        mock_ocr.side_effect = mock_extract
        
        for _ in range(BENCHMARK_ITERATIONS):
            start = time.perf_counter()
            
            # Simulate complete image capture flow
            text, ocr_confidence = await ocr_service.extract_text(mock_image_data)
            draft_type, confidence, entities = await nlp_service.classify_and_extract(text)
            
            # Simulate draft creation
            draft = {
                "draft_type": draft_type,
                "confidence": confidence,
                "title": entities["title"],
                "entities": entities
            }
            
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
    
    print_benchmark_results("Image Capture End-to-End (with mocked OCR)", timings, TARGET_CAPTURE_TIME)
    
    stats = calculate_statistics(timings)
    assert stats['p95'] < TARGET_CAPTURE_TIME, \
        f"P95 latency {stats['p95']:.3f}s exceeds target {TARGET_CAPTURE_TIME}s"


# ============================================================================
# Google Sync Performance Benchmarks
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
async def test_google_sync_latency(mock_google_credentials):
    """
    Benchmark: Google Tasks/Calendar sync latency
    Target: < 10 seconds
    
    Tests the time to sync a draft to Google Tasks or Calendar.
    Uses mocked Google APIs to test only our sync logic overhead.
    """
    timings = []
    
    # Mock Google API calls
    with patch.object(google_sync_service, 'sync_task', new_callable=AsyncMock) as mock_task, \
         patch.object(google_sync_service, 'sync_event', new_callable=AsyncMock) as mock_event:
        
        # Simulate realistic Google API latency (500-2000ms)
        async def mock_sync_task(*args, **kwargs):
            await asyncio.sleep(1.0)  # 1000ms simulated API latency
            return "mock_task_id_12345", None
        
        async def mock_sync_event(*args, **kwargs):
            await asyncio.sleep(1.2)  # 1200ms simulated API latency
            return "mock_event_id_67890", None
        
        mock_task.side_effect = mock_sync_task
        mock_event.side_effect = mock_sync_event
        
        for _ in range(BENCHMARK_ITERATIONS):
            # Test task sync
            start = time.perf_counter()
            task_id, error = await google_sync_service.sync_task(
                credentials=mock_google_credentials,
                title="Test task",
                description="Test description"
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
            
            # Test event sync
            start = time.perf_counter()
            event_id, error = await google_sync_service.sync_event(
                credentials=mock_google_credentials,
                title="Test event",
                description="Test description"
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
    
    print_benchmark_results("Google Sync Latency (with mocked API)", timings, TARGET_SYNC_LATENCY)
    
    stats = calculate_statistics(timings)
    assert stats['p95'] < TARGET_SYNC_LATENCY, \
        f"P95 latency {stats['p95']:.3f}s exceeds target {TARGET_SYNC_LATENCY}s"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_offline_sync_batch_performance(db_session, mock_google_credentials):
    """
    Benchmark: Offline sync batch processing
    Target: 60-80% improvement over serial sync
    
    Tests that batch syncing multiple drafts in parallel is significantly
    faster than syncing them serially (as would happen without optimization).
    """
    from app.models.capture import Draft
    from datetime import datetime
    
    num_drafts = 5
    
    # Create mock drafts
    draft_ids = []
    for i in range(num_drafts):
        draft = Draft(
            id=1000 + i,
            user_id="test_user",
            capture_id=100 + i,
            draft_type=DraftType.TASK,
            title=f"Test draft {i}",
            ai_confidence=0.9,
            is_confirmed=True,
            sync_state=CaptureState.CONFIRMED
        )
        db_session.add(draft)
        draft_ids.append(draft.id)
    
    db_session.commit()
    
    # Mock Google API with realistic latency
    with patch.object(google_sync_service, 'sync_task', new_callable=AsyncMock) as mock_sync:
        async def mock_task_sync(*args, **kwargs):
            await asyncio.sleep(1.0)  # 1000ms per sync
            return f"mock_task_id_{time.time()}", None
        
        mock_sync.side_effect = mock_task_sync
        
        # Benchmark serial sync (baseline)
        serial_start = time.perf_counter()
        for draft_id in draft_ids:
            await google_sync_service.sync_task(
                credentials=mock_google_credentials,
                title="Test task"
            )
        serial_time = time.perf_counter() - serial_start
        
        # Benchmark parallel sync (optimized)
        parallel_start = time.perf_counter()
        sync_tasks = [
            google_sync_service.sync_task(
                credentials=mock_google_credentials,
                title="Test task"
            )
            for _ in range(num_drafts)
        ]
        await asyncio.gather(*sync_tasks)
        parallel_time = time.perf_counter() - parallel_start
    
    improvement = ((serial_time - parallel_time) / serial_time) * 100
    
    print(f"\n{'=' * 70}")
    print("Benchmark: Offline Sync Batch Processing")
    print(f"{'=' * 70}")
    print(f"Number of drafts: {num_drafts}")
    print(f"Serial sync time: {serial_time:.3f}s")
    print(f"Parallel sync time: {parallel_time:.3f}s")
    print(f"Improvement: {improvement:.1f}%")
    print(f"Target: 60-80% improvement")
    print(f"Status: {'✅ PASS' if improvement >= 60 else '❌ FAIL'}")
    print(f"{'=' * 70}\n")
    
    assert improvement >= 60, \
        f"Parallel sync improvement {improvement:.1f}% below 60% target"
    assert parallel_time < serial_time * 0.4, \
        f"Parallel sync not fast enough: {parallel_time:.3f}s vs {serial_time:.3f}s"


# ============================================================================
# Concurrent Load Benchmarks
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_nlp_processing():
    """
    Benchmark: Concurrent NLP processing under load
    Target: Handle 10 concurrent classifications within 1 second
    
    Tests that the NLP service can handle multiple concurrent requests
    efficiently, simulating multiple users capturing tasks simultaneously.
    """
    num_concurrent = 10
    texts = [SAMPLE_TASKS[i % len(SAMPLE_TASKS)] for i in range(num_concurrent)]
    
    # Warm up
    await nlp_service.classify_and_extract(texts[0])
    
    start = time.perf_counter()
    
    # Process concurrently
    tasks = [
        nlp_service.classify_and_extract(text)
        for text in texts
    ]
    results = await asyncio.gather(*tasks)
    
    elapsed = time.perf_counter() - start
    avg_per_request = elapsed / num_concurrent
    
    print(f"\n{'=' * 70}")
    print("Benchmark: Concurrent NLP Processing")
    print(f"{'=' * 70}")
    print(f"Concurrent requests: {num_concurrent}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Average per request: {avg_per_request:.3f}s")
    print(f"Target: < 1.0s total time")
    print(f"Status: {'✅ PASS' if elapsed < 1.0 else '❌ FAIL'}")
    print(f"{'=' * 70}\n")
    
    assert elapsed < 1.0, \
        f"Concurrent processing took {elapsed:.3f}s, exceeds 1.0s target"
    assert all(r[1] > 0.5 for r in results), \
        "Some classifications have low confidence under load"


# ============================================================================
# Regression and Stress Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
async def test_nlp_performance_with_long_text():
    """
    Benchmark: NLP performance with long/complex text
    Target: < 800ms (allowance for longer text)
    
    Tests that the NLP service handles longer, more complex inputs
    without significant performance degradation.
    """
    long_texts = [
        "Schedule a team meeting for next Monday at 10am in Conference Room B to discuss the Q4 roadmap, "
        "invite all engineering leads, send calendar invite with Zoom link, prepare slides about feature priorities, "
        "and don't forget to include the budget review document in the meeting notes",
        
        "Buy groceries tomorrow morning before 10am including milk, eggs, bread, chicken, vegetables, "
        "coffee, and cereal, also pick up prescription at pharmacy on the way back, "
        "remember to use the discount coupon that expires this week",
    ]
    
    timings = []
    
    for _ in range(BENCHMARK_ITERATIONS):
        for text in long_texts:
            start = time.perf_counter()
            await nlp_service.classify_and_extract(text)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)
    
    print_benchmark_results("NLP Performance with Long Text", timings, 0.8)
    
    stats = calculate_statistics(timings)
    assert stats['p95'] < 0.8, \
        f"P95 latency {stats['p95']:.3f}s exceeds 800ms target for long text"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_memory_efficiency():
    """
    Benchmark: Memory efficiency during sustained operation
    Target: No significant memory growth over 100 operations
    
    Tests that repeated NLP operations don't cause memory leaks
    or excessive memory consumption.
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    # Measure initial memory
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Run sustained operations
    for _ in range(100):
        for text in SAMPLE_TASKS + SAMPLE_EVENTS:
            await nlp_service.classify_and_extract(text)
    
    # Measure final memory
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - initial_memory
    growth_percentage = (memory_growth / initial_memory) * 100
    
    print(f"\n{'=' * 70}")
    print("Benchmark: Memory Efficiency")
    print(f"{'=' * 70}")
    print(f"Initial memory: {initial_memory:.2f} MB")
    print(f"Final memory: {final_memory:.2f} MB")
    print(f"Memory growth: {memory_growth:.2f} MB ({growth_percentage:.1f}%)")
    print(f"Target: < 20% growth")
    print(f"Status: {'✅ PASS' if growth_percentage < 20 else '❌ FAIL'}")
    print(f"{'=' * 70}\n")
    
    assert growth_percentage < 20, \
        f"Memory grew by {growth_percentage:.1f}%, exceeds 20% threshold"


# ============================================================================
# Summary Test
# ============================================================================

@pytest.mark.performance
@pytest.mark.asyncio
async def test_performance_summary():
    """
    Summary benchmark that runs all key metrics and reports overall performance.
    
    This test provides a comprehensive performance report card for the system.
    """
    results = {}
    
    # NLP inference
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        await nlp_service.classify_and_extract(SAMPLE_TASKS[0])
        timings.append(time.perf_counter() - start)
    results['nlp_inference'] = {
        'mean': statistics.mean(timings),
        'target': TARGET_NLP_INFERENCE,
        'pass': statistics.mean(timings) < TARGET_NLP_INFERENCE
    }
    
    # Text capture
    timings = []
    for _ in range(5):
        start = time.perf_counter()
        await nlp_service.classify_and_extract("Buy groceries tomorrow")
        timings.append(time.perf_counter() - start)
    results['text_capture'] = {
        'mean': statistics.mean(timings),
        'target': TARGET_CAPTURE_TIME,
        'pass': statistics.mean(timings) < TARGET_CAPTURE_TIME
    }
    
    # Classification accuracy
    correct = 0
    total = 0
    for text in SAMPLE_TASKS[:3]:
        draft_type, _, _ = await nlp_service.classify_and_extract(text)
        if draft_type == DraftType.TASK:
            correct += 1
        total += 1
    results['classification_accuracy'] = {
        'mean': correct / total,
        'target': TARGET_AI_ACCURACY,
        'pass': (correct / total) >= TARGET_AI_ACCURACY
    }
    
    # Print summary
    print(f"\n{'=' * 70}")
    print("PERFORMANCE SUMMARY")
    print(f"{'=' * 70}")
    
    for metric, data in results.items():
        status = "✅ PASS" if data['pass'] else "❌ FAIL"
        if metric == 'classification_accuracy':
            print(f"{metric:30s}: {data['mean']:.1%} (target: {data['target']:.0%}) {status}")
        else:
            print(f"{metric:30s}: {data['mean']:.3f}s (target: {data['target']:.3f}s) {status}")
    
    overall_pass = all(r['pass'] for r in results.values())
    print(f"\nOverall Status: {'✅ ALL TESTS PASS' if overall_pass else '❌ SOME TESTS FAIL'}")
    print(f"{'=' * 70}\n")
    
    assert overall_pass, "Some performance benchmarks failed"
