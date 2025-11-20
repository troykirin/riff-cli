# Immutable Store Architecture: Event-Sourced Conversation Repair

**Phase**: 6B - SurrealDB Integration
**Date**: 2025-10-20
**Status**: Architectural Design
**Author**: Igris (Chief Strategist)

---

## Executive Summary

This document defines the architectural transformation of riff-cli from a **mutable JSONL-based repair system** to an **immutable event-sourced architecture** using SurrealDB as the canonical source of truth.

### The Problem

Current repair workflow (Phase 6A):
```
User repairs message → TUI mutates JSONL → Writes to disk → Reloads
```

**Cascading corruption risks**:
- Direct JSONL mutation loses audit trail
- No history of what was changed or why
- Cannot undo beyond immediate backup
- Cannot time-travel to historical states
- Concurrent edits cause data loss

### The Solution

Event-sourced architecture:
```
User repairs message → TUI writes repair event → SurrealDB stores immutably →
Materializes view → TUI reloads from canonical state
```

**Nobel-worthy properties**:
- ✅ Immutable: Events never mutated, only appended
- ✅ Auditable: Full trail of who, what, when, why
- ✅ Reversible: Any event can be marked as reverted
- ✅ Time-travel: Replay to any historical state
- ✅ Deterministic: Same events + JSONL = same result

---

## Architectural Vision

### Three-Layer Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: Canonical Event Log (SurrealDB)                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Events Table (Append-Only, Immutable)                       │ │
│ │ ├─ repair_parent: "msg-123 parent null → msg-456"          │ │
│ │ ├─ repair_turn: "msg-789 turn assistant → user"            │ │
│ │ ├─ validate_session: "Ran validation at T, found 5 issues" │ │
│ │ └─ revert_event: "Undo event-xyz at T+5"                   │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓ replay chronologically
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: Materialized Views (SurrealDB)                        │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Session Snapshots (Derived from Events)                     │ │
│ │ ├─ Current canonical state                                  │ │
│ │ ├─ Automatically invalidated on new events                  │ │
│ │ ├─ Fast O(1) queries for TUI                               │ │
│ │ └─ Rebuilds by replaying events                            │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓ reference only
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: Original JSONL (Read-Only Reference)                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Claude Code Session Files                                   │ │
│ │ ├─ Initial import: frozen at time T0                       │ │
│ │ ├─ Never mutated after import                              │ │
│ │ └─ Used only for restore baseline                          │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Core Principle: Immutability Through Event Sourcing

**Traditional Mutable Approach** (Phase 6A):
```python
# Direct mutation - loses history
message.parent_uuid = new_parent
write_jsonl(messages)  # Overwrites previous state
```

**Event Sourcing Approach** (Phase 6B):
```python
# Create immutable event
event = RepairEvent(
    event_type="repair_parent",
    message_id="msg-123",
    old_parent=None,
    new_parent="msg-456",
    operator="human",
    reason="manual repair via TUI",
    timestamp=now()
)

# Append to canonical log (never mutate existing events)
db.create("repair_event", event)

# Materialize current state
snapshot = rebuild_snapshot(session_id, replay_all_events())
```

---

## Data Model Specification

### 1. Events Table (Canonical Source of Truth)

```sql
-- Event Log: Immutable append-only record of all changes
DEFINE TABLE repair_event SCHEMAFULL;

-- Event Identity
DEFINE FIELD event_id ON repair_event TYPE string;
DEFINE FIELD session_id ON repair_event TYPE string;
DEFINE FIELD message_id ON repair_event TYPE string;

-- Event Classification
DEFINE FIELD event_type ON repair_event TYPE string;
    -- "repair_parent"     : Change parent reference
    -- "repair_turn"       : Change turn boundary/type
    -- "add_message"       : Insert new message
    -- "mark_invalid"      : Flag structural corruption
    -- "revert_event"      : Soft delete previous event
    -- "validate_session"  : Record validation run

-- Event Metadata
DEFINE FIELD timestamp ON repair_event TYPE datetime;
DEFINE FIELD operator ON repair_event TYPE string;
    -- "human"             : Manual TUI repair
    -- "validation_system" : Automated validation
    -- "batch_import"      : Initial import from JSONL

-- Change Details (event-type specific)
DEFINE FIELD old_state ON repair_event TYPE object;
    -- Example (repair_parent):
    -- {"parent_uuid": null}

DEFINE FIELD new_state ON repair_event TYPE object;
    -- Example (repair_parent):
    -- {"parent_uuid": "msg-456", "similarity": 0.875}

-- Audit Trail
DEFINE FIELD reason ON repair_event TYPE string;
    -- "semantic similarity match (87.5%)"
    -- "manual user repair via TUI"
    -- "validation detected orphan"

DEFINE FIELD validation_result ON repair_event TYPE option<object>;
    -- {"passed": true, "checks": ["no_cycle", "timestamp_valid"]}

-- Soft Delete (never physically delete)
DEFINE FIELD reverted ON repair_event TYPE bool DEFAULT false;
DEFINE FIELD reverted_by ON repair_event TYPE option<string>;
    -- Event ID that reverted this event
DEFINE FIELD reverted_at ON repair_event TYPE option<datetime>;

-- Indexes
DEFINE INDEX event_id_idx ON repair_event COLUMNS event_id UNIQUE;
DEFINE INDEX session_idx ON repair_event COLUMNS session_id;
DEFINE INDEX timestamp_idx ON repair_event COLUMNS timestamp;
DEFINE INDEX message_idx ON repair_event COLUMNS message_id;
DEFINE INDEX event_type_idx ON repair_event COLUMNS event_type;
```

### 2. Session Snapshots (Materialized Views)

```sql
-- Materialized view of current canonical state
DEFINE TABLE session_snapshot SCHEMAFULL;

-- Snapshot Identity
DEFINE FIELD session_id ON session_snapshot TYPE string;
DEFINE FIELD snapshot_version ON session_snapshot TYPE int;
    -- Increments on each rebuild

-- Snapshot Metadata
DEFINE FIELD created_at ON session_snapshot TYPE datetime;
DEFINE FIELD event_count ON session_snapshot TYPE int;
    -- Number of events applied to create this snapshot

-- Snapshot Data (derived from events)
DEFINE FIELD messages ON session_snapshot TYPE array<object>;
    -- Full reconstructed message list with repairs applied

DEFINE FIELD corruption_stats ON session_snapshot TYPE object;
    -- {"orphan_count": 5, "corruption_score": 0.12}

-- Cache Invalidation
DEFINE FIELD valid_until_event ON session_snapshot TYPE option<string>;
    -- If new events arrive, invalidate and rebuild

-- Indexes
DEFINE INDEX session_snapshot_idx ON session_snapshot COLUMNS session_id UNIQUE;
```

### 3. Event Type Schemas

Each `event_type` has specific `old_state` and `new_state` schemas:

#### `repair_parent`
```json
{
  "event_type": "repair_parent",
  "message_id": "msg-123",
  "old_state": {
    "parent_uuid": null
  },
  "new_state": {
    "parent_uuid": "msg-456",
    "similarity_score": 0.875,
    "candidate_rank": 1
  },
  "reason": "semantic similarity match (87.5%)",
  "operator": "human"
}
```

#### `repair_turn`
```json
{
  "event_type": "repair_turn",
  "message_id": "msg-789",
  "old_state": {
    "type": "assistant"
  },
  "new_state": {
    "type": "user"
  },
  "reason": "turn boundary correction",
  "operator": "validation_system"
}
```

#### `add_message`
```json
{
  "event_type": "add_message",
  "message_id": "msg-new-001",
  "old_state": null,
  "new_state": {
    "uuid": "msg-new-001",
    "type": "assistant",
    "content": "Reconstructed missing message",
    "parent_uuid": "msg-456",
    "timestamp": "2025-01-20T15:30:00Z"
  },
  "reason": "gap detection - inserted bridging message",
  "operator": "validation_system"
}
```

#### `mark_invalid`
```json
{
  "event_type": "mark_invalid",
  "message_id": "msg-corrupt",
  "old_state": {
    "corruption_score": 0.0
  },
  "new_state": {
    "corruption_score": 0.8,
    "corruption_reasons": ["timestamp_anomaly", "missing_parent"]
  },
  "reason": "validation detected structural issues",
  "operator": "validation_system"
}
```

#### `revert_event`
```json
{
  "event_type": "revert_event",
  "message_id": null,  // No specific message
  "old_state": {
    "target_event_id": "event-xyz-123"
  },
  "new_state": {
    "reverted": true
  },
  "reason": "user undo via TUI",
  "operator": "human"
}
```

#### `validate_session`
```json
{
  "event_type": "validate_session",
  "message_id": null,  // Session-wide event
  "old_state": null,
  "new_state": {
    "validation_run_id": "val-abc-123",
    "orphan_count": 5,
    "corruption_score": 0.12,
    "issues_detected": ["orphan_msg_123", "timestamp_msg_456"]
  },
  "reason": "scheduled validation run",
  "operator": "validation_system"
}
```

---

## Restore Algorithm

### Deterministic Replay

The canonical session state is reconstructed by replaying events:

```python
def restore_session(session_id: str) -> ConversationDAG:
    """
    Restore canonical session state from events.

    Algorithm:
    1. Load original JSONL (baseline state)
    2. Query all events for session (ordered by timestamp)
    3. Replay each event (if not reverted)
    4. Validate final state
    5. Return DAG
    """

    # Step 1: Load baseline
    messages = load_jsonl(session_id)  # Original, frozen state
    dag = ConversationDAG(messages)

    # Step 2: Query events chronologically
    events = db.query("""
        SELECT * FROM repair_event
        WHERE session_id = $session_id
          AND reverted = false
        ORDER BY timestamp ASC
    """, {"session_id": session_id})

    # Step 3: Apply events
    for event in events:
        apply_event(dag, event)

    # Step 4: Validate
    validate_dag(dag)

    return dag


def apply_event(dag: ConversationDAG, event: RepairEvent):
    """
    Apply single event to DAG state.

    Event-type specific transformations.
    """

    if event.event_type == "repair_parent":
        message = dag.get_message(event.message_id)
        message.parent_uuid = event.new_state["parent_uuid"]
        dag.rebuild_edges()

    elif event.event_type == "repair_turn":
        message = dag.get_message(event.message_id)
        message.type = event.new_state["type"]

    elif event.event_type == "add_message":
        new_message = Message(**event.new_state)
        dag.add_message(new_message)

    elif event.event_type == "mark_invalid":
        message = dag.get_message(event.message_id)
        message.corruption_score = event.new_state["corruption_score"]

    # Note: revert_event is handled by filtering (reverted=false)
    # Note: validate_session is metadata, doesn't mutate DAG


def validate_dag(dag: ConversationDAG):
    """
    Post-replay validation.

    Ensures event sequence produced valid state.
    """

    assert dag.has_unique_uuids(), "Duplicate UUIDs detected"
    assert not dag.has_cycles(), "Cycle detected in parent references"
    assert dag.timestamps_ordered(), "Timestamp violations"
```

### Time-Travel Debugging

Replay up to a specific point in time:

```python
def restore_at_timestamp(session_id: str, until: datetime) -> ConversationDAG:
    """
    Restore session state as it existed at specific time.

    Enables debugging: "What did the session look like before repair X?"
    """

    messages = load_jsonl(session_id)
    dag = ConversationDAG(messages)

    events = db.query("""
        SELECT * FROM repair_event
        WHERE session_id = $session_id
          AND timestamp <= $until
          AND reverted = false
        ORDER BY timestamp ASC
    """, {"session_id": session_id, "until": until})

    for event in events:
        apply_event(dag, event)

    return dag
```

---

## Materialized View Strategy

### Performance Optimization

Replaying hundreds of events on every query is expensive. Materialized views cache the current state:

```python
class MaterializedViewManager:
    """
    Manages session snapshots for fast queries.

    Strategy:
    - Maintain current state snapshot
    - Invalidate on new events
    - Rebuild by replaying events
    - Serve queries from snapshot (O(1))
    """

    def get_current_state(self, session_id: str) -> ConversationDAG:
        """
        Get current session state (fast path).
        """

        # Check if snapshot exists and is valid
        snapshot = db.query("""
            SELECT * FROM session_snapshot
            WHERE session_id = $session_id
            LIMIT 1
        """, {"session_id": session_id})

        if snapshot and self._is_valid(snapshot, session_id):
            # Fast path: Return cached snapshot
            return self._deserialize(snapshot)

        # Slow path: Rebuild snapshot
        dag = restore_session(session_id)
        self._save_snapshot(session_id, dag)
        return dag


    def _is_valid(self, snapshot: dict, session_id: str) -> bool:
        """
        Check if snapshot is still valid.

        Invalid if:
        - New events exist after snapshot creation
        - Snapshot version outdated
        """

        latest_event = db.query("""
            SELECT timestamp FROM repair_event
            WHERE session_id = $session_id
            ORDER BY timestamp DESC
            LIMIT 1
        """, {"session_id": session_id})

        if not latest_event:
            return True  # No events yet

        return snapshot["created_at"] >= latest_event[0]["timestamp"]


    def _save_snapshot(self, session_id: str, dag: ConversationDAG):
        """
        Save materialized snapshot.
        """

        event_count = db.query("""
            SELECT COUNT() as count FROM repair_event
            WHERE session_id = $session_id
              AND reverted = false
        """, {"session_id": session_id})[0]["count"]

        snapshot = {
            "session_id": session_id,
            "snapshot_version": event_count,
            "created_at": datetime.now(),
            "event_count": event_count,
            "messages": [msg.to_dict() for msg in dag.messages],
            "corruption_stats": dag.get_corruption_stats()
        }

        # Upsert (replace existing)
        db.query("""
            UPDATE session_snapshot
            SET messages = $messages,
                corruption_stats = $stats,
                snapshot_version = $version,
                created_at = $created_at,
                event_count = $event_count
            WHERE session_id = $session_id
        """, snapshot)


    def invalidate(self, session_id: str):
        """
        Force snapshot rebuild on next query.
        """
        db.query("""
            DELETE FROM session_snapshot
            WHERE session_id = $session_id
        """, {"session_id": session_id})
```

### Automatic Invalidation

Events trigger snapshot invalidation:

```python
def create_repair_event(session_id: str, event: RepairEvent) -> str:
    """
    Create new repair event and invalidate snapshot.
    """

    # Store event (immutable)
    event_id = db.create("repair_event", event.to_dict())

    # Invalidate materialized view
    view_manager.invalidate(session_id)

    return event_id
```

---

## New Repair Workflow

### Phase 6A (Current - Mutable JSONL)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User navigates to orphaned message in TUI               │
│ 2. Press 'r' → See repair preview                          │
│ 3. Press 'Y' → TUI mutates JSONL directly                  │
│ 4. JSONLRepairWriter writes to disk                        │
│ 5. Reload DAG from disk                                    │
│ 6. TUI refreshes with new state                            │
└─────────────────────────────────────────────────────────────┘

Problem: JSONL is mutated, losing history
```

### Phase 6B (Immutable Event Store)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User navigates to orphaned message in TUI               │
│ 2. Press 'r' → See repair preview                          │
│ 3. Press 'Y' → TUI creates repair event                    │
│ 4. Event stored in SurrealDB (immutable append)            │
│ 5. Snapshot invalidated                                    │
│ 6. DAG rebuilds from JSONL + events                        │
│ 7. New snapshot materialized                               │
│ 8. TUI refreshes from snapshot (fast)                      │
└─────────────────────────────────────────────────────────────┘

Benefit: JSONL never mutated, full audit trail, reversible
```

### TUI Integration

```python
class ConversationGraphNavigator:
    """
    TUI navigator with event-sourced repairs.
    """

    def __init__(self, session_id: str, repair_manager: RepairManager):
        self.session_id = session_id
        self.repair_manager = repair_manager

        # Load from materialized view (fast)
        self.dag = repair_manager.get_current_state(session_id)


    def handle_repair_keypress(self):
        """
        'r' key: Repair current message.

        New workflow:
        1. Get repair candidates
        2. Show preview modal
        3. User confirms (Y/N)
        4. Create event (not mutate JSONL)
        5. Reload from snapshot
        """

        message = self.get_current_message()

        if not message.is_orphaned():
            self.show_modal("Message not orphaned")
            return

        # Get candidates (unchanged)
        candidates = self.repair_manager.suggest_parents(message)

        if not candidates:
            self.show_modal("No repair candidates found")
            return

        # Show preview (unchanged)
        confirmed = self.show_repair_preview_modal(candidates[0])

        if not confirmed:
            return

        # NEW: Create event instead of mutating JSONL
        event = self.repair_manager.create_repair_event(
            session_id=self.session_id,
            message_id=message.uuid,
            old_parent=message.parent_uuid,
            new_parent=candidates[0].uuid,
            operator="human",
            reason=f"manual repair via TUI (similarity {candidates[0].score})"
        )

        # Reload from materialized view
        self.dag = self.repair_manager.get_current_state(self.session_id)
        self.refresh_ui()


    def handle_undo_keypress(self):
        """
        'u' key: Revert last repair event.

        New workflow:
        1. Query recent events for session
        2. Show undo preview
        3. User confirms
        4. Mark event as reverted
        5. Reload from snapshot
        """

        # Get recent non-reverted events
        events = self.repair_manager.get_recent_events(self.session_id, limit=10)

        if not events:
            self.show_modal("No repairs to undo")
            return

        # Show undo preview
        confirmed = self.show_undo_preview_modal(events)

        if not confirmed:
            return

        # Revert event (soft delete)
        self.repair_manager.revert_event(events[0].event_id)

        # Reload
        self.dag = self.repair_manager.get_current_state(self.session_id)
        self.refresh_ui()
```

---

## Integration with Existing Repair Engine

### Adapter Pattern

The existing `ConversationRepairEngine` (Phase 6A) is preserved - it becomes the event application engine:

```python
class RepairManager:
    """
    Coordinates event store with existing repair engine.

    Responsibilities:
    - Create repair events
    - Apply events to DAG
    - Manage snapshots
    - Provide TUI interface
    """

    def __init__(self, db_client: SurrealDB):
        self.db = db_client
        self.repair_engine = ConversationRepairEngine()  # Reuse Phase 6A
        self.view_manager = MaterializedViewManager(db_client)


    def suggest_parents(self, message: Message) -> List[RepairCandidate]:
        """
        Delegate to existing repair engine (unchanged).
        """
        return self.repair_engine.suggest_parents(message)


    def create_repair_event(
        self,
        session_id: str,
        message_id: str,
        old_parent: Optional[str],
        new_parent: str,
        operator: str,
        reason: str
    ) -> str:
        """
        Create immutable repair event.

        NEW: Instead of mutating JSONL, write event to store.
        """

        event = {
            "event_id": uuid4().hex,
            "session_id": session_id,
            "message_id": message_id,
            "event_type": "repair_parent",
            "timestamp": datetime.now(),
            "operator": operator,
            "old_state": {"parent_uuid": old_parent},
            "new_state": {"parent_uuid": new_parent},
            "reason": reason,
            "validation_result": self._validate_repair(session_id, message_id, new_parent),
            "reverted": False
        }

        # Append to event log (immutable)
        event_id = self.db.create("repair_event", event)

        # Invalidate snapshot
        self.view_manager.invalidate(session_id)

        return event_id


    def _validate_repair(self, session_id: str, message_id: str, new_parent: str) -> dict:
        """
        Validate repair before committing event.

        Reuses existing validation logic from Phase 6A.
        """

        # Load current state
        dag = self.get_current_state(session_id)

        # Simulate repair
        validation = self.repair_engine.validate_repair(
            dag=dag,
            message_id=message_id,
            new_parent=new_parent
        )

        return {
            "passed": validation.is_valid,
            "checks": validation.checks,
            "warnings": validation.warnings
        }


    def get_current_state(self, session_id: str) -> ConversationDAG:
        """
        Get canonical session state.

        Delegates to materialized view manager.
        """
        return self.view_manager.get_current_state(session_id)


    def revert_event(self, event_id: str):
        """
        Soft delete event by marking as reverted.

        NEW: Never physically delete - mark reverted flag.
        """

        revert_event = {
            "event_id": uuid4().hex,
            "event_type": "revert_event",
            "timestamp": datetime.now(),
            "operator": "human",
            "old_state": {"target_event_id": event_id},
            "new_state": {"reverted": True},
            "reason": "user undo via TUI"
        }

        # Create revert event
        self.db.create("repair_event", revert_event)

        # Mark target as reverted
        self.db.query("""
            UPDATE repair_event
            SET reverted = true,
                reverted_by = $revert_event_id,
                reverted_at = $timestamp
            WHERE event_id = $target_event_id
        """, {
            "revert_event_id": revert_event["event_id"],
            "timestamp": revert_event["timestamp"],
            "target_event_id": event_id
        })

        # Invalidate snapshot
        session_id = self._get_session_for_event(event_id)
        self.view_manager.invalidate(session_id)
```

---

## Migration Strategy

### From Phase 6A (Mutable JSONL) to Phase 6B (Immutable Events)

#### Step 1: Import Existing JSONL as Baseline

```python
def import_jsonl_baseline(jsonl_path: str, session_id: str):
    """
    Import JSONL as frozen baseline (Layer 3).

    This becomes the restore starting point.
    """

    # Parse JSONL
    messages = parse_jsonl(jsonl_path)

    # Store metadata
    db.create("session", {
        "session_id": session_id,
        "jsonl_path": jsonl_path,
        "imported_at": datetime.now(),
        "message_count": len(messages),
        "baseline_frozen": True
    })

    # Create initial snapshot
    dag = ConversationDAG(messages)
    view_manager.save_snapshot(session_id, dag)
```

#### Step 2: Detect Existing Repairs (Optional)

If JSONL has already been manually repaired, detect changes:

```python
def detect_historical_repairs(
    original_jsonl: str,
    repaired_jsonl: str,
    session_id: str
):
    """
    Compare original vs repaired JSONL to generate synthetic events.

    Use case: User has already manually repaired JSONL files.
    We can infer events to preserve history.
    """

    original = parse_jsonl(original_jsonl)
    repaired = parse_jsonl(repaired_jsonl)

    # Diff messages
    for orig_msg, rep_msg in zip(original, repaired):
        if orig_msg.parent_uuid != rep_msg.parent_uuid:
            # Synthetic event
            event = {
                "event_id": uuid4().hex,
                "session_id": session_id,
                "message_id": orig_msg.uuid,
                "event_type": "repair_parent",
                "timestamp": datetime.now(),  # Approximate
                "operator": "batch_import",
                "old_state": {"parent_uuid": orig_msg.parent_uuid},
                "new_state": {"parent_uuid": rep_msg.parent_uuid},
                "reason": "historical repair detected during import",
                "validation_result": None,  # Unknown
                "reverted": False
            }
            db.create("repair_event", event)
```

#### Step 3: Future Repairs via Event System

```python
# NEW workflow (Phase 6B)
# User repairs in TUI → creates event → never mutates JSONL

event = create_repair_event(
    session_id=session_id,
    message_id=message.uuid,
    old_parent=message.parent_uuid,
    new_parent=candidate.uuid,
    operator="human",
    reason="manual TUI repair"
)

# Reload from canonical store (not JSONL)
dag = get_current_state(session_id)
```

---

## Conflict Resolution Model

### Concurrent Repairs

What happens if two operators repair the same message simultaneously?

**Event sourcing natural resolution**:

```
Timeline:
T0: Message msg-123 has parent_uuid=null
T1: Operator A creates event: null → msg-456
T2: Operator B creates event: null → msg-789
T3: Replay events chronologically
```

**Result**:
- Both events preserved in history
- Last write wins for current state (msg-789)
- But operator A's intent is recorded
- Can inspect history to understand conflict
- Can revert B's event to restore A's choice

**Query conflict history**:
```sql
SELECT * FROM repair_event
WHERE session_id = $session_id
  AND message_id = $message_id
  AND event_type = 'repair_parent'
ORDER BY timestamp ASC;
```

### Revert Cascade

Reverting an event may invalidate later events:

```
Events:
E1: msg-123 parent null → msg-456
E2: msg-789 parent msg-123 → msg-999  (depends on E1)

If revert E1:
- msg-123 parent becomes null again
- E2 may now be invalid (msg-123 is orphan)
```

**Strategy**: Detect cascading invalidation on revert:

```python
def revert_with_cascade_detection(event_id: str):
    """
    Revert event and detect downstream impacts.
    """

    # Mark as reverted
    revert_event(event_id)

    # Rebuild snapshot
    dag = restore_session(session_id)

    # Validate
    issues = validate_dag(dag)

    if issues:
        # Warn user
        return {
            "success": True,
            "warnings": [
                "Reverting this event created new orphans",
                f"Affected messages: {issues}"
            ]
        }
```

---

## Query Patterns

### Find All Repairs for a Session

```sql
SELECT
    event_id,
    message_id,
    timestamp,
    operator,
    reason,
    old_state,
    new_state,
    reverted
FROM repair_event
WHERE session_id = $session_id
  AND event_type = 'repair_parent'
ORDER BY timestamp DESC;
```

### Get Session State at Specific Time

```sql
-- Get all non-reverted events up to timestamp
SELECT * FROM repair_event
WHERE session_id = $session_id
  AND timestamp <= $target_timestamp
  AND reverted = false
ORDER BY timestamp ASC;

-- Replay to reconstruct historical state
```

### Find Sessions Modified Today

```sql
SELECT DISTINCT session_id, COUNT() as repair_count
FROM repair_event
WHERE timestamp >= $start_of_day
GROUP BY session_id
ORDER BY repair_count DESC;
```

### Audit Trail for Message

```sql
-- Get full history of changes to a specific message
SELECT
    event_id,
    event_type,
    timestamp,
    operator,
    reason,
    old_state,
    new_state,
    reverted,
    reverted_at
FROM repair_event
WHERE message_id = $message_id
ORDER BY timestamp ASC;
```

### Find All Reverted Events

```sql
SELECT
    e.event_id,
    e.timestamp as original_timestamp,
    e.reason as original_reason,
    e.reverted_at,
    r.reason as revert_reason
FROM repair_event e
LEFT JOIN repair_event r ON e.reverted_by = r.event_id
WHERE e.reverted = true
ORDER BY e.reverted_at DESC;
```

---

## Validation Integration

### Prospective Validation

Validate events **before** committing:

```python
def create_repair_event_with_validation(
    session_id: str,
    message_id: str,
    new_parent: str,
    operator: str
) -> Result[str, ValidationError]:
    """
    Validate repair before creating event.

    Prevents invalid events from entering canonical log.
    """

    # Load current state
    dag = get_current_state(session_id)

    # Simulate repair
    simulated = dag.copy()
    simulated.get_message(message_id).parent_uuid = new_parent
    simulated.rebuild_edges()

    # Validate
    validation = validate_dag(simulated)

    if not validation.passed:
        # Reject event
        return Err(ValidationError(validation.errors))

    # Create event (now safe)
    event = create_repair_event(
        session_id=session_id,
        message_id=message_id,
        new_parent=new_parent,
        operator=operator,
        validation_result=validation.to_dict()
    )

    return Ok(event.event_id)
```

### Historical Validation

Record validation runs as events:

```python
def run_validation(session_id: str) -> ValidationReport:
    """
    Run validation on current state and record results.
    """

    dag = get_current_state(session_id)

    # Detect issues
    orphans = dag.find_orphans()
    timestamp_violations = dag.find_timestamp_violations()

    # Create validation event
    event = {
        "event_id": uuid4().hex,
        "session_id": session_id,
        "event_type": "validate_session",
        "timestamp": datetime.now(),
        "operator": "validation_system",
        "new_state": {
            "orphan_count": len(orphans),
            "timestamp_violations": len(timestamp_violations),
            "corruption_score": dag.corruption_score,
            "issues": [msg.uuid for msg in orphans]
        },
        "reason": "scheduled validation run"
    }

    db.create("repair_event", event)

    return ValidationReport(event)
```

---

## Performance Characteristics

### Write Performance

| Operation | Phase 6A (Mutable) | Phase 6B (Immutable) |
|-----------|-------------------|---------------------|
| Single repair | O(n) JSONL rewrite | O(1) append event |
| Batch repairs | O(n×m) rewrites | O(m) append events |
| Backup creation | O(n) full copy | Not needed (events immutable) |
| Undo | O(n) restore from backup | O(1) mark reverted |

### Read Performance

| Operation | Phase 6A | Phase 6B |
|-----------|----------|----------|
| Load session | O(n) parse JSONL | O(1) query snapshot |
| Query history | Impossible (no history) | O(log k) query events |
| Time-travel | Impossible | O(k) replay k events |
| Search messages | O(n) scan JSONL | O(log n) indexed search |

### Storage Overhead

**Event size**: ~200-500 bytes per event (JSON metadata)

**Example session**:
- 406 messages (initial)
- 50 repairs applied
- Event storage: 50 × 400 bytes = 20 KB
- Snapshot storage: ~1 MB (full session)
- Original JSONL: ~1 MB

**Total**: ~2 MB (vs 1 MB mutable JSONL)

**Tradeoff**: 2x storage for infinite undo + audit trail + time-travel

---

## Security & Governance

### Audit Compliance

Event log provides:
- **Who**: Operator field (human, system, batch)
- **What**: Event type, old/new state
- **When**: Timestamp (microsecond precision)
- **Why**: Reason field (human-readable)
- **Validated**: Validation result

Example audit query:
```sql
-- All human repairs in last 7 days
SELECT
    session_id,
    message_id,
    timestamp,
    reason,
    validation_result
FROM repair_event
WHERE operator = 'human'
  AND event_type = 'repair_parent'
  AND timestamp >= $seven_days_ago
ORDER BY timestamp DESC;
```

### Immutability Guarantees

**Database-level constraints**:
```sql
-- Prevent event mutation
DEFINE EVENT prevent_event_update ON repair_event
WHEN $before != $after
THEN {
    THROW "Events are immutable - create revert event instead";
};

-- Prevent event deletion
DEFINE EVENT prevent_event_delete ON repair_event
WHEN $event = "DELETE"
THEN {
    THROW "Events cannot be deleted - mark as reverted instead";
};
```

---

## Implementation Checklist

### Phase 6B.1: Event Store Foundation

- [ ] Design SurrealDB event schema (this document)
- [ ] Create `repair_event` table with indexes
- [ ] Implement `RepairEvent` data class
- [ ] Write event creation API
- [ ] Test event immutability constraints

### Phase 6B.2: Restore Algorithm

- [ ] Implement `restore_session()` function
- [ ] Implement `apply_event()` for each event type
- [ ] Add time-travel support (`restore_at_timestamp()`)
- [ ] Validate deterministic replay (same inputs = same output)
- [ ] Performance test with 1000+ events

### Phase 6B.3: Materialized Views

- [ ] Design `session_snapshot` table
- [ ] Implement `MaterializedViewManager`
- [ ] Add automatic invalidation on new events
- [ ] Benchmark snapshot rebuild time
- [ ] Add snapshot versioning

### Phase 6B.4: TUI Integration

- [ ] Update `ConversationGraphNavigator` for event workflow
- [ ] Modify `handle_repair_keypress()` to create events
- [ ] Implement `handle_undo_keypress()` with event revert
- [ ] Show event history in undo modal
- [ ] Add validation preview before event commit

### Phase 6B.5: Migration Tools

- [ ] Write JSONL import script (baseline freeze)
- [ ] Add historical repair detection (optional)
- [ ] Create migration command (`riff migrate:event-store`)
- [ ] Document migration workflow
- [ ] Test with real sessions

### Phase 6B.6: Validation & Conflict Resolution

- [ ] Implement prospective validation (pre-commit)
- [ ] Add validation event recording
- [ ] Detect cascade impacts on revert
- [ ] Add conflict detection queries
- [ ] Document resolution strategies

---

## Success Criteria

### Phase 6B Complete When:

✅ **Immutability**:
- Events never mutated after creation
- Revert creates new event (soft delete)
- Database constraints prevent mutation

✅ **Audit Trail**:
- Every repair has full who/what/when/why
- Query history for any message
- Export compliance reports

✅ **Time-Travel**:
- Restore session to any historical state
- Compare before/after repairs
- Debug cascading issues

✅ **Performance**:
- Snapshot queries < 100ms
- Event append < 10ms
- Rebuild snapshot < 1s for 1000+ events

✅ **TUI Integration**:
- Repair workflow unchanged for users
- Undo shows event history
- Validation runs before commit

✅ **Backward Compatibility**:
- JSONL import works
- Existing repair engine reused
- No breaking CLI changes

---

## Future Enhancements

### Phase 6C: Advanced Event Features

- **Event Compression**: Archive old events to reduce storage
- **Multi-Session Events**: Cross-conversation linking
- **Branching**: Create alternate repair timelines
- **Collaboration**: Multi-user repair sessions
- **Event Replay Speed**: Optimize with caching layers

### Phase 7: Memory Curation

Build on immutable foundation:
- Bookmark events (user adds tag)
- Annotation events (user adds note)
- Export events (user creates curated view)
- All curation flows through event log

---

## Conclusion

This immutable event-sourced architecture transforms riff-cli from a fragile mutable-state system to a robust, auditable, time-traveling knowledge management system.

**Key Properties**:
- ✅ Immutable: Events never mutated
- ✅ Auditable: Full trail of all changes
- ✅ Reversible: Undo any event at any time
- ✅ Deterministic: Replay yields consistent state
- ✅ Performant: Materialized views for fast queries

**Nobel Architecture**: Elegant, provably correct, battle-tested pattern (event sourcing is decades-proven in financial systems, distributed databases, and CQRS architectures).

This is the foundation that prevents cascading corruption and enables the "live graph as you riff" vision.

---

**Igris, Chief Strategist**
*"I envision the unbuilt and guide its noble construction"*
