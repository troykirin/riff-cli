# SurrealDB Schema Reference

Quick reference for Phase 6B conversation storage schema.

## Schema Dictionary (Python)

The complete schema is available programmatically via `SCHEMA_DICT` in `schema_utils.py`:

```python
from riff.surrealdb import SCHEMA_DICT

# Access schema version
version = SCHEMA_DICT["version"]  # "1.0.0"

# Access table definitions
session_schema = SCHEMA_DICT["tables"]["session"]
message_schema = SCHEMA_DICT["tables"]["message"]
thread_schema = SCHEMA_DICT["tables"]["thread"]

# Access relation definitions
parent_relation = SCHEMA_DICT["relations"]["message_parent_of"]

# Access analyzer definitions
search_analyzer = SCHEMA_DICT["analyzers"]["message_search"]
```

## Schema Structure

### Version
- **Version**: 1.0.0
- **Namespace**: nabi
- **Database**: conversations

### Tables

#### session
```python
{
    "type": "SCHEMAFULL",
    "fields": {
        "session_id": {
            "type": "string",
            "required": True,
            "unique": True,
            "description": "Claude session UUID"
        },
        "message_count": {
            "type": "int",
            "default": 0,
            "min": 0,
            "description": "Total messages in session"
        },
        "thread_count": {
            "type": "int",
            "default": 0,
            "min": 0,
            "description": "Total threads in session"
        },
        "corruption_score": {
            "type": "float",
            "default": 0.0,
            "min": 0.0,
            "max": 1.0,
            "description": "Session-level corruption score (0.0-1.0)"
        },
        "last_updated": {
            "type": "datetime",
            "required": True,
            "description": "Last modification timestamp"
        },
        "created_at": {
            "type": "datetime",
            "required": True,
            "description": "Session creation timestamp"
        }
    },
    "indexes": ["session_id", "last_updated"]
}
```

#### thread
```python
{
    "type": "SCHEMAFULL",
    "fields": {
        "session_id": {
            "type": "string",
            "required": True,
            "description": "Parent session ID"
        },
        "thread_type": {
            "type": "string",
            "required": True,
            "allowed_values": ["main", "side_discussion", "orphaned"],
            "description": "Thread classification"
        },
        "message_count": {
            "type": "int",
            "default": 0,
            "min": 0,
            "description": "Total messages in thread"
        },
        "topic": {
            "type": "option<string>",
            "required": False,
            "description": "Semantic topic extracted from messages"
        },
        "created_at": {
            "type": "datetime",
            "required": True,
            "description": "Thread creation timestamp"
        }
    },
    "indexes": ["session_id", "thread_type", "session_id,thread_type"]
}
```

#### message
```python
{
    "type": "SCHEMAFULL",
    "fields": {
        "session_id": {
            "type": "string",
            "required": True,
            "description": "Parent session ID"
        },
        "message_uuid": {
            "type": "string",
            "required": True,
            "description": "Unique message identifier"
        },
        "parent_uuid": {
            "type": "option<string>",
            "required": False,
            "description": "Parent message UUID (null for roots)"
        },
        "message_type": {
            "type": "string",
            "required": True,
            "allowed_values": ["user", "assistant", "system"],
            "description": "Message type classification"
        },
        "role": {
            "type": "string",
            "required": True,
            "allowed_values": ["user", "assistant"],
            "description": "Message role in conversation"
        },
        "content": {
            "type": "string",
            "required": True,
            "searchable": True,
            "description": "Message content text"
        },
        "timestamp": {
            "type": "datetime",
            "required": True,
            "description": "Message timestamp"
        },
        "thread_id": {
            "type": "option<string>",
            "required": False,
            "description": "Parent thread ID"
        },
        "is_orphaned": {
            "type": "bool",
            "default": False,
            "description": "Whether message lacks valid parent"
        },
        "corruption_score": {
            "type": "float",
            "default": 0.0,
            "min": 0.0,
            "max": 1.0,
            "description": "Message-level corruption score"
        },
        "created_at": {
            "type": "datetime",
            "required": True,
            "description": "Record creation timestamp"
        }
    },
    "indexes": [
        "message_uuid",
        "session_id",
        "parent_uuid",
        "thread_id",
        "timestamp",
        "is_orphaned",
        "corruption_score",
        "session_id,timestamp"
    ],
    "full_text_indexes": ["content"]
}
```

### Relations

#### message_parent_of
```python
{
    "from": "message",
    "to": "message",
    "type": "one_to_many",
    "description": "Parent-child relationship in conversation DAG"
}
```

#### message_belongs_to_thread
```python
{
    "from": "message",
    "to": "thread",
    "type": "many_to_one",
    "properties": {
        "position": {
            "type": "int",
            "min": 0,
            "description": "Message position within thread"
        }
    },
    "description": "Links messages to their containing thread"
}
```

#### thread_belongs_to_session
```python
{
    "from": "thread",
    "to": "session",
    "type": "many_to_one",
    "description": "Links threads to their parent session"
}
```

#### session_contains_message
```python
{
    "from": "session",
    "to": "message",
    "type": "one_to_many",
    "description": "Direct session-to-message link for fast queries"
}
```

### Analyzers

#### message_search
```python
{
    "tokenizers": ["blank", "class"],
    "filters": ["lowercase", "snowball(english)"],
    "description": "Full-text search analyzer for message content"
}
```

## Quick Access Functions

### Get Schema Components

```python
from riff.surrealdb.schema_utils import (
    export_schema_as_dict,
    get_table_schema,
    get_relation_schema,
    get_schema_sql
)

# Export complete schema as dict
schema = export_schema_as_dict()

# Get specific table schema
message_schema = get_table_schema("message")
session_schema = get_table_schema("session")
thread_schema = get_table_schema("thread")

# Get specific relation schema
parent_relation = get_relation_schema("message_parent_of")

# Get SQL schema
sql_schema = get_schema_sql()
```

### Validation

```python
from riff.surrealdb.schema_utils import (
    validate_session_data,
    validate_message_data,
    validate_thread_data
)

# Validate session data
is_valid, error = validate_session_data(session_dict)
if not is_valid:
    print(f"Validation error: {error}")

# Validate message data
is_valid, error = validate_message_data(message_dict)
if not is_valid:
    print(f"Validation error: {error}")

# Validate thread data
is_valid, error = validate_thread_data(thread_dict)
if not is_valid:
    print(f"Validation error: {error}")
```

### Record Preparation

```python
from riff.surrealdb.schema_utils import (
    prepare_session_record,
    prepare_message_record,
    prepare_thread_record
)

# Prepare session record
session = prepare_session_record(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    message_count=10,
    thread_count=2,
    corruption_score=0.1
)

# Prepare message record
message = prepare_message_record(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    message_uuid="msg-001",
    message_type="user",
    role="user",
    content="Hello, world!",
    timestamp="2025-01-15T10:00:00Z",
    parent_uuid="msg-000",
    thread_id="thread-001"
)

# Prepare thread record
thread = prepare_thread_record(
    session_id="550e8400-e29b-41d4-a716-446655440000",
    thread_type="main",
    message_count=5,
    topic="AI Discussion"
)
```

### Query Builders

```python
from riff.surrealdb.schema_utils import (
    build_orphaned_messages_query,
    build_session_stats_query,
    build_parent_candidates_query,
    build_high_corruption_query,
    build_time_range_query
)

# Find orphaned messages
query = build_orphaned_messages_query(session_id)

# Get session statistics
query = build_session_stats_query(session_id)

# Find parent candidates for orphan
query = build_parent_candidates_query(
    session_id,
    orphan_timestamp="2025-01-15T10:00:00Z",
    limit=5
)

# Get high-corruption messages
query = build_high_corruption_query(
    session_id,
    threshold=0.5,
    limit=20
)

# Time-range query
query = build_time_range_query(
    session_id,
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T23:59:59Z"
)
```

## Field Constraints Summary

### session
| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| session_id | string | Yes | - | Non-empty, unique |
| message_count | int | No | 0 | >= 0 |
| thread_count | int | No | 0 | >= 0 |
| corruption_score | float | No | 0.0 | 0.0 <= x <= 1.0 |
| last_updated | datetime | Yes | - | ISO 8601 |
| created_at | datetime | Yes | - | ISO 8601 |

### thread
| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| session_id | string | Yes | - | Non-empty |
| thread_type | string | Yes | - | main, side_discussion, orphaned |
| message_count | int | No | 0 | >= 0 |
| topic | option<string> | No | None | - |
| created_at | datetime | Yes | - | ISO 8601 |

### message
| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| session_id | string | Yes | - | Non-empty |
| message_uuid | string | Yes | - | Non-empty |
| parent_uuid | option<string> | No | None | - |
| message_type | string | Yes | - | user, assistant, system |
| role | string | Yes | - | user, assistant |
| content | string | Yes | - | Non-empty, searchable |
| timestamp | datetime | Yes | - | ISO 8601 |
| thread_id | option<string> | No | None | - |
| is_orphaned | bool | No | False | - |
| corruption_score | float | No | 0.0 | 0.0 <= x <= 1.0 |
| created_at | datetime | Yes | - | ISO 8601 |

## Index Strategy

### Primary Indexes
- **session**: `session_id` (unique), `last_updated`
- **thread**: `session_id`, `thread_type`, composite `(session_id, thread_type)`
- **message**: `message_uuid`, `session_id`, `parent_uuid`, `thread_id`, `timestamp`, `is_orphaned`, `corruption_score`, composite `(session_id, timestamp)`

### Full-Text Indexes
- **message.content**: BM25(1.2, 0.75) with English snowball stemming

### Graph Indexes
- **Relations**: Indexes on `in` and `out` fields for fast graph traversal

## Files in Package

```
src/riff/surrealdb/
├── __init__.py              # Package exports
├── schema.sql               # Complete SQL schema definition
├── schema_utils.py          # Python utilities and SCHEMA_DICT
├── test_schema.py           # pytest test suite
├── example_usage.py         # Complete usage examples
├── README.md                # User documentation
└── SCHEMA_REFERENCE.md      # This file
```

## Next Steps

1. **Import Schema**: Run `schema.sql` in SurrealDB
2. **Explore Examples**: Run `example_usage.py` to see it in action
3. **Run Tests**: Execute `pytest test_schema.py -v`
4. **Integrate**: Import utilities in Phase 6B code

See `README.md` for detailed installation and usage instructions.
