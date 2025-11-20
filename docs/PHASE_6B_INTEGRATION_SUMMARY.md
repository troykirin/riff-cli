# Phase 6B Integration Summary: Persistence Provider Architecture

## Session Context

**Date**: 2025-10-20
**Commit**: 1c96cc6 (feat(Phase 6B): Complete persistence provider integration - Make SurrealDB canonical store)
**Status**: ✅ Complete - All 16 integration tests passing

## What is Phase 6B?

Phase 6B transforms riff-cli from a JSONL-only mutation-based system to a pluggable architecture where:
- **SurrealDB** becomes the canonical (primary, authoritative) store for repairs
- **JSONL** becomes reference-only (immutable baseline for comparison)
- Different backends can be used interchangeably without code changes

## Problem Solved

### Before Phase 6B
- Repairs directly mutated JSONL files
- No audit trail for who changed what and when
- Cascading corruption across session copies
- No way to view history of repairs
- JSONL is primary data source

### After Phase 6B
- Repairs are append-only events in SurrealDB
- Full immutable audit trail: who, what, when, why, confidence score
- JSONL never changes (reference-only)
- Complete history viewable and queryable
- Flexible backend selection at runtime

## Architecture: Pluggable Persistence Provider System

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Workflow                              │
│                (riff graph <session> --surrealdb-url)           │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │  CLI (cmd_graph)             │
                    │  Sets SURREALDB_URL env     │
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────▼────────────────────┐
                    │ TUI Navigator                    │
                    │ Auto-detects backend            │
                    │ (_create_persistence_provider)  │
                    └─────────────┬────────────────────┘
                                  │
        ┌─────────────────────────▼──────────────────────────┐
        │         RepairManager (Backend-Agnostic)           │
        │         Accepts PersistenceProvider                │
        └─────────────────────────┬──────────────────────────┘
                                  │
            ┌─────────────────────┼─────────────────────┐
            │                     │                     │
    ┌───────▼────────────┐ ┌────▼─────────────┐  │ (Future)
    │ JSONLRepairProvider│ │SurrealDBRepair   │  │ PostgreSQL
    │                    │ │Provider          │  │ Adapter
    │ - Mutates JSONL    │ │                  │  │
    │ - Creates backups  │ │ - Logs events    │  │
    │ - Rollback support │ │ - Virtual backup │  │
    │ - Undo history     │ │ - No mutations   │  │
    └────────┬───────────┘ └────┬─────────────┘  │
             │                  │                 │
      ┌──────▼─────────┐  ┌────▼──────────────┐  │
      │ JSONLRepairWriter
      │ (existing)      │  │ SurrealDBStorage │  │
      │                 │  │ (existing)       │  │
      │ JSONL files     │  │ repairs_events   │  │
      │                 │  │ table (immutable)│  │
      └─────────────────┘  └──────────────────┘  │
```

## Core Components

### 1. PersistenceProvider (Abstract Interface)

**File**: `src/riff/graph/persistence_provider.py`

```python
class PersistenceProvider(ABC):
    """Abstract base class for repair persistence backends."""

    @abstractmethod
    def create_backup(self, session_id: str, source_path: Path) -> Path:
        """Create backup before repair."""

    @abstractmethod
    def apply_repair(self, target_path: Path, repair_op: EngineRepairOperation) -> bool:
        """Apply repair operation."""

    @abstractmethod
    def rollback_to_backup(self, target_path: Path, backup_path: Path) -> bool:
        """Rollback to previous backup."""

    @abstractmethod
    def show_undo_history(self, session_id: str) -> List[RepairSnapshot]:
        """Get available undo points."""

    @abstractmethod
    def get_backend_name(self) -> str:
        """Get human-readable backend name."""
```

### 2. JSONLRepairProvider

**File**: `src/riff/graph/persistence_providers.py`

Wraps existing JSONLRepairWriter to implement PersistenceProvider:
- Creates physical JSONL backups
- Atomic writes to JSONL files
- Undo/rollback from JSONL backups
- Backwards compatible (default backend)

### 3. SurrealDBRepairProvider

**File**: `src/riff/surrealdb/repair_provider.py`

Event-sourced repairs using SurrealDB:
- Virtual backups (no physical files)
- Immutable repair events (append-only)
- Automatic revert events for undo
- Full audit trail preservation

### 4. RepairManager Integration

**File**: `src/riff/graph/repair_manager.py`

Now accepts optional PersistenceProvider:

```python
def __init__(
    self,
    session_id: str,
    jsonl_path: Path,
    session: Session,
    dag: ConversationDAG,
    loader: JSONLLoader,
    persistence_provider: Optional[PersistenceProvider] = None,
):
    # ...
    if persistence_provider is None:
        self.persistence_provider = JSONLRepairProvider()  # Default
    else:
        self.persistence_provider = persistence_provider
```

### 5. TUI Auto-Detection

**File**: `src/riff/tui/graph_navigator.py`

New function `_create_persistence_provider()`:
- Checks `SURREALDB_URL` environment variable
- Creates SurrealDBRepairProvider if available
- Falls back to JSONLRepairProvider
- Logs backend selection

### 6. CLI Integration

**File**: `src/riff/cli.py`

Graph command extended:
- New `--surrealdb-url` flag
- Sets `SURREALDB_URL` environment variable
- Passes to TUI navigator

## Usage Examples

### Default (JSONL Backend)
```bash
riff graph <session-id>
```
Automatically uses JSONL backend, works exactly as before.

### Explicit SurrealDB Backend (CLI Flag)
```bash
riff graph <session-id> --surrealdb-url http://localhost:8000
```
Uses SurrealDB for repairs, creates immutable event log.

### Environment-Based Selection
```bash
export SURREALDB_URL=http://localhost:8000
riff graph <session-id>
```
Automatically detects and uses SurrealDB.

## Testing

**File**: `tests/test_persistence_provider_integration.py`

16 comprehensive integration tests covering:

1. **JSONLRepairProvider** (5 tests)
   - Backend name identification
   - Backup creation
   - Repair operation handling
   - Undo history (empty case)
   - Fallback behavior

2. **SurrealDBRepairProvider** (6 tests)
   - Backend name identification
   - Virtual backup paths
   - Event logging
   - Failure handling
   - Revert event creation
   - History querying

3. **RepairManager with Providers** (3 tests)
   - JSONL backend integration
   - SurrealDB backend integration
   - Default backend selection

4. **Provider Switching** (2 tests)
   - Runtime backend switching
   - Abstract interface validation

**Result**: ✅ All 16 tests passing

## Key Design Decisions

### 1. Backend Interface Abstraction
Instead of coupling to JSONLRepairWriter, defined abstract `PersistenceProvider` interface. This allows:
- Easy addition of new backends (PostgreSQL, S3, etc.)
- Testing with mock implementations
- Clean separation of concerns

### 2. Default to JSONL
Maintains backwards compatibility. Existing workflows continue to work without changes. SurrealDB opt-in via environment variable or CLI flag.

### 3. Virtual Backups for SurrealDB
Rather than creating physical backup files, SurrealDB backend creates virtual backup paths. The event log IS the backup - events are immutable and timestamped.

### 4. Append-Only Undo
Instead of destructive rollback, SurrealDB backend creates "revert" events that document the undo action. This preserves complete audit trail.

### 5. Auto-Detection
TUI automatically detects `SURREALDB_URL` environment variable. No configuration files needed - environment variable is the convention.

## Benefits

### For Users
- Seamless backend switching
- Full audit trail of all repairs
- Point-in-time session reconstruction
- Immutable history (no accidental overwrites)
- Same TUI experience, improved backend

### For Developers
- Pluggable architecture for future backends
- Clear separation of concerns
- Testable components (mocking friendly)
- No code duplication

### For Operations
- Choose backend that fits infrastructure
- Query repair history via SurrealDB queries
- Compliance-friendly audit trails
- Disaster recovery via event replay

## File Statistics

| Component | Lines | Purpose |
|-----------|-------|---------|
| persistence_provider.py | 95 | Abstract interface |
| persistence_providers.py | 136 | JSONL adapter |
| repair_provider.py | 254 | SurrealDB adapter |
| test_persistence_provider_integration.py | 378 | 16 integration tests |
| repair_manager.py (modified) | +30 | Backend parameter support |
| graph_navigator.py (modified) | +50 | Auto-detection logic |
| cli.py (modified) | +10 | CLI flag support |
| **Total** | **~950** | **New Phase 6B code** |

## Next Steps (Phase 6C)

### TUI Integration with SurrealDB Backend
- Update repair preview modal to show event metadata
- Display full repair history in TUI
- Enable event-based undo workflow
- Show immutable audit trail

### Phase 6D: Background Jobs
- Materialized view rebuilding
- Drift detection
- Cleanup of stale views

### Phase 7: Memory Curation
- Bookmarks and tags
- Cross-conversation linking
- Memory DAW interface

## Lessons Learned

1. **Abstraction First**: Defining PersistenceProvider interface upfront made backend switching trivial
2. **Environment-Based Config**: SURREALDB_URL env var avoids configuration file complexity
3. **Immutable Events**: Append-only log provides better auditability than mutable state
4. **Backwards Compatibility**: Defaulting to JSONL ensures zero disruption to existing users
5. **Virtual Abstractions**: Virtual paths for SurrealDB backups reduce complexity

## References

- PHASE_6B_ROADMAP.md: High-level phase planning
- IMMUTABLE_STORE_ARCHITECTURE.md: Detailed immutable event architecture
- REPAIR_WORKFLOW.md: User-facing repair documentation
- test_persistence_provider_integration.py: Integration test examples
