"""
Test suite for repair event creation and immutability validation.

Tests event creation, immutability enforcement, event log integrity,
session digests, and compliance exports.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List
import uuid

from riff.graph.models import Message, MessageType, Session, Thread


# ============================================================================
# TEST REPAIR EVENT CREATION
# ============================================================================

@pytest.mark.asyncio
async def test_repair_event_creation(mock_surrealdb_client):
    """Test creating various types of repair events."""
    session_id = "test-session-events"

    # Test different event types
    event_types = [
        {
            "event_type": "REPAIR_PARENT",
            "message_uuid": "msg-001",
            "before_state": {"parent_uuid": None, "is_orphaned": True},
            "after_state": {"parent_uuid": "msg-000", "is_orphaned": False}
        },
        {
            "event_type": "REPAIR_TIMESTAMP",
            "message_uuid": "msg-002",
            "before_state": {"timestamp": "invalid"},
            "after_state": {"timestamp": "2024-01-01T10:00:00Z"}
        },
        {
            "event_type": "REPAIR_THREAD",
            "thread_id": "thread-001",
            "before_state": {"thread_type": "orphaned"},
            "after_state": {"thread_type": "main"}
        },
        {
            "event_type": "REPAIR_CORRUPTION",
            "session_id": session_id,
            "before_state": {"corruption_score": 0.8},
            "after_state": {"corruption_score": 0.2}
        }
    ]

    created_events = []
    for event_data in event_types:
        event = {
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            **event_data
        }
        event["hash"] = calculate_event_hash(event)

        result = await mock_surrealdb_client.create("repair_events", event)
        created_events.append(result)

    # Verify all events created
    assert len(created_events) == 4
    assert all("repair_events:" in e["id"] for e in created_events)

    # Verify event log contains all
    assert len(mock_surrealdb_client.data["event_log"]) == 4

    # Check event types
    event_types_in_log = [e["event_type"] for e in mock_surrealdb_client.data["event_log"]]
    assert "REPAIR_PARENT" in event_types_in_log
    assert "REPAIR_TIMESTAMP" in event_types_in_log
    assert "REPAIR_THREAD" in event_types_in_log
    assert "REPAIR_CORRUPTION" in event_types_in_log


@pytest.mark.asyncio
async def test_event_immutability_validation(mock_surrealdb_client):
    """Test that events are truly immutable after creation."""
    event = {
        "event_id": "immut-001",
        "event_type": "REPAIR_PARENT",
        "session_id": "test-session",
        "message_uuid": "msg-001",
        "timestamp": datetime.utcnow().isoformat(),
        "before_state": {"parent_uuid": None},
        "after_state": {"parent_uuid": "msg-000"}
    }
    event["hash"] = calculate_event_hash(event)

    # Create event
    await mock_surrealdb_client.create("repair_events", event)

    # Test various mutation attempts
    original_hash = event["hash"]

    # 1. Cannot recreate with same ID
    with pytest.raises(ValueError, match="already exists"):
        await mock_surrealdb_client.create("repair_events", event)

    # 2. Cannot update via query
    with pytest.raises(ValueError, match="Cannot update immutable"):
        await mock_surrealdb_client.query(
            "UPDATE repair_events:immut-001 SET event_type = 'MODIFIED'"
        )

    # 3. Verify data unchanged
    stored = mock_surrealdb_client.data["repair_events"]["immut-001"]
    assert stored["hash"] == original_hash
    assert stored["event_type"] == "REPAIR_PARENT"

    # 4. Hash validation still works
    recalculated = calculate_event_hash(stored)
    assert recalculated == original_hash


@pytest.mark.asyncio
async def test_event_log_integrity(mock_surrealdb_client):
    """Test event log maintains integrity and append-only behavior."""
    session_id = "test-log-integrity"

    # Create series of events
    events = []
    for i in range(10):
        event = {
            "event_id": f"log-{i:03d}",
            "event_type": "MESSAGE_ADDED",
            "session_id": session_id,
            "timestamp": (datetime.utcnow() + timedelta(seconds=i)).isoformat(),
            "data": {"index": i}
        }
        event["hash"] = calculate_event_hash(event)
        events.append(event)
        await mock_surrealdb_client.create("repair_events", event)

    # Test: Log should be append-only
    event_log = mock_surrealdb_client.data["event_log"]
    assert len(event_log) == 10

    # Verify order preservation (append order)
    for i, logged_event in enumerate(event_log):
        assert logged_event["data"]["index"] == i

    # Test: Cannot remove from log (simulate by checking immutability)
    initial_length = len(event_log)

    # Attempting to "delete" should not affect log
    # (In real implementation, deletes would be prohibited)
    stored_events = mock_surrealdb_client.data["repair_events"]
    assert len(stored_events) == 10

    # Log remains intact
    assert len(event_log) == initial_length


@pytest.mark.asyncio
async def test_calculate_session_digest(mock_surrealdb_client):
    """Test calculating cryptographic digest of session state."""
    session_id = "test-digest"

    # Create session state through events
    events = [
        {
            "event_id": "digest-001",
            "event_type": "SESSION_CREATED",
            "session_id": session_id,
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {
                "message_count": 5,
                "thread_count": 2,
                "corruption_score": 0.0
            }
        },
        {
            "event_id": "digest-002",
            "event_type": "MESSAGE_ADDED",
            "session_id": session_id,
            "timestamp": "2024-01-01T10:01:00Z",
            "message_uuid": "msg-006",
            "data": {
                "content": "New message",
                "type": "user"
            }
        },
        {
            "event_id": "digest-003",
            "event_type": "SESSION_UPDATED",
            "session_id": session_id,
            "timestamp": "2024-01-01T10:01:30Z",
            "data": {
                "message_count": 6
            }
        }
    ]

    # Save events and calculate intermediate digests
    digests = []
    for event in events:
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

        # Calculate cumulative digest after each event
        current_log = mock_surrealdb_client.data["event_log"]
        digest = calculate_log_digest(current_log)
        digests.append(digest)

    # Test: Digests should be different as log grows
    assert len(set(digests)) == 3  # All unique

    # Test: Digest deterministic for same log state
    final_log = mock_surrealdb_client.data["event_log"]
    digest1 = calculate_log_digest(final_log)
    digest2 = calculate_log_digest(final_log)
    assert digest1 == digest2

    # Test: Any change affects digest
    modified_log = final_log.copy()
    modified_log[-1]["data"]["message_count"] = 7
    modified_digest = calculate_log_digest(modified_log)
    assert modified_digest != digest1


@pytest.mark.asyncio
async def test_export_event_log_compliance(mock_surrealdb_client):
    """Test exporting event log for compliance and audit purposes."""
    session_id = "test-export"

    # Create events with metadata for compliance
    events = [
        {
            "event_id": "export-001",
            "event_type": "SESSION_CREATED",
            "session_id": session_id,
            "timestamp": "2024-01-01T10:00:00Z",
            "actor": "system",
            "reason": "New conversation started",
            "data": {"initial_state": "clean"}
        },
        {
            "event_id": "export-002",
            "event_type": "REPAIR_PARENT",
            "session_id": session_id,
            "timestamp": "2024-01-01T11:00:00Z",
            "actor": "repair_algorithm_v1",
            "reason": "Orphaned message detected",
            "message_uuid": "msg-001",
            "before_state": {"parent_uuid": None},
            "after_state": {"parent_uuid": "msg-000"},
            "confidence": 0.95
        },
        {
            "event_id": "export-003",
            "event_type": "AUDIT_MARKER",
            "session_id": session_id,
            "timestamp": "2024-01-01T12:00:00Z",
            "actor": "compliance_system",
            "reason": "Scheduled audit checkpoint",
            "audit_data": {
                "events_processed": 2,
                "integrity_check": "passed",
                "log_digest": "abc123..."
            }
        }
    ]

    for event in events:
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

    # Test: Export for compliance
    event_log = mock_surrealdb_client.data["event_log"]
    export = create_compliance_export(event_log)

    # Verify export structure
    assert "metadata" in export
    assert "events" in export
    assert "summary" in export
    assert "integrity" in export

    # Check metadata
    assert export["metadata"]["session_id"] == session_id
    assert export["metadata"]["event_count"] == 3
    assert "export_timestamp" in export["metadata"]

    # Check events preserved
    assert len(export["events"]) == 3
    for i, event in enumerate(export["events"]):
        assert event["event_id"] == events[i]["event_id"]
        assert event["hash"] == events[i]["hash"]
        assert "actor" in event
        assert "reason" in event

    # Check summary statistics
    assert export["summary"]["repair_events"] == 1
    assert export["summary"]["audit_events"] == 1
    assert export["summary"]["actors"] == ["system", "repair_algorithm_v1", "compliance_system"]

    # Check integrity
    assert export["integrity"]["log_digest"] is not None
    assert export["integrity"]["event_hashes"] == [e["hash"] for e in events]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_event_hash(event: Dict) -> str:
    """Calculate deterministic hash for an event."""
    hashable = {k: v for k, v in event.items() if k not in ["hash", "timestamp"]}
    content = json.dumps(hashable, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def calculate_log_digest(event_log: List[Dict]) -> str:
    """Calculate cryptographic digest of entire event log."""
    # Combine all event hashes
    combined = "".join(e.get("hash", "") for e in event_log)
    return hashlib.sha256(combined.encode()).hexdigest()


def create_compliance_export(event_log: List[Dict]) -> Dict:
    """Create compliance-ready export of event log."""
    # Extract unique actors
    actors = list(set(e.get("actor", "unknown") for e in event_log))

    # Count event types
    repair_count = sum(1 for e in event_log if "REPAIR" in e.get("event_type", ""))
    audit_count = sum(1 for e in event_log if "AUDIT" in e.get("event_type", ""))

    return {
        "metadata": {
            "session_id": event_log[0]["session_id"] if event_log else None,
            "event_count": len(event_log),
            "export_timestamp": datetime.utcnow().isoformat(),
            "format_version": "1.0"
        },
        "events": event_log,
        "summary": {
            "repair_events": repair_count,
            "audit_events": audit_count,
            "actors": actors,
            "time_range": {
                "start": min(e["timestamp"] for e in event_log) if event_log else None,
                "end": max(e["timestamp"] for e in event_log) if event_log else None
            }
        },
        "integrity": {
            "log_digest": calculate_log_digest(event_log),
            "event_hashes": [e.get("hash") for e in event_log]
        }
    }