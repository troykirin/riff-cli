"""
Pytest fixtures for SurrealDB immutable event store testing.

Provides mock SurrealDB instances, sample sessions with corruption,
and utilities for testing event replay and materialization.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import uuid

from riff.graph.models import Message, MessageType, Session, Thread, ThreadType


# ============================================================================
# MOCK SURREALDB HTTP CLIENT
# ============================================================================

class MockSurrealDBClient:
    """Mock SurrealDB HTTP client for testing."""

    def __init__(self):
        """Initialize mock client with in-memory storage."""
        self.data = {
            "sessions": {},
            "messages": {},
            "threads": {},
            "repair_events": {},
            "event_log": []
        }
        self.connection_error = False
        self.query_history = []

    async def connect(self, url: str) -> None:
        """Mock connection to SurrealDB."""
        if self.connection_error:
            raise ConnectionError("Failed to connect to SurrealDB")

    async def use(self, namespace: str, database: str) -> None:
        """Mock namespace/database selection."""
        self.namespace = namespace
        self.database = database

    async def query(self, sql: str, vars: Optional[Dict] = None) -> List[Dict]:
        """Mock SQL query execution."""
        self.query_history.append({"sql": sql, "vars": vars})

        if self.connection_error:
            raise ConnectionError("Lost connection to SurrealDB")

        # Simple query parsing for testing
        if "SELECT * FROM repair_events" in sql:
            return list(self.data["repair_events"].values())
        elif "INSERT INTO repair_events" in sql:
            # Simulate immutability - prevent updates
            return [{"status": "ok", "id": f"repair_events:{uuid.uuid4()}"}]
        elif "UPDATE repair_events" in sql:
            # Immutable - updates should fail
            raise ValueError("Cannot update immutable repair events")

        return []

    async def create(self, table: str, data: Dict) -> Dict:
        """Mock record creation."""
        if table == "repair_events":
            # Enforce immutability
            event_id = data.get("event_id", str(uuid.uuid4()))
            if event_id in self.data["repair_events"]:
                raise ValueError(f"Event {event_id} already exists (immutable)")
            self.data["repair_events"][event_id] = data
            self.data["event_log"].append(data)
            return {"id": f"repair_events:{event_id}", **data}

        record_id = str(uuid.uuid4())
        self.data[table][record_id] = data
        return {"id": f"{table}:{record_id}", **data}

    async def select(self, table: str, record_id: Optional[str] = None) -> Any:
        """Mock record selection."""
        if record_id:
            return self.data.get(table, {}).get(record_id)
        return list(self.data.get(table, {}).values())


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def mock_surrealdb_client():
    """Provide mock SurrealDB client."""
    return MockSurrealDBClient()


@pytest.fixture
def sample_session_with_corruption():
    """Create a sample session with known corruption patterns."""
    session_id = "test-session-001"

    # Create messages with corruption
    messages = [
        Message(
            uuid="msg-001",
            parent_uuid=None,
            type=MessageType.USER,
            content="Hello, can you help me?",
            timestamp="2024-01-01T10:00:00Z",
            session_id=session_id,
            corruption_score=0.0
        ),
        Message(
            uuid="msg-002",
            parent_uuid="msg-001",
            type=MessageType.ASSISTANT,
            content="Of course! How can I assist?",
            timestamp="2024-01-01T10:00:30Z",
            session_id=session_id,
            corruption_score=0.0
        ),
        # Orphaned message (invalid parent)
        Message(
            uuid="msg-003",
            parent_uuid="msg-999",  # Non-existent parent
            type=MessageType.USER,
            content="This is orphaned",
            timestamp="2024-01-01T10:01:00Z",
            session_id=session_id,
            is_orphaned=True,
            corruption_score=0.8
        ),
        # Valid continuation
        Message(
            uuid="msg-004",
            parent_uuid="msg-002",
            type=MessageType.USER,
            content="Can you explain DAGs?",
            timestamp="2024-01-01T10:02:00Z",
            session_id=session_id,
            corruption_score=0.0
        )
    ]

    # Create threads
    main_thread = Thread(
        thread_id="thread-main",
        messages=[messages[0], messages[1], messages[3]],
        thread_type=ThreadType.MAIN,
        corruption_score=0.0
    )

    orphan_thread = Thread(
        thread_id="thread-orphan",
        messages=[messages[2]],
        thread_type=ThreadType.ORPHANED,
        corruption_score=0.8
    )

    return Session(
        session_id=session_id,
        messages=messages,
        threads=[main_thread],
        orphans=[orphan_thread],
        corruption_score=0.2,  # Some corruption present
        metadata={"source": "test_fixture"}
    )


@pytest.fixture
def sample_repair_event():
    """Create a sample repair event."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "REPAIR_PARENT",
        "session_id": "test-session-001",
        "message_uuid": "msg-003",
        "timestamp": datetime.utcnow().isoformat(),
        "before_state": {
            "parent_uuid": "msg-999",
            "is_orphaned": True,
            "corruption_score": 0.8
        },
        "after_state": {
            "parent_uuid": "msg-002",
            "is_orphaned": False,
            "corruption_score": 0.0
        },
        "repair_metadata": {
            "repair_type": "parent_reconnection",
            "confidence": 0.95,
            "algorithm": "temporal_proximity"
        },
        "hash": None  # Will be calculated
    }


@pytest.fixture
def mock_http_response():
    """Mock HTTP response for SurrealDB API calls."""
    class MockResponse:
        def __init__(self, json_data, status=200):
            self._json_data = json_data
            self.status = status

        async def json(self):
            return self._json_data

        async def text(self):
            return json.dumps(self._json_data)

    return MockResponse


@pytest.fixture
async def cleanup_test_data(mock_surrealdb_client):
    """Cleanup test data after each test."""
    yield
    # Clear all test data
    mock_surrealdb_client.data = {
        "sessions": {},
        "messages": {},
        "threads": {},
        "repair_events": {},
        "event_log": []
    }


def calculate_event_hash(event: Dict) -> str:
    """Calculate deterministic hash for an event."""
    # Remove mutable fields
    hashable = {k: v for k, v in event.items() if k not in ["hash", "timestamp"]}
    content = json.dumps(hashable, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()