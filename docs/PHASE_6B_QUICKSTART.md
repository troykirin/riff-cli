# Phase 6B Quick Start: SurrealDB Sync

## TL;DR

```bash
# 1. Start SurrealDB
surreal start --bind 0.0.0.0:8000 --user root --pass root

# 2. Import schema
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  src/riff/surrealdb/schema.sql

# 3. Sync a session
riff sync:surrealdb 794650a6

# 4. View in SurrealDB
surreal sql --conn http://localhost:8000 --user root --pass root --ns nabi --db conversations
SELECT * FROM session;
```

## What Phase 6B Adds

**Before (Phase 6A):**
- JSONL is source of truth
- No persistence layer
- Repairs modify JSONL directly
- No audit trail

**After (Phase 6B):**
- SurrealDB is canonical source
- Immutable event log (`repairs_events`)
- JSONL is reference-only
- Full audit trail for compliance

## Command Usage

### Basic Sync

```bash
riff sync:surrealdb <session-id>
```

**What it does:**
1. Loads session from JSONL
2. Calculates hash to detect changes
3. Compares with SurrealDB (if exists)
4. Logs changes as immutable events
5. Materializes updated session view
6. Shows summary report

**Output:**
```
✓ Sync Complete

Session Status:
  Messages: 159
  Threads: 5
  Corruption: 16.23%
  Hash: abc123def456

Changes Logged:
  Repair events: 24
```

### Dry Run (Preview Changes)

```bash
riff sync:surrealdb 794650a6 --dry-run
```

Shows what would be synced without writing to database.

### Force Re-sync

```bash
riff sync:surrealdb 794650a6 --force
```

Syncs even if hash matches (rebuilds from scratch).

### Track Operator

```bash
riff sync:surrealdb 794650a6 --operator "alice@example.com"
```

Logs who performed the sync (for audit trail).

## Data Model

### Three Tables

**`session`** - One record per session
- `session_id`: Claude UUID
- `session_hash`: SHA256 for change detection
- `corruption_score`: Current corruption percentage
- `message_count`, `thread_count`: Metrics

**`repairs_events`** - Immutable append-only log
- `event_id`: Unique event identifier
- `session_id`, `message_id`: What was changed
- `old_parent_uuid` → `new_parent_uuid`: What changed
- `operator`: Who made the change
- `timestamp`: When it happened
- `reason`: Why it was changed

**`sessions_materialized`** - Cached results
- `session_id`: Session identifier
- `corruption_score`: After repairs applied
- `cached_at`: When materialized
- `repair_events_applied`: How many events applied

## Workflow Example

### Initial Import

```bash
# Session exists in JSONL, not in SurrealDB
riff sync:surrealdb 794650a6
```

Creates:
- 1 session record
- 0 repair events (no changes)
- 159 message records
- 1 materialized view

### After Repairs in JSONL

```bash
# User repairs parentUuid in JSONL via TUI
riff graph 794650a6
# ... press 'r' to repair ...

# Sync changes to SurrealDB
riff sync:surrealdb 794650a6
```

Creates:
- Updates session record (new hash)
- 24 repair events (one per changed message)
- Updates 24 message records
- Refreshes materialized view

### Query Repair History

```sql
-- In SurrealDB SQL shell
SELECT * FROM repairs_events
WHERE session_id = '794650a6'
ORDER BY timestamp DESC;
```

Shows:
```
event_id | message_id | old_parent_uuid | new_parent_uuid | operator | timestamp
---------|------------|-----------------|-----------------|----------|----------
evt-123  | msg-456    | null            | msg-789         | cli      | 2025-10-20T15:30:45Z
evt-124  | msg-457    | null            | msg-790         | cli      | 2025-10-20T15:30:46Z
...
```

## Integration with Existing Tools

### With `riff graph`

```bash
# Currently: Always loads from JSONL
riff graph 794650a6

# Future: Can load from SurrealDB (faster)
riff graph 794650a6 --source surrealdb
```

### Repair Workflow

```
┌─────────────┐
│ JSONL File  │ (reference)
└──────┬──────┘
       │
       ├──> riff graph (view/repair)
       │
       └──> riff sync:surrealdb (persist)
              │
              ▼
       ┌──────────────────┐
       │   SurrealDB      │ (canonical)
       │ ─────────────── │
       │ repairs_events   │ (immutable log)
       │ sessions_mat.    │ (cached view)
       └──────────────────┘
```

## Error Handling

### SurrealDB Not Running

```
Error: Cannot connect to SurrealDB at ws://localhost:8000/rpc
```

**Fix:**
```bash
surreal start --bind 0.0.0.0:8000 --user root --pass root
```

### Schema Not Imported

```
SurrealDB error: Table 'repairs_events' does not exist
```

**Fix:**
```bash
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  src/riff/surrealdb/schema.sql
```

### Session Not Found

```
Error: Session 794650a6 not found
```

**Fix:** Verify session UUID or provide full path:
```bash
riff sync:surrealdb ~/.claude/projects/-Users-tryk--nabi/794650a6.jsonl
```

## Performance

### Hash-Based Skip

If session hasn't changed since last sync:
```
✓ Session already up-to-date in SurrealDB
Use --force to re-sync anyway
```

No database writes performed (instant).

### Incremental Sync

Only changed messages generate repair events:
- New messages: `old_parent_uuid = null`
- Changed parents: `old_parent_uuid != new_parent_uuid`

Other messages skipped.

## Next Steps

- **Phase 7**: Read from SurrealDB in `riff graph`
- **Phase 8**: Batch sync all sessions
- **Phase 9**: Auto-sync on JSONL changes

## Files Modified

### New CLI Command
- `src/riff/cli.py`: Added `cmd_sync_surrealdb()`

### Schema Updates
- `src/riff/surrealdb/schema.sql`: Added `repairs_events`, `sessions_materialized`

### Documentation
- `docs/SYNC_SURREALDB.md`: Full reference
- `docs/PHASE_6B_QUICKSTART.md`: This file

## Testing

```bash
# Manual test
riff sync:surrealdb 794650a6

# Verify in SurrealDB
surreal sql --conn http://localhost:8000 --user root --pass root --ns nabi --db conversations
SELECT COUNT() FROM session;
SELECT COUNT() FROM repairs_events;
SELECT COUNT() FROM message;
```

Expected:
- 1 session
- 0-24 repair events (depends on changes)
- 159 messages

## Philosophy

**Immutable Pattern**: Events never deleted, only appended.

**Canonical Source**: SurrealDB is truth, JSONL is reference.

**Audit Trail**: Full history of who changed what, when, why.

**Compliance**: Ready for governance, legal, security requirements.
