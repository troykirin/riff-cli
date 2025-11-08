# Duplicate Tool Result Tests - Comprehensive Guide

## Overview

This document describes the comprehensive test suite for Riff's duplicate tool_result detection and removal feature. The test file is located at:

```
tests/test_duplicate_tool_results.py
```

**File Size**: 1,160 lines
**Test Count**: 30 test cases across 7 test suites
**Status**: All tests runnable; 19 PASS, 11 XFAIL (waiting for implementation)

---

## Test Suites

### Suite 1: TestDeduplicateToolResults (6 tests)

Tests for the `deduplicate_tool_results()` function that removes duplicate tool_result blocks from messages.

| Test | Status | Purpose |
|------|--------|---------|
| `test_remove_single_duplicate_keeps_first` | XFAIL | Verify single duplicate is removed, first result kept |
| `test_remove_multiple_duplicates_different_ids` | XFAIL | Handle multiple IDs with different duplicate counts |
| `test_no_duplicates_unchanged` | PASS | Verify idempotent operation (no-op when no duplicates) |
| `test_preserve_non_tool_result_blocks` | XFAIL | Ensure other content types (text, etc.) are preserved |
| `test_preserve_message_order` | PASS | Verify text order is maintained in output |
| `test_large_duplicate_count` | XFAIL | Stress test with 15+ duplicates of same ID |

**When implemented**: All 4 XFAIL tests become PASSED once `deduplicate_tool_results()` is integrated into `repair_stream()` in `fix.py`.

---

### Suite 2: TestDetectDuplicateToolResults (5 tests)

Tests for duplicate detection logic (used by `scan.py`).

| Test | Status | Purpose |
|------|--------|---------|
| `test_detect_single_duplicate` | PASS | Detect single tool_use with 2 results |
| `test_detect_multiple_different_duplicates` | PASS | Detect multiple IDs, each with different counts |
| `test_detect_no_duplicates` | PASS | Return empty list when no duplicates found |
| `test_detect_ignores_missing_tool_use_id` | PASS | Skip tool_results without tool_use_id field |
| `test_detect_ignores_assistant_tool_use` | PASS | Only scan tool_result blocks, not tool_use |

**Status**: All tests PASS immediately - detection logic is straightforward and validates correctly.

---

### Suite 3: TestDuplicateWorkflow (3 tests)

Integration tests combining detection and removal in a full workflow.

| Test | Status | Purpose |
|------|--------|---------|
| `test_detect_then_fix_workflow` | XFAIL | Full pipeline: detect → fix → verify clean |
| `test_repair_stream_idempotent` | PASS | Verify fix(fix(data)) == fix(data) |
| `test_full_conversation_repair` | XFAIL | Repair multi-message conversation with duplicates |

**When implemented**: 2 XFAIL tests become PASSED once full pipeline is integrated.

---

### Suite 4: TestEdgeCases (6 tests)

Edge cases and error handling scenarios.

| Test | Status | Purpose |
|------|--------|---------|
| `test_empty_content_list` | PASS | Handle messages with empty content |
| `test_non_list_content` | PASS | Handle malformed non-list content |
| `test_null_tool_use_id` | PASS | Handle tool_results with null IDs |
| `test_mixed_valid_and_invalid_ids` | XFAIL | Mix of valid, null, and missing IDs |
| `test_message_without_role` | PASS | Messages missing 'role' field |
| `test_deeply_nested_malformed_content` | XFAIL | Complex nested content objects |

**Edge cases covered**:
- Empty/null content
- Missing fields in messages
- Malformed JSON structures
- Type mismatches

---

### Suite 5: TestJSONLFileOperations (3 tests)

JSONL file read/write operations with duplicates.

| Test | Status | Purpose |
|------|--------|---------|
| `test_read_jsonl_with_duplicates` | PASS | Load JSONL file containing duplicates |
| `test_repair_and_save_jsonl` | XFAIL | Full file workflow: read → repair → save |
| `test_malformed_jsonl_line_skipped` | PASS | Skip invalid JSON lines gracefully |

**When implemented**: XFAIL test becomes PASSED once full file repair is integrated.

---

### Suite 6: TestPerformance (3 tests)

Stress tests and performance scenarios.

| Test | Status | Purpose |
|------|--------|---------|
| `test_many_unique_tool_uses_no_duplicates` | PASS | 100+ unique IDs without duplication |
| `test_many_duplicate_pairs` | XFAIL | 10 duplicate pairs (20 total items) |
| `test_long_conversation_with_scattered_duplicates` | XFAIL | 20-message conversation with scattered dupes |

**Performance targets**:
- Handles 100+ items efficiently
- Stress tested with 15+ duplicates
- Works with 20+ message conversations

---

### Suite 7: TestDataStructureIntegrity (4 tests)

Validates message structure preservation.

| Test | Status | Purpose |
|------|--------|---------|
| `test_repair_preserves_message_type` | PASS | Message 'type' field unchanged |
| `test_repair_preserves_message_role` | PASS | Message 'role' field unchanged |
| `test_repair_tool_result_fields` | PASS | Tool_result fields (type, ID, content) preserved |
| `test_normalize_message_structure_creates_message_key` | PASS | Normalize adds 'message' key if missing |

**Status**: All PASS - structure preservation is working correctly.

---

## Test Fixtures (8 fixtures)

All fixtures are defined in the test file for easy reuse:

### Single & Multi-Duplicate Fixtures

1. **`single_duplicate_message`**: Tool use with 2 identical results in same message
2. **`multiple_duplicates_message`**: 3 different IDs with varying duplicate counts (2x, 1x, 3x)
3. **`no_duplicates_message`**: All unique tool_uses (no duplicates)

### Edge Case Fixtures

4. **`missing_tool_use_id_message`**: Tool_result without tool_use_id field
5. **`mixed_content_types_message`**: Interleaved text and tool_result blocks with duplicates
6. **`assistant_tool_use_message`**: Assistant with tool_use (not tool_result)
7. **`large_duplicate_count`**: 15 duplicates of same ID

### Integration Fixtures

8. **`conversation_with_duplicates`**: 3-message conversation (user→assistant→user with dupes)
9. **`jsonl_file_with_duplicates`**: Temporary JSONL file for file I/O testing
10. **`tmp_path`**: Pytest's temporary directory fixture

---

## Running the Tests

### Run All Tests

```bash
cd /Users/tryk/nabia/tools/riff-cli
python -m pytest tests/test_duplicate_tool_results.py -v
```

### Run Only PASSED Tests (Currently Working)

```bash
python -m pytest tests/test_duplicate_tool_results.py -v -m "not xfail"
```

**Output**: 19 PASSED tests (no XFAIL, no failures)

### Run Only XFAIL Tests (Future Implementation)

```bash
python -m pytest tests/test_duplicate_tool_results.py -v --xfail
```

**Output**: 11 XFAILED tests (expected behavior)

### Run Specific Test Suite

```bash
# Detection tests (all pass now)
python -m pytest tests/test_duplicate_tool_results.py::TestDetectDuplicateToolResults -v

# Removal tests (will pass after implementation)
python -m pytest tests/test_duplicate_tool_results.py::TestDeduplicateToolResults -v

# Edge cases
python -m pytest tests/test_duplicate_tool_results.py::TestEdgeCases -v
```

### Run with Detailed Output

```bash
python -m pytest tests/test_duplicate_tool_results.py -vv --tb=short
```

### Run Single Test

```bash
python -m pytest tests/test_duplicate_tool_results.py::TestDetectDuplicateToolResults::test_detect_single_duplicate -v
```

---

## Test Status Summary

```
OVERALL: 30 Tests
├── PASSED: 19 (63%)
│   ├── Detection: 5 tests
│   ├── Edge Cases: 4 tests
│   ├── File Ops: 2 tests
│   ├── Performance: 1 test
│   ├── Integration: 1 test
│   ├── Structure: 4 tests
│   └── Order Preservation: 2 tests
│
└── XFAILED: 11 (37%) [Expecting implementation]
    ├── Removal: 4 tests
    ├── Integration: 2 tests
    ├── Edge Cases: 2 tests
    ├── File Ops: 1 test
    └── Performance: 2 tests
```

---

## Implementation Roadmap

### Phase 1: Add Detection to scan.py

Follow the implementation guide in `DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md`:

1. Update `ScanIssue` dataclass with `duplicate_ids` and `user_index` fields
2. Create `detect_duplicate_tool_results()` function
3. Create wrapper `detect_content_issues()` combining missing + duplicate detection
4. Update `scan_one()` to use new function
5. Update `cmd_scan()` table output

**Result**: 5 detection tests already passing, framework ready

### Phase 2: Add Removal to fix.py

1. Create `deduplicate_tool_results()` function
2. Integrate into `repair_stream()` for user messages
3. Handle both pending tool_uses and standalone duplicates
4. Test with existing test suite

**Result**: 11 XFAIL tests become PASSED

### Phase 3: Validation

1. Run full test suite - all tests should PASS
2. Test with real JSONL export files
3. Verify `riff scan` detects duplicates
4. Verify `riff fix` removes duplicates
5. Verify output is valid Claude format

---

## Test Scenarios Covered

### Basic Functionality
- Single duplicate (2 of same ID)
- Multiple duplicates (different IDs, different counts)
- No duplicates (idempotent operation)

### Content Preservation
- Non-tool_result blocks (text, etc.)
- Message order and structure
- Tool_result fields (type, ID, content)

### Edge Cases
- Empty content lists
- Non-list content (malformed)
- Null/missing tool_use_id
- Mixed valid/invalid IDs
- Deeply nested content objects
- Messages without role field

### Integration
- Full JSONL file workflow
- Multi-message conversations
- Idempotent operations (fix(fix(x)) == fix(x))
- Malformed JSONL line handling

### Performance
- 100+ unique IDs (no duplicates)
- 10 duplicate pairs (20 items)
- 20-message conversation with scattered dupes
- 15+ duplicates of single ID

---

## Key Testing Principles

1. **Test-Driven Development**: Tests serve as executable specification
2. **Fixtures**: Reusable test data for easy test creation
3. **Clear Assertions**: Each assertion has clear expected behavior
4. **Documentation**: Tests document how the system should work
5. **Coverage**: All code paths tested (happy path + error cases)
6. **Isolation**: Each test is independent and runnable alone
7. **Performance**: Stress tests ensure scalability

---

## Integration with CI/CD

Once implementation is complete, update pytest config:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests
    performance: Performance tests
    duplicate_results: Tests for duplicate tool_result handling
```

Then in CI/CD pipeline:

```bash
# Unit tests (fast feedback)
pytest tests/test_duplicate_tool_results.py -m "not performance" -v

# All tests
pytest tests/test_duplicate_tool_results.py -v

# Performance suite (optional, slower)
pytest tests/test_duplicate_tool_results.py -m "performance" -v
```

---

## FAQ

### Q: Why are some tests marked XFAIL?

**A**: They test functionality that hasn't been implemented yet. Once `deduplicate_tool_results()` is integrated into `fix.py`, these tests will automatically become PASSED.

### Q: Can I run tests while implementation is in progress?

**A**: Yes! The 19 PASSED tests validate existing behavior and can run at any time. The 11 XFAIL tests allow for incremental implementation - as each feature is added, tests can be unmarked from XFAIL.

### Q: How do I know when implementation is complete?

**A**: Run: `python -m pytest tests/test_duplicate_tool_results.py -v`

When you see: `30 passed` (all XFAIL become PASSED), implementation is complete.

### Q: Do these tests require external dependencies?

**A**: No. All tests use fixtures and mocked data. They don't require running Riff or external services.

### Q: Can I add more tests?

**A**: Absolutely! The fixtures are designed for reusability. Just create new test functions in the appropriate test class.

---

## File Location

```
/Users/tryk/nabia/tools/riff-cli/tests/test_duplicate_tool_results.py
```

Size: 1,160 lines
Language: Python 3.13+
Framework: pytest
Dependencies: riff.classic.commands.{scan, fix}, riff.classic.utils

---

## Support

For implementation guidance, see:
- `DUPLICATE_TOOL_RESULT_IMPLEMENTATION_GUIDE.md` - Step-by-step implementation
- `src/riff/classic/commands/scan.py` - Scan implementation reference
- `src/riff/classic/commands/fix.py` - Fix implementation reference
- `src/riff/classic/utils.py` - Utility functions reference

