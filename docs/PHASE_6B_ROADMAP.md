# Phase 6B Implementation Roadmap

**Goal**: Transform riff-cli from mutable JSONL repairs to immutable event-sourced architecture

**Timeline**: 6 sub-phases over 2-3 weeks

**Reference**: See `IMMUTABLE_STORE_ARCHITECTURE.md` for complete design

---

## Prerequisites

### Completed (Phase 6A)
- ✅ Repair engine with orphan detection
- ✅ Parent suggestion algorithm (semantic, temporal, type)
- ✅ TUI integration (m/r/u keybindings)
- ✅ Persistence layer (atomic writes, backups)
- ✅ Validation system

### Required Infrastructure
- ✅ SurrealDB running (`http://localhost:8000`)
- ✅ Namespace: `knowledge`, Database: `conversations`
- ✅ Python SurrealDB client library

---

## Phase 6B.1: Event Store Foundation (Week 1, Days 1-2)

### Goal
Create immutable event log in SurrealDB

### Tasks

#### 1.1 Schema Definition
```bash
File: src/riff/db/schema/events.surql
```

Create SurrealDB schema:
```sql
DEFINE TABLE repair_event SCHEMAFULL;
DEFINE FIELD event_id ON repair_event TYPE string;
DEFINE FIELD session_id ON repair_event TYPE string;
DEFINE FIELD message_id ON repair_event TYPE string;
DEFINE FIELD event_type ON repair_event TYPE string;
-- (see IMMUTABLE_STORE_ARCHITECTURE.md for full schema)
```

**Deliverable**: `events.surql` schema file

#### 1.2 Python Data Classes
```bash
File: src/riff/graph/events.py
```

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class RepairEvent:
    event_id: str
    session_id: str
    message_id: str
    event_type: str  # "repair_parent", "repair_turn", etc.
    timestamp: datetime
    operator: str  # "human", "validation_system", "batch_import"
    old_state: Dict[str, Any]
    new_state: Dict[str, Any]
    reason: str
    validation_result: Optional[Dict[str, Any]] = None
    reverted: bool = False
    reverted_by: Optional[str] = None
    reverted_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for SurrealDB"""
        ...

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepairEvent':
        """Deserialize from SurrealDB"""
        ...
```

**Deliverable**: `events.py` with event data models

#### 1.3 Event Store Interface
```bash
File: src/riff/graph/event_store.py
```

```python
class EventStore:
    """Interface to SurrealDB event log"""

    def __init__(self, db_url: str = "http://localhost:8000"):
        self.client = Surreal(db_url)
        self.client.signin({"user": "root", "pass": "root"})
        self.client.use("knowledge", "conversations")

    def create_event(self, event: RepairEvent) -> str:
        """Append event to log (immutable)"""
        ...

    def query_events(
        self,
        session_id: str,
        until: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> List[RepairEvent]:
        """Query events chronologically"""
        ...

    def revert_event(self, event_id: str, operator: str, reason: str):
        """Mark event as reverted (soft delete)"""
        ...
```

**Deliverable**: `event_store.py` with CRUD operations

#### 1.4 Immutability Constraints
```bash
File: src/riff/db/schema/constraints.surql
```

```sql
-- Prevent event mutation
DEFINE EVENT prevent_event_update ON repair_event
WHEN $before != $after
THEN {
    THROW "Events are immutable";
};

-- Prevent event deletion
DEFINE EVENT prevent_event_delete ON repair_event
WHEN $event = "DELETE"
THEN {
    THROW "Events cannot be deleted - mark as reverted";
};
```

**Deliverable**: Database constraints enforcing immutability

#### 1.5 Tests
```bash
File: tests/graph/test_event_store.py
```

Test coverage:
- Create event (success)
- Query events (filtering, chronological order)
- Revert event (soft delete)
- Immutability constraints (prevent mutation/deletion)

**Deliverable**: 10+ tests with 100% coverage

---

## Phase 6B.2: Restore Algorithm (Week 1, Days 3-4)

### Goal
Reconstruct session state by replaying events

### Tasks

#### 2.1 Event Application Engine
```bash
File: src/riff/graph/event_replay.py
```

```python
class EventReplay:
    """Apply events to DAG state"""

    def apply_event(self, dag: ConversationDAG, event: RepairEvent):
        """
        Apply single event transformation

        Dispatches to event-type specific handlers:
        - repair_parent → modify parent_uuid
        - repair_turn → modify type
        - add_message → insert new message
        - mark_invalid → update corruption_score
        """

        handlers = {
            "repair_parent": self._apply_repair_parent,
            "repair_turn": self._apply_repair_turn,
            "add_message": self._apply_add_message,
            "mark_invalid": self._apply_mark_invalid,
        }

        handler = handlers.get(event.event_type)
        if handler:
            handler(dag, event)

    def _apply_repair_parent(self, dag: ConversationDAG, event: RepairEvent):
        message = dag.get_message(event.message_id)
        message.parent_uuid = event.new_state["parent_uuid"]
        dag.rebuild_edges()

    # ... other handlers
```

**Deliverable**: `event_replay.py` with application logic

#### 2.2 Restore Function
```bash
File: src/riff/graph/restore.py
```

```python
def restore_session(
    session_id: str,
    jsonl_path: str,
    event_store: EventStore,
    until: Optional[datetime] = None
) -> ConversationDAG:
    """
    Restore canonical session state from events

    Algorithm:
    1. Load baseline JSONL (frozen state)
    2. Query events (chronological, non-reverted)
    3. Apply each event
    4. Validate final state
    5. Return DAG
    """

    # Load baseline
    messages = parse_jsonl(jsonl_path)
    dag = ConversationDAG(messages)

    # Query events
    events = event_store.query_events(
        session_id=session_id,
        until=until
    )

    # Replay
    replayer = EventReplay()
    for event in events:
        if not event.reverted:
            replayer.apply_event(dag, event)

    # Validate
    validate_dag(dag)

    return dag
```

**Deliverable**: `restore.py` with deterministic replay

#### 2.3 Validation
```bash
File: src/riff/graph/validation.py
```

Post-replay validation checks:
- Unique UUIDs (no duplicates)
- No cycles (DAG property)
- Timestamp ordering (parent before child)
- Referential integrity (all parent UUIDs exist)

**Deliverable**: `validate_dag()` function

#### 2.4 Tests
```bash
File: tests/graph/test_restore.py
```

Test scenarios:
- Empty event log (baseline only)
- Single event (repair_parent)
- Multiple events (complex repairs)
- Time-travel (restore at timestamp)
- Reverted events (ignored in replay)
- Validation failures (cycle detection)

**Deliverable**: 15+ tests with edge cases

---

## Phase 6B.3: Materialized Views (Week 2, Days 1-2)

### Goal
Cache current state for fast queries

### Tasks

#### 3.1 Snapshot Schema
```bash
File: src/riff/db/schema/snapshots.surql
```

```sql
DEFINE TABLE session_snapshot SCHEMAFULL;
DEFINE FIELD session_id ON session_snapshot TYPE string;
DEFINE FIELD snapshot_version ON session_snapshot TYPE int;
DEFINE FIELD created_at ON session_snapshot TYPE datetime;
DEFINE FIELD event_count ON session_snapshot TYPE int;
DEFINE FIELD messages ON session_snapshot TYPE array<object>;
DEFINE FIELD corruption_stats ON session_snapshot TYPE object;

DEFINE INDEX session_snapshot_idx ON session_snapshot COLUMNS session_id UNIQUE;
```

**Deliverable**: Snapshot schema

#### 3.2 View Manager
```bash
File: src/riff/graph/view_manager.py
```

```python
class MaterializedViewManager:
    """Manages session snapshots for performance"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self.db = event_store.client

    def get_current_state(self, session_id: str, jsonl_path: str) -> ConversationDAG:
        """
        Get current session state (fast path)

        Strategy:
        1. Check if snapshot exists
        2. Validate snapshot is current
        3. If valid: return snapshot (O(1))
        4. If invalid: rebuild from events
        """

        snapshot = self._load_snapshot(session_id)

        if snapshot and self._is_valid(snapshot, session_id):
            # Fast path
            return self._deserialize_snapshot(snapshot)

        # Slow path: rebuild
        dag = restore_session(session_id, jsonl_path, self.event_store)
        self._save_snapshot(session_id, dag)
        return dag

    def _is_valid(self, snapshot: dict, session_id: str) -> bool:
        """Check if new events exist after snapshot creation"""

        latest_event = self.event_store.query_events(
            session_id=session_id,
            limit=1,
            order="DESC"
        )

        if not latest_event:
            return True

        return snapshot["created_at"] >= latest_event[0].timestamp

    def invalidate(self, session_id: str):
        """Force rebuild on next query"""
        self.db.query("""
            DELETE FROM session_snapshot
            WHERE session_id = $session_id
        """, {"session_id": session_id})
```

**Deliverable**: `view_manager.py` with caching logic

#### 3.3 Auto-Invalidation
```bash
File: src/riff/graph/event_store.py (update)
```

```python
class EventStore:
    def __init__(self, db_url: str, view_manager: Optional['MaterializedViewManager'] = None):
        self.view_manager = view_manager
        # ...

    def create_event(self, event: RepairEvent) -> str:
        # Store event
        event_id = self.client.create("repair_event", event.to_dict())

        # Invalidate snapshot
        if self.view_manager:
            self.view_manager.invalidate(event.session_id)

        return event_id
```

**Deliverable**: Automatic invalidation on event creation

#### 3.4 Tests
```bash
File: tests/graph/test_view_manager.py
```

Test coverage:
- Snapshot creation (initial state)
- Snapshot retrieval (fast path)
- Snapshot invalidation (on new event)
- Snapshot rebuild (slow path)
- Snapshot versioning

**Deliverable**: 10+ tests

---

## Phase 6B.4: TUI Integration (Week 2, Days 3-4)

### Goal
Replace JSONL mutation with event creation

### Tasks

#### 4.1 RepairManager Refactor
```bash
File: src/riff/graph/repair_manager.py (major update)
```

```python
class RepairManager:
    """Coordinates event store with repair engine"""

    def __init__(
        self,
        session_id: str,
        jsonl_path: str,
        event_store: EventStore,
        view_manager: MaterializedViewManager
    ):
        self.session_id = session_id
        self.jsonl_path = jsonl_path
        self.event_store = event_store
        self.view_manager = view_manager
        self.repair_engine = ConversationRepairEngine()  # Reuse Phase 6A

    def get_current_state(self) -> ConversationDAG:
        """Load from materialized view"""
        return self.view_manager.get_current_state(self.session_id, self.jsonl_path)

    def create_repair_event(
        self,
        message_id: str,
        old_parent: Optional[str],
        new_parent: str,
        operator: str = "human",
        reason: str = ""
    ) -> str:
        """
        Create repair event (NEW workflow)

        Replaces JSONL mutation with event creation
        """

        # Validate repair
        validation = self._validate_repair(message_id, new_parent)

        if not validation["passed"]:
            raise ValidationError(validation["errors"])

        # Create event
        event = RepairEvent(
            event_id=uuid4().hex,
            session_id=self.session_id,
            message_id=message_id,
            event_type="repair_parent",
            timestamp=datetime.now(),
            operator=operator,
            old_state={"parent_uuid": old_parent},
            new_state={"parent_uuid": new_parent},
            reason=reason,
            validation_result=validation
        )

        # Append to log (immutable)
        event_id = self.event_store.create_event(event)

        # Snapshot auto-invalidated by EventStore

        return event_id

    def revert_last_repair(self) -> bool:
        """Revert most recent repair event"""

        events = self.event_store.query_events(
            session_id=self.session_id,
            event_type="repair_parent",
            limit=1,
            order="DESC"
        )

        if not events:
            return False

        self.event_store.revert_event(
            event_id=events[0].event_id,
            operator="human",
            reason="user undo via TUI"
        )

        return True
```

**Deliverable**: Updated `repair_manager.py` with event workflow

#### 4.2 TUI Navigator Update
```bash
File: src/riff/tui/graph_navigator.py (update)
```

```python
class ConversationGraphNavigator:
    def __init__(self, repair_manager: RepairManager):
        self.repair_manager = repair_manager

        # Load from materialized view (fast)
        self.dag = repair_manager.get_current_state()

    def handle_repair_keypress(self):
        """'r' key: Create repair event"""

        message = self.get_current_message()

        # Get candidates (existing logic)
        candidates = self.repair_manager.repair_engine.suggest_parents(message)

        # Show preview (existing UI)
        confirmed = self.show_repair_preview_modal(candidates[0])

        if not confirmed:
            return

        # NEW: Create event instead of mutating JSONL
        try:
            self.repair_manager.create_repair_event(
                message_id=message.uuid,
                old_parent=message.parent_uuid,
                new_parent=candidates[0].uuid,
                operator="human",
                reason=f"TUI repair (similarity {candidates[0].score:.1%})"
            )
        except ValidationError as e:
            self.show_error_modal(str(e))
            return

        # Reload from materialized view
        self.dag = self.repair_manager.get_current_state()
        self.refresh_ui()

    def handle_undo_keypress(self):
        """'u' key: Revert last event"""

        # Get recent events
        events = self.repair_manager.event_store.query_events(
            session_id=self.repair_manager.session_id,
            limit=10,
            order="DESC"
        )

        if not events:
            self.show_modal("No repairs to undo")
            return

        # Show undo preview
        confirmed = self.show_undo_preview_modal(events)

        if not confirmed:
            return

        # Revert
        self.repair_manager.revert_last_repair()

        # Reload
        self.dag = self.repair_manager.get_current_state()
        self.refresh_ui()
```

**Deliverable**: Updated TUI with event-based workflow

#### 4.3 CLI Integration
```bash
File: src/riff/cli.py (update)
```

```python
@click.command()
@click.argument('session-id')
def graph(session_id: str):
    """Open session in TUI navigator"""

    # Resolve JSONL path
    jsonl_path = resolve_session_path(session_id)

    # Initialize event store
    event_store = EventStore()

    # Initialize view manager
    view_manager = MaterializedViewManager(event_store)

    # Initialize repair manager
    repair_manager = RepairManager(
        session_id=session_id,
        jsonl_path=jsonl_path,
        event_store=event_store,
        view_manager=view_manager
    )

    # Launch TUI
    navigator = ConversationGraphNavigator(repair_manager)
    navigator.navigate()
```

**Deliverable**: CLI passes event infrastructure to TUI

#### 4.4 Tests
```bash
File: tests/tui/test_event_workflow.py
```

Integration tests:
- Repair creates event (not mutates JSONL)
- Undo reverts event
- Reload fetches from snapshot
- JSONL never mutated after import

**Deliverable**: 8+ integration tests

---

## Phase 6B.5: Migration Tools (Week 3, Days 1-2)

### Goal
Import existing JSONL sessions into event store

### Tasks

#### 5.1 JSONL Import
```bash
File: src/riff/cli.py (new command)
```

```python
@click.command()
@click.argument('session-id')
@click.option('--jsonl-path', help='Path to JSONL file')
def import_session(session_id: str, jsonl_path: str):
    """
    Import JSONL as frozen baseline

    Creates:
    - Session metadata in SurrealDB
    - Initial snapshot (Layer 2)
    - No events (Layer 1 empty)
    """

    # Parse JSONL
    messages = parse_jsonl(jsonl_path)

    # Create session metadata
    event_store.db.create("session", {
        "session_id": session_id,
        "jsonl_path": jsonl_path,
        "imported_at": datetime.now(),
        "message_count": len(messages),
        "baseline_frozen": True
    })

    # Create initial snapshot
    dag = ConversationDAG(messages)
    view_manager.save_snapshot(session_id, dag)

    click.echo(f"✓ Imported {len(messages)} messages")
    click.echo(f"✓ Session {session_id} ready")
```

**Deliverable**: `riff import-session` command

#### 5.2 Batch Import
```bash
File: src/riff/cli.py (new command)
```

```python
@click.command()
@click.option('--sessions-dir', default='~/.cache/claude/sessions')
def import_all_sessions(sessions_dir: str):
    """
    Import all JSONL sessions from directory

    Scans directory, imports each session
    """

    sessions_dir = Path(sessions_dir).expanduser()

    for jsonl_file in sessions_dir.glob("*.jsonl"):
        session_id = jsonl_file.stem

        try:
            import_session(session_id, str(jsonl_file))
            click.echo(f"✓ {session_id}")
        except Exception as e:
            click.echo(f"✗ {session_id}: {e}")
```

**Deliverable**: `riff import-all-sessions` command

#### 5.3 Historical Repair Detection (Optional)
```bash
File: src/riff/migration/detect_repairs.py
```

```python
def detect_historical_repairs(
    original_jsonl: str,
    repaired_jsonl: str,
    session_id: str
) -> List[RepairEvent]:
    """
    Compare original vs repaired JSONL to infer events

    Use case: User has manually repaired JSONL
    Generate synthetic events to preserve history
    """

    original = parse_jsonl(original_jsonl)
    repaired = parse_jsonl(repaired_jsonl)

    events = []

    for orig_msg, rep_msg in zip(original, repaired):
        if orig_msg.parent_uuid != rep_msg.parent_uuid:
            # Create synthetic event
            event = RepairEvent(
                event_id=uuid4().hex,
                session_id=session_id,
                message_id=orig_msg.uuid,
                event_type="repair_parent",
                timestamp=datetime.now(),  # Approximate
                operator="batch_import",
                old_state={"parent_uuid": orig_msg.parent_uuid},
                new_state={"parent_uuid": rep_msg.parent_uuid},
                reason="historical repair detected during import"
            )
            events.append(event)

    return events
```

**Deliverable**: `detect_repairs.py` utility

#### 5.4 Migration Verification
```bash
File: tests/migration/test_import.py
```

Test coverage:
- Import single session
- Import batch sessions
- Detect historical repairs
- Snapshot matches JSONL
- Query current state

**Deliverable**: 10+ migration tests

---

## Phase 6B.6: Validation & Docs (Week 3, Days 3-4)

### Goal
Production readiness and documentation

### Tasks

#### 6.1 Prospective Validation
```bash
File: src/riff/graph/repair_manager.py (update)
```

```python
def _validate_repair(self, message_id: str, new_parent: str) -> Dict:
    """
    Validate repair before creating event

    Prevents invalid events from entering log
    """

    # Load current state
    dag = self.get_current_state()

    # Simulate repair
    simulated = dag.copy()
    message = simulated.get_message(message_id)
    message.parent_uuid = new_parent
    simulated.rebuild_edges()

    # Validate
    checks = {
        "no_cycle": not simulated.has_cycles(),
        "timestamp_valid": self._check_timestamps(message, new_parent, simulated),
        "parent_exists": new_parent in simulated.messages,
    }

    passed = all(checks.values())

    return {
        "passed": passed,
        "checks": checks,
        "errors": [k for k, v in checks.items() if not v]
    }
```

**Deliverable**: Pre-commit validation

#### 6.2 Conflict Detection
```bash
File: src/riff/graph/conflict_detector.py
```

```python
def detect_conflicts(session_id: str, event_store: EventStore) -> List[Dict]:
    """
    Find concurrent repairs to same message

    Returns conflicts with timestamps and operators
    """

    events = event_store.query_events(session_id)

    conflicts = []

    for message_id in set(e.message_id for e in events):
        message_events = [e for e in events if e.message_id == message_id]

        if len(message_events) > 1:
            conflicts.append({
                "message_id": message_id,
                "events": message_events,
                "resolution": "last_write_wins"
            })

    return conflicts
```

**Deliverable**: `conflict_detector.py` utility

#### 6.3 Performance Benchmarks
```bash
File: tests/performance/test_benchmarks.py
```

Benchmark scenarios:
- Write performance (event creation vs JSONL rewrite)
- Read performance (snapshot vs JSONL parse)
- Rebuild performance (1000+ events)
- Storage overhead (event log size)

**Deliverable**: Performance report

#### 6.4 User Documentation
```bash
Files:
- docs/IMMUTABLE_STORE_ARCHITECTURE.md ✓ (already created)
- docs/IMMUTABLE_STORE_VISUAL_SUMMARY.md ✓ (already created)
- docs/PHASE_6B_MIGRATION_GUIDE.md (new)
```

Migration guide for users:
- How to import existing sessions
- How repair workflow changes (transparent)
- How to use undo (event history)
- How to query event log
- Troubleshooting

**Deliverable**: User-facing migration guide

#### 6.5 Developer Documentation
```bash
File: docs/PHASE_6B_DEVELOPER_GUIDE.md
```

Developer guide:
- Event store API reference
- How to add new event types
- How to extend validation
- How to query event history
- Debugging tips

**Deliverable**: Developer reference

---

## Success Criteria

### Phase 6B Complete When:

✅ **Event Store**:
- Events created, queried, reverted
- Immutability enforced by database
- Test coverage > 90%

✅ **Restore Algorithm**:
- Deterministic replay (same inputs = same output)
- Time-travel works (restore at timestamp)
- Validation detects corruption

✅ **Materialized Views**:
- Snapshots created and cached
- Auto-invalidation on new events
- Query performance < 100ms

✅ **TUI Integration**:
- Repairs create events (not mutate JSONL)
- Undo shows event history
- User experience unchanged

✅ **Migration**:
- Existing sessions imported
- Historical repairs detected (optional)
- Backward compatibility verified

✅ **Production**:
- Performance benchmarks met
- Documentation complete
- Zero breaking changes to CLI

---

## Risk Mitigation

### Risk 1: Performance Regression

**Mitigation**:
- Benchmark early (Phase 6B.3)
- Materialized views for fast queries
- Event replay optimizations (batching)

### Risk 2: Data Loss

**Mitigation**:
- JSONL remains untouched (Layer 3)
- Events append-only (immutable)
- Database constraints prevent mutation

### Risk 3: User Confusion

**Mitigation**:
- TUI workflow unchanged
- Migration guide with examples
- Backward compatibility (JSONL still readable)

### Risk 4: Event Explosion

**Mitigation**:
- Event compression (archive old events)
- Snapshot pruning (keep last N)
- Monitor storage growth

---

## Post-Phase 6B

### Phase 7: Memory Curation

Build on immutable foundation:
- Bookmark events (user tags)
- Annotation events (user notes)
- Export events (curated views)
- Cross-session linking

### Phase 8: Advanced Features

- Event replay speed optimizations
- Multi-session queries
- Branching (alternate timelines)
- Collaboration (multi-user sessions)

---

## Implementation Notes

### Development Workflow

1. **Branch strategy**: `feature/phase-6b-{sub-phase}`
2. **PR reviews**: Each sub-phase = separate PR
3. **Testing**: Unit + integration tests required
4. **Documentation**: Updated in same PR

### Testing Strategy

- **Unit tests**: Each module tested in isolation
- **Integration tests**: TUI workflow end-to-end
- **Performance tests**: Benchmarks vs Phase 6A
- **Migration tests**: Real JSONL sessions imported

### Deployment

- **Rollout**: Gradual (enable via feature flag)
- **Rollback**: Keep Phase 6A code until 6B proven
- **Monitoring**: Track event log size, query latency

---

**This roadmap transforms riff-cli into a production-grade, immutable, auditable knowledge management system.**

*Igris, Chief Strategist*
