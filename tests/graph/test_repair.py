"""
Comprehensive unit tests for the ConversationRepairEngine.

Tests orphan detection, parent suggestion, repair validation,
diff generation, and structural integrity checks.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from riff.graph.models import Message, Session, Thread, MessageType, ThreadType
from riff.graph.repair import ConversationRepairEngine, ParentCandidate, RepairDiff
from riff.graph.persistence import RepairOperation


@pytest.fixture
def sample_messages():
    """Create a set of sample messages for testing."""
    return [
        Message(
            uuid="msg-001",
            parent_uuid=None,  # Root message
            type=MessageType.USER,
            content="What is authentication?",
            timestamp="2024-01-01T10:00:00Z",
            session_id="session-001",
        ),
        Message(
            uuid="msg-002",
            parent_uuid="msg-001",
            type=MessageType.ASSISTANT,
            content="Authentication is the process of verifying identity",
            timestamp="2024-01-01T10:01:00Z",
            session_id="session-001",
        ),
        Message(
            uuid="msg-003",
            parent_uuid="msg-002",
            type=MessageType.USER,
            content="How does OAuth work?",
            timestamp="2024-01-01T10:02:00Z",
            session_id="session-001",
        ),
        Message(
            uuid="msg-004",
            parent_uuid=None,  # Orphaned - should have parent
            type=MessageType.ASSISTANT,
            content="OAuth uses tokens for authentication",
            timestamp="2024-01-01T10:03:00Z",
            session_id="session-001",
            corruption_score=0.8,
        ),
        Message(
            uuid="msg-005",
            parent_uuid=None,  # Orphaned - should have parent
            type=MessageType.USER,
            content="What about API keys?",
            timestamp="2024-01-01T10:04:00Z",
            session_id="session-001",
            corruption_score=0.6,
        ),
    ]


@pytest.fixture
def sample_session(sample_messages):
    """Create a sample session with messages and threads."""
    # Main thread contains first 3 messages
    main_thread = Thread(
        thread_id="thread-main",
        messages=sample_messages[:3],
        thread_type=ThreadType.MAIN,
    )

    # Orphan thread contains the orphaned messages
    orphan_thread = Thread(
        thread_id="thread-orphan",
        messages=[sample_messages[3], sample_messages[4]],
        thread_type=ThreadType.ORPHANED,
    )

    return Session(
        session_id="session-001",
        messages=sample_messages,
        threads=[main_thread],
        orphans=[orphan_thread],
        corruption_score=0.5,
    )


@pytest.fixture
def repair_engine():
    """Create a ConversationRepairEngine instance."""
    return ConversationRepairEngine()


class TestConversationRepairEngine:
    """Test suite for ConversationRepairEngine."""

    def test_find_orphaned_messages(self, repair_engine, sample_session):
        """
        Test detection of orphaned messages in a session.
        Should find exactly 2 orphaned messages, sorted by corruption_score desc.
        """
        orphans = repair_engine.find_orphaned_messages(sample_session)

        # Should find 2 orphaned messages
        assert len(orphans) == 2

        # Should be sorted by corruption_score descending
        assert orphans[0].uuid == "msg-004"  # score 0.8
        assert orphans[1].uuid == "msg-005"  # score 0.6

        # Should be marked as orphaned
        assert all(msg.is_orphaned for msg in orphans)

    def test_suggest_parent_candidates(self, repair_engine, sample_session):
        """
        Test parent candidate suggestion for orphaned messages.
        Should return top_k candidates sorted by similarity score.
        """
        orphan = sample_session.messages[3]  # msg-004 about OAuth
        candidates = repair_engine.suggest_parent_candidates(
            orphan, sample_session, top_k=3
        )

        # Should return at most 3 candidates
        assert len(candidates) <= 3

        # All candidates should be ParentCandidate objects
        assert all(isinstance(c, ParentCandidate) for c in candidates)

        # Similarity scores should be between 0 and 1
        for candidate in candidates:
            assert 0.0 <= candidate.similarity_score <= 1.0

        # Should be sorted by similarity score descending
        if len(candidates) > 1:
            scores = [c.similarity_score for c in candidates]
            assert scores == sorted(scores, reverse=True)

        # First candidate should be msg-003 (asking about OAuth)
        if candidates:
            best_candidate = candidates[0]
            assert best_candidate.message.uuid == "msg-003"
            assert "authentication" in best_candidate.reason.lower() or \
                   "oauth" in best_candidate.reason.lower()

    def test_calculate_repair_diff(self, repair_engine, sample_messages):
        """
        Test diff generation for a repair operation.
        Should show before/after states with clear diff lines.
        """
        orphan = sample_messages[3]  # msg-004
        new_parent_uuid = "msg-003"

        diff = repair_engine.calculate_repair_diff(orphan, new_parent_uuid)

        # Should be a RepairDiff object
        assert isinstance(diff, RepairDiff)

        # Should have before/after JSON strings
        assert diff.before
        assert diff.after
        assert isinstance(json.loads(diff.before), dict)
        assert isinstance(json.loads(diff.after), dict)

        # Diff lines should show the change
        assert any("- parentUuid: None" in line for line in diff.diff_lines)
        assert any(f"+ parentUuid: {new_parent_uuid}" in line for line in diff.diff_lines)

        # String representation should work
        diff_str = str(diff)
        assert "parentUuid" in diff_str

    def test_validate_repair_success(self, repair_engine, sample_session):
        """
        Test successful repair validation.
        Should return (True, "") for valid repairs.
        """
        orphan = sample_session.messages[3]  # msg-004
        parent_uuid = "msg-003"

        is_valid, error = repair_engine.validate_repair(orphan, parent_uuid, sample_session)

        assert is_valid is True
        assert error == ""

    def test_validate_repair_circular_dependency(self, repair_engine):
        """
        Test detection of circular dependencies in repairs.
        Should prevent A→B→C becoming A→B→C→A.
        """
        # Create a chain: A → B → C
        msg_a = Message(
            uuid="A", parent_uuid=None, type=MessageType.USER,
            content="A", timestamp="2024-01-01T10:00:00Z", session_id="test"
        )
        msg_b = Message(
            uuid="B", parent_uuid="A", type=MessageType.ASSISTANT,
            content="B", timestamp="2024-01-01T10:01:00Z", session_id="test"
        )
        msg_c = Message(
            uuid="C", parent_uuid="B", type=MessageType.USER,
            content="C", timestamp="2024-01-01T10:02:00Z", session_id="test"
        )

        session = Session(
            session_id="test",
            messages=[msg_a, msg_b, msg_c],
            threads=[],
            orphans=[],
        )

        # Try to make A's parent be C (would create cycle)
        is_valid, error = repair_engine.validate_repair(msg_a, "C", session)

        assert is_valid is False
        assert "circular dependency" in error

    def test_validate_repair_invalid_parent(self, repair_engine, sample_session):
        """
        Test validation with non-existent parent UUID.
        Should return error for invalid parent.
        """
        orphan = sample_session.messages[3]
        invalid_parent = "msg-999"  # Doesn't exist

        is_valid, error = repair_engine.validate_repair(
            orphan, invalid_parent, sample_session
        )

        assert is_valid is False
        assert "parent not found" in error

    def test_validate_repair_timestamp_violation(self, repair_engine):
        """
        Test timestamp validation in repairs.
        Parent must come before child temporally.
        """
        # Create orphan at T1
        orphan = Message(
            uuid="orphan",
            parent_uuid=None,
            type=MessageType.USER,
            content="Orphan message",
            timestamp="2024-01-01T10:00:00Z",
            session_id="test",
        )

        # Create potential parent at T2 (after orphan)
        future_parent = Message(
            uuid="parent",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            content="Future parent",
            timestamp="2024-01-01T10:05:00Z",  # After orphan
            session_id="test",
        )

        session = Session(
            session_id="test",
            messages=[orphan, future_parent],
            threads=[],
            orphans=[],
        )

        is_valid, error = repair_engine.validate_repair(orphan, "parent", session)

        assert is_valid is False
        assert "timestamp violation" in error

    def test_content_similarity_calculation(self, repair_engine):
        """Test the internal content similarity calculation."""
        # Test exact match
        score1 = repair_engine._calculate_content_similarity(
            "authentication API", "authentication API"
        )
        assert score1 == 1.0

        # Test partial match
        score2 = repair_engine._calculate_content_similarity(
            "authentication system", "authentication API"
        )
        assert 0.0 < score2 < 1.0

        # Test no match
        score3 = repair_engine._calculate_content_similarity(
            "hello world", "goodbye universe"
        )
        assert score3 == 0.0

        # Test with key terms boost
        score4 = repair_engine._calculate_content_similarity(
            "database authentication", "authentication database system"
        )
        assert score4 > 0.5  # Should get boost for matching key terms

    def test_type_compatibility(self, repair_engine):
        """Test message type compatibility checking."""
        from riff.graph.models import MessageType

        # User → Assistant is compatible
        assert repair_engine._are_types_compatible(
            MessageType.USER, MessageType.ASSISTANT
        )

        # Assistant → User is compatible
        assert repair_engine._are_types_compatible(
            MessageType.ASSISTANT, MessageType.USER
        )

        # System can parent anything
        assert repair_engine._are_types_compatible(
            MessageType.SYSTEM, MessageType.USER
        )
        assert repair_engine._are_types_compatible(
            MessageType.SYSTEM, MessageType.ASSISTANT
        )

        # Same type compatibility for certain types
        assert repair_engine._are_types_compatible(
            MessageType.ASSISTANT, MessageType.ASSISTANT
        )

    def test_would_create_cycle(self, repair_engine):
        """Test cycle detection in repair validation."""
        # Create a more complex graph: A → B → C → D
        messages = [
            Message(uuid="A", parent_uuid=None, type=MessageType.USER,
                   content="A", timestamp="2024-01-01T10:00:00Z", session_id="test"),
            Message(uuid="B", parent_uuid="A", type=MessageType.ASSISTANT,
                   content="B", timestamp="2024-01-01T10:01:00Z", session_id="test"),
            Message(uuid="C", parent_uuid="B", type=MessageType.USER,
                   content="C", timestamp="2024-01-01T10:02:00Z", session_id="test"),
            Message(uuid="D", parent_uuid="C", type=MessageType.ASSISTANT,
                   content="D", timestamp="2024-01-01T10:03:00Z", session_id="test"),
        ]

        session = Session(
            session_id="test",
            messages=messages,
            threads=[],
            orphans=[],
        )

        # D → A would not create cycle (A has no parent)
        assert not repair_engine._would_create_cycle("D", "A", session)

        # A → D would create cycle (D → C → B → A → D)
        assert repair_engine._would_create_cycle("A", "D", session)

        # B → D would create cycle (D → C → B → D)
        assert repair_engine._would_create_cycle("B", "D", session)

    def test_generate_candidate_reason(self, repair_engine):
        """Test generation of human-readable candidate reasons."""
        parent = Message(
            uuid="parent",
            parent_uuid=None,
            type=MessageType.USER,
            content="What is OAuth authentication?",
            timestamp="2024-01-01T10:00:00Z",
            session_id="test",
        )

        orphan = Message(
            uuid="orphan",
            parent_uuid=None,
            type=MessageType.ASSISTANT,
            content="OAuth is a secure authentication protocol",
            timestamp="2024-01-01T10:00:30Z",  # 30 seconds later
            session_id="test",
        )

        reason = repair_engine._generate_candidate_reason(parent, orphan, 0.75)

        # Should mention high similarity
        assert "high content similarity" in reason

        # Should mention natural flow
        assert "user→assistant" in reason

        # Should mention temporal proximity
        assert "temporal proximity" in reason

    def test_find_orphans_with_missing_parent(self, repair_engine):
        """Test detection of messages with non-existent parent UUIDs."""
        messages = [
            Message(uuid="msg-1", parent_uuid=None, type=MessageType.USER,
                   content="Start", timestamp="2024-01-01T10:00:00Z", session_id="test"),
            Message(uuid="msg-2", parent_uuid="msg-1", type=MessageType.ASSISTANT,
                   content="Reply", timestamp="2024-01-01T10:01:00Z", session_id="test"),
            Message(uuid="msg-3", parent_uuid="msg-999", type=MessageType.USER,  # Invalid parent
                   content="Orphan", timestamp="2024-01-01T10:02:00Z", session_id="test"),
        ]

        session = Session(
            session_id="test",
            messages=messages,
            threads=[Thread(
                thread_id="main",
                messages=messages[:2],
                thread_type=ThreadType.MAIN
            )],
            orphans=[],
        )

        orphans = repair_engine.find_orphaned_messages(session)

        # Should find the message with invalid parent
        assert len(orphans) == 1
        assert orphans[0].uuid == "msg-3"
        assert orphans[0].is_orphaned

    def test_empty_session_handling(self, repair_engine):
        """Test handling of empty sessions."""
        empty_session = Session(
            session_id="empty",
            messages=[],
            threads=[],
            orphans=[],
        )

        # Should handle empty session gracefully
        orphans = repair_engine.find_orphaned_messages(empty_session)
        assert orphans == []

        # Should return no candidates for non-existent orphan
        fake_orphan = Message(
            uuid="fake", parent_uuid=None, type=MessageType.USER,
            content="Test", timestamp="2024-01-01T10:00:00Z", session_id="empty"
        )
        candidates = repair_engine.suggest_parent_candidates(fake_orphan, empty_session)
        assert candidates == []