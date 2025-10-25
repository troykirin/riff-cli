"""
Immutable Repair Events Utilities for SurrealDB.

This module provides utilities for:
- Replaying repair events to rebuild session state
- Validating event immutability and integrity
- Computing session digests for tamper detection
- Exporting event logs for compliance/audit

The event sourcing pattern ensures:
1. All repairs are append-only (never UPDATE/DELETE)
2. Complete audit trail of who changed what and when
3. Ability to replay events to rebuild any historical state
4. Tamper detection via SHA256 digests

Usage:
    from riff.surrealdb.repair_events_utils import (
        replay_repair_events,
        validate_event_immutability,
        calculate_session_digest,
        export_event_log
    )

    # Replay events to get current state
    current_state = replay_repair_events(events, original_messages)

    # Validate integrity
    is_valid = validate_event_immutability(new_event, stored_events)

    # Compute digest for drift detection
    digest = calculate_session_digest(events)

    # Export for audit
    log_json = export_event_log(session_id, events)
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Set

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class RepairEvent:
    """
    Immutable repair event record.

    This represents a single repair operation in the event log.
    Once created, events MUST never be modified or deleted.

    Attributes:
        event_id: Unique identifier for this event
        session_id: Which session this repair belongs to
        timestamp: When the repair occurred (ISO8601 UTC)
        message_id: Which message was repaired
        old_parent_uuid: Previous parent (None for orphaned messages)
        new_parent_uuid: New parent assigned
        operator: Who performed the repair (e.g., "user:tryk", "agent:orchestrator")
        reason: Why this repair was made (human-readable)
        similarity_score: Confidence score 0.0-1.0 from repair engine
        validation_passed: Whether repair passed validation checks
        is_reverted: Whether this is a revert event
        reverts_event_id: If revert, which event is being reversed
        event_digest: SHA256 hash for tamper detection
        created_at: System timestamp when persisted
    """

    event_id: str
    session_id: str
    timestamp: datetime
    message_id: str
    old_parent_uuid: Optional[str]
    new_parent_uuid: str
    operator: str
    reason: str
    similarity_score: float = 0.0
    validation_passed: bool = True
    is_reverted: bool = False
    reverts_event_id: Optional[str] = None
    event_digest: str = ""
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate event after initialization."""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(
                f"similarity_score must be 0.0-1.0, got {self.similarity_score}"
            )

        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)

        # Compute digest if not provided
        if not self.event_digest:
            self.event_digest = compute_event_digest(self)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetimes to ISO8601
        data["timestamp"] = self.timestamp.isoformat()
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> RepairEvent:
        """Create RepairEvent from dictionary."""
        # Parse datetimes
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(
                data["timestamp"].replace("Z", "+00:00")
            )
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            )
        return cls(**data)


@dataclass
class Message:
    """
    Simplified message representation for replay.

    This is a lightweight version of graph.models.Message
    containing only fields needed for repair event processing.
    """

    uuid: str
    parent_uuid: Optional[str]
    content: str
    timestamp: str
    session_id: str
    is_orphaned: bool = False
    corruption_score: float = 0.0


@dataclass
class ReplayResult:
    """
    Result of replaying repair events.

    Attributes:
        message_parents: Mapping of message_id -> parent_uuid after all repairs
        total_events: Total number of events processed
        active_events: Number of non-reverted events applied
        reverted_events: Number of reverted events skipped
        messages_repaired: Set of message IDs that were repaired
        errors: List of error messages encountered
    """

    message_parents: Dict[str, Optional[str]]
    total_events: int
    active_events: int
    reverted_events: int
    messages_repaired: Set[str]
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Whether replay completed without errors."""
        return len(self.errors) == 0


@dataclass
class ValidationResult:
    """
    Result of event immutability validation.

    Attributes:
        is_valid: Whether validation passed
        errors: List of validation errors
        warnings: List of validation warnings
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        """Allow truthiness check."""
        return self.is_valid


# ============================================================================
# Event Digest Computation
# ============================================================================


def compute_event_digest(event: RepairEvent) -> str:
    """
    Compute SHA256 digest for tamper detection.

    The digest is computed from immutable fields:
    - event_id
    - session_id
    - timestamp
    - message_id
    - old_parent_uuid (or "null")
    - new_parent_uuid

    If any of these fields are modified, the digest will change,
    indicating potential tampering.

    Args:
        event: RepairEvent to compute digest for

    Returns:
        64-character hexadecimal SHA256 digest
    """
    timestamp_str = event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else event.timestamp

    content = "".join([
        event.event_id,
        event.session_id,
        timestamp_str,
        event.message_id,
        event.old_parent_uuid or "null",
        event.new_parent_uuid
    ])

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    logger.debug(f"Computed digest for event {event.event_id[:8]}: {digest[:16]}...")
    return digest


def verify_event_digest(event: RepairEvent) -> bool:
    """
    Verify that event's digest matches computed digest.

    Args:
        event: RepairEvent to verify

    Returns:
        True if digest is valid, False if tampered
    """
    computed = compute_event_digest(event)
    matches = computed == event.event_digest

    if not matches:
        logger.error(
            f"Digest mismatch for event {event.event_id[:8]}: "
            f"stored={event.event_digest[:16]}..., "
            f"computed={computed[:16]}..."
        )

    return matches


# ============================================================================
# Event Replay
# ============================================================================


def replay_repair_events(
    events: List[RepairEvent],
    original_messages: Optional[List[Message]] = None
) -> ReplayResult:
    """
    Replay repair events to compute current session state.

    This function applies all non-reverted repair events in chronological
    order to build the current parent mapping for all messages.

    Algorithm:
    1. Sort events by timestamp (ascending)
    2. Build set of reverted event IDs
    3. Apply each non-reverted event to message_parents dict
    4. Return final state

    Args:
        events: List of RepairEvent objects to replay
        original_messages: Optional list of original messages (for validation)

    Returns:
        ReplayResult with message_parents mapping and statistics
    """
    logger.info(f"Replaying {len(events)} repair events")

    # Sort events by timestamp (chronological order)
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Build set of reverted event IDs
    reverted_ids = {
        e.reverts_event_id
        for e in sorted_events
        if e.is_reverted and e.reverts_event_id
    }

    logger.debug(f"Found {len(reverted_ids)} reverted events to skip")

    # Apply events
    message_parents: Dict[str, Optional[str]] = {}
    messages_repaired: Set[str] = set()
    errors: List[str] = []
    active_count = 0
    reverted_count = 0

    # Initialize with original parent mappings if provided
    if original_messages:
        for msg in original_messages:
            message_parents[msg.uuid] = msg.parent_uuid

    # Apply each event
    for event in sorted_events:
        # Skip reverted events
        if event.event_id in reverted_ids:
            reverted_count += 1
            logger.debug(
                f"Skipping reverted event {event.event_id[:8]} "
                f"(message {event.message_id[:8]})"
            )
            continue

        # Verify digest
        if not verify_event_digest(event):
            errors.append(
                f"Event {event.event_id[:8]} failed digest verification (tampered?)"
            )
            continue

        # Apply repair
        old_parent = message_parents.get(event.message_id)
        message_parents[event.message_id] = event.new_parent_uuid
        messages_repaired.add(event.message_id)
        active_count += 1

        logger.debug(
            f"Applied event {event.event_id[:8]}: "
            f"msg={event.message_id[:8]} "
            f"parent {old_parent[:8] if old_parent else 'null'} -> "
            f"{event.new_parent_uuid[:8]}"
        )

    logger.info(
        f"Replay complete: {active_count} active, {reverted_count} reverted, "
        f"{len(messages_repaired)} messages repaired, {len(errors)} errors"
    )

    return ReplayResult(
        message_parents=message_parents,
        total_events=len(events),
        active_events=active_count,
        reverted_events=reverted_count,
        messages_repaired=messages_repaired,
        errors=errors
    )


# ============================================================================
# Immutability Validation
# ============================================================================


def validate_event_immutability(
    event: RepairEvent,
    stored_events: List[RepairEvent]
) -> ValidationResult:
    """
    Validate that an event hasn't been mutated after creation.

    Checks:
    1. Event ID is unique (not reused)
    2. If event exists, all fields match exactly
    3. Digest is valid

    Args:
        event: New or existing RepairEvent to validate
        stored_events: List of events already in the store

    Returns:
        ValidationResult with is_valid and error details
    """
    logger.debug(f"Validating immutability for event {event.event_id[:8]}")

    errors: List[str] = []
    warnings: List[str] = []

    # Check 1: Verify digest
    if not verify_event_digest(event):
        errors.append("Event digest invalid (event may be tampered)")

    # Check 2: Look for existing event with same ID
    existing = None
    for stored_event in stored_events:
        if stored_event.event_id == event.event_id:
            existing = stored_event
            break

    if existing:
        # Event already exists - verify it wasn't mutated
        logger.debug(f"Found existing event {event.event_id[:8]}, checking for mutations")

        # Compare all immutable fields
        if existing.session_id != event.session_id:
            errors.append(
                f"session_id changed: {existing.session_id} -> {event.session_id}"
            )

        if existing.message_id != event.message_id:
            errors.append(
                f"message_id changed: {existing.message_id} -> {event.message_id}"
            )

        if existing.old_parent_uuid != event.old_parent_uuid:
            errors.append(
                f"old_parent_uuid changed: {existing.old_parent_uuid} -> {event.old_parent_uuid}"
            )

        if existing.new_parent_uuid != event.new_parent_uuid:
            errors.append(
                f"new_parent_uuid changed: {existing.new_parent_uuid} -> {event.new_parent_uuid}"
            )

        if existing.timestamp != event.timestamp:
            errors.append(
                f"timestamp changed: {existing.timestamp} -> {event.timestamp}"
            )

        if existing.event_digest != event.event_digest:
            errors.append(
                f"event_digest changed: {existing.event_digest[:16]}... -> {event.event_digest[:16]}..."
            )

        # Warn about mutable field changes (allowed but suspicious)
        if existing.is_reverted != event.is_reverted:
            warnings.append(
                f"is_reverted changed: {existing.is_reverted} -> {event.is_reverted}"
            )

    else:
        # New event - check for duplicate event_id
        logger.debug(f"New event {event.event_id[:8]}, checking for duplicates")

    # Check 3: Validate event_id uniqueness
    event_ids = [e.event_id for e in stored_events]
    if event_ids.count(event.event_id) > 1:
        errors.append(f"Duplicate event_id detected: {event.event_id}")

    is_valid = len(errors) == 0

    if is_valid:
        logger.debug(f"Event {event.event_id[:8]} passed immutability validation")
    else:
        logger.error(
            f"Event {event.event_id[:8]} failed immutability validation: {errors}"
        )

    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings
    )


# ============================================================================
# Session Digest Computation
# ============================================================================


def calculate_session_digest(events: List[RepairEvent]) -> str:
    """
    Calculate SHA256 digest of event sequence for integrity checking.

    The session digest is computed from the sorted list of event_id values.
    This provides a fingerprint of the entire event log, useful for:
    - Detecting if events were added/removed
    - Verifying materialized view matches event log
    - Compliance/audit trail

    Args:
        events: List of RepairEvent objects

    Returns:
        64-character hexadecimal SHA256 digest
    """
    logger.debug(f"Calculating session digest for {len(events)} events")

    # Sort event IDs for deterministic digest
    event_ids = sorted([e.event_id for e in events])

    # Concatenate and hash
    content = "".join(event_ids)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()

    logger.debug(f"Session digest: {digest[:16]}... (from {len(event_ids)} events)")
    return digest


def verify_session_digest(
    events: List[RepairEvent],
    expected_digest: str
) -> bool:
    """
    Verify session digest matches expected value.

    Args:
        events: List of RepairEvent objects
        expected_digest: Expected SHA256 digest

    Returns:
        True if digest matches, False otherwise
    """
    computed = calculate_session_digest(events)
    matches = computed == expected_digest

    if not matches:
        logger.error(
            f"Session digest mismatch: "
            f"expected={expected_digest[:16]}..., "
            f"computed={computed[:16]}..."
        )

    return matches


# ============================================================================
# Event Log Export
# ============================================================================


def export_event_log(
    session_id: str,
    events: List[RepairEvent],
    include_metadata: bool = True
) -> str:
    """
    Export event log to JSON for compliance/audit.

    Creates a complete, self-contained JSON document with:
    - Session metadata
    - All repair events in chronological order
    - Integrity digests
    - Export timestamp

    Args:
        session_id: Session UUID
        events: List of RepairEvent objects to export
        include_metadata: Whether to include metadata section

    Returns:
        JSON string (pretty-printed)
    """
    logger.info(f"Exporting event log for session {session_id} ({len(events)} events)")

    # Sort events chronologically
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Build export document
    export_data = {
        "format_version": "1.0",
        "export_type": "repair_event_log",
        "session_id": session_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "events": [event.to_dict() for event in sorted_events]
    }

    if include_metadata:
        # Compute statistics
        active_events = [e for e in events if not e.is_reverted]
        reverted_events = [e for e in events if e.is_reverted]
        messages_repaired = {e.message_id for e in active_events}

        # Get operator distribution
        operator_counts: Dict[str, int] = {}
        for event in events:
            operator_counts[event.operator] = operator_counts.get(event.operator, 0) + 1

        # Compute session digest
        session_digest = calculate_session_digest(events)

        export_data["metadata"] = {
            "total_events": len(events),
            "active_events": len(active_events),
            "reverted_events": len(reverted_events),
            "messages_repaired": len(messages_repaired),
            "operators": operator_counts,
            "session_digest": session_digest,
            "first_event_timestamp": sorted_events[0].timestamp.isoformat() if events else None,
            "last_event_timestamp": sorted_events[-1].timestamp.isoformat() if events else None,
        }

        # Validate all event digests
        invalid_digests = [
            e.event_id for e in events
            if not verify_event_digest(e)
        ]

        if invalid_digests:
            export_data["metadata"]["integrity_warnings"] = {
                "invalid_digests": invalid_digests,
                "message": "WARNING: Some events have invalid digests (possible tampering)"
            }

    # Convert to JSON
    json_output = json.dumps(export_data, indent=2)

    logger.info(f"Exported {len(events)} events ({len(json_output)} bytes)")
    return json_output


def import_event_log(json_data: str) -> Tuple[str, List[RepairEvent]]:
    """
    Import event log from JSON.

    Args:
        json_data: JSON string from export_event_log()

    Returns:
        Tuple of (session_id, list of RepairEvent objects)

    Raises:
        ValueError: If JSON is invalid or format version unsupported
    """
    logger.info("Importing event log from JSON")

    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Validate format
    if data.get("format_version") != "1.0":
        raise ValueError(
            f"Unsupported format version: {data.get('format_version')}"
        )

    if data.get("export_type") != "repair_event_log":
        raise ValueError(
            f"Invalid export type: {data.get('export_type')}"
        )

    session_id = data["session_id"]
    events = [RepairEvent.from_dict(e) for e in data["events"]]

    logger.info(f"Imported {len(events)} events for session {session_id}")

    # Validate session digest if present
    if "metadata" in data and "session_digest" in data["metadata"]:
        expected_digest = data["metadata"]["session_digest"]
        if not verify_session_digest(events, expected_digest):
            logger.warning("Session digest mismatch - event log may be incomplete")

    return session_id, events


# ============================================================================
# Utilities
# ============================================================================


def generate_event_id() -> str:
    """
    Generate unique event ID.

    Uses timestamp + random component for uniqueness.

    Returns:
        Event ID string (e.g., "evt_20241020_123456_abc123")
    """
    import uuid
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    random_suffix = uuid.uuid4().hex[:6]
    return f"evt_{timestamp}_{random_suffix}"


def create_revert_event(
    original_event: RepairEvent,
    operator: str,
    reason: str = "Manual revert"
) -> RepairEvent:
    """
    Create a revert event for an existing repair.

    Revert events:
    - Swap old_parent_uuid ↔ new_parent_uuid
    - Set is_reverted = True
    - Link to original via reverts_event_id

    Args:
        original_event: Event to revert
        operator: Who is performing the revert
        reason: Why the revert is being performed

    Returns:
        New RepairEvent that reverses the original
    """
    logger.info(f"Creating revert event for {original_event.event_id[:8]}")

    revert_event = RepairEvent(
        event_id=generate_event_id(),
        session_id=original_event.session_id,
        timestamp=datetime.now(timezone.utc),
        message_id=original_event.message_id,
        old_parent_uuid=original_event.new_parent_uuid,  # Swap
        new_parent_uuid=original_event.old_parent_uuid or "",  # Swap
        operator=operator,
        reason=reason,
        similarity_score=0.0,  # Manual revert
        validation_passed=True,
        is_reverted=True,
        reverts_event_id=original_event.event_id
    )

    logger.debug(
        f"Created revert event {revert_event.event_id[:8]}: "
        f"msg={revert_event.message_id[:8]} "
        f"parent {original_event.old_parent_uuid[:8] if original_event.old_parent_uuid else 'null'} <- "
        f"{original_event.new_parent_uuid[:8]}"
    )

    return revert_event


# ============================================================================
# Example Usage
# ============================================================================


def example_usage():
    """
    Example workflow demonstrating repair event utilities.
    """
    print("=== Repair Events Utilities Example ===\n")

    # 1. Create a repair event
    event1 = RepairEvent(
        event_id=generate_event_id(),
        session_id="session-abc-123",
        timestamp=datetime.now(timezone.utc),
        message_id="msg-orphaned-456",
        old_parent_uuid=None,  # Was orphaned
        new_parent_uuid="msg-parent-789",
        operator="user:tryk",
        reason="semantic similarity (0.87)",
        similarity_score=0.87,
        validation_passed=True
    )
    print(f"Created event: {event1.event_id}")
    print(f"  Digest: {event1.event_digest[:16]}...\n")

    # 2. Create a second event
    event2 = RepairEvent(
        event_id=generate_event_id(),
        session_id="session-abc-123",
        timestamp=datetime.now(timezone.utc),
        message_id="msg-orphaned-999",
        old_parent_uuid=None,
        new_parent_uuid="msg-parent-789",
        operator="user:tryk",
        reason="timestamp proximity",
        similarity_score=0.65
    )
    print(f"Created event: {event2.event_id}\n")

    # 3. Replay events
    events = [event1, event2]
    result = replay_repair_events(events)
    print("Replay result:")
    print(f"  Total events: {result.total_events}")
    print(f"  Active events: {result.active_events}")
    print(f"  Messages repaired: {len(result.messages_repaired)}")
    print(f"  Current state: {result.message_parents}\n")

    # 4. Validate immutability
    validation = validate_event_immutability(event1, events)
    print(f"Validation: {'✓ PASS' if validation.is_valid else '✗ FAIL'}")
    if validation.errors:
        print(f"  Errors: {validation.errors}")
    if validation.warnings:
        print(f"  Warnings: {validation.warnings}")
    print()

    # 5. Calculate session digest
    digest = calculate_session_digest(events)
    print(f"Session digest: {digest[:16]}...\n")

    # 6. Export event log
    log_json = export_event_log("session-abc-123", events)
    print(f"Exported event log ({len(log_json)} bytes):")
    print(log_json[:200] + "...\n")

    # 7. Create revert event
    revert = create_revert_event(event1, "user:tryk", "Testing revert")
    print(f"Created revert event: {revert.event_id}")
    print(f"  Reverts: {revert.reverts_event_id}\n")

    # 8. Replay with revert
    events_with_revert = events + [revert]
    result2 = replay_repair_events(events_with_revert)
    print("Replay with revert:")
    print(f"  Active events: {result2.active_events}")
    print(f"  Reverted events: {result2.reverted_events}")
    print(f"  Current state: {result2.message_parents}\n")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print(__doc__)
    print("\n" + "=" * 60 + "\n")
    example_usage()
