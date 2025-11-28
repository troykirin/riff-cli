# E2E Test Suite for nabi scan Query Enhancement

## Quick Start

```bash
# Run all E2E tests
task test:scan:e2e

# Run specific test
uv run pytest tests/e2e/test_scan_integration.py::TestFullPipeline::test_simple_query_full_pipeline -v
```

## Test Coverage

This directory contains end-to-end integration tests for the `nabi scan` query enhancement pipeline:

- **21 tests** covering full pipeline execution
- Timeout handling and performance validation
- ripgrep pattern compatibility
- Real-world search scenarios
- Error recovery and resilience
- CLI compatibility

## Files

- `test_scan_integration.py` - Main E2E test suite
- `__init__.py` - Package initialization

## Documentation

- Full documentation: `/Users/tryk/nabia/tools/riff-cli/docs/TEST_SUITE_DOCUMENTATION.md`
- Quick start: `/Users/tryk/nabia/tools/riff-cli/docs/SCAN_ENHANCEMENT_QUICK_START.md`
- Execution summary: `/Users/tryk/nabia/tools/riff-cli/TEST_EXECUTION_SUMMARY.md`

## Test Classes

1. `TestFullPipeline` - Complete pipeline execution
2. `TestFallbackMechanism` - Graceful degradation
3. `TestTimeoutHandling` - Performance and timeout protection
4. `TestRipgrepIntegration` - ripgrep pattern compatibility
5. `TestRealWorldScenarios` - Realistic usage patterns
6. `TestErrorRecovery` - Error handling and resilience
7. `TestPerformance` - Performance characteristics
8. `TestCLICompatibility` - CLI interface compliance

## Status

✅ All 21 tests passing (100%)
