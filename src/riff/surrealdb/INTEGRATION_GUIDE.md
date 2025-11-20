# Phase 6B Integration Guide

How to integrate the SurrealDB schema with riff-cli's conversation graph visualization.

## Overview

This guide walks through integrating the SurrealDB schema with Phase 6B of riff-cli for:
- Conversation graph storage
- Orphan detection and repair
- Time-based filtering
- DAG visualization in TUI

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
# Add to pyproject.toml
[tool.uv.dependencies]
surrealdb = "^0.3.2"

# Or install directly
uv pip install surrealdb
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

# Verify
surreal sql --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations

# In SQL shell:
INFO FOR DB;
```

## Architecture Integration

### Current Architecture (Phase 6A)

```
riff-cli/
├── src/riff/
│   ├── backends/           # Storage backends (JSON, SQLite)
│   ├── graph/              # Conversation graph logic
│   │   ├── builder.py      # Graph construction
│   │   ├── analyzer.py     # Corruption detection
│   │   └── visualizer.py   # DAG rendering
│   └── tui/                # Terminal UI
```

### New Architecture (Phase 6B)

```
riff-cli/
├── src/riff/
│   ├── backends/
│   │   ├── json.py         # Existing JSON backend
│   │   ├── sqlite.py       # Existing SQLite backend
│   │   └── surrealdb.py    # NEW: SurrealDB backend
│   ├── graph/
│   │   ├── builder.py      # Uses backend abstraction
│   │   ├── analyzer.py     # Enhanced with SurrealDB queries
│   │   └── visualizer.py   # Unchanged
│   ├── surrealdb/          # NEW: Schema and utilities
│   │   ├── schema.sql
│   │   ├── schema_utils.py
│   │   └── ...
│   └── tui/                # Enhanced with SurrealDB features
```

## Implementation Steps

### Step 1: Create SurrealDB Backend

Create `/Users/tryk/nabia/tools/riff-cli/src/riff/backends/surrealdb_backend.py`:

```python
"""SurrealDB backend for conversation storage."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from surrealdb import Surreal

from ..surrealdb import (
    prepare_session_record,
    prepare_message_record,
    prepare_thread_record,
    validate_message_data,
    build_orphaned_messages_query,
    build_session_stats_query,
)


class SurrealDBBackend:
    """SurrealDB storage backend for conversations."""

    def __init__(
        self,
        url: str = "ws://localhost:8000/rpc",
        namespace: str = "nabi",
        database: str = "conversations",
        username: str = "root",
        password: str = "root",
    ):
        """Initialize SurrealDB backend.

        Args:
            url: SurrealDB WebSocket URL
            namespace: Database namespace
            database: Database name
            username: Auth username
            password: Auth password
        """
        self.url = url
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.db: Optional[Surreal] = None

    async def connect(self):
        """Establish connection to SurrealDB."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.signin({"user": self.username, "pass": self.password})
        await self.db.use(self.namespace, self.database)

    async def disconnect(self):
        """Close connection to SurrealDB."""
        if self.db:
            await self.db.close()

    async def store_session(
        self, session_id: str, messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store a conversation session.

        Args:
            session_id: Session UUID
            messages: List of message dictionaries

        Returns:
            Session statistics
        """
        if not self.db:
            await self.connect()

        # Create session record
        session = prepare_session_record(
            session_id=session_id,
            message_count=len(messages),
            thread_count=0,  # Will be calculated
        )
        await self.db.create("session", session)

        # Create main thread
        thread = prepare_thread_record(
            session_id=session_id, thread_type="main", message_count=len(messages)
        )
        thread_result = await self.db.create("thread", thread)
        thread_id = thread_result[0]["id"]

        # Store messages
        for msg in messages:
            message = prepare_message_record(
                session_id=session_id,
                message_uuid=msg["uuid"],
                message_type=msg.get("type", "user"),
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                parent_uuid=msg.get("parent_uuid"),
                thread_id=thread_id,
                is_orphaned=msg.get("is_orphaned", False),
                corruption_score=msg.get("corruption_score", 0.0),
            )

            is_valid, error = validate_message_data(message)
            if is_valid:
                await self.db.create("message", message)
            else:
                print(f"Validation error for {msg['uuid']}: {error}")

        # Update session counts
        await self.db.query(
            f"""
            UPDATE session
            SET thread_count = 1
            WHERE session_id = '{session_id}';
        """
        )

        # Get statistics
        stats_query = build_session_stats_query(session_id)
        stats = await self.db.query(stats_query)

        return stats[0]["result"][0] if stats[0]["result"] else {}

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieve a conversation session.

        Args:
            session_id: Session UUID

        Returns:
            Session data with messages
        """
        if not self.db:
            await self.connect()

        # Get session
        session_query = f"""
            SELECT * FROM session WHERE session_id = '{session_id}';
        """
        session_result = await self.db.query(session_query)

        if not session_result[0]["result"]:
            raise ValueError(f"Session not found: {session_id}")

        session = session_result[0]["result"][0]

        # Get messages
        messages_query = f"""
            SELECT * FROM message
            WHERE session_id = '{session_id}'
            ORDER BY timestamp ASC;
        """
        messages_result = await self.db.query(messages_query)
        messages = messages_result[0]["result"]

        # Get threads
        threads_query = f"""
            SELECT * FROM thread WHERE session_id = '{session_id}';
        """
        threads_result = await self.db.query(threads_query)
        threads = threads_result[0]["result"]

        return {"session": session, "messages": messages, "threads": threads}

    async def find_orphans(self, session_id: str) -> List[Dict[str, Any]]:
        """Find orphaned messages in session.

        Args:
            session_id: Session UUID

        Returns:
            List of orphaned messages
        """
        if not self.db:
            await self.connect()

        query = build_orphaned_messages_query(session_id)
        result = await self.db.query(query)
        return result[0]["result"] if result[0]["result"] else []

    async def search_messages(
        self, session_id: str, query: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Full-text search on message content.

        Args:
            session_id: Session UUID
            query: Search query
            limit: Maximum results

        Returns:
            List of matching messages
        """
        if not self.db:
            await self.connect()

        search_query = f"""
            SELECT * FROM message
            WHERE session_id = '{session_id}'
              AND content @@ '{query}'
            ORDER BY timestamp DESC
            LIMIT {limit};
        """
        result = await self.db.query(search_query)
        return result[0]["result"] if result[0]["result"] else []

    async def get_time_range(
        self, session_id: str, start_time: str, end_time: str
    ) -> List[Dict[str, Any]]:
        """Get messages in time range.

        Args:
            session_id: Session UUID
            start_time: Start timestamp (ISO 8601)
            end_time: End timestamp (ISO 8601)

        Returns:
            List of messages in range
        """
        if not self.db:
            await self.connect()

        query = f"""
            SELECT * FROM message
            WHERE session_id = '{session_id}'
              AND timestamp >= '{start_time}'
              AND timestamp <= '{end_time}'
            ORDER BY timestamp ASC;
        """
        result = await self.db.query(query)
        return result[0]["result"] if result[0]["result"] else []
```

### Step 2: Update Graph Builder

Update `/Users/tryk/nabia/tools/riff-cli/src/riff/graph/builder.py` to use backends:

```python
"""Graph builder with backend abstraction."""

from typing import Optional
from ..backends.json import JSONBackend
from ..backends.sqlite import SQLiteBackend
from ..backends.surrealdb_backend import SurrealDBBackend


class ConversationGraphBuilder:
    """Builds conversation graphs from various backends."""

    def __init__(self, backend: str = "json"):
        """Initialize builder with specified backend.

        Args:
            backend: Backend type ("json", "sqlite", "surrealdb")
        """
        self.backend_type = backend
        self.backend = self._create_backend(backend)

    def _create_backend(self, backend: str):
        """Create backend instance.

        Args:
            backend: Backend type

        Returns:
            Backend instance
        """
        if backend == "json":
            return JSONBackend()
        elif backend == "sqlite":
            return SQLiteBackend()
        elif backend == "surrealdb":
            return SurrealDBBackend()
        else:
            raise ValueError(f"Unknown backend: {backend}")

    async def load_session(self, session_id: str):
        """Load session from backend.

        Args:
            session_id: Session UUID
        """
        if self.backend_type == "surrealdb":
            data = await self.backend.get_session(session_id)
            return data
        else:
            # Existing JSON/SQLite logic
            return self.backend.load_session(session_id)

    async def detect_orphans(self, session_id: str):
        """Detect orphaned messages.

        Args:
            session_id: Session UUID
        """
        if self.backend_type == "surrealdb":
            return await self.backend.find_orphans(session_id)
        else:
            # Existing detection logic
            return self._detect_orphans_legacy(session_id)
```

### Step 3: Update CLI Commands

Add SurrealDB option to CLI in `/Users/tryk/nabia/tools/riff-cli/src/riff/cli.py`:

```python
@click.command()
@click.argument("session_id")
@click.option(
    "--backend",
    type=click.Choice(["json", "sqlite", "surrealdb"]),
    default="json",
    help="Storage backend to use",
)
@click.option(
    "--surrealdb-url",
    default="ws://localhost:8000/rpc",
    help="SurrealDB connection URL",
)
async def visualize(session_id: str, backend: str, surrealdb_url: str):
    """Visualize conversation graph."""
    builder = ConversationGraphBuilder(backend=backend)

    if backend == "surrealdb":
        builder.backend.url = surrealdb_url

    data = await builder.load_session(session_id)

    # Launch TUI with data
    from .tui import launch_tui
    launch_tui(data)
```

### Step 4: Add Configuration

Add SurrealDB config to `~/.riff/config.toml`:

```toml
[storage]
default_backend = "surrealdb"

[storage.surrealdb]
url = "ws://localhost:8000/rpc"
namespace = "nabi"
database = "conversations"
username = "root"
password = "root"
```

## Testing Integration

### 1. Unit Tests

```bash
# Test schema utilities
pytest src/riff/surrealdb/test_schema.py -v

# Test backend integration
pytest src/riff/backends/test_surrealdb_backend.py -v
```

### 2. Manual Testing

```bash
# Start SurrealDB
surreal start --bind 0.0.0.0:8000 --user root --pass root

# Import sample session
python -m riff.surrealdb.example_usage

# Visualize with riff
riff visualize 550e8400-e29b-41d4-a716-446655440000 --backend surrealdb
```

### 3. Performance Testing

```bash
# Load 1000 messages
python scripts/benchmark_surrealdb.py --messages 1000

# Measure query performance
python scripts/benchmark_queries.py --session-id <uuid>
```

## Migration from JSON/SQLite

### Migrate Existing Sessions

```python
"""Migrate sessions from JSON to SurrealDB."""

import asyncio
import json
from pathlib import Path
from riff.backends.surrealdb_backend import SurrealDBBackend


async def migrate_session(json_file: Path, backend: SurrealDBBackend):
    """Migrate a single session."""
    with open(json_file) as f:
        session_data = json.load(f)

    await backend.store_session(
        session_id=session_data["uuid"], messages=session_data["messages"]
    )
    print(f"✓ Migrated: {json_file.name}")


async def migrate_all(sessions_dir: Path):
    """Migrate all sessions in directory."""
    backend = SurrealDBBackend()
    await backend.connect()

    for json_file in sessions_dir.glob("*.json"):
        try:
            await migrate_session(json_file, backend)
        except Exception as e:
            print(f"✗ Failed {json_file.name}: {e}")

    await backend.disconnect()


if __name__ == "__main__":
    sessions_dir = Path("~/.riff/sessions").expanduser()
    asyncio.run(migrate_all(sessions_dir))
```

## Production Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    command: start --bind 0.0.0.0:8000 --user root --pass ${SURREAL_PASS}
    ports:
      - "8000:8000"
    volumes:
      - surreal_data:/data
    environment:
      - SURREAL_PATH=/data/riff.db
    restart: unless-stopped

  riff-api:
    build: .
    depends_on:
      - surrealdb
    environment:
      - SURREALDB_URL=ws://surrealdb:8000/rpc
      - SURREALDB_USER=root
      - SURREALDB_PASS=${SURREAL_PASS}
    ports:
      - "8080:8080"

volumes:
  surreal_data:
```

### Environment Variables

```bash
# .env
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_NAMESPACE=nabi
SURREALDB_DATABASE=conversations
SURREALDB_USER=root
SURREALDB_PASS=your-secure-password
```

## Monitoring and Maintenance

### Health Checks

```python
async def health_check(backend: SurrealDBBackend) -> bool:
    """Check SurrealDB connectivity."""
    try:
        await backend.connect()
        result = await backend.db.query("INFO FOR DB;")
        return bool(result)
    except Exception:
        return False
```

### Backup Strategy

```bash
#!/bin/bash
# backup-surrealdb.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$HOME/.riff/backups"
mkdir -p "$BACKUP_DIR"

surreal export --conn http://localhost:8000 \
  --user root --pass root \
  --ns nabi --db conversations \
  "$BACKUP_DIR/conversations_$DATE.surql"

# Keep last 7 days
find "$BACKUP_DIR" -name "conversations_*.surql" -mtime +7 -delete
```

### Performance Monitoring

```python
async def monitor_performance(backend: SurrealDBBackend):
    """Monitor query performance."""
    import time

    queries = [
        ("Session stats", build_session_stats_query),
        ("Find orphans", build_orphaned_messages_query),
        ("High corruption", lambda sid: build_high_corruption_query(sid, 0.5)),
    ]

    for name, query_fn in queries:
        start = time.time()
        query = query_fn(session_id)
        await backend.db.query(query)
        elapsed = time.time() - start
        print(f"{name}: {elapsed:.3f}s")
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check SurrealDB is running: `docker ps` or `ps aux | grep surreal`
   - Verify port is accessible: `curl http://localhost:8000/health`

2. **Schema Import Fails**
   - Validate SQL syntax: `cat schema.sql | surreal sql`
   - Check namespace/database exist: `INFO FOR DB;`

3. **Slow Queries**
   - Verify indexes: `INFO FOR TABLE message;`
   - Analyze query plan: `EXPLAIN <query>;`

4. **Data Validation Errors**
   - Check constraints: Review `validate_*_data()` functions
   - Validate timestamps: Ensure ISO 8601 format

## Next Steps

1. **Complete Backend Implementation**: Finish `surrealdb_backend.py`
2. **Add TUI Features**: Integrate SurrealDB queries into TUI navigation
3. **Performance Optimization**: Add caching layer for frequent queries
4. **Advanced Features**: Add semantic search with embeddings

## References

- [SurrealDB Documentation](https://surrealdb.com/docs)
- [Python Client](https://github.com/surrealdb/surrealdb.py)
- [riff-cli Phase 6B Spec](../docs/TIME_FILTERING.md)
