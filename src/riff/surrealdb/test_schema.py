"""
Test schema validation and utilities.

Run with: python -m pytest src/riff/surrealdb/test_schema.py -v
"""


from .schema_utils import (
    build_high_corruption_query,
    build_orphaned_messages_query,
    build_parent_candidates_query,
    build_session_stats_query,
    build_time_range_query,
    prepare_message_record,
    prepare_session_record,
    prepare_thread_record,
    validate_message_data,
    validate_session_data,
    validate_thread_data,
)


class TestSessionValidation:
    """Test session data validation."""

    def test_valid_session(self):
        """Test validation of valid session data."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_count": 10,
            "thread_count": 2,
            "corruption_score": 0.1,
            "last_updated": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-15T09:00:00Z",
        }
        is_valid, error = validate_session_data(data)
        assert is_valid is True
        assert error is None

    def test_missing_session_id(self):
        """Test validation fails for missing session_id."""
        data = {
            "message_count": 10,
            "last_updated": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-15T09:00:00Z",
        }
        is_valid, error = validate_session_data(data)
        assert is_valid is False
        assert "session_id" in error

    def test_invalid_corruption_score(self):
        """Test validation fails for invalid corruption_score."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "corruption_score": 1.5,  # Invalid: > 1.0
            "last_updated": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-15T09:00:00Z",
        }
        is_valid, error = validate_session_data(data)
        assert is_valid is False
        assert "corruption_score" in error

    def test_negative_message_count(self):
        """Test validation fails for negative message_count."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_count": -5,  # Invalid: negative
            "last_updated": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-15T09:00:00Z",
        }
        is_valid, error = validate_session_data(data)
        assert is_valid is False
        assert "message_count" in error


class TestMessageValidation:
    """Test message data validation."""

    def test_valid_message(self):
        """Test validation of valid message data."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_uuid": "msg-001",
            "parent_uuid": "msg-000",
            "message_type": "user",
            "role": "user",
            "content": "Hello, world!",
            "timestamp": "2025-01-15T10:00:00Z",
            "thread_id": "thread-001",
            "is_orphaned": False,
            "corruption_score": 0.0,
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_message_data(data)
        assert is_valid is True
        assert error is None

    def test_invalid_message_type(self):
        """Test validation fails for invalid message_type."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_uuid": "msg-001",
            "message_type": "invalid",  # Invalid: not in allowed values
            "role": "user",
            "content": "Hello",
            "timestamp": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_message_data(data)
        assert is_valid is False
        assert "message_type" in error

    def test_missing_content(self):
        """Test validation fails for missing content."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "message_uuid": "msg-001",
            "message_type": "user",
            "role": "user",
            "timestamp": "2025-01-15T10:00:00Z",
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_message_data(data)
        assert is_valid is False
        assert "content" in error


class TestThreadValidation:
    """Test thread data validation."""

    def test_valid_thread(self):
        """Test validation of valid thread data."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "thread_type": "main",
            "message_count": 5,
            "topic": "Discussion about AI",
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_thread_data(data)
        assert is_valid is True
        assert error is None

    def test_invalid_thread_type(self):
        """Test validation fails for invalid thread_type."""
        data = {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "thread_type": "invalid",  # Invalid: not in allowed values
            "created_at": "2025-01-15T10:00:00Z",
        }
        is_valid, error = validate_thread_data(data)
        assert is_valid is False
        assert "thread_type" in error


class TestRecordPreparation:
    """Test record preparation utilities."""

    def test_prepare_session_record(self):
        """Test session record preparation."""
        record = prepare_session_record(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            message_count=10,
            thread_count=2,
            corruption_score=0.1,
        )

        assert record["session_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert record["message_count"] == 10
        assert record["thread_count"] == 2
        assert record["corruption_score"] == 0.1
        assert "last_updated" in record
        assert "created_at" in record

        # Validate prepared record
        is_valid, error = validate_session_data(record)
        assert is_valid is True

    def test_prepare_message_record(self):
        """Test message record preparation."""
        record = prepare_message_record(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            message_uuid="msg-001",
            message_type="user",
            role="user",
            content="Hello, world!",
            timestamp="2025-01-15T10:00:00Z",
            parent_uuid="msg-000",
            thread_id="thread-001",
        )

        assert record["session_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert record["message_uuid"] == "msg-001"
        assert record["parent_uuid"] == "msg-000"
        assert record["content"] == "Hello, world!"
        assert "created_at" in record

        # Validate prepared record
        is_valid, error = validate_message_data(record)
        assert is_valid is True

    def test_prepare_message_without_optional_fields(self):
        """Test message record preparation without optional fields."""
        record = prepare_message_record(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            message_uuid="msg-001",
            message_type="user",
            role="user",
            content="Hello, world!",
            timestamp="2025-01-15T10:00:00Z",
        )

        assert "parent_uuid" not in record
        assert "thread_id" not in record

        # Validate prepared record
        is_valid, error = validate_message_data(record)
        assert is_valid is True

    def test_prepare_thread_record(self):
        """Test thread record preparation."""
        record = prepare_thread_record(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            thread_type="main",
            message_count=5,
            topic="AI Discussion",
        )

        assert record["session_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert record["thread_type"] == "main"
        assert record["message_count"] == 5
        assert record["topic"] == "AI Discussion"
        assert "created_at" in record

        # Validate prepared record
        is_valid, error = validate_thread_data(record)
        assert is_valid is True


class TestQueryBuilders:
    """Test query builder utilities."""

    def test_build_orphaned_messages_query(self):
        """Test orphaned messages query builder."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        query = build_orphaned_messages_query(session_id)

        assert session_id in query
        assert "is_orphaned = true" in query
        assert "ORDER BY timestamp DESC" in query

    def test_build_session_stats_query(self):
        """Test session stats query builder."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        query = build_session_stats_query(session_id)

        assert session_id in query
        assert "COUNT()" in query
        assert "math::sum(is_orphaned)" in query
        assert "math::avg(corruption_score)" in query

    def test_build_parent_candidates_query(self):
        """Test parent candidates query builder."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        orphan_timestamp = "2025-01-15T10:00:00Z"
        query = build_parent_candidates_query(
            session_id, orphan_timestamp, limit=10
        )

        assert session_id in query
        assert orphan_timestamp in query
        assert "LIMIT 10" in query
        assert "timestamp <" in query

    def test_build_high_corruption_query(self):
        """Test high corruption query builder."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        query = build_high_corruption_query(
            session_id, threshold=0.7, limit=15
        )

        assert session_id in query
        assert "corruption_score > 0.7" in query
        assert "LIMIT 15" in query

    def test_build_time_range_query(self):
        """Test time range query builder."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        start_time = "2025-01-15T00:00:00Z"
        end_time = "2025-01-15T23:59:59Z"
        query = build_time_range_query(session_id, start_time, end_time)

        assert session_id in query
        assert start_time in query
        assert end_time in query
        assert "timestamp >=" in query
        assert "timestamp <=" in query
