# SurrealDB Schema for Conversation Storage

Phase 6B integration for riff-cli conversation graph visualization.

## Overview

This schema provides a complete SurrealDB data model for storing and analyzing Claude conversation sessions with:

- **Session-level tracking**: High-level metrics and corruption scores
- **Thread-based organization**: Logical conversation flows (main/side_discussion/orphaned)
- **Message DAG structure**: Parent-child relationships with temporal ordering
- **Full-text search**: BM25-based content search across messages
- **Corruption detection**: Support for orphan identification and repair

## Schema Components

### Tables

#### 1. `session`
Represents a single Claude conversation session.

**Fields:**
- `session_id` (string, unique): Claude session UUID
- `message_count` (int): Total messages in session
- `thread_count` (int): Total threads in session
- `corruption_score` (float): Session-level corruption score (0.0-1.0)
- `last_updated` (datetime): Last modification timestamp
- `created_at` (datetime): Session creation timestamp

**Indexes:** `session_id`, `last_updated`

#### 2. `thread`
Represents a logical conversation thread within a session.

**Fields:**
- `session_id` (string): Parent session ID
- `thread_type` (string): Thread classification (`main`, `side_discussion`, `orphaned`)
- `message_count` (int): Total messages in thread
- `topic` (optional string): Semantic topic extracted from messages
- `created_at` (datetime): Thread creation timestamp

**Indexes:** `session_id`, `thread_type`, composite `session_id,thread_type`

#### 3. `message`
Represents a single message in a conversation.

**Fields:**
- `session_id` (string): Parent session ID
- `message_uuid` (string): Unique message identifier
- `parent_uuid` (optional string): Parent message UUID (null for roots)
- `message_type` (string): Message type (`user`, `assistant`, `system`)
- `role` (string): Message role (`user`, `assistant`)
- `content` (string): Message content text (full-text searchable)
- `timestamp` (datetime): Message timestamp
- `thread_id` (optional string): Parent thread ID
- `is_orphaned` (bool): Whether message lacks valid parent
- `corruption_score` (float): Message-level corruption score (0.0-1.0)
- `created_at` (datetime): Record creation timestamp

**Indexes:** `message_uuid`, `session_id`, `parent_uuid`, `thread_id`, `timestamp`, `is_orphaned`, `corruption_score`, composite `session_id,timestamp`

**Full-text Index:** `content` (BM25 with English snowball stemming)

### Relations

#### 1. `message_parent_of`
Parent-child relationship in conversation DAG.

- **From:** `message` → **To:** `message`
- **Type:** one-to-many
- **Usage:** Track conversation flow and threading

#### 2. `message_belongs_to_thread`
Links messages to their containing thread.

- **From:** `message` → **To:** `thread`
- **Type:** many-to-one
- **Properties:** `position` (int) - message order within thread

#### 3. `thread_belongs_to_session`
Links threads to their parent session.

- **From:** `thread` → **To:** `session`
- **Type:** many-to-one

#### 4. `session_contains_message`
Direct session-to-message link for fast queries (optional).

- **From:** `session` → **To:** `message`
- **Type:** one-to-many

### Analyzers

#### `message_search`
Full-text search analyzer for message content.

- **Tokenizers:** blank, class
- **Filters:** lowercase, snowball(english)
- **Usage:** Powers BM25 search on message content

## Installation

### 1. Import Schema

```bash
# Start SurrealDB (if not already running)
surreal start --bind 0.0.0.0:8000 --user root --pass root

# Import schema
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  schema.sql
```

### 2. Verify Installation

```bash
# Connect to SurrealDB
surreal sql --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations

# Check tables
INFO FOR DB;

# Check indexes
SELECT * FROM information_schema.indexes;
```

## Usage Examples

### Python Client

```python
from riff.surrealdb import (
    prepare_session_record,
    prepare_message_record,
    prepare_thread_record,
    validate_message_data,
)
from surrealdb import Surreal

# Connect to SurrealDB
async with Surreal("ws://localhost:8000/rpc") as db:
    await db.signin({"user": "root", "pass": "root"})
    await db.use("nabi", "conversations")

    # Create session
    session = prepare_session_record(
        session_id="550e8400-e29b-41d4-a716-446655440000",
        message_count=0,
        thread_count=0,
    )
    result = await db.create("session", session)

    # Create message
    message = prepare_message_record(
        session_id="550e8400-e29b-41d4-a716-446655440000",
        message_uuid="msg-001",
        message_type="user",
        role="user",
        content="Hello, how are you?",
        timestamp="2025-01-15T10:00:00Z",
    )

    # Validate before insertion
    is_valid, error = validate_message_data(message)
    if is_valid:
        result = await db.create("message", message)
    else:
        print(f"Validation error: {error}")
```

### Common Queries

#### Find Orphaned Messages

```python
from riff.surrealdb import build_orphaned_messages_query

session_id = "550e8400-e29b-41d4-a716-446655440000"
query = build_orphaned_messages_query(session_id)
orphans = await db.query(query)
```

#### Get Session Statistics

```python
from riff.surrealdb import build_session_stats_query

session_id = "550e8400-e29b-41d4-a716-446655440000"
query = build_session_stats_query(session_id)
stats = await db.query(query)
```

#### Find High-Corruption Messages

```python
from riff.surrealdb import build_high_corruption_query

session_id = "550e8400-e29b-41d4-a716-446655440000"
query = build_high_corruption_query(session_id, threshold=0.5, limit=20)
corrupted = await db.query(query)
```

#### Time-Range Query

```python
from riff.surrealdb import build_time_range_query

session_id = "550e8400-e29b-41d4-a716-446655440000"
start = "2025-01-15T00:00:00Z"
end = "2025-01-15T23:59:59Z"
query = build_time_range_query(session_id, start, end)
messages = await db.query(query)
```

#### Full-Text Search

```sql
SELECT * FROM message
WHERE session_id = $session_id
  AND content @@ 'search terms'
ORDER BY timestamp DESC;
```

#### Graph Traversal (Get Message with Relationships)

```sql
SELECT *,
  <-message_parent_of<-message as children,
  ->message_parent_of->message as parent
FROM message:$message_id;
```

## Data Migration

### From Existing JSON/SQLite

```python
from riff.surrealdb import prepare_message_record, validate_message_data
from surrealdb import Surreal
import json

async def migrate_session(session_file: str, db: Surreal):
    """Migrate session from JSON to SurrealDB."""

    # Load existing session
    with open(session_file) as f:
        session_data = json.load(f)

    # Create session record
    session = prepare_session_record(
        session_id=session_data["uuid"],
        message_count=len(session_data["messages"]),
    )
    await db.create("session", session)

    # Migrate messages
    for msg in session_data["messages"]:
        message = prepare_message_record(
            session_id=session_data["uuid"],
            message_uuid=msg["uuid"],
            message_type=msg["type"],
            role=msg["role"],
            content=msg["content"],
            timestamp=msg["timestamp"],
            parent_uuid=msg.get("parent_uuid"),
        )

        # Validate and insert
        is_valid, error = validate_message_data(message)
        if is_valid:
            await db.create("message", message)
        else:
            print(f"Skipping invalid message: {error}")
```

## Backup and Restore

### Backup

```bash
surreal export --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  backup.surql
```

### Restore

```bash
surreal import --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  backup.surql
```

## Performance Tuning

### Index Monitoring

```sql
-- Check index usage
EXPLAIN SELECT * FROM message
WHERE session_id = $session_id AND is_orphaned = true;

-- Analyze query performance
INFO FOR INDEX message_content_idx ON message;
```

### BM25 Parameter Tuning

The full-text search uses BM25(1.2, 0.75) by default. Adjust these parameters in `schema.sql` based on your search quality needs:

- **k1** (default: 1.2): Controls term frequency saturation
- **b** (default: 0.75): Controls document length normalization

### Partitioning Strategy

For very large datasets (millions of messages), consider:

1. **Session-based partitioning**: Split by `session_id` hash
2. **Time-based partitioning**: Separate historical vs. recent data
3. **Corruption-based views**: Materialized views for high-corruption messages

## Integration with riff-cli

### Phase 6B: Conversation Graph

```python
from riff.surrealdb import SCHEMA_DICT, get_schema_sql
from riff.graph import ConversationGraph

# Initialize graph with SurrealDB backend
graph = ConversationGraph(backend="surrealdb", schema=SCHEMA_DICT)

# Load session
await graph.load_session("550e8400-e29b-41d4-a716-446655440000")

# Detect orphans
orphans = await graph.detect_orphans()

# Visualize in TUI
from riff.tui import launch_tui
launch_tui(graph)
```

## Schema Evolution

### Version 1.0.0 (Current)

- Initial schema with session/message/thread tables
- Full-text search on message content
- Corruption detection support
- DAG-based message relationships

### Future Enhancements

- **Version 1.1.0**: Add semantic embeddings for message similarity
- **Version 1.2.0**: Add user preferences and session metadata
- **Version 2.0.0**: Add cross-session topic clustering

## Troubleshooting

### Common Issues

#### 1. Connection Refused

```bash
# Check SurrealDB is running
surreal start --bind 0.0.0.0:8000 --user root --pass root
```

#### 2. Schema Import Fails

```bash
# Verify SQL syntax
cat schema.sql | surreal sql --conn http://localhost:8000 \
  --user root --pass root --ns nabi --db conversations
```

#### 3. Full-Text Search Not Working

```sql
-- Verify analyzer exists
INFO FOR DB;

-- Rebuild search index
DEFINE INDEX message_content_idx ON TABLE message
COLUMNS content SEARCH ANALYZER message_search BM25(1.2, 0.75);
```

## References

- [SurrealDB Documentation](https://surrealdb.com/docs)
- [SurrealQL Reference](https://surrealdb.com/docs/surrealql)
- [Full-Text Search](https://surrealdb.com/docs/surrealql/statements/define/indexes#full-text-search)
- [Graph Relations](https://surrealdb.com/docs/surrealql/statements/relate)

## License

Part of riff-cli. See project LICENSE.
