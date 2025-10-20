# Phase 6B: SurrealDB Sync Command

## Overview

The `riff sync:surrealdb` command syncs Claude conversation sessions from JSONL files to SurrealDB as an immutable event store. This provides:

- **Immutable audit trail**: All changes logged as append-only events
- **Hash-based change detection**: Efficient sync only when needed
- **Canonical source migration**: SurrealDB becomes the single source of truth
- **Performance**: Fast queries without re-parsing JSONL

## Quick Start

```bash
# Sync a session to SurrealDB
riff sync:surrealdb 794650a6

# Force re-sync even if unchanged
riff sync:surrealdb 794650a6 --force

# Dry run to preview changes
riff sync:surrealdb 794650a6 --dry-run

# Specify operator for audit trail
riff sync:surrealdb 794650a6 --operator "alice@example.com"
```

## Prerequisites

### 1. Install SurrealDB

```bash
# macOS (Homebrew)
brew install surrealdb/tap/surreal

# Linux
curl -sSf https://install.surrealdb.com | sh

# Docker
docker run --rm --pull always -p 8000:8000 surrealdb/surrealdb:latest \
  start --user root --pass root
```

### 2. Install Python Client

```bash
# Using uv (recommended)
uv pip install surrealdb

# Or using pip
pip install surrealdb
```

### 3. Import Schema

```bash
# Start SurrealDB
surreal start --bind 0.0.0.0:8000 --user root --pass root

# Import schema
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  src/riff/surrealdb/schema.sql

# Verify tables exist
surreal sql --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations

# In SQL shell:
INFO FOR DB;
```

## Usage

### Basic Sync

```bash
# Sync by session UUID
riff sync:surrealdb 794650a6-84a5-446b-879c-639ee85fbde4

# Or use short UUID prefix
riff sync:surrealdb 794650a6

# Or provide full path
riff sync:surrealdb ~/.claude/projects/-Users-tryk--nabi/794650a6.jsonl
```

**Output:**
```
Syncing session: 794650a6
Source: /Users/tryk/.claude/projects/-Users-tryk--nabi/794650a6.jsonl

Step 1: Loading from JSONL...
  ✓ Loaded 159 messages
  ✓ Session hash: abc123def456789a

Step 2: Connecting to SurrealDB...
  ✓ Connected to ws://localhost:8000/rpc

Step 3: Checking existing session...
  • New session (not in SurrealDB)

Step 4: Analyzing session structure...
  • Messages: 159
  • Threads: 5
  • Corruption: 16.23%

Step 5: Initial import (no changes to detect)

Step 6: Writing to SurrealDB...
  ✓ Synced session record
  ✓ Logged 0 repair events
  ✓ Synced 159 messages

============================================================
✓ Sync Complete

Session Status:
  Messages: 159
  Threads: 5
  Corruption: 16.23%
  Hash: abc123def456789a

Next Steps:
  riff graph 794650a6  # View conversation graph
  # SurrealDB query: SELECT * FROM session:794650a6

Note: JSONL is now reference-only.
SurrealDB is the canonical source for this session.
============================================================
```

### Incremental Sync (Re-sync After Changes)

If you modify the JSONL (e.g., via repair operations), re-sync to log changes:

```bash
# Make repairs in JSONL
riff graph 794650a6  # Use TUI to repair parentUuid

# Re-sync to SurrealDB
riff sync:surrealdb 794650a6
```

**Output:**
```
Step 3: Checking existing session...
  • Found existing session (hash: abc123def456789a)

Step 5: Detecting changes...
  ✓ Found 24 changes

Changes Logged:
  Repair events: 24
```

The system detects:
- **New messages**: Messages added to JSONL
- **Parent repairs**: Changed `parentUuid` fields
- **Content updates**: Modified message content

All changes are logged as immutable `repair_event` records.

## Command-Line Options

### `--force`

Force re-sync even if session hash matches.

```bash
riff sync:surrealdb 794650a6 --force
```

**Use case**: Rebuild SurrealDB from scratch after schema changes.

### `--dry-run`

Show what would be synced without writing to SurrealDB.

```bash
riff sync:surrealdb 794650a6 --dry-run
```

**Output:**
```
DRY RUN - No changes written
Would log 24 repair events
Would sync 159 messages
```

**Use case**: Preview changes before committing to SurrealDB.

### `--operator`

Specify operator name for audit trail (default: "cli").

```bash
riff sync:surrealdb 794650a6 --operator "alice@example.com"
```

**Use case**: Track who made repairs for governance/compliance.

### `--surrealdb-url`

Override default SurrealDB WebSocket URL.

```bash
riff sync:surrealdb 794650a6 --surrealdb-url ws://192.168.1.100:8000/rpc
```

**Default**: `ws://localhost:8000/rpc`

**Use case**: Connect to remote SurrealDB instance.

## Workflow

The sync process follows these steps:

### Step 1: Load from JSONL

```python
loader = JSONLLoader(jsonl_path.parent)
messages = loader.load_messages(session_id)
```

- Reads all messages from JSONL file
- Calculates SHA256 hash of message structure
- Uses existing `JSONLLoader` (no new dependencies)

### Step 2: Connect to SurrealDB

```python
db = Surreal(db_url)
await db.connect()
await db.signin({"user": "root", "pass": "root"})
await db.use("nabi", "conversations")
```

- Establishes WebSocket connection
- Authenticates with credentials
- Selects namespace and database

### Step 3: Check Existing Session

```sql
SELECT * FROM session WHERE session_id = '794650a6'
```

- Queries for existing session record
- Compares session hash to detect changes
- Skips sync if hash matches (unless `--force`)

### Step 4: Analyze Session Structure

```python
dag = ConversationDAG(loader, session_id)
session = dag.to_session()
```

- Builds conversation DAG
- Calculates corruption score
- Counts threads and messages

### Step 5: Detect Changes

```sql
SELECT * FROM message WHERE session_id = '794650a6'
```

- Fetches existing messages from SurrealDB
- Compares with JSONL messages
- Generates repair events for:
  - New messages (`message_added`)
  - Changed parent UUIDs (`parent_repaired`)
  - Updated content (`content_updated`)

### Step 6: Write to SurrealDB

```sql
-- Create/update session
CREATE session:794650a6 CONTENT {
  session_id: '794650a6',
  message_count: 159,
  corruption_score: 0.1623,
  session_hash: 'abc123def456789a',
  ...
}

-- Log repair events (immutable append)
CREATE repair_event CONTENT {
  session_id: '794650a6',
  message_uuid: 'msg-123',
  event_type: 'parent_repaired',
  operator: 'cli',
  old_value: null,
  new_value: 'msg-456',
  ...
}

-- Sync messages (upsert)
CREATE message:msg-123 CONTENT {
  session_id: '794650a6',
  message_uuid: 'msg-123',
  parent_uuid: 'msg-456',
  ...
}
```

- Session record: Single canonical record per session
- Repair events: Immutable append-only log
- Messages: Full message data with metadata

### Step 7: Display Report

```
Session Status:
  Messages: 159
  Threads: 5
  Corruption: 16.23%

Changes Logged:
  Repair events: 24
```

- Shows session statistics
- Lists changes logged
- Provides next steps

## Data Model

### Session Record

```json
{
  "id": "session:794650a6",
  "session_id": "794650a6-84a5-446b-879c-639ee85fbde4",
  "message_count": 159,
  "thread_count": 5,
  "corruption_score": 0.1623,
  "session_hash": "abc123def456789a",
  "last_updated": "2025-10-20T15:30:45Z",
  "created_at": "2025-10-20T14:00:00Z"
}
```

### Repair Event Record (Immutable)

```json
{
  "id": "repair_event:abc123",
  "session_id": "794650a6",
  "message_uuid": "msg-123",
  "event_type": "parent_repaired",
  "operator": "cli",
  "timestamp": "2025-10-20T15:30:45Z",
  "reason": "Parent UUID changed in JSONL",
  "old_value": null,
  "new_value": "msg-456"
}
```

**Event Types:**
- `message_added`: New message detected
- `parent_repaired`: Changed parent reference
- `content_updated`: Modified message content
- `corruption_fixed`: General corruption repair

### Message Record

```json
{
  "id": "message:msg-123",
  "session_id": "794650a6",
  "message_uuid": "msg-123",
  "parent_uuid": "msg-456",
  "message_type": "user",
  "role": "user",
  "content": "What's the best way to...",
  "timestamp": "2025-10-20T15:30:00Z",
  "is_orphaned": false,
  "corruption_score": 0.0
}
```

## Querying SurrealDB

### Get Session Status

```bash
surreal sql --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations

# In SQL shell:
SELECT * FROM session:794650a6;
```

### Get Repair Event History

```sql
SELECT * FROM repair_event
WHERE session_id = '794650a6'
ORDER BY timestamp DESC
LIMIT 50;
```

### Get Corruption Improvement Timeline

```sql
SELECT
  timestamp,
  old_value,
  new_value,
  reason
FROM repair_event
WHERE session_id = '794650a6'
  AND event_type = 'corruption_fixed'
ORDER BY timestamp ASC;
```

### Get Operator Audit Trail

```sql
SELECT
  operator,
  event_type,
  COUNT() as event_count,
  MAX(timestamp) as last_repair
FROM repair_event
WHERE session_id = '794650a6'
GROUP BY operator, event_type
ORDER BY event_count DESC;
```

## Integration with Existing Commands

### `riff graph` (Future Enhancement)

```bash
# Currently: Loads from JSONL
riff graph 794650a6

# Future: Check SurrealDB first, fallback to JSONL
riff graph 794650a6 --use-surrealdb
```

**Benefits:**
- Instant load (no JSONL parsing)
- Cached corruption scores
- Pre-computed thread relationships

### Repair Workflow

```bash
# 1. Open session in TUI
riff graph 794650a6

# 2. Make repairs interactively
# Press 'r' to repair orphaned messages

# 3. Sync to SurrealDB
riff sync:surrealdb 794650a6

# 4. Verify in SurrealDB
surreal sql --conn http://localhost:8000
SELECT * FROM repair_event WHERE session_id = '794650a6';
```

## Error Handling

### SurrealDB Not Running

```
Error: Cannot connect to SurrealDB at ws://localhost:8000/rpc
Make sure SurrealDB is running:
  surreal start --bind 0.0.0.0:8000 --user root --pass root
```

**Fix**: Start SurrealDB server.

### Session Not Found

```
Error: Session 794650a6 not found
Searched in: /Users/tryk/.claude/projects
```

**Fix**: Verify session UUID or provide full path.

### Missing Dependencies

```
Error: surrealdb package not installed
Install with: uv pip install surrealdb
```

**Fix**: Install SurrealDB Python client.

### Schema Not Imported

```
SurrealDB error: Table 'session' does not exist
```

**Fix**: Import schema (see Prerequisites).

## Performance Considerations

### Hash-Based Change Detection

- **Fast skip**: If hash matches, no sync needed (O(1))
- **Incremental sync**: Only changed messages compared (O(n))
- **Efficient**: Avoids full re-import on every sync

### Batch Operations

```python
# Syncs all messages in single transaction
for msg in messages:
    await db.create("message", msg)
```

**Future optimization**: Bulk insert API for 1000+ messages.

### Index Usage

SurrealDB indexes optimize:
- Session lookups by UUID: `session_id_idx`
- Message queries by session: `message_session_idx`
- Repair event history: `repair_event_timestamp_idx`

## Security

### Authentication

Default credentials: `root:root` (development only)

**Production**: Use environment variables:
```bash
export SURREALDB_USER=production_user
export SURREALDB_PASS=secure_password

riff sync:surrealdb 794650a6
```

### Immutability

Repair events are **append-only**:
- Never `UPDATE` or `DELETE` repair_event records
- Audit trail is immutable
- Only way to undo: Restore from JSONL backup

## Future Enhancements

### Phase 7: Read from SurrealDB

```bash
# Use SurrealDB as primary source
riff graph 794650a6 --source surrealdb

# Fallback to JSONL if SurrealDB unavailable
riff graph 794650a6 --source auto
```

### Phase 8: Batch Sync

```bash
# Sync all sessions at once
riff sync:surrealdb --all

# Sync by time range
riff sync:surrealdb --since 2025-10-01
```

### Phase 9: Real-time Sync

```bash
# Watch JSONL directory for changes
riff sync:surrealdb --watch
```

## Troubleshooting

### Connection Timeout

**Symptom**: Command hangs at "Connecting to SurrealDB..."

**Cause**: Firewall blocking WebSocket connection

**Fix**:
```bash
# Check SurrealDB is reachable
curl http://localhost:8000/health

# Use HTTP URL if WebSocket blocked
riff sync:surrealdb 794650a6 --surrealdb-url http://localhost:8000
```

### Hash Mismatch Loop

**Symptom**: Every sync shows changes, even without JSONL edits

**Cause**: Non-deterministic JSON serialization

**Fix**: Use `--force` to rebuild from scratch:
```bash
riff sync:surrealdb 794650a6 --force
```

### Corrupt SurrealDB State

**Symptom**: Query errors after partial sync

**Fix**: Delete session and re-sync:
```sql
DELETE session:794650a6;
DELETE message WHERE session_id = '794650a6';
DELETE repair_event WHERE session_id = '794650a6';
```

Then:
```bash
riff sync:surrealdb 794650a6 --force
```

## References

- [SurrealDB Schema Reference](../src/riff/surrealdb/SCHEMA_REFERENCE.md)
- [SurrealDB Integration Guide](../src/riff/surrealdb/INTEGRATION_GUIDE.md)
- [Repair Workflow Guide](REPAIR_WORKFLOW.md)
- [Phase 6B Handoff](HANDOFF_2025-10-20.md)

## Architecture

```
┌──────────────┐
│  JSONL File  │ (reference-only)
└──────┬───────┘
       │
       │ riff sync:surrealdb
       ▼
┌──────────────────────────────────┐
│         SurrealDB                │
│  ┌────────────────────────────┐  │
│  │  session (canonical)       │  │
│  │  - session_id              │  │
│  │  - session_hash (detect)   │  │
│  │  - corruption_score        │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │  message (materialized)    │  │
│  │  - Fast queries            │  │
│  │  - Pre-computed scores     │  │
│  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │
│  │  repair_event (immutable)  │  │
│  │  - Audit trail             │  │
│  │  - Append-only log         │  │
│  └────────────────────────────┘  │
└──────────────────────────────────┘
       │
       │ riff graph --source surrealdb
       ▼
┌──────────────┐
│   TUI Graph  │
└──────────────┘
```

## Philosophy

**Immutable Pattern**: JSONL is reference-only, SurrealDB is canonical.

**Benefits**:
- Audit trail: All changes tracked
- Performance: Fast queries without parsing
- Reliability: Single source of truth
- Governance: Compliance-ready event log

**Trade-off**: Requires SurrealDB infrastructure.

**Recommendation**: Start with JSONL, migrate to SurrealDB as sessions grow.
