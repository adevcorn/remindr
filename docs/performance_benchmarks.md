# Performance Benchmarks Documentation

## Overview

This document describes the performance benchmark suite for Remindr and provides guidance on interpreting results, troubleshooting performance issues, and optimizing the system to meet PRD targets.

## PRD Performance Targets

The following performance targets are defined in the Product Requirements Document (PRD):

| Metric | Target | Critical Path |
|--------|--------|---------------|
| **Task Capture Time** | < 3 seconds | Voice/text/image → parsed draft |
| **Google Sync Latency** | < 10 seconds | Draft confirmation → synced to Google |
| **AI Classification Accuracy** | ≥ 90% | Correct task/event/note classification |
| **NLP Inference Time** | < 500ms | Text → classification + entities |

## Running Benchmarks

### Quick Start

```bash
# Run all performance benchmarks
bash scripts/run-performance-tests.sh

# Run quick smoke tests only
bash scripts/run-performance-tests.sh --quick

# Verbose output with timing details
bash scripts/run-performance-tests.sh --verbose

# CI mode (strict assertions, no verbose output)
bash scripts/run-performance-tests.sh --ci
```

### Direct pytest Execution

```bash
# Run all performance tests
cd backend
pytest tests/test_performance.py -m performance -v -s

# Run specific benchmark
pytest tests/test_performance.py::test_nlp_inference_performance -v -s

# Run with coverage report
pytest tests/test_performance.py -m performance --cov=app --cov-report=html
```

## Benchmark Test Suite

### Core Performance Benchmarks

#### 1. NLP Inference Performance
- **Test**: `test_nlp_inference_performance`
- **Target**: < 500ms per classification
- **What it tests**: End-to-end NLP pipeline (embedding generation, classification, entity extraction)
- **Iterations**: 10 runs across 15 diverse samples
- **Metrics**: Mean, median, min, max, P95, P99, standard deviation

**Expected Results:**
```
Mean: ~200-400ms
P95: < 500ms
Average Confidence: > 80%
```

**Optimization tips if failing:**
- Ensure sentence-transformers model is cached (`~/.cache/huggingface/`)
- Check CPU/memory availability
- Profile with `python -m cProfile` to identify bottlenecks
- Consider model quantization for faster inference

---

#### 2. AI Classification Accuracy
- **Test**: `test_nlp_classification_accuracy`
- **Target**: ≥ 90% correct classification
- **What it tests**: Classification accuracy across tasks, events, and notes
- **Sample Size**: 15 test cases (5 tasks, 5 events, 5 notes)

**Expected Results:**
```
Accuracy: 90-100%
Status: ✅ PASS
```

**Troubleshooting low accuracy:**
- Review misclassified samples in output
- Adjust confidence thresholds in `nlp_service.py`
- Retrain or fine-tune classification patterns
- Add more pattern examples to `task_patterns`, `event_patterns`, `note_patterns`

---

#### 3. Text Capture End-to-End
- **Test**: `test_text_capture_end_to_end_performance`
- **Target**: < 3 seconds
- **What it tests**: Complete text capture flow (text → NLP → draft)
- **Iterations**: 10 runs

**Expected Results:**
```
Mean: ~200-500ms
P95: < 3.0s
```

**This is the fastest capture path** - no ASR/OCR overhead. If this fails, NLP optimization is needed.

---

#### 4. Voice Capture End-to-End
- **Test**: `test_voice_capture_end_to_end_performance`
- **Target**: < 3 seconds
- **What it tests**: Complete voice capture flow (audio → STT → NLP → draft)
- **Note**: Google Speech API is **mocked** with 750ms simulated latency

**Expected Results:**
```
Mean: ~1.0-1.5s
P95: < 3.0s
```

**Real-world considerations:**
- Actual STT latency depends on Google Speech API (typically 500-1500ms)
- Network latency adds 50-200ms
- Audio quality affects transcription time
- Use streaming STT for real-time feedback

---

#### 5. Image Capture End-to-End
- **Test**: `test_image_capture_end_to_end_performance`
- **Target**: < 3 seconds
- **What it tests**: Complete image capture flow (image → OCR → NLP → draft)
- **Note**: Google Vision API is **mocked** with 1000ms simulated latency

**Expected Results:**
```
Mean: ~1.2-1.8s
P95: < 3.0s
```

**Real-world considerations:**
- Actual OCR latency depends on Google Vision API (typically 800-2000ms)
- Image size/quality affects processing time
- Handwriting recognition is slower than printed text
- Consider client-side image compression before upload

---

#### 6. Google Sync Latency
- **Test**: `test_google_sync_latency`
- **Target**: < 10 seconds
- **What it tests**: Time to sync draft to Google Tasks/Calendar
- **Note**: Google APIs are **mocked** with realistic latency (1000-1200ms)

**Expected Results:**
```
Mean: ~1.0-1.2s
P95: < 10.0s
```

**Real-world considerations:**
- Actual sync latency: 1-3 seconds typical, up to 10 seconds under load
- Network conditions significantly impact latency
- Google API rate limits may cause retries (exponential backoff)
- Use background sync to avoid blocking user

---

#### 7. Offline Sync Batch Performance
- **Test**: `test_offline_sync_batch_performance`
- **Target**: 60-80% improvement over serial sync
- **What it tests**: Parallel sync of multiple drafts vs serial

**Expected Results:**
```
Serial: ~5.0s (5 drafts × 1s each)
Parallel: ~1.0-1.5s (concurrent execution)
Improvement: 70-80%
```

**Optimization architecture:**
- Uses `asyncio.gather()` for concurrent API calls
- Background tasks via FastAPI `BackgroundTasks`
- Removed Celery overhead (was adding 1-3s per task)

---

### Stress and Load Tests

#### 8. Concurrent NLP Processing
- **Test**: `test_concurrent_nlp_processing`
- **Target**: 10 concurrent requests in < 1 second
- **What it tests**: NLP service under concurrent load

**Expected Results:**
```
Total: < 1.0s for 10 concurrent requests
Average per request: ~100-200ms
```

**This validates that async/await doesn't block on I/O.**

---

#### 9. NLP Performance with Long Text
- **Test**: `test_nlp_performance_with_long_text`
- **Target**: < 800ms (allowance for longer text)
- **What it tests**: NLP handles complex, multi-sentence inputs

**Expected Results:**
```
Mean: ~300-600ms
P95: < 800ms
```

**Long text is still fast** due to efficient sentence-transformers embeddings.

---

#### 10. Memory Efficiency
- **Test**: `test_memory_efficiency`
- **Target**: < 20% memory growth over 100 operations
- **What it tests**: No memory leaks during sustained operation

**Expected Results:**
```
Memory Growth: < 20%
Status: ✅ PASS
```

**Troubleshooting memory issues:**
- Check for unclosed database sessions
- Verify model embeddings are cached, not regenerated
- Profile with `memory_profiler` or `tracemalloc`

---

## Interpreting Results

### Performance Statistics Explained

Each benchmark reports the following statistics:

| Metric | Description | When to Use |
|--------|-------------|-------------|
| **Mean** | Average latency | General performance indicator |
| **Median** | 50th percentile | Typical user experience |
| **P95** | 95th percentile | Used for pass/fail (captures outliers) |
| **P99** | 99th percentile | Worst-case latency |
| **Min** | Fastest run | Best-case performance |
| **Max** | Slowest run | Detects spikes/anomalies |
| **StdDev** | Standard deviation | Consistency indicator |

**We use P95 for pass/fail criteria** to ensure 95% of requests meet the target, allowing for occasional outliers.

### Status Indicators

- ✅ **PASS**: P95 latency is within target
- ❌ **FAIL**: P95 latency exceeds target
- Performance % better/worse than target

### Example Output

```
======================================================================
Benchmark: NLP Inference Time
======================================================================
Iterations: 150
Target: 0.500s
Mean: 0.287s
Median: 0.275s
Min: 0.198s
Max: 0.456s
StdDev: 0.063s
P95: 0.412s
P99: 0.448s

Status: ✅ PASS
Performance: 42.6% better than target
======================================================================
```

## Performance Optimization Guide

### NLP Inference Optimization

**If NLP is slow (> 500ms):**

1. **Model Caching**: Ensure model is cached locally
   ```bash
   ls ~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2
   ```

2. **Pre-compute Pattern Embeddings**: Already implemented in `NLPService.__init__()`

3. **Use GPU if available**:
   ```python
   # In nlp.py
   self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cuda')
   ```

4. **Batch Processing**:
   ```python
   # Process multiple texts at once
   embeddings = self.model.encode(texts, batch_size=32)
   ```

5. **Profile bottlenecks**:
   ```bash
   python -m cProfile -s cumtime -m pytest tests/test_performance.py::test_nlp_inference_performance
   ```

### Capture Flow Optimization

**If capture time exceeds 3s:**

1. **Parallelize I/O**: Already implemented using `asyncio.gather()`
   ```python
   # In captures.py
   (draft_type, confidence), entities = await asyncio.gather(
       classification_task, entity_extraction_task
   )
   ```

2. **Reduce Database Roundtrips**: Use bulk operations
   ```python
   # Bad: Multiple commits
   db.add(capture); db.commit()
   db.add(draft); db.commit()
   
   # Good: Single commit
   db.add(capture); db.add(draft); db.commit()
   ```

3. **Offload to Background**: Move sync to background tasks
   ```python
   background_tasks.add_task(sync_draft_to_google_with_retry, draft_id, credentials)
   ```

### Google Sync Optimization

**If sync exceeds 10s:**

1. **Check Network Latency**: Test Google API directly
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s https://www.googleapis.com/tasks/v1/lists
   ```

2. **Optimize Retry Logic**: Already implemented with exponential backoff
   ```python
   # In tasks.py
   backoff_seconds = (2 ** retry_count) * 60
   ```

3. **Batch API Calls**: Use Google's batch API
   ```python
   # Google batch requests (future optimization)
   batch = service.new_batch_http_request()
   batch.add(service.tasks().insert(...))
   batch.add(service.events().insert(...))
   batch.execute()
   ```

4. **Monitor Rate Limits**: Check Google API quota
   ```bash
   # Check Cloud Console quotas
   gcloud alpha services quota list --service=tasks.googleapis.com
   ```

### General Performance Tips

1. **Use Connection Pooling**: Already configured in `db/session.py`

2. **Enable Query Caching**: For repeated queries
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_user_preferences(user_id):
       ...
   ```

3. **Monitor Database Performance**:
   ```bash
   # Enable SQLAlchemy query logging
   export SQLALCHEMY_ECHO=True
   ```

4. **Use CDN for Static Assets**: Offload mobile app assets

5. **Horizontal Scaling**: Deploy multiple backend instances with load balancer

## Troubleshooting Common Issues

### Test Failures

#### "P95 latency exceeds target"
- **Cause**: System under load, cold start, or inefficient code
- **Fix**: Run warmup iterations, close background processes, profile code

#### "Classification accuracy below target"
- **Cause**: Insufficient training data or ambiguous samples
- **Fix**: Review misclassified examples, add more patterns

#### "Import errors"
- **Cause**: Missing dependencies
- **Fix**: `pip install -r backend/requirements.txt`

#### "Mock objects not working"
- **Cause**: Service instance already initialized
- **Fix**: Patch at import level: `@patch('app.services.nlp.nlp_service')`

### Performance Degradation

**If benchmarks suddenly fail:**

1. **Check system resources**:
   ```bash
   top  # CPU usage
   free -h  # Memory usage
   df -h  # Disk space
   ```

2. **Verify model files**:
   ```bash
   ls -lh ~/.cache/huggingface/hub/
   ```

3. **Test Google APIs**:
   ```bash
   gcloud auth application-default login
   gcloud projects list  # Verify access
   ```

4. **Check database**:
   ```bash
   psql -U postgres -d remindr -c "SELECT COUNT(*) FROM captures;"
   ```

## CI/CD Integration

### GitHub Actions

Add performance tests to CI pipeline:

```yaml
# .github/workflows/backend-ci.yml
- name: Run Performance Benchmarks
  run: |
    bash scripts/run-performance-tests.sh --ci
  
- name: Upload Performance Report
  uses: actions/upload-artifact@v3
  with:
    name: performance-report
    path: backend/htmlcov/
```

### Performance Monitoring

**Track performance metrics over time:**

1. **Store benchmark results**:
   ```bash
   pytest tests/test_performance.py --benchmark-json=output.json
   ```

2. **Visualize trends**:
   - Use Grafana + Prometheus
   - GitHub Actions status checks
   - Sentry performance monitoring

3. **Alert on regressions**:
   - Fail CI if P95 > target
   - Notify team on Slack/email

## Further Reading

- [Remindr PRD](prd.md) - Performance requirements
- [Architecture Spec](spec.txt) - System design
- [NLP Service](../backend/app/services/nlp.py) - AI implementation
- [FastAPI Performance](https://fastapi.tiangolo.com/async/) - Async patterns
- [sentence-transformers](https://www.sbert.net/) - Model documentation

## Appendix: Dependencies

### Required for Benchmarks

```txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
psutil>=5.9.0  # For memory benchmarks
```

### Optional for Enhanced Profiling

```bash
pip install memory_profiler line_profiler py-spy
```

### Usage Examples

```bash
# Memory profiling
python -m memory_profiler backend/app/services/nlp.py

# Line-by-line profiling
kernprof -l -v backend/app/services/nlp.py

# Live profiling (sampling)
py-spy top --pid <backend_pid>
```

---

**Last Updated**: 2025-11-09  
**Maintainer**: Developer Agent  
**Version**: 1.0
