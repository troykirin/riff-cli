"""
Tests for SurrealDBStorage with immutable event-based repairs.

Demonstrates:
- RepairEvent creation and validation
- Immutable event logging
- Session materialization from event replay
- HTTP API mocking for testing
- Error handling and edge cases
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest  # type: ignore[import-not-found]
import httpx

from .storage import (
    SurrealDBStorage,
    RepairEvent,
    SurrealDBConnectionError,
    RepairEventValidationError,
    SessionNotFoundError,
    create_surrealdb_storage,
)
from ..graph.models import Message, MessageType
from ..graph.repair import RepairOperation as EngineRepairOperation


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_http_client() -> Mock:
    """Create mock HTTP client for testing."""
    client = Mock(spec=httpx.Client)

    # Mock successful connection test
    response = Mock()
    response.json.return_value = [
        {
            "status": "OK",
            "result": [{"info": "database info"}],
        }
    ]
    response.raise_for_status = Mock()
    client.post.return_value = response
    client.get.return_value = response

    return client


@pytest.fixture
def storage(mock_http_client: Mock) -> SurrealDBStorage:
    """Create SurrealDBStorage instance with mocked HTTP client."""
    return SurrealDBStorage(
        base_url="http://localhost:8000",
        namespace="conversations",
        database="repairs",
        http_client=mock_http_client,
    )


@pytest.fixture
def sample_message() -> Message:
    """Create sample message for testing."""
    return Message(
        uuid="msg-123",
        parent_uuid=None,
        type=MessageType.USER,
        content="Sample message content",
        timestamp="2024-01-15T10:30:00Z",
        session_id="session-abc",
        is_orphaned=True,
        corruption_score=0.8,
    )


@pytest.fixture
def sample_repair_op() -> EngineRepairOperation:
    """Create sample repair operation."""
    return EngineRepairOperation(
        message_id="msg-123",
        original_parent_uuid=None,
        suggested_parent_uuid="msg-456",
        similarity_score=0.85,
        reason="High semantic similarity",
        timestamp=datetime.now(timezone.utc),
    )


# ============================================================================
# RepairEvent Tests
# ============================================================================


def test_repair_event_creation():
    """Test RepairEvent creation with valid data."""
    event = RepairEvent(
        session_id="session-abc",
        timestamp=datetime.now(timezone.utc),
        operator="test-user",
        message_id="msg-123",
        old_parent_uuid=None,
        new_parent_uuid="msg-456",
        reason="Test repair",
        validation_passed=True,
    )

    assert event.session_id == "session-abc"
    assert event.message_id == "msg-123"
    assert event.new_parent_uuid == "msg-456"
    assert event.validation_passed is True
    assert len(event.event_id) > 0  # UUID generated


def test_repair_event_validation_empty_session_id():
    """Test RepairEvent validation fails with empty session_id."""
    with pytest.raises(RepairEventValidationError, match="session_id cannot be empty"):
        RepairEvent(
            session_id="",
            timestamp=datetime.now(timezone.utc),
            operator="test-user",
            message_id="msg-123",
            old_parent_uuid=None,
            new_parent_uuid="msg-456",
            reason="Test",
            validation_passed=True,
        )


def test_repair_event_validation_empty_message_id():
    """Test RepairEvent validation fails with empty message_id."""
    with pytest.raises(RepairEventValidationError, match="message_id cannot be empty"):
        RepairEvent(
            session_id="session-abc",
            timestamp=datetime.now(timezone.utc),
            operator="test-user",
            message_id="",
            old_parent_uuid=None,
            new_parent_uuid="msg-456",
            reason="Test",
            validation_passed=True,
        )


def test_repair_event_from_repair_operation(sample_repair_op: EngineRepairOperation):
    """Test creating RepairEvent from RepairOperation."""
    event = RepairEvent.from_repair_operation(
        session_id="session-abc",
        repair_op=sample_repair_op,
        operator="tui-user",
        validation_passed=True,
    )

    assert event.session_id == "session-abc"
    assert event.message_id == sample_repair_op.message_id
    assert event.old_parent_uuid == sample_repair_op.original_parent_uuid
    assert event.new_parent_uuid == sample_repair_op.suggested_parent_uuid
    assert event.reason == sample_repair_op.reason
    assert event.operator == "tui-user"
    assert event.validation_passed is True


def test_repair_event_to_dict():
    """Test RepairEvent serialization to dict."""
    event = RepairEvent(
        session_id="session-abc",
        timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        operator="test-user",
        message_id="msg-123",
        old_parent_uuid="msg-old",
        new_parent_uuid="msg-456",
        reason="Test repair",
        validation_passed=True,
        event_id="event-xyz",
    )

    result = event.to_dict()

    assert result["session_id"] == "session-abc"
    assert result["message_id"] == "msg-123"
    assert result["old_parent_uuid"] == "msg-old"
    assert result["new_parent_uuid"] == "msg-456"
    assert result["operator"] == "test-user"
    assert result["validation_passed"] is True
    assert result["event_id"] == "event-xyz"
    assert "2024-01-15" in result["timestamp"]


def test_repair_event_from_dict():
    """Test RepairEvent deserialization from dict."""
    data = {
        "session_id": "session-abc",
        "timestamp": "2024-01-15T10:30:00+00:00",
        "operator": "test-user",
        "message_id": "msg-123",
        "old_parent_uuid": "msg-old",
        "new_parent_uuid": "msg-456",
        "reason": "Test repair",
        "validation_passed": True,
        "event_id": "event-xyz",
    }

    event = RepairEvent.from_dict(data)

    assert event.session_id == "session-abc"
    assert event.message_id == "msg-123"
    assert event.old_parent_uuid == "msg-old"
    assert event.new_parent_uuid == "msg-456"
    assert event.operator == "test-user"
    assert event.validation_passed is True
    assert event.event_id == "event-xyz"


# ============================================================================
# SurrealDBStorage Tests
# ============================================================================


def test_storage_initialization(storage: SurrealDBStorage):
    """Test SurrealDBStorage initialization."""
    assert storage.base_url == "http://localhost:8000"
    assert storage.namespace == "conversations"
    assert storage.database == "repairs"
    assert storage.timeout == 30.0


def test_storage_connection_failure():
    """Test SurrealDBStorage connection failure."""
    client = Mock()
    client.post.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(SurrealDBConnectionError, match="Failed to connect"):
        SurrealDBStorage(http_client=client)


def test_log_repair_event_success(
    storage: SurrealDBStorage,
    mock_http_client: Mock,
    sample_repair_op: EngineRepairOperation,
):
    """Test successful repair event logging."""
    # Mock successful CREATE query
    response = Mock()
    response.json.return_value = [
        {
            "status": "OK",
            "result": [{"id": "repairs_events:1", "event_id": "event-xyz"}],
        }
    ]
    response.raise_for_status = Mock()
    mock_http_client.post.return_value = response

    result = storage.log_repair_event(sample_repair_op, operator="test-user")

    assert result is True

    # Verify query was called
    assert mock_http_client.post.called
    call_args = mock_http_client.post.call_args
    payload = call_args.kwargs["json"]

    assert "CREATE repairs_events CONTENT" in payload["query"]
    assert "event" in payload["variables"]


def test_get_session_history_empty(storage: SurrealDBStorage, mock_http_client: Mock):
    """Test getting session history with no events."""
    # Mock empty result
    response = Mock()
    response.json.return_value = [{"status": "OK", "result": []}]
    response.raise_for_status = Mock()
    mock_http_client.post.return_value = response

    history = storage.get_session_history("session-abc")

    assert len(history) == 0
    assert isinstance(history, list)


def test_get_session_history_with_events(
    storage: SurrealDBStorage, mock_http_client: Mock
):
    """Test getting session history with multiple events."""
    # Mock result with events
    response = Mock()
    response.json.return_value = [
        {
            "status": "OK",
            "result": [
                {
                    "event_id": "event-1",
                    "session_id": "session-abc",
                    "timestamp": "2024-01-15T10:00:00+00:00",
                    "operator": "user1",
                    "message_id": "msg-1",
                    "old_parent_uuid": None,
                    "new_parent_uuid": "msg-2",
                    "reason": "First repair",
                    "validation_passed": True,
                },
                {
                    "event_id": "event-2",
                    "session_id": "session-abc",
                    "timestamp": "2024-01-15T11:00:00+00:00",
                    "operator": "user2",
                    "message_id": "msg-3",
                    "old_parent_uuid": "msg-2",
                    "new_parent_uuid": "msg-4",
                    "reason": "Second repair",
                    "validation_passed": True,
                },
            ],
        }
    ]
    response.raise_for_status = Mock()
    mock_http_client.post.return_value = response

    history = storage.get_session_history("session-abc")

    assert len(history) == 2
    assert history[0].event_id == "event-1"
    assert history[0].operator == "user1"
    assert history[1].event_id == "event-2"
    assert history[1].operator == "user2"


def test_load_messages_not_found(storage: SurrealDBStorage, mock_http_client: Mock):
    """Test loading messages for non-existent session."""
    # Mock empty result
    response = Mock()
    response.json.return_value = [{"status": "OK", "result": []}]
    response.raise_for_status = Mock()
    mock_http_client.post.return_value = response

    with pytest.raises(SessionNotFoundError, match="No messages found"):
        storage.load_messages("nonexistent-session")


def test_load_messages_success(storage: SurrealDBStorage, mock_http_client: Mock):
    """Test successfully loading messages."""
    # Mock result with messages
    response = Mock()
    response.json.return_value = [
        {
            "status": "OK",
            "result": [
                {
                    "message_uuid": "msg-1",
                    "session_id": "session-abc",
                    "parent_uuid": None,
                    "message_type": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-15T10:00:00+00:00",
                    "is_orphaned": False,
                    "corruption_score": 0.0,
                },
                {
                    "message_uuid": "msg-2",
                    "session_id": "session-abc",
                    "parent_uuid": "msg-1",
                    "message_type": "assistant",
                    "content": "Hi there",
                    "timestamp": "2024-01-15T10:01:00+00:00",
                    "is_orphaned": False,
                    "corruption_score": 0.0,
                },
            ],
        }
    ]
    response.raise_for_status = Mock()
    mock_http_client.post.return_value = response

    messages = storage.load_messages("session-abc")

    assert len(messages) == 2
    assert messages[0].uuid == "msg-1"
    assert messages[0].type == MessageType.USER
    assert messages[1].uuid == "msg-2"
    assert messages[1].type == MessageType.ASSISTANT


def test_materialize_session_no_repairs(
    storage: SurrealDBStorage, mock_http_client: Mock
):
    """Test materializing session with no repair events."""
    # Mock messages query
    messages_response = Mock()
    messages_response.json.return_value = [
        {
            "status": "OK",
            "result": [
                {
                    "message_uuid": "msg-1",
                    "session_id": "session-abc",
                    "parent_uuid": None,
                    "message_type": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-15T10:00:00+00:00",
                    "is_orphaned": False,
                    "corruption_score": 0.0,
                }
            ],
        }
    ]
    messages_response.raise_for_status = Mock()

    # Mock empty repair events query
    events_response = Mock()
    events_response.json.return_value = [{"status": "OK", "result": []}]
    events_response.raise_for_status = Mock()

    # Mock cache query
    cache_response = Mock()
    cache_response.json.return_value = [{"status": "OK", "result": []}]
    cache_response.raise_for_status = Mock()

    # Setup mock to return different responses
    mock_http_client.post.side_effect = [
        messages_response,
        events_response,
        cache_response,
    ]

    session = storage.materialize_session("session-abc")

    assert session.session_id == "session-abc"
    assert len(session.messages) == 1


def test_create_surrealdb_storage_factory():
    """Test factory function for creating storage."""
    client = Mock()
    client.post.return_value = Mock(
        json=lambda: [{"status": "OK", "result": [{"info": "db"}]}],
        raise_for_status=Mock(),
    )

    storage = create_surrealdb_storage(
        base_url="http://test:9000",
        namespace="test-ns",
        database="test-db",
        http_client=client,
    )

    assert storage.base_url == "http://test:9000"
    assert storage.namespace == "test-ns"
    assert storage.database == "test-db"


# ============================================================================
# Integration Tests (require running SurrealDB)
# ============================================================================


@pytest.mark.integration
@pytest.mark.skip(reason="Requires running SurrealDB instance")
def test_full_repair_workflow_integration():
    """
    Full integration test with real SurrealDB.

    Requirements:
    - SurrealDB running on localhost:8000
    - Namespace: conversations
    - Database: repairs

    Workflow:
    1. Create session with orphaned message
    2. Log repair event
    3. Materialize session
    4. Verify repair was applied
    """
    storage = create_surrealdb_storage()

    # Create repair operation
    repair_op = EngineRepairOperation(
        message_id="integration-msg-1",
        original_parent_uuid=None,
        suggested_parent_uuid="integration-msg-0",
        similarity_score=0.9,
        reason="Integration test repair",
        timestamp=datetime.now(timezone.utc),
    )

    # Log repair event
    success = storage.log_repair_event(repair_op, operator="integration-test")
    assert success is True

    # Get history
    history = storage.get_session_history("integration-session")
    assert len(history) > 0

    # Verify last event
    last_event = history[-1]
    assert last_event.message_id == "integration-msg-1"
    assert last_event.new_parent_uuid == "integration-msg-0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
