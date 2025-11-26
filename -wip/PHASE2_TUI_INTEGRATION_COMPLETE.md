# Phase 2: TUI Integration Complete - READY FOR TESTING

**Status**: ✅ INTEGRATION WIRED (2025-11-17)
**Execution Time**: 60 minutes (architecture discovery + wiring)
**Previous Phase**: Phase 1 (SurrealDB Backend Activation)

---

## Executive Summary

Phase 2 successfully connected the TUI to SurrealDB repair logging through config-driven backend selection. The integration is now COMPLETE and ready for end-to-end testing.

**Key Discovery**: riff-cli already had a fully-implemented pluggable persistence architecture! The work was NOT building new features, but wiring existing components through the config system.

**Critical Change**: `_create_persistence_provider()` in `graph_navigator.py` now reads from `~/.config/nabi/riff.toml` instead of `SURREALDB_URL` environment variable.

---

## Architecture Discovery

### 1. Pluggable Persistence Architecture ✅

**Location**: `src/riff/graph/`

```
RepairManager
    ├── Uses PersistenceProvider interface (abstract)
    │
    ├── JSONLRepairProvider (default)
    │   └── Mutates JSONL files atomically
    │
    └── SurrealDBRepairProvider (Phase 6B)
        └── Logs immutable repair events
```

**Key Files**:
- `persistence_provider.py` - Abstract interface (5 methods)
- `persistence_providers.py` - JSONLRepairProvider implementation
- `surrealdb/repair_provider.py` - SurrealDBRepairProvider implementation ✅ ALREADY EXISTS

**Interface Methods**:
1. `create_backup()` - Create backup before repair
2. `apply_repair()` - Apply repair operation
3. `rollback_to_backup()` - Undo repair
4. `show_undo_history()` - Get undo points
5. `get_backend_name()` - Return backend name

### 2. SurrealDBRepairProvider Implementation ✅

**Location**: `src/riff/surrealdb/repair_provider.py` (258 lines)

**Status**: FULLY IMPLEMENTED (discovered, not built)

**Key Features**:
```python
class SurrealDBRepairProvider(PersistenceProvider):
    def __init__(self, storage: SurrealDBStorage, operator: str = "tui"):
        self.storage = storage
        self.operator = operator

    def apply_repair(self, target_path: Path, repair_op: EngineRepairOperation) -> bool:
        # Line 107: Calls storage.log_repair_event()
        success = self.storage.log_repair_event(
            repair_op=repair_op,
            operator=self.operator,
        )
        return success
```

**Immutable Event Logging**:
- Appends to `repairs_events` table (never UPDATE or DELETE)
- Full audit trail: who, what, when, why, confidence
- Revert events for undo (no destructive updates)
- Virtual backups (event log is the backup)

### 3. TUI Integration Point ✅

**Location**: `src/riff/tui/graph_navigator.py`

**Before** (Line 25-60):
```python
def _create_persistence_provider() -> Optional[PersistenceProvider]:
    surrealdb_url = os.getenv("SURREALDB_URL")  # ❌ Environment variable

    if surrealdb_url:
        storage = SurrealDBStorage(base_url=surrealdb_url)
        return SurrealDBRepairProvider(storage=storage, operator="tui")

    return JSONLRepairProvider()  # Default fallback
```

**After** (Phase 2 modification):
```python
def _create_persistence_provider() -> Optional[PersistenceProvider]:
    from ..config import get_config
    config = get_config()

    if config.surrealdb_enabled:  # ✅ Config-driven
        storage = SurrealDBStorage(
            base_url=config.surrealdb_endpoint,
            namespace=config.surrealdb_namespace,
            database=config.surrealdb_database,
            username=config.surrealdb_username,
            password=config.surrealdb_password,
        )
        return SurrealDBRepairProvider(storage=storage, operator="tui")

    return JSONLRepairProvider()  # Default fallback
```

**Changes**:
1. Import `get_config()` from config module
2. Check `config.surrealdb_enabled` instead of env var
3. Initialize SurrealDBStorage with all config values (5 parameters)
4. Log proper namespace.database in info message

---

## Files Modified

### `/Users/tryk/nabia/tools/riff-cli/src/riff/tui/graph_navigator.py`

**Lines**: 25-76 (modified _create_persistence_provider function)

**Before**:
- Checked `SURREALDB_URL` environment variable
- Only passed `base_url` to SurrealDBStorage
- No namespace/database/auth configuration

**After**:
- Checks `config.surrealdb_enabled` from TOML
- Passes all 5 SurrealDB configuration parameters
- Logs `namespace.database` for clarity
- Falls back gracefully if init fails

**Testing**: Not yet tested (Phase 3)

---

## Integration Flow

### User Triggers Repair in TUI

```
1. TUI launches with graph_navigator.py

2. _create_persistence_provider() is called (line 172)
   ├── Loads config from ~/.config/nabi/riff.toml
   ├── Checks config.surrealdb_enabled (currently: true)
   ├── Creates SurrealDBStorage with config values:
   │   - endpoint: http://localhost:8284
   │   - namespace: memory
   │   - database: riff
   │   - username: root
   │   - password: federation-root-pass
   └── Returns SurrealDBRepairProvider

3. RepairManager is initialized with SurrealDBRepairProvider (line 174)

4. User marks orphaned message (m keybinding)

5. User requests repair (r keybinding)
   └── RepairManager.create_repair_preview() shows diff

6. User confirms repair (y keybinding)
   └── RepairManager.apply_repair() is called
       ├── Step 1: Validate repair (circular dependency, timestamp logic)
       ├── Step 2: Create virtual backup marker
       ├── Step 3: Create RepairOperation object
       ├── Step 4: Call persistence_provider.apply_repair()
       │   └── SurrealDBRepairProvider.apply_repair()
       │       └── storage.log_repair_event()
       │           └── INSERT into repairs_events (append-only)
       └── Step 5: Reload DAG

7. Immutable repair event now in SurrealDB ✅
```

### Verification Query

```sql
SELECT * FROM repairs_events
WHERE session_id = 'session-uuid-here'
ORDER BY timestamp DESC
LIMIT 5;
```

---

## Configuration State

### ~/.config/nabi/riff.toml

**Relevant Sections**:
```toml
[surrealdb]
endpoint = "http://localhost:8284"
namespace = "memory"
database = "riff"
username = "root"
password = "federation-root-pass"

[features]
surrealdb_enabled = true  # ✅ ENABLED
```

### SurrealDB Schema (Deployed in Phase 1)

**Database**: `memory.riff`
**Tables**:
- `repairs_events` - Immutable event log
- `repairs_events_for_session` - Session relation edges
- `repairs_events_for_message` - Message relation edges

**Status**: ✅ Schema deployed and verified

---

## What Works NOW

### Backend Integration ✅
- [x] Config flag enabled (`surrealdb_enabled = true`)
- [x] SurrealDB schema deployed (3 tables)
- [x] Connection configured (http://localhost:8284)
- [x] SurrealDBRepairProvider fully implemented
- [x] TUI wired to use config-driven backend selection

### What's Implemented But Untested ⏸️
- [ ] TUI launches with SurrealDB backend
- [ ] RepairManager receives SurrealDBRepairProvider
- [ ] Repair operations log to SurrealDB
- [ ] Undo operations create revert events
- [ ] Repair history displays from SurrealDB

---

## Next Steps (Phase 3: Testing)

### 1. Manual TUI Test

```bash
# Launch TUI with a session that has orphans
cd ~/nabia/tools/riff-cli
riff tui ~/.claude/projects/{project}/{session-id}.jsonl

# In TUI:
# 1. Press 'm' to mark orphaned message
# 2. Press 'r' to request repair
# 3. Press 'y' to confirm
# 4. Check logs for "Using SurrealDB repair backend"
```

### 2. Verify Event Logged

```bash
surreal sql --endpoint http://localhost:8284 \
  --namespace memory --database riff \
  --username root --password federation-root-pass \
  --pretty << 'EOF'
SELECT * FROM repairs_events
ORDER BY timestamp DESC
LIMIT 5;
EOF
```

**Expected**: Should see repair event with:
- `event_id` (UUID)
- `session_id` (from JSONL)
- `message_id` (orphaned message)
- `old_parent_uuid` (null for orphans)
- `new_parent_uuid` (suggested parent)
- `operator` ("tui")
- `reason` ("User-initiated repair from TUI")
- `similarity_score` (0.0-1.0)
- `timestamp` (ISO8601)

### 3. Test Undo

```bash
# In TUI:
# 1. Press 'u' to undo last repair
# 2. Check logs for "Created revert event"
```

**Expected**: Should see revert event in repairs_events with:
- `is_reverted = true`
- `reason = "System-initiated revert/undo"`
- `operator = "tui:system-revert"`

---

## Known Issues

### 1. SurrealDBStorage Constructor Parameters

**Status**: ✅ RESOLVED (verified constructor signature matches)

The constructor accepts all 5 parameters we're passing:
```python
def __init__(
    self,
    base_url: str = "http://localhost:8000",
    namespace: str = "conversations",
    database: str = "repairs",
    username: str = "root",
    password: str = "root",
    timeout: float = 30.0,
    http_client: Optional[HTTPClientProtocol] = None,
) -> None:
```

### 2. Test Suite Configuration

**Status**: ⏸️ DEFERRED (not blocking for integration)

Pytest async tests need configuration:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Impact**: None on TUI integration (tests are validation, not runtime)

---

## Architecture Validation

### Design Patterns Used ✅

1. **Strategy Pattern**: PersistenceProvider interface with multiple implementations
2. **Factory Pattern**: `_create_persistence_provider()` auto-detects backend
3. **Template Method**: RepairManager orchestrates repair workflow, delegates to provider
4. **Event Sourcing**: SurrealDBRepairProvider uses append-only event log
5. **Config-Driven**: Backend selection via TOML, not environment variables

### Separation of Concerns ✅

```
┌─────────────────────────┐
│   TUI (graph_navigator) │  ← User interaction
└───────────┬─────────────┘
            │ creates
            ↓
┌─────────────────────────┐
│    RepairManager        │  ← Orchestration logic
└───────────┬─────────────┘
            │ delegates to
            ↓
┌─────────────────────────┐
│  PersistenceProvider    │  ← Backend abstraction
└───────────┬─────────────┘
            │ implements
    ┌───────┴────────┐
    ↓                ↓
┌─────────┐    ┌──────────────────┐
│  JSONL  │    │  SurrealDB       │  ← Concrete backends
└─────────┘    └──────────────────┘
```

---

## Success Criteria Met

✅ **Phase 1**: Backend activated, schema deployed
✅ **Phase 2**: TUI wired to config-driven backend selection
⏸️ **Phase 3**: End-to-end testing (next)

---

## Rollback Plan

If issues arise during testing:

### Disable SurrealDB
```toml
# ~/.config/nabi/riff.toml
[features]
surrealdb_enabled = false
```

TUI will automatically fall back to JSONLRepairProvider.

### Revert Code Change

```bash
cd ~/nabia/tools/riff-cli
git diff src/riff/tui/graph_navigator.py  # Review change
git checkout src/riff/tui/graph_navigator.py  # Revert if needed
```

---

## Operational Status

**Production Readiness**: Integration complete, testing pending
**Risk Level**: Low (graceful fallback to JSONL)
**Dependencies**:
- federation-surrealdb container running on port 8284 ✅
- Schema deployed in memory.riff database ✅
- Config flag enabled in riff.toml ✅

**Health Check**:
```bash
# Verify SurrealDB responsive
curl http://localhost:8284/health

# Verify config loadable
cd ~/nabia/tools/riff-cli
python3 << 'EOF'
from src.riff.config import get_config
config = get_config()
print(f"SurrealDB enabled: {config.surrealdb_enabled}")
print(f"Endpoint: {config.surrealdb_endpoint}")
print(f"Namespace: {config.surrealdb_namespace}")
print(f"Database: {config.surrealdb_database}")
EOF
```

---

**Phase Completion Date**: 2025-11-17
**Integration Status**: COMPLETE
**Next Action**: Phase 3 end-to-end testing
**Documentation**: This file + PHASE1_SURREALDB_ACTIVATION_COMPLETE.md
