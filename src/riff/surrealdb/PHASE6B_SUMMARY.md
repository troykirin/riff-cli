# Phase 6B: Immutable Repair Events Persistence - Summary

## Overview

Phase 6B introduces an **immutable event sourcing pattern** for conversation repair operations, ensuring:

- ✅ Complete audit trail (never lose history)
- ✅ Tamper detection via SHA256 digests
- ✅ Replay capability (rebuild any historical state)
- ✅ Reversible repairs (create revert events, not deletions)
- ✅ No cascading corruption (append-only, never UPDATE/DELETE)
- ✅ Compliance ready (exportable JSON audit logs)

## Files Created

### 1. `schema_events.sql` (304 lines)

**Purpose**: SurrealDB schema for immutable repair events

**Key Tables**:
- `repairs_events` - Append-only event log
  - **IMMUTABLE**: Events can ONLY be INSERTed, never UPDATEd or DELETEd
  - Each event has SHA256 digest for tamper detection
  - Includes: event_id, session_id, message_id, old_parent, new_parent, operator, reason, validation_passed, etc.

**Key Indexes**:
- `event_id_idx` (UNIQUE) - Prevent duplicate events
- `session_timestamp_idx` - Fast chronological replay
- `message_id_idx` - Find all repairs for a message
- `operator_idx` - Audit who performed repairs

**Relations**:
- `repairs_events_for_session` - Link events to sessions
- `repairs_events_for_message` - Link events to messages

**Example Queries**:
```sql
-- Get all active repairs for session
SELECT * FROM repairs_events
WHERE session_id = $session_id
  AND is_reverted = false
ORDER BY timestamp ASC;

-- Find messages with multiple repairs (unstable parentage)
SELECT message_id, COUNT() as repair_count
FROM repairs_events
WHERE session_id = $session_id
GROUP BY message_id
HAVING COUNT() > 1
ORDER BY repair_count DESC;
```

### 2. `materialized_views.sql` (359 lines)

**Purpose**: Cached "current state" rebuilt from immutable events

**Key Table**:
- `sessions_materialized` - MUTABLE cache (can be rebuilt anytime)
  - `message_parents` - Current parent mapping after all repairs
  - `materialization_digest` - SHA256 of all event_ids for drift detection
  - `is_stale` - Flag indicating cache needs rebuild
  - `drift_detected` - Flag indicating mismatch with event replay

**Rebuild Strategies**:
1. **Full Rebuild** - Drop cache and replay all events (expensive but guaranteed correct)
2. **Incremental Update** - Apply only new events since last materialization (fast)
3. **Validation** - Periodically rebuild and compare for drift detection

**Example Queries**:
```sql
-- Get current parent mappings (FAST - no event replay needed)
SELECT message_parents FROM sessions_materialized
WHERE session_id = $session_id;

-- Find stale views that need rebuild
SELECT session_id FROM sessions_materialized
WHERE is_stale = true OR drift_detected = true
ORDER BY materialized_at ASC
LIMIT 10;
```

### 3. `immutable_store.md` (628 lines)

**Purpose**: Comprehensive documentation of immutable event sourcing pattern

**Sections**:
- **Philosophy**: Why immutability? Event sourcing vs traditional mutable databases
- **Architecture**: Two-table design (repairs_events + sessions_materialized)
- **Data Flow**: Repair request → Validate → Insert event → Update cache
- **Undo/Rollback**: Create revert events instead of deleting
- **Replay Algorithm**: Step-by-step event replay to rebuild state
- **Integrity Validation**: SHA256 digests for tamper detection
- **Examples**: Complete code examples for common operations
- **Performance**: Full rebuild vs incremental update strategies
- **Maintenance**: Background jobs (rebuild stale views, validate samples)
- **Security**: Immutability enforcement, database permissions
- **Troubleshooting**: Drift detection, slow rebuilds

**Key Concepts**:
```
Traditional Mutable:
┌─────────────────┐
│ messages table  │  ← UPDATE parent_uuid = '...' (loses history)
└─────────────────┘

Event Sourcing:
┌─────────────────────┐         ┌──────────────────────┐
│ repairs_events      │ ──────> │ sessions_materialized│
│ (immutable log)     │ rebuild │ (cached state)       │
└─────────────────────┘         └──────────────────────┘
        ↓
    Append only (INSERT)
    Never UPDATE/DELETE
```

### 4. `repair_events_utils.py` (820 lines)

**Purpose**: Python utilities for immutable repair events

**Key Functions**:

1. **`replay_repair_events(events, original_messages)`** (Lines 258-336)
   - Replays all non-reverted events in chronological order
   - Returns `ReplayResult` with message_parents mapping and statistics
   - Validates event digests during replay
   - Skips reverted events automatically

2. **`validate_event_immutability(event, stored_events)`** (Lines 348-427)
   - Ensures event wasn't mutated after creation
   - Checks event_id uniqueness
   - Compares all immutable fields with stored version
   - Returns `ValidationResult` with errors and warnings

3. **`calculate_session_digest(events)`** (Lines 438-463)
   - Computes SHA256 of all event_ids for integrity checking
   - Used for drift detection (cache vs event replay)
   - Provides fingerprint of entire event log

4. **`export_event_log(session_id, events)`** (Lines 476-558)
   - Exports complete event log as JSON
   - Includes metadata (statistics, operator distribution)
   - Validates all event digests
   - Compliance/audit ready format

5. **`create_revert_event(original_event, operator, reason)`** (Lines 684-722)
   - Creates revert event for existing repair
   - Swaps old_parent ↔ new_parent to reverse
   - Links to original via reverts_event_id
   - Never deletes or modifies original event

**Data Models**:
- `RepairEvent` - Immutable repair event record with SHA256 digest
- `ReplayResult` - Result of replaying events (message_parents, statistics)
- `ValidationResult` - Result of immutability validation (is_valid, errors, warnings)

**Example Usage**:
```python
# Create repair event
event = RepairEvent(
    event_id=generate_event_id(),
    session_id="session-abc",
    message_id="msg-orphan-123",
    old_parent_uuid=None,
    new_parent_uuid="msg-parent-456",
    operator="user:tryk",
    reason="semantic similarity (0.87)",
    similarity_score=0.87
)

# Replay events to get current state
result = replay_repair_events([event])
print(result.message_parents)  # {'msg-orphan-123': 'msg-parent-456'}

# Validate immutability
validation = validate_event_immutability(event, all_events)
assert validation.is_valid

# Export for audit
log_json = export_event_log(session_id, all_events)

# Create revert
revert = create_revert_event(event, "user:tryk", "Incorrect repair")
```

## Architecture

### Event Sourcing Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                     Repair Request                          │
│                 (from TUI or repair engine)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Validate Repair                           │
│  - Circular dependency check                                │
│  - Timestamp logic (parent before child)                    │
│  - Parent exists in session                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Create RepairEvent (with SHA256)               │
│  - event_id, session_id, timestamp                          │
│  - message_id, old_parent, new_parent                       │
│  - operator, reason, similarity_score                       │
│  - event_digest = SHA256(immutable fields)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│          INSERT INTO repairs_events (IMMUTABLE)             │
│  - Append-only (never UPDATE/DELETE)                        │
│  - Complete audit trail preserved                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│        UPDATE sessions_materialized (CACHE)                 │
│  - Apply event to message_parents dict                      │
│  - Update statistics (total_repairs, active_repairs)        │
│  - Set is_stale = false                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Return Success                           │
└─────────────────────────────────────────────────────────────┘
```

### Undo/Rollback Pattern

```
Traditional DELETE:
  DELETE FROM repairs WHERE id = '...'  ← LOSES HISTORY!

Event Sourcing REVERT:
  INSERT INTO repairs_events {
    event_id: 'revert-xyz',
    is_reverted: true,
    reverts_event_id: 'original-abc',
    # Swap old_parent ↔ new_parent to reverse
  }
  ← PRESERVES HISTORY! Can see who reverted and why.
```

## Key Benefits

### 1. Complete Audit Trail

Every repair is logged with:
- **Who**: `operator` field (user:tryk, agent:orchestrator, system:auto)
- **What**: `message_id`, `old_parent`, `new_parent`
- **When**: `timestamp` (ISO8601 UTC)
- **Why**: `reason` field (human-readable explanation)
- **How confident**: `similarity_score` (0.0-1.0)

### 2. Tamper Detection

SHA256 digests prevent silent corruption:
```python
# Event digest computed from immutable fields
event_digest = SHA256(
    event_id +
    session_id +
    timestamp +
    message_id +
    old_parent +
    new_parent
)

# Session digest computed from all event_ids
session_digest = SHA256(sorted(event_ids))
```

If any event is tampered with, the digest will mismatch.

### 3. Replay Capability

Rebuild any historical state:
```python
# Get state at specific time
events = db.query("""
    SELECT * FROM repairs_events
    WHERE session_id = $session_id
      AND timestamp <= $target_time
    ORDER BY timestamp ASC
""")

historical_state = replay_repair_events(events)
```

### 4. Reversible Repairs

Mistakes are not permanent:
```python
# Wrong repair? Create revert event
revert = create_revert_event(
    original_event,
    operator="user:tryk",
    reason="Incorrect parent detected"
)

# Original event preserved for audit
# Replay automatically skips reverted events
```

### 5. No Cascading Corruption

Append-only pattern prevents:
- Accidental overwrites
- Lost repair history
- Cascading failures from bad UPDATE statements
- Data loss from DELETE operations

### 6. Compliance Ready

Export complete audit logs:
```json
{
  "format_version": "1.0",
  "session_id": "...",
  "exported_at": "2024-10-20T...",
  "event_count": 42,
  "metadata": {
    "total_events": 42,
    "active_events": 38,
    "reverted_events": 4,
    "operators": {
      "user:tryk": 30,
      "system:auto": 8
    },
    "session_digest": "sha256..."
  },
  "events": [...]
}
```

## Performance Considerations

### Full Rebuild vs Incremental Update

**Full Rebuild** (expensive, guaranteed correct):
```python
# Fetch ALL events
events = db.query("""
    SELECT * FROM repairs_events
    WHERE session_id = $session_id
    ORDER BY timestamp ASC
""")

# Rebuild from scratch
message_parents = replay_repair_events(events)
```

**Incremental Update** (fast, assumes cache is correct):
```python
# Fetch only NEW events since last materialization
last_timestamp = cache.last_event_timestamp
new_events = db.query("""
    SELECT * FROM repairs_events
    WHERE session_id = $session_id
      AND timestamp > $last_timestamp
    ORDER BY timestamp ASC
""")

# Apply only new events to existing cache
for event in new_events:
    cache.message_parents[event.message_id] = event.new_parent_uuid
```

### When to Use Each

- **Full Rebuild**:
  - After drift detection
  - Weekly validation
  - Initial materialization
  - Compliance audit

- **Incremental Update**:
  - After each new repair event
  - Background job processing queue
  - Real-time TUI updates

## Maintenance

### Background Jobs

1. **Rebuild Stale Views** (every 5 minutes):
   - Find `is_stale = true`
   - Rebuild using incremental update
   - Limit to 10 per run

2. **Validate Random Sample** (hourly):
   - Select 5 random sessions
   - Full rebuild and compare with cache
   - Alert if drift detected

3. **Archive Old Events** (weekly):
   - Events older than 90 days
   - Export to cold storage (S3)
   - Optionally: Delete from hot storage

4. **Integrity Check** (weekly):
   - Validate all event digests
   - Verify session digests
   - Alert on mismatches

## Integration with Existing Code

### With Repair Engine

```python
from riff.graph.repair import ConversationRepairEngine
from riff.surrealdb.repair_events_utils import RepairEvent, generate_event_id

# Existing repair engine
engine = ConversationRepairEngine()
orphans = engine.find_orphaned_messages(session)
candidates = engine.suggest_parent_candidates(orphan, session)

# Best candidate
best = candidates[0]

# Create immutable event
event = RepairEvent(
    event_id=generate_event_id(),
    session_id=session.session_id,
    message_id=best.message_id,
    old_parent_uuid=best.original_parent_uuid,
    new_parent_uuid=best.suggested_parent_uuid,
    operator="user:tryk",
    reason=best.reason,
    similarity_score=best.similarity_score
)

# Log to SurrealDB (append-only)
db.query("INSERT INTO repairs_events", event.to_dict())
```

### With TUI

```python
# User selects repair in TUI
selected_repair = tui.get_selected_repair()

# Log event (immutable)
event = create_repair_event(selected_repair)
db.insert_event(event)

# Update materialized view (cache)
rebuild_materialized_view(session_id)

# Reload TUI with repaired session
session = materialize_session(session_id, jsonl_path)
tui.update_session(session)
```

## Migration Path

### Phase 1: Parallel Write (No Breaking Changes)

```python
# Continue using existing JSONL persistence
jsonl_writer.apply_repair(jsonl_path, repair_op)

# ALSO log to SurrealDB (audit trail)
db.insert_event(create_repair_event(repair_op))
```

### Phase 2: Dual Read (Validation)

```python
# Primary: Read from JSONL
jsonl_session = load_from_jsonl(session_id)

# Secondary: Materialize from events
surrealdb_session = materialize_session(session_id, jsonl_path)

# Compare for drift detection
validate_consistency(jsonl_session, surrealdb_session)
```

### Phase 3: Event-First (SurrealDB primary)

```python
# Primary: Materialize from events
session = materialize_session(session_id, jsonl_path)

# JSONL becomes backup only (read-only)
```

### Phase 4: Event-Only (Full Migration)

```python
# All repairs via event log
# JSONL deprecated (archive only)
session = rebuild_from_events(session_id)
```

## Security

### Immutability Enforcement

```python
class ImmutableEventStore:
    def write_event(self, event: RepairEvent) -> bool:
        """Only INSERT allowed."""
        return db.query("INSERT INTO repairs_events", event.to_dict())

    def update_event(self, event_id: str) -> None:
        """FORBIDDEN - raises exception."""
        raise ImmutableEventError(
            "Cannot modify repair events. "
            "Create a revert event instead."
        )

    def delete_event(self, event_id: str) -> None:
        """FORBIDDEN - raises exception."""
        raise ImmutableEventError(
            "Cannot delete repair events. "
            "Mark as reverted instead."
        )
```

### Database Permissions

```sql
-- Grant INSERT only on repairs_events
DEFINE ACCESS repair_writer ON DATABASE TYPE RECORD
    SIGNUP (CREATE user SET name = $name, pass = crypto::argon2::generate($pass))
    SIGNIN (SELECT * FROM user WHERE name = $name AND crypto::argon2::compare(pass, $pass))
    DURATION FOR SESSION 24h;

-- Restrict to INSERT only
DEFINE SCOPE repair_writer SESSION 24h
    INSERT ON repairs_events
    SELECT ON repairs_events, sessions_materialized;
```

## Testing

Run example workflow:
```bash
cd /Users/tryk/nabia/tools/riff-cli/src/riff/surrealdb
python repair_events_utils.py
```

Expected output:
- ✓ Create repair events
- ✓ Replay events to rebuild state
- ✓ Validate immutability
- ✓ Calculate session digest
- ✓ Export event log
- ✓ Create revert event
- ✓ Replay with revert

## Next Steps

1. **Phase 6C**: Integrate with existing TUI (repair workflow)
2. **Phase 6D**: Background jobs (rebuild stale views, validate samples)
3. **Phase 6E**: Analytics dashboard (repair statistics, operator metrics)
4. **Phase 6F**: Compliance/audit features (export logs, regulatory reports)

## References

- Event Sourcing: Martin Fowler (https://martinfowler.com/eaaDev/EventSourcing.html)
- CQRS: Greg Young (https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf)
- Immutable Data: Rich Hickey (https://www.infoq.com/presentations/Value-Values/)
- SurrealDB Docs: https://surrealdb.com/docs

## Files Summary

| File | Lines | Purpose |
|------|-------|---------|
| `schema_events.sql` | 304 | SurrealDB schema for immutable repair events |
| `materialized_views.sql` | 359 | Cached current state (rebuildable from events) |
| `immutable_store.md` | 628 | Comprehensive documentation |
| `repair_events_utils.py` | 820 | Python utilities for event replay, validation, export |
| **TOTAL** | **2,111** | **Complete immutable repair events system** |

## Status

✅ **Phase 6B Complete**: Immutable event sourcing foundation implemented

This phase provides the **immutable foundation** that prevents cascading corruption and enables complete audit trails for all conversation repairs.
