# Immutable Repair Events Store

## Overview

This document describes the **immutable event sourcing pattern** used for conversation repair operations in the Riff CLI's SurrealDB persistence layer.

## Philosophy

### Why Immutability?

Traditional mutable databases allow UPDATE and DELETE operations, which can lead to:

1. **Loss of Audit Trail**: No record of who changed what and when
2. **Cascading Corruption**: A bad repair can overwrite good data permanently
3. **No Rollback**: Can't undo changes after they're committed
4. **Compliance Risk**: No provenance for regulatory requirements

Immutable event sourcing solves these problems by **never mutating data**. Instead:

- All changes are **appended** as events (INSERT only)
- Current state is **computed** by replaying events
- History is **permanent** and tamper-evident
- Rollback is **trivial** (ignore events after a point)

### Event Sourcing Pattern

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

## Architecture

### Two-Table Design

#### 1. `repairs_events` (Source of Truth)

- **IMMUTABLE**: Once written, never changed
- **APPEND-ONLY**: Only INSERT allowed
- **COMPLETE**: Full audit trail of all repairs
- **REPLAYABLE**: Can rebuild state from scratch

#### 2. `sessions_materialized` (Performance Cache)

- **MUTABLE**: Updated when events change
- **REBUILDABLE**: Can be dropped and recreated
- **OPTIMIZED**: Fast queries without replaying events
- **VALIDATED**: Periodically verified against event replay

### Data Flow

```
1. Repair Request
   ↓
2. Validate (circular deps, timestamps, etc.)
   ↓
3. Create RepairEvent (with SHA256 digest)
   ↓
4. INSERT INTO repairs_events (immutable)
   ↓
5. UPDATE sessions_materialized (cache)
   ↓
6. Return success
```

### Undo/Rollback

```
Traditional:
  DELETE FROM repairs WHERE id = '...'  ← Loses history

Event Sourcing:
  INSERT INTO repairs_events {
    event_id: 'revert-123',
    is_reverted: true,
    reverts_event_id: 'original-456',
    # Swap old_parent ↔ new_parent to reverse
  }
```

## Schema Details

### RepairEvent Structure

```sql
{
  event_id: "uuid",           -- Unique event identifier
  session_id: "session-uuid", -- Which session
  timestamp: "2024-10-20T...", -- When repair occurred

  message_id: "msg-uuid",     -- Which message was repaired
  old_parent_uuid: "...",     -- Previous parent (or null)
  new_parent_uuid: "...",     -- New parent

  operator: "user:tryk",      -- Who performed repair
  reason: "semantic match",   -- Why this repair
  similarity_score: 0.85,     -- Confidence (0.0-1.0)

  validation_passed: true,    -- Passed checks?
  is_reverted: false,         -- Is this a revert?
  reverts_event_id: null,     -- If revert, which event?

  event_digest: "sha256...",  -- Tamper detection
  created_at: "2024-10-20..." -- System timestamp
}
```

### Materialized View Structure

```sql
{
  session_id: "session-uuid",

  message_parents: {          -- Current state after all repairs
    "msg-1": "parent-1",
    "msg-2": "parent-2",
    "msg-3": null             -- Root message
  },

  total_repairs: 42,          -- Including reverted
  active_repairs: 38,         -- Excluding reverted
  reverted_repairs: 4,

  last_event_id: "...",       -- For incremental updates
  last_event_timestamp: "...",
  materialized_at: "...",     -- When cache was built

  materialization_digest: "sha256...", -- Integrity check
  is_stale: false,            -- Needs rebuild?
  drift_detected: false,      -- Cache mismatch?

  rebuild_duration_ms: 123    -- Performance metric
}
```

## Replay Algorithm

To rebuild current state from events:

```python
def replay_repair_events(session_id: str) -> Dict[str, str]:
    """
    Replay all repair events to compute current parent mappings.

    Returns:
        message_parents: {message_id: parent_uuid}
    """
    # 1. Fetch all active events
    events = db.query("""
        SELECT * FROM repairs_events
        WHERE session_id = $session_id
          AND is_reverted = false
        ORDER BY timestamp ASC
    """)

    # 2. Apply events in chronological order
    message_parents = {}
    for event in events:
        message_parents[event.message_id] = event.new_parent_uuid

    # 3. Return current state
    return message_parents
```

### Handling Reverts

```python
def replay_with_reverts(session_id: str) -> Dict[str, str]:
    """
    Replay including revert events.
    """
    # Fetch ALL events (including reverted)
    all_events = db.query("""
        SELECT * FROM repairs_events
        WHERE session_id = $session_id
        ORDER BY timestamp ASC
    """)

    # Track which events are reverted
    reverted_ids = {
        e.reverts_event_id
        for e in all_events
        if e.is_reverted and e.reverts_event_id
    }

    # Apply only non-reverted events
    message_parents = {}
    for event in all_events:
        if event.event_id not in reverted_ids:
            message_parents[event.message_id] = event.new_parent_uuid

    return message_parents
```

## Integrity Validation

### Event Digest (Tamper Detection)

Each event has a SHA256 digest computed as:

```python
def compute_event_digest(event: RepairEvent) -> str:
    """
    Compute SHA256 digest for tamper detection.
    """
    content = "".join([
        event.event_id,
        event.session_id,
        event.timestamp.isoformat(),
        event.message_id,
        event.old_parent_uuid or "null",
        event.new_parent_uuid
    ])
    return hashlib.sha256(content.encode()).hexdigest()
```

### Materialization Digest (Drift Detection)

Materialized view has a digest computed as:

```python
def compute_materialization_digest(events: List[RepairEvent]) -> str:
    """
    Compute digest of all event_ids for drift detection.
    """
    event_ids = sorted([e.event_id for e in events])
    content = "".join(event_ids)
    return hashlib.sha256(content.encode()).hexdigest()
```

### Validation Workflow

```python
def validate_integrity(session_id: str) -> ValidationResult:
    """
    Validate that materialized view matches event replay.
    """
    # 1. Get materialized state
    materialized = db.query("""
        SELECT * FROM sessions_materialized
        WHERE session_id = $session_id
    """)

    # 2. Replay from events
    replayed = replay_repair_events(session_id)

    # 3. Compare
    if materialized.message_parents != replayed:
        # Drift detected - cache is stale
        db.query("""
            UPDATE sessions_materialized
            SET drift_detected = true
            WHERE session_id = $session_id
        """)
        return ValidationResult(
            valid=False,
            error="Drift detected: cache doesn't match event replay"
        )

    # 4. Validate event digests
    events = db.query("""
        SELECT * FROM repairs_events
        WHERE session_id = $session_id
    """)

    for event in events:
        computed = compute_event_digest(event)
        if computed != event.event_digest:
            return ValidationResult(
                valid=False,
                error=f"Event {event.event_id} digest mismatch (tampered?)"
            )

    return ValidationResult(valid=True)
```

## Examples

### Example 1: Simple Repair

```python
# Original state: msg-123 has parent=null (orphaned)
# Repair: Set parent to msg-456

event = RepairEvent(
    event_id=generate_uuid(),
    session_id="session-abc",
    timestamp=datetime.now(UTC),
    message_id="msg-123",
    old_parent_uuid=None,
    new_parent_uuid="msg-456",
    operator="user:tryk",
    reason="semantic similarity (0.85)",
    similarity_score=0.85,
    validation_passed=True,
    is_reverted=False,
    reverts_event_id=None,
    event_digest=compute_event_digest(...),
    created_at=datetime.now(UTC)
)

db.query("INSERT INTO repairs_events", event)
```

### Example 2: Revert Repair

```python
# Undo previous repair by creating revert event

original_event = db.query("""
    SELECT * FROM repairs_events
    WHERE event_id = $event_id
""")

revert_event = RepairEvent(
    event_id=generate_uuid(),
    session_id=original_event.session_id,
    timestamp=datetime.now(UTC),
    message_id=original_event.message_id,
    old_parent_uuid=original_event.new_parent_uuid,  # Swap
    new_parent_uuid=original_event.old_parent_uuid,  # Swap
    operator="user:tryk",
    reason="Reverting incorrect repair",
    similarity_score=0.0,  # Manual revert
    validation_passed=True,
    is_reverted=True,
    reverts_event_id=original_event.event_id,  # Link
    event_digest=compute_event_digest(...),
    created_at=datetime.now(UTC)
)

db.query("INSERT INTO repairs_events", revert_event)
```

### Example 3: Rebuild Materialized View

```python
def rebuild_materialized_view(session_id: str) -> None:
    """
    Full rebuild of materialized view from events.
    """
    start_time = time.time()

    # Fetch all active events
    events = db.query("""
        SELECT * FROM repairs_events
        WHERE session_id = $session_id
          AND is_reverted = false
        ORDER BY timestamp ASC
    """)

    # Build message_parents dict
    message_parents = {}
    for event in events:
        message_parents[event.message_id] = event.new_parent_uuid

    # Compute statistics
    total = db.query("""
        SELECT COUNT() FROM repairs_events
        WHERE session_id = $session_id
    """).result

    active = len(events)
    reverted = total - active

    # Generate digest
    digest = compute_materialization_digest(events)

    # Update materialized view
    db.query("""
        UPDATE sessions_materialized
        SET message_parents = $message_parents,
            total_repairs = $total,
            active_repairs = $active,
            reverted_repairs = $reverted,
            last_event_id = $last_event_id,
            last_event_timestamp = $last_timestamp,
            materialized_at = time::now(),
            event_count_at_materialization = $event_count,
            materialization_digest = $digest,
            is_stale = false,
            drift_detected = false,
            rebuild_duration_ms = $duration_ms
        WHERE session_id = $session_id
    """, {
        "session_id": session_id,
        "message_parents": message_parents,
        "total": total,
        "active": active,
        "reverted": reverted,
        "last_event_id": events[-1].event_id if events else None,
        "last_timestamp": events[-1].timestamp if events else None,
        "event_count": len(events),
        "digest": digest,
        "duration_ms": int((time.time() - start_time) * 1000)
    })
```

## Event Log Export

For compliance/audit, export complete event log:

```python
def export_event_log(session_id: str) -> str:
    """
    Export complete event log as JSON for archival.
    """
    events = db.query("""
        SELECT * FROM repairs_events
        WHERE session_id = $session_id
        ORDER BY timestamp ASC
    """)

    log = {
        "session_id": session_id,
        "exported_at": datetime.now(UTC).isoformat(),
        "event_count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "message_id": e.message_id,
                "old_parent_uuid": e.old_parent_uuid,
                "new_parent_uuid": e.new_parent_uuid,
                "operator": e.operator,
                "reason": e.reason,
                "similarity_score": e.similarity_score,
                "validation_passed": e.validation_passed,
                "is_reverted": e.is_reverted,
                "reverts_event_id": e.reverts_event_id,
                "event_digest": e.event_digest
            }
            for e in events
        ]
    }

    return json.dumps(log, indent=2)
```

## Performance Considerations

### Full Rebuild vs Incremental Update

```python
# FULL REBUILD (expensive, but guaranteed correct)
def full_rebuild(session_id: str):
    message_parents = replay_repair_events(session_id)
    update_materialized_view(session_id, message_parents)

# INCREMENTAL UPDATE (fast, assumes cache is correct)
def incremental_update(session_id: str):
    last_event = get_last_event_from_cache(session_id)
    new_events = db.query("""
        SELECT * FROM repairs_events
        WHERE session_id = $session_id
          AND timestamp > $last_timestamp
        ORDER BY timestamp ASC
    """)

    # Apply only new events to existing cache
    message_parents = get_cached_message_parents(session_id)
    for event in new_events:
        message_parents[event.message_id] = event.new_parent_uuid

    update_materialized_view(session_id, message_parents)
```

### When to Use Each

- **Full Rebuild**:
  - After drift detection
  - Weekly validation
  - Initial materialization

- **Incremental Update**:
  - After each new repair event
  - Background job processing queue
  - Real-time updates

## Maintenance

### Background Jobs

1. **Rebuild Stale Views** (every 5 minutes):
   ```python
   def rebuild_stale_views():
       stale = db.query("""
           SELECT session_id FROM sessions_materialized
           WHERE is_stale = true
           LIMIT 10
       """)
       for session in stale:
           rebuild_materialized_view(session.session_id)
   ```

2. **Validate Random Sample** (hourly):
   ```python
   def validate_random_sample():
       sessions = db.query("""
           SELECT session_id FROM sessions_materialized
           ORDER BY RAND()
           LIMIT 5
       """)
       for session in sessions:
           validate_integrity(session.session_id)
   ```

3. **Archive Old Events** (weekly):
   ```python
   def archive_old_events():
       cutoff = datetime.now(UTC) - timedelta(days=90)
       old_events = db.query("""
           SELECT * FROM repairs_events
           WHERE created_at < $cutoff
       """)
       # Export to cold storage
       export_to_s3(old_events)
       # Optionally: Delete from hot storage
   ```

## Security

### Immutability Enforcement

Since SurrealDB doesn't have built-in triggers, enforce immutability in Python:

```python
class ImmutableEventStore:
    def write_event(self, event: RepairEvent) -> bool:
        """Only INSERT allowed."""
        return db.query("INSERT INTO repairs_events", event)

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

If using SurrealDB authentication:

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

## Troubleshooting

### Drift Detected

If `drift_detected = true`:

1. Export both states for comparison:
   ```python
   materialized = get_cached_state(session_id)
   replayed = replay_repair_events(session_id)
   diff = compute_diff(materialized, replayed)
   logger.error(f"Drift: {diff}")
   ```

2. Investigate cause (corrupted cache? missing event?)

3. Force full rebuild:
   ```python
   full_rebuild(session_id)
   ```

### Slow Rebuilds

If rebuild takes too long:

1. Check event count:
   ```sql
   SELECT COUNT() FROM repairs_events
   WHERE session_id = $session_id;
   ```

2. If >10,000 events, consider:
   - Archiving old events
   - Partitioning by time range
   - Using incremental updates only

3. Monitor `rebuild_duration_ms`:
   ```sql
   SELECT
       session_id,
       event_count_at_materialization,
       rebuild_duration_ms,
       rebuild_duration_ms / event_count_at_materialization as ms_per_event
   FROM sessions_materialized
   ORDER BY rebuild_duration_ms DESC
   LIMIT 20;
   ```

## References

- Event Sourcing: Martin Fowler (https://martinfowler.com/eaaDev/EventSourcing.html)
- CQRS: Greg Young (https://cqrs.files.wordpress.com/2010/11/cqrs_documents.pdf)
- Immutable Data: Rich Hickey (https://www.infoq.com/presentations/Value-Values/)
