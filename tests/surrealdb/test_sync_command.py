"""
Test suite for the sync command that pushes sessions to SurrealDB.

Tests syncing new sessions, detecting changes, creating repair events,
improving corruption scores, and command flags.
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, call
from pathlib import Path
import uuid

from riff.graph.models import Message, MessageType, Session, Thread, ThreadType


# ============================================================================
# TEST SYNC COMMAND
# ============================================================================

@pytest.mark.asyncio
async def test_sync_new_session_to_surrealdb(mock_surrealdb_client, sample_session_with_corruption):
    """Test syncing a new session to SurrealDB for the first time."""
    session = sample_session_with_corruption

    # Mock sync command
    sync_command = MockSyncCommand(mock_surrealdb_client)

    # Execute sync
    result = await sync_command.sync_session(session)

    # Verify session created
    assert result["status"] == "success"
    assert result["session_id"] == session.session_id
    assert result["events_created"] > 0

    # Check initial events created
    events = await mock_surrealdb_client.select("repair_events")
    event_types = [e["event_type"] for e in events]

    assert "SESSION_CREATED" in event_types
    assert "MESSAGE_ADDED" in event_types  # For each message

    # Verify messages stored
    stored_session = await mock_surrealdb_client.select("sessions", session.session_id)
    assert stored_session is not None
    assert stored_session["message_count"] == session.message_count
    assert stored_session["corruption_score"] == session.corruption_score


@pytest.mark.asyncio
async def test_sync_detects_changes(mock_surrealdb_client, sample_session_with_corruption):
    """Test that sync detects changes in session since last sync."""
    session = sample_session_with_corruption
    sync_command = MockSyncCommand(mock_surrealdb_client)

    # First sync
    await sync_command.sync_session(session)
    initial_events = len(mock_surrealdb_client.data["event_log"])

    # Modify session
    new_message = Message(
        uuid="msg-005",
        parent_uuid="msg-004",
        type=MessageType.ASSISTANT,
        content="Here's an explanation of DAGs",
        timestamp="2024-01-01T10:03:00Z",
        session_id=session.session_id,
        corruption_score=0.0
    )
    session.messages.append(new_message)
    session.metadata["last_modified"] = datetime.utcnow().isoformat()

    # Second sync - should detect changes
    result = await sync_command.sync_session(session, detect_changes=True)

    assert result["status"] == "success"
    assert result["changes_detected"] is True
    assert result["new_messages"] == 1

    # Check change event created
    events = mock_surrealdb_client.data["event_log"]
    assert len(events) > initial_events

    latest_events = events[initial_events:]
    change_events = [e for e in latest_events if e["event_type"] == "MESSAGE_ADDED"]
    assert len(change_events) == 1
    assert change_events[0]["message_uuid"] == "msg-005"


@pytest.mark.asyncio
async def test_sync_creates_repair_events(mock_surrealdb_client, sample_session_with_corruption):
    """Test that sync creates repair events for corruption fixes."""
    session = sample_session_with_corruption
    sync_command = MockSyncCommand(mock_surrealdb_client)

    # Simulate repair detection
    repairs = [
        {
            "message_uuid": "msg-003",
            "repair_type": "REPAIR_PARENT",
            "before": {"parent_uuid": "msg-999", "is_orphaned": True},
            "after": {"parent_uuid": "msg-002", "is_orphaned": False}
        }
    ]

    # Sync with repairs
    result = await sync_command.sync_session(
        session,
        repairs=repairs,
        create_repair_events=True
    )

    assert result["status"] == "success"
    assert result["repairs_applied"] == 1

    # Verify repair event created
    events = await mock_surrealdb_client.select("repair_events")
    repair_events = [e for e in events if "REPAIR" in e["event_type"]]

    assert len(repair_events) == 1
    repair = repair_events[0]
    assert repair["event_type"] == "REPAIR_PARENT"
    assert repair["message_uuid"] == "msg-003"
    assert repair["before_state"]["is_orphaned"] is True
    assert repair["after_state"]["is_orphaned"] is False


@pytest.mark.asyncio
async def test_sync_improves_corruption_score(mock_surrealdb_client):
    """Test that sync with repairs improves corruption score."""
    session_id = "corrupt-session"

    # Create highly corrupted session
    messages = []
    for i in range(10):
        is_orphaned = i % 3 == 0  # Every 3rd message is orphaned
        messages.append(
            Message(
                uuid=f"msg-{i:03d}",
                parent_uuid=None if is_orphaned else f"msg-{i-1:03d}" if i > 0 else None,
                type=MessageType.USER if i % 2 == 0 else MessageType.ASSISTANT,
                content=f"Message {i}",
                timestamp=f"2024-01-01T10:{i:02d}:00Z",
                session_id=session_id,
                is_orphaned=is_orphaned,
                corruption_score=0.8 if is_orphaned else 0.0
            )
        )

    session = Session(
        session_id=session_id,
        messages=messages,
        threads=[],
        orphans=[],
        corruption_score=0.6  # High corruption
    )

    sync_command = MockSyncCommand(mock_surrealdb_client)

    # First sync - establish baseline
    result1 = await sync_command.sync_session(session)
    assert result1["initial_corruption_score"] == 0.6

    # Apply repairs
    repairs = []
    for i in range(0, 10, 3):  # Fix all orphaned messages
        if i > 0:
            repairs.append({
                "message_uuid": f"msg-{i:03d}",
                "repair_type": "REPAIR_PARENT",
                "before": {"parent_uuid": None, "is_orphaned": True},
                "after": {"parent_uuid": f"msg-{i-1:03d}", "is_orphaned": False}
            })

    # Update session after repairs
    for msg in session.messages:
        if msg.is_orphaned:
            msg.is_orphaned = False
            msg.corruption_score = 0.0
    session.corruption_score = 0.1  # Much improved

    # Second sync with repairs
    result2 = await sync_command.sync_session(
        session,
        repairs=repairs,
        create_repair_events=True
    )

    assert result2["status"] == "success"
    assert result2["repairs_applied"] == len(repairs)
    assert result2["final_corruption_score"] == 0.1
    assert result2["corruption_improved"] is True
    assert result2["improvement_delta"] == -0.5  # 0.6 -> 0.1


@pytest.mark.asyncio
async def test_sync_dry_run(mock_surrealdb_client, sample_session_with_corruption):
    """Test dry run mode that simulates sync without writing."""
    session = sample_session_with_corruption
    sync_command = MockSyncCommand(mock_surrealdb_client)

    # Initial state
    initial_event_count = len(mock_surrealdb_client.data["event_log"])

    # Dry run
    result = await sync_command.sync_session(session, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["would_create_events"] > 0
    assert result["would_sync_messages"] == session.message_count

    # Verify nothing actually written
    assert len(mock_surrealdb_client.data["event_log"]) == initial_event_count
    assert len(mock_surrealdb_client.data["sessions"]) == 0

    # Report what would happen
    assert "dry_run_summary" in result
    summary = result["dry_run_summary"]
    assert summary["session_would_be_created"] is True
    assert summary["messages_to_sync"] == 4
    assert summary["events_to_create"] > 0


@pytest.mark.asyncio
async def test_sync_force_flag(mock_surrealdb_client, sample_session_with_corruption):
    """Test force flag that overwrites existing session data."""
    session = sample_session_with_corruption
    sync_command = MockSyncCommand(mock_surrealdb_client)

    # First sync
    await sync_command.sync_session(session)
    initial_events = len(mock_surrealdb_client.data["event_log"])

    # Modify session to simulate conflict
    session.corruption_score = 0.0  # "Fixed" locally
    session.metadata["local_fix"] = True

    # Try sync without force - should detect conflict
    result = await sync_command.sync_session(session, detect_changes=True)
    assert result.get("conflict_detected") is True

    # Sync with force - overwrites remote
    result_forced = await sync_command.sync_session(
        session,
        force=True,
        reason="Local fixes validated"
    )

    assert result_forced["status"] == "success"
    assert result_forced["forced"] is True
    assert result_forced["reason"] == "Local fixes validated"

    # Check force event created
    events = mock_surrealdb_client.data["event_log"]
    force_events = [
        e for e in events
        if e.get("event_type") == "SESSION_FORCED_UPDATE"
    ]
    assert len(force_events) == 1
    assert force_events[0]["reason"] == "Local fixes validated"


# ============================================================================
# MOCK SYNC COMMAND CLASS
# ============================================================================

class MockSyncCommand:
    """Mock implementation of sync command for testing."""

    def __init__(self, surrealdb_client):
        """Initialize with mock client."""
        self.client = surrealdb_client

    async def sync_session(
        self,
        session: Session,
        detect_changes: bool = False,
        repairs: list = None,
        create_repair_events: bool = False,
        dry_run: bool = False,
        force: bool = False,
        reason: str = None
    ) -> dict:
        """Sync session to SurrealDB with various options."""

        result = {
            "session_id": session.session_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Dry run mode
        if dry_run:
            result["status"] = "dry_run"
            result["would_create_events"] = len(session.messages) + 1
            result["would_sync_messages"] = session.message_count
            result["dry_run_summary"] = {
                "session_would_be_created": True,
                "messages_to_sync": session.message_count,
                "events_to_create": len(session.messages) + 1
            }
            return result

        # Check for existing session
        existing = await self.client.select("sessions", session.session_id)

        # Conflict detection
        if existing and detect_changes and not force:
            if existing.get("corruption_score") != session.corruption_score:
                result["conflict_detected"] = True
                return result

        # Force update handling
        if force and existing:
            force_event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "SESSION_FORCED_UPDATE",
                "session_id": session.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "before_state": existing,
                "after_state": {
                    "corruption_score": session.corruption_score,
                    "metadata": session.metadata
                }
            }
            force_event["hash"] = self._calculate_hash(force_event)
            await self.client.create("repair_events", force_event)
            result["forced"] = True
            result["reason"] = reason

        # Create or update session
        if not existing:
            # Create session event
            create_event = {
                "event_id": str(uuid.uuid4()),
                "event_type": "SESSION_CREATED",
                "session_id": session.session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "message_count": session.message_count,
                    "thread_count": session.thread_count,
                    "corruption_score": session.corruption_score
                }
            }
            create_event["hash"] = self._calculate_hash(create_event)
            await self.client.create("repair_events", create_event)

            # Add message events
            for msg in session.messages:
                msg_event = {
                    "event_id": str(uuid.uuid4()),
                    "event_type": "MESSAGE_ADDED",
                    "session_id": session.session_id,
                    "message_uuid": msg.uuid,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "type": msg.type.value,
                        "content": msg.content[:100]  # Truncate for events
                    }
                }
                msg_event["hash"] = self._calculate_hash(msg_event)
                await self.client.create("repair_events", msg_event)

            result["events_created"] = len(session.messages) + 1
        else:
            # Detect changes
            if detect_changes:
                old_msg_count = existing.get("message_count", 0)
                new_msg_count = session.message_count
                if new_msg_count > old_msg_count:
                    result["changes_detected"] = True
                    result["new_messages"] = new_msg_count - old_msg_count

                    # Add events for new messages
                    new_messages = session.messages[old_msg_count:]
                    for msg in new_messages:
                        msg_event = {
                            "event_id": str(uuid.uuid4()),
                            "event_type": "MESSAGE_ADDED",
                            "session_id": session.session_id,
                            "message_uuid": msg.uuid,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        msg_event["hash"] = self._calculate_hash(msg_event)
                        await self.client.create("repair_events", msg_event)

        # Apply repairs
        if repairs and create_repair_events:
            for repair in repairs:
                repair_event = {
                    "event_id": str(uuid.uuid4()),
                    "event_type": repair["repair_type"],
                    "session_id": session.session_id,
                    "message_uuid": repair["message_uuid"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "before_state": repair["before"],
                    "after_state": repair["after"]
                }
                repair_event["hash"] = self._calculate_hash(repair_event)
                await self.client.create("repair_events", repair_event)

            result["repairs_applied"] = len(repairs)

        # Track corruption improvement
        if existing:
            old_score = existing.get("corruption_score", 1.0)
            new_score = session.corruption_score
            result["initial_corruption_score"] = old_score
            result["final_corruption_score"] = new_score
            if new_score < old_score:
                result["corruption_improved"] = True
                result["improvement_delta"] = new_score - old_score

        # Store session
        await self.client.create("sessions", {
            "session_id": session.session_id,
            "message_count": session.message_count,
            "thread_count": session.thread_count,
            "corruption_score": session.corruption_score,
            "metadata": session.metadata
        })

        result["status"] = "success"
        return result

    def _calculate_hash(self, event: dict) -> str:
        """Calculate event hash."""
        hashable = {k: v for k, v in event.items() if k not in ["hash", "timestamp"]}
        content = json.dumps(hashable, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()