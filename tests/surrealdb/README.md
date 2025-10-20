# SurrealDB Immutable Event Store Test Suite

## Overview

Comprehensive test suite for Phase 6B SurrealDB immutable event store implementation. These tests validate the event sourcing architecture that prevents cascading corruption through immutable repair events.

## Test Coverage

### 1. `conftest.py` (235 lines)
**Fixtures and Utilities**
- Mock SurrealDB HTTP client with immutability enforcement
- Sample sessions with known corruption patterns
- Mock HTTP responses for API simulation
- Event hash calculation utilities
- Test data cleanup between runs

### 2. `test_storage.py` (274 lines)
**Storage Operations and Immutability**
- `test_load_session_from_surrealdb()` - Loading sessions from storage
- `test_save_repair_event_immutable()` - Saving immutable repair events
- `test_cannot_update_repair_event()` - Enforcing immutability constraints
- `test_materialize_session_from_events()` - Building state from event log
- `test_replay_events_in_order()` - Chronological event replay
- `test_session_hash_consistency()` - Hash verification across operations
- `test_surrealdb_connection_error_handling()` - Connection failure recovery

### 3. `test_events.py` (356 lines)
**Event Creation and Validation**
- `test_repair_event_creation()` - Creating various repair event types
- `test_event_immutability_validation()` - Validating true immutability
- `test_event_log_integrity()` - Append-only log behavior
- `test_calculate_session_digest()` - Cryptographic state digests
- `test_export_event_log_compliance()` - Compliance/audit exports

### 4. `test_materialization.py` (439 lines)
**Session State Materialization**
- `test_materialize_empty_session()` - Handling empty event streams
- `test_materialize_with_single_repair()` - Single repair application
- `test_materialize_with_multiple_repairs()` - Complex repair sequences
- `test_materialized_view_cache()` - Performance caching
- `test_materialize_detects_stale_cache()` - Cache invalidation

### 5. `test_sync_command.py` (432 lines)
**Sync Command Integration**
- `test_sync_new_session_to_surrealdb()` - Initial session sync
- `test_sync_detects_changes()` - Change detection
- `test_sync_creates_repair_events()` - Repair event generation
- `test_sync_improves_corruption_score()` - Corruption reduction tracking
- `test_sync_dry_run()` - Safe preview mode
- `test_sync_force_flag()` - Conflict resolution

## Key Features Tested

### Immutability Guarantees
- Events cannot be modified after creation
- Hash verification ensures data integrity
- Append-only log prevents history rewriting

### Event Sourcing
- Complete session state from event replay
- Chronological ordering preservation
- Deterministic state reconstruction

### Corruption Prevention
- Repair events track all changes
- Corruption scores improve over time
- Cascading corruption prevented

### Performance Optimization
- Materialized view caching
- Incremental updates from cache points
- Stale cache detection

## Running Tests

```bash
# Run all SurrealDB tests
pytest tests/surrealdb/

# Run with coverage
pytest tests/surrealdb/ --cov=riff.surrealdb --cov-report=term-missing

# Run specific test file
pytest tests/surrealdb/test_storage.py

# Run with verbose output
pytest tests/surrealdb/ -v

# Run specific test
pytest tests/surrealdb/test_events.py::test_repair_event_creation
```

## Coverage Target

Target: **90%+ coverage** for all SurrealDB-related code

Current test count:
- 5 test files
- 28 test functions
- 1,741 total lines of test code

## Mock Infrastructure

Tests use `MockSurrealDBClient` that simulates:
- HTTP API responses
- Immutability enforcement
- Event log append-only behavior
- Connection error scenarios
- Query tracking for verification

## Integration Points

These tests validate integration with:
- `riff.graph.models` - Session/Message/Thread models
- `riff.surrealdb.schema_utils` - Schema validation
- Event hash calculation for integrity
- Repair event generation from corruption detection

## Test Patterns

### Immutability Testing
```python
# Attempt to modify should fail
with pytest.raises(ValueError, match="Cannot update immutable"):
    await client.query("UPDATE repair_events SET field = value")
```

### Event Replay Testing
```python
# Apply events to build state
for event in event_log:
    if event["event_type"] == "SESSION_CREATED":
        state = event["data"]
    elif event["event_type"] == "SESSION_UPDATED":
        state.update(event["data"])
```

### Hash Verification
```python
# Deterministic hashing
event["hash"] = calculate_event_hash(event)
assert stored_event["hash"] == original_hash
```

## Future Enhancements

- [ ] Performance benchmarks for large event logs
- [ ] Concurrent write conflict resolution
- [ ] Event compression for storage efficiency
- [ ] Multi-session batch operations
- [ ] Event stream subscriptions for real-time updates