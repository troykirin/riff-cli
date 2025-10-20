"""
Test suite for SurrealDB storage operations and immutable event store.

Tests loading sessions, saving repair events, immutability enforcement,
event replay, and error handling.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid

from riff.graph.models import Message, MessageType, Session, Thread, ThreadType


# ============================================================================
# TEST LOADING SESSIONS FROM SURREALDB
# ============================================================================

@pytest.mark.asyncio
async def test_load_session_from_surrealdb(mock_surrealdb_client, sample_session_with_corruption):
    """Test loading a session from SurrealDB storage."""
    # Setup: Store session data
    session = sample_session_with_corruption
    await mock_surrealdb_client.create("sessions", {
        "session_id": session.session_id,
        "message_count": session.message_count,
        "thread_count": session.thread_count,
        "corruption_score": session.corruption_score,
        "metadata": session.metadata
    })

    # Store messages
    for msg in session.messages:
        await mock_surrealdb_client.create("messages", {
            "message_uuid": msg.uuid,
            "session_id": msg.session_id,
            "parent_uuid": msg.parent_uuid,
            "type": msg.type.value,
            "content": msg.content,
            "timestamp": msg.timestamp,
            "corruption_score": msg.corruption_score
        })

    # Test: Load session
    loaded_session = await mock_surrealdb_client.select("sessions", session.session_id)
    assert loaded_session is not None
    assert loaded_session["session_id"] == session.session_id
    assert loaded_session["corruption_score"] == session.corruption_score

    # Verify messages loaded
    messages = await mock_surrealdb_client.select("messages")
    assert len(messages) == 4
    msg_uuids = [m["message_uuid"] for m in messages]
    assert "msg-001" in msg_uuids
    assert "msg-003" in msg_uuids  # Include orphaned


@pytest.mark.asyncio
async def test_save_repair_event_immutable(mock_surrealdb_client, sample_repair_event):
    """Test saving repair events as immutable records."""
    event = sample_repair_event

    # Calculate hash for immutability
    event["hash"] = calculate_event_hash(event)

    # Test: Save event
    result = await mock_surrealdb_client.create("repair_events", event)
    assert result is not None
    assert event["event_id"] in result["id"]

    # Verify immutability - attempt to save same event should fail
    with pytest.raises(ValueError, match="already exists"):
        await mock_surrealdb_client.create("repair_events", event)

    # Verify event in log
    assert len(mock_surrealdb_client.data["event_log"]) == 1
    logged_event = mock_surrealdb_client.data["event_log"][0]
    assert logged_event["event_type"] == "REPAIR_PARENT"
    assert logged_event["hash"] == event["hash"]


@pytest.mark.asyncio
async def test_cannot_update_repair_event(mock_surrealdb_client, sample_repair_event):
    """Test that repair events cannot be updated (immutability)."""
    event = sample_repair_event
    event["hash"] = calculate_event_hash(event)

    # Save event
    await mock_surrealdb_client.create("repair_events", event)

    # Test: Attempt to update should fail
    with pytest.raises(ValueError, match="Cannot update immutable"):
        await mock_surrealdb_client.query(
            "UPDATE repair_events SET corruption_score = 0.5"
        )

    # Verify original remains unchanged
    stored = mock_surrealdb_client.data["repair_events"][event["event_id"]]
    assert stored["hash"] == event["hash"]
    assert "corruption_score" not in stored


@pytest.mark.asyncio
async def test_materialize_session_from_events(mock_surrealdb_client, sample_session_with_corruption):
    """Test materializing current session state from event log."""
    session = sample_session_with_corruption

    # Create sequence of repair events
    events = [
        {
            "event_id": f"evt-001",
            "event_type": "SESSION_CREATED",
            "session_id": session.session_id,
            "timestamp": "2024-01-01T09:00:00Z",
            "data": {
                "message_count": 3,
                "corruption_score": 0.8
            }
        },
        {
            "event_id": f"evt-002",
            "event_type": "REPAIR_PARENT",
            "session_id": session.session_id,
            "message_uuid": "msg-003",
            "timestamp": "2024-01-01T11:00:00Z",
            "before_state": {"parent_uuid": "msg-999", "corruption_score": 0.8},
            "after_state": {"parent_uuid": "msg-002", "corruption_score": 0.0}
        },
        {
            "event_id": f"evt-003",
            "event_type": "SESSION_UPDATED",
            "session_id": session.session_id,
            "timestamp": "2024-01-01T11:00:30Z",
            "data": {
                "message_count": 4,
                "corruption_score": 0.0  # Fixed
            }
        }
    ]

    # Save events in order
    for event in events:
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

    # Test: Materialize current state
    event_log = mock_surrealdb_client.data["event_log"]
    assert len(event_log) == 3

    # Apply events to build current state
    materialized_state = {}
    for event in event_log:
        if event["event_type"] == "SESSION_CREATED":
            materialized_state = event["data"].copy()
        elif event["event_type"] == "SESSION_UPDATED":
            materialized_state.update(event["data"])
        elif event["event_type"] == "REPAIR_PARENT":
            materialized_state["last_repair"] = event["timestamp"]

    assert materialized_state["corruption_score"] == 0.0
    assert materialized_state["message_count"] == 4
    assert "last_repair" in materialized_state


@pytest.mark.asyncio
async def test_replay_events_in_order(mock_surrealdb_client):
    """Test replaying events maintains chronological order."""
    session_id = "test-session-replay"

    # Create events with timestamps
    base_time = datetime(2024, 1, 1, 10, 0, 0)
    events = []
    for i in range(5):
        event = {
            "event_id": f"evt-{i:03d}",
            "event_type": "MESSAGE_ADDED",
            "session_id": session_id,
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "data": {"message_index": i}
        }
        events.append(event)

    # Save events out of order
    for event in [events[2], events[0], events[4], events[1], events[3]]:
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

    # Test: Events should be replayable in timestamp order
    event_log = sorted(
        mock_surrealdb_client.data["event_log"],
        key=lambda e: e["timestamp"]
    )

    for i, event in enumerate(event_log):
        assert event["data"]["message_index"] == i

    # Verify order preservation
    timestamps = [e["timestamp"] for e in event_log]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_session_hash_consistency(mock_surrealdb_client, sample_session_with_corruption):
    """Test that session hashes remain consistent across operations."""
    session = sample_session_with_corruption

    def calculate_session_hash(session_data: dict) -> str:
        """Calculate deterministic hash for session state."""
        # Sort and serialize for consistent hashing
        content = json.dumps(session_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    # Initial session state
    initial_state = {
        "session_id": session.session_id,
        "message_count": session.message_count,
        "corruption_score": session.corruption_score
    }
    initial_hash = calculate_session_hash(initial_state)

    # Create event with hash
    event = {
        "event_id": "evt-001",
        "event_type": "SESSION_SNAPSHOT",
        "session_id": session.session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "state_hash": initial_hash,
        "data": initial_state
    }
    event["hash"] = calculate_event_hash(event)

    await mock_surrealdb_client.create("repair_events", event)

    # Test: Reconstructed state should have same hash
    stored_event = mock_surrealdb_client.data["repair_events"]["evt-001"]
    reconstructed_hash = calculate_session_hash(stored_event["data"])

    assert reconstructed_hash == initial_hash
    assert stored_event["state_hash"] == initial_hash


@pytest.mark.asyncio
async def test_surrealdb_connection_error_handling(mock_surrealdb_client):
    """Test handling of SurrealDB connection errors."""
    # Simulate connection error
    mock_surrealdb_client.connection_error = True

    # Test: Connection failure
    with pytest.raises(ConnectionError, match="Failed to connect"):
        await mock_surrealdb_client.connect("ws://localhost:8000")

    # Test: Query failure with lost connection
    mock_surrealdb_client.connection_error = False
    await mock_surrealdb_client.connect("ws://localhost:8000")

    # Lose connection after connecting
    mock_surrealdb_client.connection_error = True

    with pytest.raises(ConnectionError, match="Lost connection"):
        await mock_surrealdb_client.query("SELECT * FROM sessions")

    # Test: Graceful recovery
    mock_surrealdb_client.connection_error = False
    result = await mock_surrealdb_client.query("SELECT * FROM sessions")
    assert result == []  # Empty but successful


def calculate_event_hash(event: dict) -> str:
    """Calculate deterministic hash for an event."""
    hashable = {k: v for k, v in event.items() if k not in ["hash", "timestamp"]}
    content = json.dumps(hashable, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()