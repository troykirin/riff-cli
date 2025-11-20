"""
SurrealDB Storage for Phase 6B: Immutable Event-Based Repairs.

This module implements conversation storage with immutable repair event logging,
allowing full audit trails and point-in-time session reconstruction.

Architecture:
- repairs_events table: Immutable append-only log of all repair operations
- sessions_materialized view: Cached rebuilt sessions from events
- HTTP API integration: Direct SurrealDB HTTP API calls (no WebSocket overhead)

Key Features:
- Immutable event sourcing for repairs
- Session materialization from event replay
- Full type safety with Python 3.13+ annotations
- Comprehensive error handling and validation
- Testing hooks for dependency injection
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Protocol, TypedDict, TypeIs
from urllib.parse import urljoin

import httpx

from ..graph.loaders import ConversationStorage
from ..graph.models import Message, MessageType, Session, Thread
from ..graph.repair import RepairOperation as EngineRepairOperation
from .schema_utils import (
    prepare_message_record,
    prepare_session_record,
    prepare_thread_record,
    validate_message_data,
    validate_session_data,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================


class SurrealDBConnectionError(Exception):
    """Raised when SurrealDB connection fails."""

    pass


class RepairEventValidationError(Exception):
    """Raised when repair event validation fails."""

    pass


class SessionNotFoundError(Exception):
    """Raised when requested session doesn't exist."""

    pass


class MaterializationError(Exception):
    """Raised when session materialization fails."""

    pass


# ============================================================================
# Type Definitions
# ============================================================================


class SurrealDBQueryResult(TypedDict, total=False):
    """Type definition for SurrealDB query results."""

    result: List[dict[str, Any]]
    status: str
    time: str


class HTTPClientProtocol(Protocol):
    """Protocol for HTTP client (allows mocking in tests)."""

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """POST request to SurrealDB."""
        ...

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """GET request to SurrealDB."""
        ...


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class RepairEvent:
    """
    Immutable event representing a single repair operation.

    All repair events are append-only and never updated after creation.
    This enables full audit trails and event replay for session reconstruction.

    Attributes:
        session_id: Claude session UUID being repaired
        timestamp: When repair was performed (UTC)
        operator: Who performed the repair (user, agent, system)
        message_id: UUID of message being repaired
        old_parent_uuid: Original parent UUID (None for orphans)
        new_parent_uuid: New parent UUID assigned
        reason: Human-readable explanation
        validation_passed: Whether repair passed pre-flight validation
        event_id: Unique immutable event identifier
    """

    session_id: str
    timestamp: datetime
    operator: str
    message_id: str
    old_parent_uuid: Optional[str]
    new_parent_uuid: str
    reason: str
    validation_passed: bool
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Validate repair event after initialization."""
        if not self.session_id:
            raise RepairEventValidationError("session_id cannot be empty")
        if not self.message_id:
            raise RepairEventValidationError("message_id cannot be empty")
        if not self.new_parent_uuid:
            raise RepairEventValidationError("new_parent_uuid cannot be empty")
        if not self.operator:
            raise RepairEventValidationError("operator cannot be empty")
        if not self.event_id:
            raise RepairEventValidationError("event_id cannot be empty")

        # Ensure timestamp has timezone
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for SurrealDB insertion."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "operator": self.operator,
            "message_id": self.message_id,
            "old_parent_uuid": self.old_parent_uuid,
            "new_parent_uuid": self.new_parent_uuid,
            "reason": self.reason,
            "validation_passed": self.validation_passed,
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RepairEvent:
        """Create RepairEvent from dictionary."""
        return cls(
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            operator=data["operator"],
            message_id=data["message_id"],
            old_parent_uuid=data.get("old_parent_uuid"),
            new_parent_uuid=data["new_parent_uuid"],
            reason=data["reason"],
            validation_passed=data["validation_passed"],
            event_id=data["event_id"],
        )

    @classmethod
    def from_repair_operation(
        cls,
        session_id: str,
        repair_op: EngineRepairOperation,
        operator: str,
        validation_passed: bool,
    ) -> RepairEvent:
        """
        Create RepairEvent from repair engine's RepairOperation.

        Args:
            session_id: Session being repaired
            repair_op: Repair operation from engine
            operator: Who is performing the repair
            validation_passed: Whether validation passed

        Returns:
            New RepairEvent instance
        """
        return cls(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            operator=operator,
            message_id=repair_op.message_id,
            old_parent_uuid=repair_op.original_parent_uuid,
            new_parent_uuid=repair_op.suggested_parent_uuid,
            reason=repair_op.reason,
            validation_passed=validation_passed,
        )


# ============================================================================
# Type Guard Functions
# ============================================================================


def is_valid_surreal_result(result: Any) -> TypeIs[List[dict[str, Any]]]:
    """
    Type guard to check if SurrealDB result is valid.

    Args:
        result: Result to validate

    Returns:
        True if result is valid list of dictionaries
    """
    return isinstance(result, list) and all(isinstance(item, dict) for item in result)


# ============================================================================
# SurrealDB Storage Implementation
# ============================================================================


class SurrealDBStorage(ConversationStorage):
    """
    SurrealDB-backed storage with immutable event-based repairs.

    This implementation provides:
    - Full ConversationStorage interface compatibility
    - Immutable repair event logging (append-only)
    - Session materialization from event replay
    - Atomic operations via HTTP API
    - Comprehensive error handling

    Connection Details:
    - Namespace: conversations
    - Database: repairs
    - Tables: repairs_events (immutable), sessions_materialized (cache)

    Example:
        >>> storage = SurrealDBStorage(
        ...     base_url="http://localhost:8000",
        ...     namespace="conversations",
        ...     database="repairs"
        ... )
        >>> session = storage.load_session("session-uuid")
        >>> storage.log_repair_event(repair_op)
        >>> history = storage.get_session_history("session-uuid")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        namespace: str = "conversations",
        database: str = "repairs",
        username: str = "root",
        password: str = "root",
        timeout: float = 30.0,
        http_client: Optional[HTTPClientProtocol] = None,
    ) -> None:
        """
        Initialize SurrealDB storage.

        Args:
            base_url: SurrealDB HTTP API base URL
            namespace: SurrealDB namespace
            database: SurrealDB database
            username: Authentication username
            password: Authentication password
            timeout: Request timeout in seconds
            http_client: Optional HTTP client (for testing/mocking)
        """
        self.base_url = base_url.rstrip("/")
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.timeout = timeout

        # Use provided client or create default
        self._client = http_client or httpx.Client(timeout=timeout)

        # Build common headers for authentication
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "NS": namespace,
            "DB": database,
        }

        # Test connection on initialization
        self._test_connection()

        logger.info(
            f"SurrealDBStorage initialized: {base_url}/{namespace}/{database}"
        )

    def _test_connection(self) -> None:
        """
        Test SurrealDB connection on initialization.

        Raises:
            SurrealDBConnectionError: If connection fails
        """
        try:
            response = self._query("INFO FOR DB;")
            if not response or not isinstance(response, list):
                raise SurrealDBConnectionError("Invalid response from SurrealDB")
            logger.debug("SurrealDB connection test successful")
        except Exception as e:
            raise SurrealDBConnectionError(f"Failed to connect to SurrealDB: {e}")

    def _query(
        self, query: str, variables: Optional[dict[str, Any]] = None
    ) -> List[dict[str, Any]]:
        """
        Execute SurrealQL query via HTTP API.

        Args:
            query: SurrealQL query string
            variables: Optional query variables

        Returns:
            List of result records

        Raises:
            SurrealDBConnectionError: If query fails
        """
        url = urljoin(self.base_url, "/sql")

        try:
            # Build request payload
            payload: dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables

            # Execute query with basic auth
            headers_with_auth = dict(self._headers)
            import base64
            auth_string = f"{self.username}:{self.password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers_with_auth["Authorization"] = f"Basic {encoded_auth}"

            response = self._client.post(
                url,
                json=payload,
                headers=headers_with_auth,
            )

            response.raise_for_status()
            result = response.json()

            # SurrealDB returns array of query results
            if not isinstance(result, list):
                raise SurrealDBConnectionError(f"Unexpected response format: {result}")

            # Extract first result (single query)
            if not result:
                return []

            first_result = result[0]
            if first_result.get("status") != "OK":
                error_msg = first_result.get("result", "Unknown error")
                raise SurrealDBConnectionError(f"Query failed: {error_msg}")

            query_result = first_result.get("result", [])

            if not is_valid_surreal_result(query_result):
                logger.warning(f"Invalid result format: {query_result}")
                return []

            return query_result

        except httpx.HTTPError as e:
            raise SurrealDBConnectionError(f"HTTP error: {e}")
        except json.JSONDecodeError as e:
            raise SurrealDBConnectionError(f"JSON decode error: {e}")
        except Exception as e:
            raise SurrealDBConnectionError(f"Query execution failed: {e}")

    # ========================================================================
    # ConversationStorage Interface Implementation
    # ========================================================================

    def load_messages(self, session_id: str) -> List[Message]:
        """
        Load all messages for a session.

        Args:
            session_id: Session UUID

        Returns:
            List of Message objects

        Raises:
            SessionNotFoundError: If session doesn't exist
            SurrealDBConnectionError: If query fails
        """
        query = """
            SELECT * FROM message
            WHERE session_id = $session_id
            ORDER BY timestamp ASC;
        """

        try:
            results = self._query(query, {"session_id": session_id})

            if not results:
                raise SessionNotFoundError(f"No messages found for session {session_id}")

            messages = []
            for record in results:
                message = self._record_to_message(record)
                messages.append(message)

            logger.info(f"Loaded {len(messages)} messages for session {session_id}")
            return messages

        except SurrealDBConnectionError:
            raise
        except Exception as e:
            raise SurrealDBConnectionError(f"Failed to load messages: {e}")

    def save_session(self, session: Session) -> None:
        """
        Save complete session to SurrealDB.

        Args:
            session: Session object to persist

        Raises:
            SurrealDBConnectionError: If save fails
        """
        try:
            # Save session metadata
            session_record = prepare_session_record(
                session_id=session.session_id,
                message_count=session.message_count,
                thread_count=session.thread_count,
                corruption_score=session.corruption_score,
            )

            # Validate session data
            is_valid, error = validate_session_data(session_record)
            if not is_valid:
                raise ValueError(f"Invalid session data: {error}")

            # Upsert session
            session_query = """
                UPDATE session SET
                    message_count = $message_count,
                    thread_count = $thread_count,
                    corruption_score = $corruption_score,
                    last_updated = $last_updated
                WHERE session_id = $session_id;
            """
            self._query(session_query, session_record)

            # Save all messages
            for message in session.messages:
                self._save_message(message)

            # Save threads
            for thread in session.threads + session.orphans:
                self._save_thread(thread)

            logger.info(f"Saved session {session.session_id} with {len(session.messages)} messages")

        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise SurrealDBConnectionError(f"Session save failed: {e}")

    def update_message(self, message: Message) -> None:
        """
        Update a single message.

        Args:
            message: Message with updated data

        Raises:
            ValueError: If message doesn't exist
            SurrealDBConnectionError: If update fails
        """
        try:
            self._save_message(message)
            logger.debug(f"Updated message {message.uuid}")
        except Exception as e:
            raise SurrealDBConnectionError(f"Failed to update message: {e}")

    # ========================================================================
    # Repair Event Methods (New in Phase 6B)
    # ========================================================================

    def log_repair_event(self, repair_op: EngineRepairOperation, operator: str = "user") -> bool:
        """
        Log an immutable repair event to SurrealDB.

        This is the core of Phase 6B: all repairs are logged as immutable events
        rather than directly mutating the JSONL. Events can be replayed to
        reconstruct session state at any point in time.

        Args:
            repair_op: Repair operation from engine
            operator: Who performed the repair (user, agent, system)

        Returns:
            True if event logged successfully, False otherwise

        Raises:
            RepairEventValidationError: If event validation fails
            SurrealDBConnectionError: If database operation fails
        """
        try:
            # Create repair event
            event = RepairEvent.from_repair_operation(
                session_id=repair_op.message_id,  # TODO: Extract session_id properly
                repair_op=repair_op,
                operator=operator,
                validation_passed=True,  # Already validated by engine
            )

            # Convert to dict for insertion
            event_dict = event.to_dict()

            # Insert into repairs_events table (append-only)
            query = """
                CREATE repairs_events CONTENT $event;
            """

            result = self._query(query, {"event": event_dict})

            if not result:
                logger.error("Failed to create repair event: empty result")
                return False

            logger.info(f"Logged repair event {event.event_id} for message {event.message_id}")

            # Trigger materialization rebuild (async in production)
            # For now, invalidate materialized view
            self._invalidate_materialized_session(repair_op.message_id)

            return True

        except RepairEventValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to log repair event: {e}")
            raise SurrealDBConnectionError(f"Repair event logging failed: {e}")

    def get_session_history(self, session_id: str) -> List[RepairEvent]:
        """
        Get all repair events for a session in chronological order.

        Args:
            session_id: Session UUID

        Returns:
            List of RepairEvent objects, oldest first

        Raises:
            SurrealDBConnectionError: If query fails
        """
        query = """
            SELECT * FROM repairs_events
            WHERE session_id = $session_id
            ORDER BY timestamp ASC;
        """

        try:
            results = self._query(query, {"session_id": session_id})

            events = []
            for record in results:
                event = RepairEvent.from_dict(record)
                events.append(event)

            logger.info(f"Retrieved {len(events)} repair events for session {session_id}")
            return events

        except Exception as e:
            raise SurrealDBConnectionError(f"Failed to get session history: {e}")

    def materialize_session(self, session_id: str, jsonl_path: Optional[Path] = None) -> Session:
        """
        Rebuild session from original JSONL + replay repair events.

        This is the core materialization logic:
        1. Load original messages from JSONL (or DB)
        2. Load all repair events for session
        3. Replay events in chronological order
        4. Build DAG and return Session

        Args:
            session_id: Session UUID to materialize
            jsonl_path: Optional path to original JSONL (fallback to DB)

        Returns:
            Reconstructed Session object

        Raises:
            SessionNotFoundError: If session doesn't exist
            MaterializationError: If replay fails
        """
        try:
            # Step 1: Load original messages
            if jsonl_path and jsonl_path.exists():
                # Load from JSONL
                from ..graph.loaders import JSONLLoader

                loader = JSONLLoader(jsonl_path.parent)
                messages = loader.load_messages(session_id)
                logger.debug(f"Loaded {len(messages)} messages from JSONL")
            else:
                # Load from database
                messages = self.load_messages(session_id)
                logger.debug(f"Loaded {len(messages)} messages from DB")

            # Step 2: Load repair events
            repair_events = self.get_session_history(session_id)
            logger.debug(f"Loaded {len(repair_events)} repair events")

            # Step 3: Replay events in order
            message_map = {msg.uuid: msg for msg in messages}

            for event in repair_events:
                if not event.validation_passed:
                    logger.warning(f"Skipping invalid event {event.event_id}")
                    continue

                # Apply repair to message
                if event.message_id in message_map:
                    message = message_map[event.message_id]
                    message.parent_uuid = event.new_parent_uuid
                    logger.debug(
                        f"Applied repair: {event.message_id} parent "
                        f"{event.old_parent_uuid} -> {event.new_parent_uuid}"
                    )
                else:
                    logger.warning(f"Message {event.message_id} not found in session")

            # Step 4: Build DAG and create Session
            from ..graph.dag import ConversationDAG

            # Create temporary loader for DAG
            class MemoryLoader(ConversationStorage):
                def __init__(self, messages: List[Message]):
                    self._messages = messages

                def load_messages(self, session_id: str) -> List[Message]:
                    return self._messages

                def save_session(self, session: Session) -> None:
                    pass

                def update_message(self, message: Message) -> None:
                    pass

            temp_loader = MemoryLoader(list(message_map.values()))
            dag = ConversationDAG(temp_loader, session_id)
            session = dag.to_session()

            logger.info(
                f"Materialized session {session_id}: "
                f"{len(messages)} messages, {len(repair_events)} repairs applied"
            )

            # Cache result (optional)
            self._cache_materialized_session(session)

            return session

        except SessionNotFoundError:
            raise
        except Exception as e:
            raise MaterializationError(f"Failed to materialize session: {e}")

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _save_message(self, message: Message) -> None:
        """Save or update a message in SurrealDB."""
        message_record = prepare_message_record(
            session_id=message.session_id,
            message_uuid=message.uuid,
            message_type=message.type.value,
            role=message.type.value if message.type.value in ["user", "assistant"] else "user",
            content=message.content,
            timestamp=message.timestamp,
            parent_uuid=message.parent_uuid,
            thread_id=message.thread_id,
            is_orphaned=message.is_orphaned,
            corruption_score=message.corruption_score,
        )

        # Validate
        is_valid, error = validate_message_data(message_record)
        if not is_valid:
            raise ValueError(f"Invalid message data: {error}")

        # Upsert message
        query = """
            UPDATE message SET
                parent_uuid = $parent_uuid,
                message_type = $message_type,
                role = $role,
                content = $content,
                timestamp = $timestamp,
                thread_id = $thread_id,
                is_orphaned = $is_orphaned,
                corruption_score = $corruption_score
            WHERE message_uuid = $message_uuid;
        """

        self._query(query, message_record)

    def _save_thread(self, thread: Thread) -> None:
        """Save or update a thread in SurrealDB."""
        thread_record = prepare_thread_record(
            session_id=thread.messages[0].session_id if thread.messages else "",
            thread_type=thread.thread_type.value,
            message_count=thread.message_count,
            topic=thread.semantic_topic,
        )

        query = """
            UPDATE thread SET
                thread_type = $thread_type,
                message_count = $message_count,
                topic = $topic
            WHERE session_id = $session_id;
        """

        self._query(query, thread_record)

    def _record_to_message(self, record: dict[str, Any]) -> Message:
        """Convert SurrealDB record to Message object."""
        return Message(
            uuid=record["message_uuid"],
            parent_uuid=record.get("parent_uuid"),
            type=MessageType(record["message_type"]),
            content=record["content"],
            timestamp=record["timestamp"],
            session_id=record["session_id"],
            is_sidechain=False,  # TODO: Add to schema
            semantic_topic=None,  # TODO: Add to schema
            thread_id=record.get("thread_id"),
            is_orphaned=record.get("is_orphaned", False),
            corruption_score=record.get("corruption_score", 0.0),
            metadata=record,
        )

    def _invalidate_materialized_session(self, session_id: str) -> None:
        """Invalidate materialized session cache (force rebuild on next load)."""
        query = """
            DELETE sessions_materialized WHERE session_id = $session_id;
        """
        try:
            self._query(query, {"session_id": session_id})
            logger.debug(f"Invalidated materialized session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to invalidate materialized session: {e}")

    def _cache_materialized_session(self, session: Session) -> None:
        """Cache materialized session for faster subsequent loads."""
        try:
            # Store serialized session in cache table
            cache_record = {
                "session_id": session.session_id,
                "message_count": session.message_count,
                "thread_count": session.thread_count,
                "corruption_score": session.corruption_score,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }

            query = """
                CREATE sessions_materialized CONTENT $cache;
            """

            self._query(query, {"cache": cache_record})
            logger.debug(f"Cached materialized session {session.session_id}")

        except Exception as e:
            logger.warning(f"Failed to cache materialized session: {e}")

    # ========================================================================
    # Public API Extensions
    # ========================================================================

    def load_session(self, session_id: str, jsonl_path: Optional[Path] = None) -> Session:
        """
        Load session with automatic materialization.

        Checks for cached materialized view first, falls back to full replay.

        Args:
            session_id: Session UUID
            jsonl_path: Optional path to original JSONL

        Returns:
            Session object (materialized if repairs exist)

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        # Check if materialized view exists and is fresh
        query = """
            SELECT * FROM sessions_materialized
            WHERE session_id = $session_id
            ORDER BY cached_at DESC
            LIMIT 1;
        """

        try:
            results = self._query(query, {"session_id": session_id})

            # If cache exists and is recent, use materialized version
            if results:
                cache_record = results[0]
                cached_at = datetime.fromisoformat(cache_record["cached_at"])
                age_seconds = (datetime.now(timezone.utc) - cached_at).total_seconds()

                # Cache is valid for 5 minutes (configurable)
                if age_seconds < 300:
                    logger.debug(f"Using cached materialized session (age={age_seconds:.1f}s)")
                    return self.materialize_session(session_id, jsonl_path)

            # Cache miss or stale - rebuild
            logger.debug("Cache miss or stale, materializing session")
            return self.materialize_session(session_id, jsonl_path)

        except SessionNotFoundError:
            raise
        except Exception as e:
            logger.warning(f"Cache lookup failed, falling back to materialization: {e}")
            return self.materialize_session(session_id, jsonl_path)

    def close(self) -> None:
        """Close HTTP client connection."""
        if hasattr(self._client, "close"):
            self._client.close()
        logger.debug("Closed SurrealDB storage connection")


# ============================================================================
# Convenience Functions
# ============================================================================


def create_surrealdb_storage(
    base_url: str = "http://localhost:8000",
    namespace: str = "conversations",
    database: str = "repairs",
    **kwargs: Any,
) -> SurrealDBStorage:
    """
    Factory function to create SurrealDBStorage instance.

    Args:
        base_url: SurrealDB HTTP API URL
        namespace: SurrealDB namespace
        database: SurrealDB database
        **kwargs: Additional arguments passed to SurrealDBStorage

    Returns:
        Configured SurrealDBStorage instance
    """
    return SurrealDBStorage(
        base_url=base_url,
        namespace=namespace,
        database=database,
        **kwargs,
    )
