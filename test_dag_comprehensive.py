#!/usr/bin/env python3
"""
Comprehensive test suite for ConversationDAG.

Tests edge cases, type safety, and all major functionality.
"""

from pathlib import Path
from typing import assert_type
from riff.graph import (
    JSONLLoader,
    ConversationDAG,
    Message,
    MessageType,
    Thread,
    ThreadType,
    Session,
)


def test_loader() -> None:
    """Test JSONLLoader functionality."""
    print("=== Testing JSONLLoader ===")

    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    loader = JSONLLoader(conversations_dir)

    # Test listing sessions
    sessions = loader.list_sessions()
    print(f"Found {len(sessions)} sessions")

    # Test session existence
    test_session = "794650a6-84a5-446b-879c-639ee85fbde4"
    exists = loader.session_exists(test_session)
    print(f"Session {test_session[:20]}... exists: {exists}")

    # Test loading messages
    messages = loader.load_messages(test_session)
    print(f"Loaded {len(messages)} messages")

    # Verify message types
    for msg in messages[:5]:
        assert isinstance(msg, Message)
        assert isinstance(msg.type, MessageType)
        assert 0.0 <= msg.corruption_score <= 1.0
        print(f"  Message {msg.uuid[:20]}... type={msg.type.value}")

    print("JSONLLoader tests passed!\n")


def test_dag_construction() -> None:
    """Test DAG construction and graph properties."""
    print("=== Testing DAG Construction ===")

    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    loader = JSONLLoader(conversations_dir)
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    dag = ConversationDAG(loader, session_id)

    # Test message index
    assert len(dag.messages) == len(dag.message_index)
    print(f"Message index: {len(dag.message_index)} entries")

    # Test parent-child relationships
    for msg in dag.messages:
        if msg.parent_uuid:
            parent = dag.get_parent(msg.uuid)
            if parent:
                children = dag.get_children(parent.uuid)
                assert msg in children, "Parent-child relationship broken"

    print("Parent-child relationships verified")

    # Test ancestry paths
    sample_msg = dag.messages[10]
    path = dag.get_ancestry_path(sample_msg.uuid)
    print(f"Ancestry path length for message 10: {len(path)}")
    assert path[-1].uuid == sample_msg.uuid, "Ancestry path doesn't end at target"

    # Test subtree
    if dag.messages:
        root_msg = [m for m in dag.messages if m.parent_uuid is None][0]
        subtree = dag.get_subtree(root_msg.uuid)
        print(f"Subtree from root: {len(subtree)} messages")

    print("DAG construction tests passed!\n")


def test_session_conversion() -> None:
    """Test conversion from DAG to Session."""
    print("=== Testing Session Conversion ===")

    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    loader = JSONLLoader(conversations_dir)
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    dag = ConversationDAG(loader, session_id)
    session = dag.to_session()

    # Verify session properties
    assert isinstance(session, Session)
    assert session.session_id == session_id
    assert session.message_count > 0
    print(f"Session: {session.message_count} messages, {session.thread_count} threads")

    # Test thread classification
    main_thread = session.main_thread
    if main_thread:
        assert main_thread.thread_type == ThreadType.MAIN
        print(f"Main thread: {main_thread.message_count} messages")

    side_threads = session.side_threads
    print(f"Side threads: {len(side_threads)}")

    # Test thread access methods
    for thread in session.threads:
        assert isinstance(thread, Thread)
        assert isinstance(thread.thread_type, ThreadType)
        assert thread.message_count > 0

        # Test thread properties
        first = thread.first_message
        last = thread.last_message
        assert first in thread.messages
        assert last in thread.messages

        # Verify thread_id is assigned to messages
        for msg in thread.messages:
            assert msg.thread_id == thread.thread_id

    # Test message lookup
    if session.messages:
        test_msg = session.messages[0]
        found = session.get_message_by_uuid(test_msg.uuid)
        assert found == test_msg, "Message lookup failed"

    # Test thread lookup
    if session.threads:
        test_thread = session.threads[0]
        found = session.get_thread_by_id(test_thread.thread_id)
        assert found == test_thread, "Thread lookup failed"

    print("Session conversion tests passed!\n")


def test_validation() -> None:
    """Test structural validation."""
    print("=== Testing Validation ===")

    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    loader = JSONLLoader(conversations_dir)
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    dag = ConversationDAG(loader, session_id)
    validation = dag.validate_structure()

    # Check validation structure
    assert "is_valid" in validation
    assert "errors" in validation
    assert "warnings" in validation
    assert "stats" in validation

    print(f"Validation result: {'PASS' if validation['is_valid'] else 'FAIL'}")
    print(f"Errors: {len(validation['errors'])}")
    print(f"Warnings: {len(validation['warnings'])}")

    # Check stats
    stats = validation['stats']
    print(f"Stats: {stats['total_messages']} messages, {stats['component_count']} components")

    print("Validation tests passed!\n")


def test_type_safety() -> None:
    """Test type annotations and enum safety."""
    print("=== Testing Type Safety ===")

    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    loader = JSONLLoader(conversations_dir)
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    dag = ConversationDAG(loader, session_id)
    session = dag.to_session()

    # Test MessageType enum
    for msg in session.messages[:10]:
        assert isinstance(msg.type, MessageType)
        # Should be able to use enum value
        type_str = msg.type.value
        assert isinstance(type_str, str)

    # Test ThreadType enum
    for thread in session.threads:
        assert isinstance(thread.thread_type, ThreadType)
        type_str = thread.thread_type.value
        assert isinstance(type_str, str)

    # Test corruption scores are floats in range
    for msg in session.messages:
        assert isinstance(msg.corruption_score, float)
        assert 0.0 <= msg.corruption_score <= 1.0

    for thread in session.threads + session.orphans:
        assert isinstance(thread.corruption_score, float)
        assert 0.0 <= thread.corruption_score <= 1.0

    assert isinstance(session.corruption_score, float)
    assert 0.0 <= session.corruption_score <= 1.0

    print("Type safety tests passed!\n")


def test_edge_cases() -> None:
    """Test edge cases and error handling."""
    print("=== Testing Edge Cases ===")

    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    loader = JSONLLoader(conversations_dir)
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    dag = ConversationDAG(loader, session_id)

    # Test missing message lookup
    missing = dag.get_message("nonexistent-uuid")
    assert missing is None, "Should return None for missing message"

    # Test missing parent lookup
    root = [m for m in dag.messages if m.parent_uuid is None][0]
    parent = dag.get_parent(root.uuid)
    assert parent is None, "Root message should have no parent"

    # Test empty children list
    leaf_messages = [m for m in dag.messages if m.uuid not in dag.children]
    if leaf_messages:
        leaf = leaf_messages[0]
        children = dag.get_children(leaf.uuid)
        assert len(children) == 0, "Leaf message should have no children"

    # Test message with missing parent
    orphaned_messages = [m for m in dag.messages if m.is_orphaned]
    print(f"Orphaned messages: {len(orphaned_messages)}")

    print("Edge case tests passed!\n")


def main() -> None:
    """Run all tests."""
    print("Running comprehensive ConversationDAG tests\n")
    print("=" * 60)

    try:
        test_loader()
        test_dag_construction()
        test_session_conversion()
        test_validation()
        test_type_safety()
        test_edge_cases()

        print("=" * 60)
        print("\nAll tests passed! ✓")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        raise
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
