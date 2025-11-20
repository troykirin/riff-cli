"""
Tests for ConversationDAG.

Tests DAG construction, thread detection, and structural analysis.
"""

import pytest
from pathlib import Path
from riff.graph import JSONLLoader, ConversationDAG, ThreadType


class TestConversationDAG:
    """Tests for ConversationDAG class."""

    @pytest.fixture
    def loader(self) -> JSONLLoader:
        """Create loader for test conversations."""
        conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
        return JSONLLoader(conversations_dir)

    @pytest.fixture
    def test_session_id(self) -> str:
        """Test session ID (orphaned session)."""
        return "794650a6-84a5-446b-879c-639ee85fbde4"

    @pytest.fixture
    def dag(self, loader: JSONLLoader, test_session_id: str) -> ConversationDAG:
        """Create DAG for test session."""
        return ConversationDAG(loader, test_session_id)

    def test_dag_initialization(self, dag: ConversationDAG) -> None:
        """Test DAG initializes correctly."""
        assert len(dag.messages) > 0
        assert len(dag.message_index) == len(dag.messages)
        assert dag.session_id is not None

    def test_message_index(self, dag: ConversationDAG) -> None:
        """Test message index provides fast lookup."""
        for msg in dag.messages:
            found = dag.message_index[msg.uuid]
            assert found == msg

    def test_parent_child_relationships(self, dag: ConversationDAG) -> None:
        """Test parent-child adjacency lists are correct."""
        for msg in dag.messages:
            if msg.parent_uuid:
                # If parent exists, check it's in children list
                if msg.parent_uuid in dag.message_index:
                    assert msg.uuid in dag.children[msg.parent_uuid]
                    assert dag.parents[msg.uuid] == msg.parent_uuid

    def test_get_message(self, dag: ConversationDAG) -> None:
        """Test message retrieval."""
        # Existing message
        first_msg = dag.messages[0]
        found = dag.get_message(first_msg.uuid)
        assert found == first_msg

        # Non-existent message
        missing = dag.get_message("nonexistent-uuid")
        assert missing is None

    def test_get_parent(self, dag: ConversationDAG) -> None:
        """Test parent retrieval."""
        # Find message with parent
        child_msg = next((m for m in dag.messages if m.parent_uuid), None)
        if child_msg:
            parent = dag.get_parent(child_msg.uuid)
            if parent:
                assert parent.uuid == child_msg.parent_uuid

        # Root message has no parent
        root_msg = next((m for m in dag.messages if m.parent_uuid is None), None)
        if root_msg:
            parent = dag.get_parent(root_msg.uuid)
            assert parent is None

    def test_get_children(self, dag: ConversationDAG) -> None:
        """Test children retrieval."""
        # Find message with children
        for msg in dag.messages:
            children = dag.get_children(msg.uuid)
            assert isinstance(children, list)

            # Verify children have correct parent
            for child in children:
                assert child.parent_uuid == msg.uuid

    def test_get_ancestry_path(self, dag: ConversationDAG) -> None:
        """Test ancestry path computation."""
        # Find message with depth > 1
        deep_msg = None
        for msg in dag.messages:
            if msg.parent_uuid:
                parent = dag.get_parent(msg.uuid)
                if parent and parent.parent_uuid:
                    deep_msg = msg
                    break

        if deep_msg:
            path = dag.get_ancestry_path(deep_msg.uuid)
            assert len(path) > 1
            assert path[-1] == deep_msg
            assert path[0].parent_uuid is None  # Root

            # Verify path is connected
            for i in range(len(path) - 1):
                assert path[i + 1].parent_uuid == path[i].uuid

    def test_get_subtree(self, dag: ConversationDAG) -> None:
        """Test subtree retrieval."""
        # Get subtree from root
        roots = [m for m in dag.messages if m.parent_uuid is None]
        if roots:
            root = roots[0]
            subtree = dag.get_subtree(root.uuid)

            assert len(subtree) > 0
            assert root in subtree

            # All messages in subtree should be descendants
            subtree_uuids = {m.uuid for m in subtree}
            for msg in subtree:
                if msg.uuid != root.uuid:
                    # Walk up to root
                    current = msg
                    found_root = False
                    visited = set()
                    while current and current.uuid not in visited:
                        visited.add(current.uuid)
                        if current.uuid == root.uuid:
                            found_root = True
                            break
                        current = dag.get_parent(current.uuid)
                    assert found_root or msg.is_orphaned

    def test_to_session(self, dag: ConversationDAG) -> None:
        """Test conversion to Session."""
        session = dag.to_session()

        assert session.session_id == dag.session_id
        assert session.message_count == len(dag.messages)
        assert session.thread_count > 0

        # Verify thread classification
        main_threads = [t for t in session.threads if t.thread_type == ThreadType.MAIN]
        assert len(main_threads) <= 1  # At most one main thread

        # Verify all messages are in threads
        thread_messages = set()
        for thread in session.threads + session.orphans:
            for msg in thread.messages:
                thread_messages.add(msg.uuid)

        for msg in session.messages:
            assert msg.uuid in thread_messages

    def test_validate_structure(self, dag: ConversationDAG) -> None:
        """Test structural validation."""
        validation = dag.validate_structure()

        assert "is_valid" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "stats" in validation

        # Check stats structure
        stats = validation["stats"]
        assert "total_messages" in stats
        assert "root_count" in stats
        assert "component_count" in stats
        assert "orphaned_messages" in stats
        assert "avg_corruption" in stats

        # Verify stats values
        assert stats["total_messages"] == len(dag.messages)
        assert stats["root_count"] > 0
        assert 0.0 <= stats["avg_corruption"] <= 1.0

    def test_cycle_detection(self, dag: ConversationDAG) -> None:
        """Test that DAG detects cycles (should be none)."""
        validation = dag.validate_structure()

        # Should be valid (no cycles)
        assert validation["is_valid"]

        cycle_errors = [e for e in validation["errors"] if "cycle" in e.lower()]
        assert len(cycle_errors) == 0

    def test_thread_corruption_scores(self, dag: ConversationDAG) -> None:
        """Test corruption scores are computed for threads."""
        session = dag.to_session()

        for thread in session.threads + session.orphans:
            assert isinstance(thread.corruption_score, float)
            assert 0.0 <= thread.corruption_score <= 1.0

    def test_thread_message_assignment(self, dag: ConversationDAG) -> None:
        """Test messages are assigned to correct threads."""
        session = dag.to_session()

        # All messages should have thread_id assigned
        for msg in session.messages:
            assert msg.thread_id is not None

            # Find the thread
            thread = session.get_thread_by_id(msg.thread_id)
            assert thread is not None
            assert msg in thread.messages

    def test_empty_session_handling(self, loader: JSONLLoader) -> None:
        """Test handling of empty/invalid sessions."""
        with pytest.raises((ValueError, FileNotFoundError)):
            ConversationDAG(loader, "nonexistent-session")

    def test_orphan_detection(self, dag: ConversationDAG) -> None:
        """Test orphaned message detection."""
        # Check if any messages reference missing parents
        for msg in dag.messages:
            if msg.parent_uuid and msg.parent_uuid not in dag.message_index:
                assert msg.is_orphaned
                assert msg.corruption_score >= 0.5

    def test_sidechain_thread_classification(self, dag: ConversationDAG) -> None:
        """Test sidechain messages form side discussion threads."""
        session = dag.to_session()

        # Find sidechain messages
        sidechain_messages = [m for m in session.messages if m.is_sidechain]

        if sidechain_messages:
            # Check they're in side discussion threads
            for msg in sidechain_messages:
                thread = session.get_thread_by_id(msg.thread_id)
                assert thread is not None

                # Should be side discussion (unless orphaned)
                if not msg.is_orphaned:
                    assert thread.thread_type == ThreadType.SIDE_DISCUSSION
