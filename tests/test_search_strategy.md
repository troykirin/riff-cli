# Riff-CLI Search Feature Test Automation Strategy

## Executive Summary

This document outlines a comprehensive test automation strategy for the riff-cli search functionality, based on empirical analysis of the live Qdrant instance containing 804 Claude session vectors. The strategy addresses current search limitations and ensures robust, maintainable testing infrastructure.

## Current State Analysis

### System Configuration
- **Database**: Qdrant v1.x running at localhost:6333
- **Collection**: `claude_sessions` with 804 points
- **Vector Model**: all-MiniLM-L6-v2 (384-dimensional embeddings)
- **Distance Metric**: Cosine similarity
- **Search Status**: Functional but requires threshold tuning

### Key Findings
1. **Search IS Working**: Semantic search returns results for relevant queries
2. **Threshold Issue**: Default min_score (0.3) filters out valid results
3. **Field Structure**: All expected fields present (session_id, content_preview, working_directory)
4. **Vector Compatibility**: Model dimensions (384) match Qdrant configuration

### Payload Structure
```json
{
  "session_id": "uuid-format",
  "file_path": "/path/to/session.jsonl",
  "working_directory": "/project/path",
  "content_preview": "conversation excerpt...",
  "content_length": 12345,
  "last_activity": "ISO-8601 timestamp",
  "indexed_at": "ISO-8601 timestamp"
}
```

## Test Architecture Design

### 1. Test Levels Hierarchy

#### Unit Tests (L1)
- **Scope**: Individual components in isolation
- **Coverage**: 90% code coverage target
- **Execution Time**: <100ms per test
- **Dependencies**: Mocked

#### Integration Tests (L2)
- **Scope**: Component interactions
- **Coverage**: Key workflows
- **Execution Time**: <1s per test
- **Dependencies**: Test containers or mocks

#### System Tests (L3)
- **Scope**: End-to-end functionality
- **Coverage**: Critical paths
- **Execution Time**: <5s per test
- **Dependencies**: Live Qdrant (read-only)

#### Acceptance Tests (L4)
- **Scope**: User requirements validation
- **Coverage**: User stories
- **Execution Time**: <10s per test
- **Dependencies**: Full stack

### 2. Test Categories

#### Functional Testing
```yaml
Search Accuracy:
  - Semantic similarity matching
  - Relevance scoring
  - Result ranking
  - Query enhancement

Search Modes:
  - Basic text search
  - UUID lookup
  - AI-enhanced search
  - Browse mode navigation

Edge Cases:
  - Empty queries
  - Special characters
  - Very long queries
  - Non-English text
  - SQL injection attempts
```

#### Performance Testing
```yaml
Latency Requirements:
  - Search response: <500ms (p95)
  - UUID lookup: <100ms (p95)
  - Browse navigation: <200ms (p95)

Throughput:
  - Concurrent searches: 10 req/s
  - Browse sessions: 50 concurrent

Resource Usage:
  - Memory: <500MB
  - CPU: <50% single core
```

#### Reliability Testing
```yaml
Error Handling:
  - Qdrant unavailable
  - Network timeouts
  - Malformed data
  - Vector dimension mismatch

Recovery:
  - Automatic reconnection
  - Graceful degradation
  - Circuit breaker pattern
```

### 3. Test Data Strategy

#### Fixture Categories
```python
# Minimal fixtures for unit tests
MINIMAL_FIXTURES = {
    "empty_session": {...},
    "basic_session": {...},
    "rich_session": {...}
}

# Representative fixtures for integration
REPRESENTATIVE_FIXTURES = {
    "typical_workflows": [...],
    "edge_cases": [...],
    "error_scenarios": [...]
}

# Synthetic data for load testing
SYNTHETIC_GENERATOR = {
    "session_count": 10000,
    "content_patterns": [...],
    "vector_variations": [...]
}
```

#### Data Management
- **Isolation**: Each test suite uses separate fixture set
- **Versioning**: Fixtures versioned with schema changes
- **Cleanup**: Automatic post-test cleanup
- **Seeding**: Deterministic test data generation

## Test Implementation Plan

### Phase 1: Foundation (Week 1)

#### 1.1 Test Infrastructure Setup
```python
# tests/conftest.py
import pytest
from unittest.mock import Mock
from qdrant_client import QdrantClient

@pytest.fixture
def mock_qdrant():
    """Mock Qdrant client for unit tests"""
    client = Mock(spec=QdrantClient)
    client.search.return_value = MOCK_SEARCH_RESULTS
    return client

@pytest.fixture(scope="session")
def live_qdrant():
    """Live Qdrant client for integration tests"""
    return QdrantClient(url="http://localhost:6333")

@pytest.fixture
def test_vectors():
    """Pre-computed test vectors"""
    return load_test_vectors()
```

#### 1.2 Unit Test Suite
```python
# tests/unit/test_search_core.py
class TestQdrantSearcher:
    """Core search functionality tests"""

    def test_initialization(self):
        """Verify searcher initialization"""

    def test_query_embedding(self):
        """Test query vector generation"""

    def test_result_mapping(self):
        """Test payload to SearchResult mapping"""

    def test_score_thresholding(self):
        """Test score filtering logic"""
```

### Phase 2: Integration (Week 2)

#### 2.1 Mock Qdrant Tests
```python
# tests/integration/test_search_integration.py
class TestSearchIntegration:
    """Search integration with mocked Qdrant"""

    @pytest.mark.integration
    def test_search_workflow(self, mock_qdrant):
        """Test complete search workflow"""

    def test_uuid_lookup(self, mock_qdrant):
        """Test direct UUID search"""

    def test_concurrent_searches(self, mock_qdrant):
        """Test parallel search operations"""
```

#### 2.2 Live Qdrant Tests (Read-Only)
```python
# tests/integration/test_live_qdrant.py
@pytest.mark.live
class TestLiveQdrant:
    """Tests against live Qdrant (read-only)"""

    def test_connection_health(self, live_qdrant):
        """Verify Qdrant connectivity"""

    def test_real_search_patterns(self, live_qdrant):
        """Test with actual data patterns"""

    def test_performance_baseline(self, live_qdrant):
        """Establish performance baselines"""
```

### Phase 3: System Tests (Week 3)

#### 3.1 End-to-End Scenarios
```python
# tests/system/test_e2e_search.py
class TestEndToEndSearch:
    """Complete user journey tests"""

    def test_cli_search_command(self):
        """Test CLI search invocation"""

    def test_search_to_browse_transition(self):
        """Test mode transitions"""

    def test_ai_enhanced_search(self):
        """Test AI query enhancement"""
```

#### 3.2 Performance Tests
```python
# tests/performance/test_search_performance.py
@pytest.mark.performance
class TestSearchPerformance:
    """Performance and load tests"""

    def test_search_latency(self):
        """Measure search response times"""

    def test_concurrent_load(self):
        """Test under concurrent load"""

    def test_memory_usage(self):
        """Monitor memory consumption"""
```

## Test Fixtures Design

### Core Fixtures Structure
```python
# tests/fixtures/sessions.py
FIXTURE_SESSIONS = {
    "empty": {
        "session_id": "test-empty-001",
        "content_preview": "",
        "content_length": 0,
        "working_directory": "/test",
        "file_path": "/test/empty.jsonl",
        "last_activity": "2025-01-01T00:00:00Z",
        "indexed_at": "2025-01-01T00:00:00Z"
    },

    "typical": {
        "session_id": "test-typical-001",
        "content_preview": "PreToolUse:TodoWrite federation hooks",
        "content_length": 5000,
        "working_directory": "/Users/test/project",
        "file_path": "/test/typical.jsonl",
        "last_activity": "2025-01-15T10:30:00Z",
        "indexed_at": "2025-01-15T11:00:00Z"
    },

    "edge_case_unicode": {
        "session_id": "test-unicode-001",
        "content_preview": "测试 テスト тест emoji 🚀",
        "content_length": 1000,
        "working_directory": "/test/unicode",
        "file_path": "/test/unicode.jsonl",
        "last_activity": "2025-01-10T00:00:00Z",
        "indexed_at": "2025-01-10T00:00:00Z"
    }
}

# tests/fixtures/vectors.py
PRECOMPUTED_VECTORS = {
    "test_queries": {
        "TodoWrite": [0.123, 0.456, ...],  # 384 dimensions
        "memchain": [...],
        "hooks": [...],
    },
    "test_documents": {
        "empty": [...],
        "typical": [...],
        "edge_case_unicode": [...]
    }
}
```

### Mock Response Builder
```python
# tests/fixtures/builders.py
class MockResponseBuilder:
    """Build realistic Qdrant responses"""

    @staticmethod
    def search_response(sessions, scores):
        """Build mock search response"""
        return [
            MockPoint(
                id=s['session_id'],
                payload=s,
                score=score
            )
            for s, score in zip(sessions, scores)
        ]

    @staticmethod
    def scroll_response(sessions):
        """Build mock scroll response"""
        return ([MockPoint(id=s['session_id'], payload=s)
                for s in sessions], None)
```

## Pytest Configuration

### pytest.ini
```ini
[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test markers
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (may use external services)
    live: Tests against live Qdrant (read-only)
    performance: Performance tests
    slow: Tests that take >5s

# Coverage settings
addopts =
    --cov=riff.search
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
    -v

# Parallel execution
workers = auto

# Timeout
timeout = 30
```

### conftest.py Structure
```python
# tests/conftest.py
import pytest
import os
from pathlib import Path

# Configure test environment
os.environ['RIFF_TEST_MODE'] = '1'

# Test data paths
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "fixtures"

# Import fixtures
from .fixtures.sessions import *
from .fixtures.vectors import *
from .fixtures.builders import *

# Pytest hooks
def pytest_configure(config):
    """Configure test environment"""
    config.addinivalue_line(
        "markers", "require_qdrant: test requires live Qdrant"
    )

def pytest_collection_modifyitems(config, items):
    """Skip tests based on environment"""
    if not os.getenv('TEST_LIVE_QDRANT'):
        skip_live = pytest.mark.skip(reason="Live Qdrant tests disabled")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
```

## Test Execution Strategy

### Local Development
```bash
# Run all unit tests
pytest -m unit

# Run integration tests with mocks
pytest -m integration

# Run specific test file
pytest tests/unit/test_search_core.py -v

# Run with coverage
pytest --cov=riff.search --cov-report=html

# Run parallel
pytest -n auto
```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
test:
  strategy:
    matrix:
      python-version: [3.11, 3.12]

  steps:
    - name: Unit Tests
      run: pytest -m unit --junit-xml=junit/unit.xml

    - name: Integration Tests
      run: pytest -m integration --junit-xml=junit/integration.xml

    - name: Coverage Report
      run: pytest --cov --cov-report=xml

    - name: Performance Tests
      run: pytest -m performance --benchmark-only
```

### Live Testing (Manual)
```bash
# Enable live Qdrant tests
export TEST_LIVE_QDRANT=1

# Run live tests (read-only)
pytest -m live --tb=short

# Run performance benchmarks
pytest -m performance --benchmark-autosave
```

## Quality Gates

### Entry Criteria
- [ ] All unit tests passing
- [ ] Mock fixtures validated
- [ ] Test environment configured
- [ ] Dependencies installed

### Exit Criteria
- [ ] 80% code coverage minimum
- [ ] All critical paths tested
- [ ] Performance baselines met
- [ ] No high-severity bugs

### Success Metrics
- **Test Coverage**: >80% lines, >70% branches
- **Test Execution Time**: <60s for full suite
- **Test Reliability**: <1% flaky test rate
- **Bug Detection Rate**: >90% before production

## Risk Mitigation

### Technical Risks
1. **Qdrant Version Changes**
   - Mitigation: Version lock, compatibility tests

2. **Vector Model Updates**
   - Mitigation: Model versioning, regression tests

3. **Performance Degradation**
   - Mitigation: Baseline tracking, alerts

### Process Risks
1. **Test Maintenance Burden**
   - Mitigation: Modular design, clear ownership

2. **False Positives**
   - Mitigation: Stable fixtures, retry logic

3. **Environment Drift**
   - Mitigation: Containerization, config management

## Maintenance Guidelines

### Test Hygiene
- Review and update tests with each feature change
- Remove obsolete tests quarterly
- Refactor duplicate test logic
- Update fixtures when schema changes

### Performance Monitoring
- Track test execution times weekly
- Investigate tests >1s
- Profile memory usage monthly
- Optimize slow test queries

### Documentation
- Keep test docstrings current
- Update strategy document quarterly
- Document test failures patterns
- Share learnings in team retrospectives

## Appendix A: Common Test Patterns

### Pattern 1: Parameterized Search Tests
```python
@pytest.mark.parametrize("query,expected_count", [
    ("TodoWrite", 3),
    ("memchain", 0),  # Known to return no results
    ("", 0),  # Empty query
])
def test_search_variations(searcher, query, expected_count):
    results = searcher.search(query)
    assert len(results) == expected_count
```

### Pattern 2: Mock Qdrant Responses
```python
def test_with_mock_qdrant(mock_qdrant):
    mock_qdrant.search.return_value = [
        MockPoint(id="1", payload={...}, score=0.9)
    ]

    searcher = QdrantSearcher()
    searcher.client = mock_qdrant

    results = searcher.search("test")
    assert len(results) == 1
```

### Pattern 3: Performance Benchmarking
```python
@pytest.mark.benchmark
def test_search_performance(benchmark, live_qdrant):
    searcher = QdrantSearcher()

    result = benchmark(searcher.search, "common query")

    assert benchmark.stats['mean'] < 0.5  # 500ms limit
```

## Appendix B: Troubleshooting Guide

### Issue: Tests Fail with "No Results"
**Cause**: Score threshold too high
**Solution**: Lower min_score parameter or adjust test expectations

### Issue: Vector Dimension Mismatch
**Cause**: Wrong embedding model
**Solution**: Verify model matches Qdrant configuration (all-MiniLM-L6-v2)

### Issue: Slow Test Execution
**Cause**: Live Qdrant queries in unit tests
**Solution**: Use mocks for unit tests, limit live tests

### Issue: Flaky Integration Tests
**Cause**: Network timeouts or Qdrant load
**Solution**: Add retry logic, increase timeouts

## Appendix C: Quick Reference

### Test Commands
```bash
# Quick test during development
pytest tests/unit -x --tb=short

# Full test suite with coverage
pytest --cov --cov-report=html

# Performance profiling
pytest -m performance --profile

# Debug failing test
pytest tests/unit/test_search_core.py::test_name -vvs --pdb
```

### Environment Variables
```bash
RIFF_TEST_MODE=1          # Enable test mode
TEST_LIVE_QDRANT=1        # Enable live Qdrant tests
QDRANT_URL=localhost:6333 # Qdrant endpoint
TEST_TIMEOUT=30           # Test timeout in seconds
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-17
**Author**: Test Automation Architect
**Review Status**: Ready for Implementation