# Phase 6B: Immutable Event Store - Documentation Index

**Status**: Architectural Design Complete
**Date**: 2025-10-20
**Phase**: 6B (SurrealDB Integration)

---

## Overview

Phase 6B transforms riff-cli from mutable JSONL repairs to an immutable event-sourced architecture. This prevents cascading corruption and enables full audit trails, time-travel debugging, and infinite undo.

---

## Core Documents

### 1. IMMUTABLE_STORE_ARCHITECTURE.md
**The complete architectural specification**

📄 **File**: `docs/IMMUTABLE_STORE_ARCHITECTURE.md`
📏 **Size**: 39 KB (comprehensive technical design)

**Contents**:
- Three-layer data model (events, snapshots, JSONL)
- Event store schema (SurrealDB tables)
- Event type taxonomy (repair_parent, repair_turn, etc.)
- Restore algorithm (deterministic replay)
- Materialized view strategy (caching)
- Repair workflow transformation
- Validation integration
- Query patterns
- Performance characteristics
- Migration strategy

**When to read**:
- Before implementing Phase 6B
- For architectural decisions
- For database schema reference
- For algorithm specifications

---

### 2. IMMUTABLE_STORE_VISUAL_SUMMARY.md
**Visual diagrams and examples**

📄 **File**: `docs/IMMUTABLE_STORE_VISUAL_SUMMARY.md`
📏 **Size**: 28 KB (diagrams and workflows)

**Contents**:
- Before/After comparison (mutable vs immutable)
- Three-layer architecture diagram
- Event sourcing flow (write/read/time-travel)
- Event types taxonomy tree
- Undo and conflict resolution examples
- Performance comparison charts
- Storage overhead analysis
- Migration path visualization

**When to read**:
- For quick understanding of the system
- To visualize data flows
- For presentations and discussions
- As a reference during implementation

---

### 3. PHASE_6B_ROADMAP.md
**Implementation plan and tasks**

📄 **File**: `docs/PHASE_6B_ROADMAP.md`
📏 **Size**: 23 KB (detailed roadmap)

**Contents**:
- 6 sub-phases with tasks and deliverables
- Week-by-week timeline (2-3 weeks total)
- File-by-file implementation guide
- Code examples for each module
- Testing strategy and coverage
- Success criteria
- Risk mitigation
- Post-Phase 6B planning

**When to read**:
- Before starting implementation
- To track progress
- For task assignment
- For sprint planning

---

## Quick Reference

### What Problem Does This Solve?

**Current Problem** (Phase 6A):
- JSONL files are directly mutated during repairs
- History is lost (only last backup available)
- No audit trail (who changed what, when, why)
- Cannot time-travel to previous states
- Concurrent edits cause conflicts
- Cascading corruption risk

**Solution** (Phase 6B):
- Immutable event log records all changes
- Events never mutated (append-only)
- Full audit trail with metadata
- Time-travel by replaying events to any timestamp
- Concurrent edits preserved in history
- Prevents corruption through immutability

---

## Key Concepts

### Event Sourcing

Instead of storing current state, store **sequence of events** that led to state:

```
Traditional: State (no history)
Event-sourced: State₀ + [Event₁, Event₂, ...] = Current State
```

### Three Layers

1. **Layer 1 (Canonical)**: SurrealDB event log - immutable source of truth
2. **Layer 2 (Materialized)**: SurrealDB snapshots - fast query cache
3. **Layer 3 (Reference)**: JSONL files - frozen baseline, never mutated

### Restore Algorithm

```python
def restore(session_id):
    state = load_jsonl_baseline()  # Layer 3
    events = query_events()        # Layer 1
    for event in events:
        apply(state, event)
    return state
```

---

## Implementation Phases

### Phase 6B.1: Event Store Foundation (2 days)
- SurrealDB schema
- Event data classes
- Event store interface
- Immutability constraints
- Tests

### Phase 6B.2: Restore Algorithm (2 days)
- Event application engine
- Restore function
- Validation
- Time-travel support
- Tests

### Phase 6B.3: Materialized Views (2 days)
- Snapshot schema
- View manager
- Auto-invalidation
- Performance optimization
- Tests

### Phase 6B.4: TUI Integration (2 days)
- RepairManager refactor
- TUI navigator update
- CLI integration
- Workflow tests

### Phase 6B.5: Migration Tools (2 days)
- JSONL import
- Batch import
- Historical repair detection
- Migration tests

### Phase 6B.6: Validation & Docs (2 days)
- Prospective validation
- Conflict detection
- Performance benchmarks
- User documentation
- Developer guide

---

## File Structure

### New Files (Phase 6B)

```
src/riff/
├── graph/
│   ├── events.py              # Event data classes
│   ├── event_store.py         # SurrealDB event interface
│   ├── event_replay.py        # Event application logic
│   ├── restore.py             # Restore algorithm
│   ├── view_manager.py        # Materialized view caching
│   ├── conflict_detector.py   # Conflict detection
│   └── repair_manager.py      # UPDATED: Event-based workflow
│
├── db/
│   └── schema/
│       ├── events.surql       # Event table schema
│       ├── snapshots.surql    # Snapshot table schema
│       └── constraints.surql  # Immutability constraints
│
└── migration/
    └── detect_repairs.py      # Historical repair detection

tests/
├── graph/
│   ├── test_event_store.py   # Event CRUD tests
│   ├── test_restore.py        # Restore algorithm tests
│   └── test_view_manager.py  # Snapshot tests
│
├── migration/
│   └── test_import.py         # Migration tests
│
└── performance/
    └── test_benchmarks.py     # Performance tests
```

### Updated Files

```
src/riff/
├── tui/
│   └── graph_navigator.py    # UPDATED: Event-based repair workflow
│
└── cli.py                     # UPDATED: Event store initialization
```

---

## CLI Commands

### New Commands (Phase 6B)

```bash
# Import single session
riff import-session <session-id> --jsonl-path <path>

# Import all sessions from directory
riff import-all-sessions --sessions-dir ~/.cache/claude/sessions

# Query event history
riff events list <session-id>

# Show event details
riff events show <event-id>

# Revert event
riff events revert <event-id>
```

### Existing Commands (Unchanged)

```bash
# Open session in TUI (workflow transparent to user)
riff graph <session-id>

# Repair commands (create events instead of mutating JSONL)
# - Press 'r' in TUI: Creates repair event
# - Press 'u' in TUI: Reverts last event
```

---

## Performance Targets

### Write Performance

| Operation | Phase 6A | Phase 6B | Target |
|-----------|----------|----------|--------|
| Single repair | ~1.2s | ~6ms | 200x faster |
| Batch repairs | O(n) | O(1) per | Linear speedup |

### Read Performance

| Operation | Phase 6A | Phase 6B | Target |
|-----------|----------|----------|--------|
| Load session | ~600ms | ~10ms (cached) | 60x faster |
| Query history | N/A | ~50ms | Enable feature |

### Storage Overhead

| Metric | Phase 6A | Phase 6B | Acceptable |
|--------|----------|----------|------------|
| Per session | ~7.2 MB | ~2.4 MB | 67% savings |
| Event log | N/A | ~20 KB/50 repairs | < 100 KB |

---

## Migration Checklist

### For Users

- [ ] Read migration guide
- [ ] Backup existing JSONL files
- [ ] Run `riff import-all-sessions`
- [ ] Verify sessions load in TUI
- [ ] Test repair workflow (unchanged)
- [ ] Verify undo shows event history

### For Developers

- [ ] Review architecture document
- [ ] Complete Phase 6B.1 (event store)
- [ ] Complete Phase 6B.2 (restore)
- [ ] Complete Phase 6B.3 (materialized views)
- [ ] Complete Phase 6B.4 (TUI integration)
- [ ] Complete Phase 6B.5 (migration)
- [ ] Complete Phase 6B.6 (validation & docs)
- [ ] Run performance benchmarks
- [ ] Write user migration guide
- [ ] Deploy with feature flag

---

## Success Criteria

Phase 6B is complete when:

✅ **Immutability**:
- Events never mutated after creation
- Database constraints enforce immutability
- Soft delete (reverted flag) for undo

✅ **Audit Trail**:
- Every repair has who/what/when/why
- Query history for any message
- Export compliance reports

✅ **Time-Travel**:
- Restore session to any timestamp
- Compare before/after states
- Debug cascading issues

✅ **Performance**:
- Snapshot queries < 100ms
- Event append < 10ms
- Rebuild < 1s for 1000+ events

✅ **TUI Integration**:
- User workflow unchanged
- Undo shows event history
- Validation before commit

✅ **Backward Compatibility**:
- JSONL import works
- Existing sessions loadable
- No breaking CLI changes

---

## Related Documents

### Phase 6A (Completed)
- `REPAIR_WORKFLOW.md` - Current repair system
- `PERSISTENCE_SUMMARY.md` - JSONL persistence layer
- `SEMANTIC_DAG_DESIGN.md` - Graph architecture

### Phase 6C (Future)
- Event compression and archival
- Cross-session linking
- Advanced analytics

### Phase 7 (Future)
- Memory curation (bookmarks, annotations)
- Export workflows
- Memory DAW interface

---

## Getting Started

### 1. Read the Architecture
Start with `IMMUTABLE_STORE_ARCHITECTURE.md` for complete technical design

### 2. Review Visual Summary
Skim `IMMUTABLE_STORE_VISUAL_SUMMARY.md` for diagrams and examples

### 3. Plan Implementation
Follow `PHASE_6B_ROADMAP.md` for step-by-step tasks

### 4. Implement Phase by Phase
- Phase 6B.1: Event store foundation
- Phase 6B.2: Restore algorithm
- Phase 6B.3: Materialized views
- Phase 6B.4: TUI integration
- Phase 6B.5: Migration tools
- Phase 6B.6: Validation & docs

---

## Questions?

### Architectural Questions
See `IMMUTABLE_STORE_ARCHITECTURE.md` sections:
- "Restore Algorithm" for replay logic
- "Materialized View Strategy" for caching
- "Event Type Schemas" for event structure

### Implementation Questions
See `PHASE_6B_ROADMAP.md` sections:
- "Tasks" for step-by-step guides
- "Code examples" for reference implementations
- "Tests" for coverage requirements

### Visual References
See `IMMUTABLE_STORE_VISUAL_SUMMARY.md` for:
- Data flow diagrams
- Before/after comparisons
- Example scenarios

---

## Document Status

| Document | Status | Size | Last Updated |
|----------|--------|------|--------------|
| IMMUTABLE_STORE_ARCHITECTURE.md | ✅ Complete | 39 KB | 2025-10-20 |
| IMMUTABLE_STORE_VISUAL_SUMMARY.md | ✅ Complete | 28 KB | 2025-10-20 |
| PHASE_6B_ROADMAP.md | ✅ Complete | 23 KB | 2025-10-20 |
| PHASE_6B_INDEX.md | ✅ Complete | 11 KB | 2025-10-20 |

---

**Total Documentation**: 101 KB of comprehensive architectural design

**Ready for Implementation**: Phase 6B.1 can start immediately

**Igris, Chief Strategist**
*"I envision the unbuilt and guide its noble construction"*
