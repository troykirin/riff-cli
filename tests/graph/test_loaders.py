"""
Tests for conversation storage loaders.

Tests JSONLLoader for proper parsing of Claude conversation files.
"""

import pytest
from pathlib import Path
from riff.graph import JSONLLoader, MessageType


class TestJSONLLoader:
    """Tests for JSONLLoader."""

    @pytest.fixture
    def loader(self) -> JSONLLoader:
        """Create loader for test conversations."""
        conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
        return JSONLLoader(conversations_dir)

    @pytest.fixture
    def test_session_id(self) -> str:
        """Test session ID (orphaned session)."""
        return "794650a6-84a5-446b-879c-639ee85fbde4"

    def test_loader_initialization(self, loader: JSONLLoader) -> None:
        """Test loader initializes correctly."""
        assert loader.conversations_dir.exists()
        assert loader.conversations_dir.is_dir()

    def test_loader_invalid_directory(self) -> None:
        """Test loader raises on invalid directory."""
        with pytest.raises(FileNotFoundError):
            JSONLLoader("/nonexistent/path")

    def test_list_sessions(self, loader: JSONLLoader) -> None:
        """Test session listing."""
        sessions = loader.list_sessions()
        assert len(sessions) > 0
        assert all(isinstance(s, str) for s in sessions)

    def test_session_exists(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test session existence check."""
        assert loader.session_exists(test_session_id)
        assert not loader.session_exists("nonexistent-session-id")

    def test_load_messages(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test message loading from JSONL."""
        messages = loader.load_messages(test_session_id)

        assert len(messages) > 0
        assert all(msg.session_id == test_session_id for msg in messages)

        # Check message structure
        for msg in messages:
            assert msg.uuid is not None
            assert isinstance(msg.type, MessageType)
            assert msg.timestamp is not None
            assert 0.0 <= msg.corruption_score <= 1.0

    def test_load_nonexistent_session(self, loader: JSONLLoader) -> None:
        """Test loading nonexistent session raises error."""
        with pytest.raises(FileNotFoundError):
            loader.load_messages("nonexistent-session-id")

    def test_message_content_extraction(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test content extraction from various message formats."""
        messages = loader.load_messages(test_session_id)

        # Find different message types
        user_msgs = [m for m in messages if m.type == MessageType.USER]
        assistant_msgs = [m for m in messages if m.type == MessageType.ASSISTANT]
        system_msgs = [m for m in messages if m.type == MessageType.SYSTEM]

        # Content should be strings (may be empty for some edge cases like "Warmup")
        assert all(isinstance(m.content, str) for m in user_msgs)
        assert all(isinstance(m.content, str) for m in assistant_msgs)

        # System messages may have empty content (that's ok)
        for msg in system_msgs:
            assert isinstance(msg.content, str)

    def test_message_parent_relationships(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test parent-child relationships are preserved."""
        messages = loader.load_messages(test_session_id)

        # Find messages with parents
        child_messages = [m for m in messages if m.parent_uuid is not None]
        assert len(child_messages) > 0

        # Check parent UUIDs are valid
        all_uuids = {m.uuid for m in messages}
        for child in child_messages:
            # Parent might be missing (orphaned case)
            # Just verify parent_uuid is a string
            assert isinstance(child.parent_uuid, str)

    def test_message_metadata_preservation(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test original JSONL metadata is preserved."""
        messages = loader.load_messages(test_session_id)

        for msg in messages:
            assert isinstance(msg.metadata, dict)
            assert "uuid" in msg.metadata or "type" in msg.metadata

    def test_sidechain_detection(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test sidechain message detection."""
        messages = loader.load_messages(test_session_id)

        sidechain_msgs = [m for m in messages if m.is_sidechain]
        # Test session has sidechains
        assert len(sidechain_msgs) > 0

        for msg in sidechain_msgs:
            assert msg.is_sidechain is True

    def test_corruption_score_calculation(self, loader: JSONLLoader, test_session_id: str) -> None:
        """Test corruption score is calculated for messages."""
        messages = loader.load_messages(test_session_id)

        # All messages should have valid corruption scores
        for msg in messages:
            assert isinstance(msg.corruption_score, float)
            assert 0.0 <= msg.corruption_score <= 1.0

        # Messages with missing fields should have higher corruption
        messages_with_empty_content = [m for m in messages if not m.content]
        if messages_with_empty_content:
            for msg in messages_with_empty_content:
                assert msg.corruption_score >= 0.3
