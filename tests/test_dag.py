#!/usr/bin/env python3
"""
Test script for ConversationDAG with real orphaned session data.

Tests the core DAG functionality with the problematic session:
794650a6-84a5-446b-879c-639ee85fbde4.jsonl
"""

from pathlib import Path
from riff.graph import JSONLLoader, ConversationDAG


def main() -> None:
    """Run DAG tests on orphaned session."""

    # Path to Claude conversations
    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    print(f"Loading session: {session_id}")
    print(f"From: {conversations_dir}\n")

    # Initialize loader
    loader = JSONLLoader(conversations_dir)

    # Check if session exists
    if not loader.session_exists(session_id):
        print(f"ERROR: Session {session_id} not found!")
        return

    print("Building DAG...")
    dag = ConversationDAG(loader, session_id)

    # Convert to session
    session = dag.to_session()

    # Print statistics
    print("\n=== Session Statistics ===")
    print(f"Session ID: {session.session_id}")
    print(f"Total messages: {session.message_count}")
    print(f"Threads: {session.thread_count}")
    print(f"Orphaned threads: {session.orphan_count}")
    print(f"Corruption score: {session.corruption_score:.2f}")

    # Print thread breakdown
    print("\n=== Thread Breakdown ===")
    for i, thread in enumerate(session.threads):
        print(f"\nThread {i + 1}: {thread.thread_type.value}")
        print(f"  ID: {thread.thread_id}")
        print(f"  Messages: {thread.message_count}")
        print(f"  Corruption: {thread.corruption_score:.2f}")
        print(f"  First message (5 lines):")
        first_lines = thread.first_message.content.split("\n")[:5]
        for line in first_lines:
            print(f"    {line[:80]}")

    # Print orphaned threads
    if session.orphans:
        print("\n=== Orphaned Threads ===")
        for i, thread in enumerate(session.orphans):
            print(f"\nOrphan {i + 1}:")
            print(f"  ID: {thread.thread_id}")
            print(f"  Messages: {thread.message_count}")
            print(f"  Corruption: {thread.corruption_score:.2f}")

    # Validate structure
    print("\n=== Structure Validation ===")
    validation = dag.validate_structure()

    print(f"Valid: {validation['is_valid']}")

    if validation['errors']:
        print(f"\nErrors ({len(validation['errors'])}):")
        for error in validation['errors']:
            print(f"  - {error}")

    if validation['warnings']:
        print(f"\nWarnings ({len(validation['warnings'])}):")
        for warning in validation['warnings'][:5]:  # Show first 5
            print(f"  - {warning}")
        if len(validation['warnings']) > 5:
            print(f"  ... and {len(validation['warnings']) - 5} more")

    print(f"\nStats:")
    for key, value in validation['stats'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # Test specific message lookup
    print("\n=== Message Lookup Test ===")
    roots = [msg for msg in session.messages if msg.parent_uuid is None]
    if roots:
        root_msg = roots[0]
        print(f"Root message: {root_msg.uuid}")
        print(f"Type: {root_msg.type.value}")
        print(f"Timestamp: {root_msg.timestamp}")
        print(f"Content preview: {root_msg.content[:100]}")

        # Get children
        children = dag.get_children(root_msg.uuid)
        print(f"\nDirect children: {len(children)}")
        for child in children[:3]:
            print(f"  - {child.uuid} ({child.type.value})")

        # Get subtree
        subtree = dag.get_subtree(root_msg.uuid)
        print(f"\nSubtree size: {len(subtree)} messages")

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
