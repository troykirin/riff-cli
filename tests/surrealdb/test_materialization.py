"""
Test suite for session materialization from event streams.

Tests building current state from events, view caching,
and staleness detection.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from riff.graph.models import Message, MessageType, Session, Thread, ThreadType


# ============================================================================
# TEST MATERIALIZATION FROM EVENTS
# ============================================================================

@pytest.mark.asyncio
async def test_materialize_empty_session(mock_surrealdb_client):
    """Test materializing a session with no events."""
    session_id = "empty-session"

    # No events exist
    materialized = await materialize_session(mock_surrealdb_client, session_id)

    assert materialized is not None
    assert materialized["session_id"] == session_id
    assert materialized["message_count"] == 0
    assert materialized["thread_count"] == 0
    assert materialized["corruption_score"] == 0.0
    assert materialized["events_applied"] == 0


@pytest.mark.asyncio
async def test_materialize_with_single_repair(mock_surrealdb_client):
    """Test materializing session after a single repair event."""
    session_id = "single-repair"

    # Initial session creation event
    create_event = {
        "event_id": "evt-001",
        "event_type": "SESSION_CREATED",
        "session_id": session_id,
        "timestamp": "2024-01-01T10:00:00Z",
        "data": {
            "message_count": 5,
            "thread_count": 1,
            "corruption_score": 0.4,
            "orphaned_messages": ["msg-003"]
        }
    }
    create_event["hash"] = calculate_event_hash(create_event)
    await mock_surrealdb_client.create("repair_events", create_event)

    # Single repair event
    repair_event = {
        "event_id": "evt-002",
        "event_type": "REPAIR_PARENT",
        "session_id": session_id,
        "timestamp": "2024-01-01T11:00:00Z",
        "message_uuid": "msg-003",
        "before_state": {
            "parent_uuid": None,
            "is_orphaned": True
        },
        "after_state": {
            "parent_uuid": "msg-002",
            "is_orphaned": False
        },
        "impact": {
            "corruption_score_delta": -0.2,
            "orphaned_messages_fixed": 1
        }
    }
    repair_event["hash"] = calculate_event_hash(repair_event)
    await mock_surrealdb_client.create("repair_events", repair_event)

    # Update event after repair
    update_event = {
        "event_id": "evt-003",
        "event_type": "SESSION_UPDATED",
        "session_id": session_id,
        "timestamp": "2024-01-01T11:00:30Z",
        "data": {
            "corruption_score": 0.2,  # Reduced after repair
            "orphaned_messages": []  # Fixed
        }
    }
    update_event["hash"] = calculate_event_hash(update_event)
    await mock_surrealdb_client.create("repair_events", update_event)

    # Test: Materialize current state
    materialized = await materialize_session(mock_surrealdb_client, session_id)

    assert materialized["message_count"] == 5
    assert materialized["thread_count"] == 1
    assert materialized["corruption_score"] == 0.2
    assert materialized["orphaned_messages"] == []
    assert materialized["events_applied"] == 3
    assert materialized["last_repair"] == repair_event["timestamp"]
    assert materialized["repair_count"] == 1


@pytest.mark.asyncio
async def test_materialize_with_multiple_repairs(mock_surrealdb_client):
    """Test materializing session after multiple repair events."""
    session_id = "multi-repair"

    # Initial corrupt state
    events = [
        {
            "event_id": "init-001",
            "event_type": "SESSION_CREATED",
            "session_id": session_id,
            "timestamp": "2024-01-01T10:00:00Z",
            "data": {
                "message_count": 10,
                "thread_count": 3,
                "corruption_score": 0.8,
                "issues": {
                    "orphaned_messages": ["msg-003", "msg-005", "msg-007"],
                    "broken_threads": ["thread-002"],
                    "timestamp_errors": ["msg-004"]
                }
            }
        }
    ]

    # Series of repair events
    repairs = [
        ("msg-003", "REPAIR_PARENT", 0.7, ["msg-005", "msg-007"]),
        ("msg-005", "REPAIR_PARENT", 0.5, ["msg-007"]),
        ("msg-004", "REPAIR_TIMESTAMP", 0.4, ["msg-007"]),
        ("thread-002", "REPAIR_THREAD", 0.3, ["msg-007"]),
        ("msg-007", "REPAIR_PARENT", 0.0, [])
    ]

    timestamp = datetime(2024, 1, 1, 11, 0, 0)
    for i, (target, repair_type, new_score, remaining) in enumerate(repairs):
        repair_event = {
            "event_id": f"repair-{i:03d}",
            "event_type": repair_type,
            "session_id": session_id,
            "timestamp": (timestamp + timedelta(minutes=i * 10)).isoformat(),
            "target_id": target,
            "result": {
                "corruption_score": new_score,
                "remaining_orphans": remaining,
                "fixed": True
            }
        }
        events.append(repair_event)

        # Add corresponding update event
        update_event = {
            "event_id": f"update-{i:03d}",
            "event_type": "SESSION_UPDATED",
            "session_id": session_id,
            "timestamp": (timestamp + timedelta(minutes=i * 10, seconds=30)).isoformat(),
            "data": {
                "corruption_score": new_score,
                "issues": {"orphaned_messages": remaining}
            }
        }
        events.append(update_event)

    # Save all events
    for event in events:
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

    # Test: Materialize final state
    materialized = await materialize_session(mock_surrealdb_client, session_id)

    assert materialized["corruption_score"] == 0.0
    assert materialized["repair_count"] == 5
    assert materialized["events_applied"] == 11  # 1 create + 5 repairs + 5 updates
    assert materialized["issues"]["orphaned_messages"] == []
    assert "last_repair" in materialized

    # Verify repair history tracked
    repair_types = await get_repair_history(mock_surrealdb_client, session_id)
    assert len(repair_types) == 5
    assert repair_types.count("REPAIR_PARENT") == 3
    assert repair_types.count("REPAIR_TIMESTAMP") == 1
    assert repair_types.count("REPAIR_THREAD") == 1


@pytest.mark.asyncio
async def test_materialized_view_cache(mock_surrealdb_client):
    """Test caching of materialized views for performance."""
    session_id = "cached-session"

    # Create initial events
    for i in range(3):
        event = {
            "event_id": f"evt-{i:03d}",
            "event_type": "MESSAGE_ADDED",
            "session_id": session_id,
            "timestamp": f"2024-01-01T10:{i:02d}:00Z",
            "data": {"message_index": i}
        }
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

    # First materialization (cache miss)
    view1 = await materialize_session_with_cache(mock_surrealdb_client, session_id)
    assert view1["cache_hit"] is False
    assert view1["events_applied"] == 3

    # Second materialization (cache hit)
    view2 = await materialize_session_with_cache(mock_surrealdb_client, session_id)
    assert view2["cache_hit"] is True
    assert view2["events_applied"] == 3
    assert view2["cache_timestamp"] == view1["materialized_at"]

    # Add new event
    new_event = {
        "event_id": "evt-003",
        "event_type": "MESSAGE_ADDED",
        "session_id": session_id,
        "timestamp": "2024-01-01T10:03:00Z",
        "data": {"message_index": 3}
    }
    new_event["hash"] = calculate_event_hash(new_event)
    await mock_surrealdb_client.create("repair_events", new_event)

    # Third materialization (cache invalidated)
    view3 = await materialize_session_with_cache(mock_surrealdb_client, session_id)
    assert view3["cache_hit"] is False
    assert view3["events_applied"] == 4
    assert view3["materialized_at"] > view1["materialized_at"]


@pytest.mark.asyncio
async def test_materialize_detects_stale_cache(mock_surrealdb_client):
    """Test detection and handling of stale cached views."""
    session_id = "stale-cache-session"

    # Create base events
    base_events = [
        {
            "event_id": f"base-{i:03d}",
            "event_type": "SESSION_UPDATED",
            "session_id": session_id,
            "timestamp": f"2024-01-01T10:{i:02d}:00Z",
            "data": {"counter": i}
        }
        for i in range(5)
    ]

    for event in base_events:
        event["hash"] = calculate_event_hash(event)
        await mock_surrealdb_client.create("repair_events", event)

    # Create cache with snapshot
    cache_snapshot = {
        "session_id": session_id,
        "last_event_id": "base-004",
        "last_event_hash": base_events[-1]["hash"],
        "materialized_at": datetime.utcnow().isoformat(),
        "event_count": 5,
        "state": {"counter": 4}
    }

    # Simulate external change (event added outside cache)
    external_event = {
        "event_id": "external-001",
        "event_type": "EXTERNAL_REPAIR",
        "session_id": session_id,
        "timestamp": "2024-01-01T11:00:00Z",
        "data": {"counter": 5, "external": True}
    }
    external_event["hash"] = calculate_event_hash(external_event)
    await mock_surrealdb_client.create("repair_events", external_event)

    # Test: Detect stale cache
    is_stale = await check_cache_staleness(
        mock_surrealdb_client,
        cache_snapshot
    )
    assert is_stale is True

    # Test: Rebuild from events
    fresh_view = await materialize_session(mock_surrealdb_client, session_id)
    assert fresh_view["events_applied"] == 6
    assert fresh_view["state"]["counter"] == 5
    assert fresh_view["state"].get("external") is True

    # Test: Incremental update from cache point
    incremental = await materialize_incremental(
        mock_surrealdb_client,
        session_id,
        cache_snapshot
    )
    assert incremental["new_events"] == 1
    assert incremental["state"]["counter"] == 5


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def materialize_session(client, session_id: str) -> Dict:
    """Materialize current session state from event log."""
    events = await client.select("repair_events")
    session_events = [e for e in events if e.get("session_id") == session_id]

    # Sort by timestamp
    session_events.sort(key=lambda e: e.get("timestamp", ""))

    # Apply events to build state
    state = {
        "session_id": session_id,
        "message_count": 0,
        "thread_count": 0,
        "corruption_score": 0.0,
        "events_applied": 0,
        "repair_count": 0
    }

    for event in session_events:
        state["events_applied"] += 1

        if event["event_type"] == "SESSION_CREATED":
            state.update(event.get("data", {}))
        elif event["event_type"] == "SESSION_UPDATED":
            state.update(event.get("data", {}))
        elif "REPAIR" in event["event_type"]:
            state["repair_count"] += 1
            state["last_repair"] = event["timestamp"]
            if "result" in event:
                state["corruption_score"] = event["result"].get(
                    "corruption_score",
                    state["corruption_score"]
                )

    return state


async def materialize_session_with_cache(client, session_id: str) -> Dict:
    """Materialize with cache support."""
    cache_key = f"materialized:{session_id}"

    # Check cache
    if hasattr(client, "_cache") and cache_key in client._cache:
        cached = client._cache[cache_key]
        # Check if cache still valid
        events = await client.select("repair_events")
        session_events = [e for e in events if e.get("session_id") == session_id]
        if len(session_events) == cached["events_applied"]:
            cached["cache_hit"] = True
            return cached

    # Cache miss - materialize
    materialized = await materialize_session(client, session_id)
    materialized["cache_hit"] = False
    materialized["materialized_at"] = datetime.utcnow().isoformat()

    # Store in cache
    if not hasattr(client, "_cache"):
        client._cache = {}
    client._cache[cache_key] = materialized

    return materialized


async def get_repair_history(client, session_id: str) -> List[str]:
    """Get list of repair event types for a session."""
    events = await client.select("repair_events")
    repairs = [
        e["event_type"]
        for e in events
        if e.get("session_id") == session_id and "REPAIR" in e.get("event_type", "")
    ]
    return repairs


async def check_cache_staleness(client, cache_snapshot: Dict) -> bool:
    """Check if cached view is stale."""
    events = await client.select("repair_events")
    session_events = [
        e for e in events
        if e.get("session_id") == cache_snapshot["session_id"]
    ]

    # More events than cache knows about
    if len(session_events) > cache_snapshot["event_count"]:
        return True

    # Last event hash mismatch
    if session_events:
        last_event = session_events[-1]
        if last_event.get("hash") != cache_snapshot.get("last_event_hash"):
            return True

    return False


async def materialize_incremental(client, session_id: str, cache_snapshot: Dict) -> Dict:
    """Incrementally update from cache point."""
    events = await client.select("repair_events")
    session_events = [
        e for e in events
        if e.get("session_id") == session_id
    ]

    # Find events after cache point
    cache_event_id = cache_snapshot.get("last_event_id")
    new_events = []
    found_cache_point = False

    for event in session_events:
        if found_cache_point:
            new_events.append(event)
        elif event.get("event_id") == cache_event_id:
            found_cache_point = True

    # Apply new events to cached state
    state = cache_snapshot.get("state", {}).copy()
    for event in new_events:
        if "data" in event:
            state.update(event["data"])

    return {
        "state": state,
        "new_events": len(new_events),
        "base_snapshot": cache_event_id
    }


def calculate_event_hash(event: Dict) -> str:
    """Calculate deterministic hash for an event."""
    hashable = {k: v for k, v in event.items() if k not in ["hash", "timestamp"]}
    content = json.dumps(hashable, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()