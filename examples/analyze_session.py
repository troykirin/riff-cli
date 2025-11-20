#!/usr/bin/env python3
"""
Example: Analyze a Claude conversation session.

Demonstrates the core ConversationDAG functionality for analyzing
conversation structure, detecting threads, and identifying issues.
"""

from pathlib import Path
from riff.graph import JSONLLoader, ConversationDAG, ThreadType


def analyze_session(session_id: str, conversations_dir: Path) -> None:
    """
    Perform comprehensive analysis of a conversation session.

    Args:
        session_id: Session UUID to analyze
        conversations_dir: Directory containing JSONL files
    """
    print(f"Analyzing session: {session_id}")
    print("=" * 70)

    # Initialize loader and DAG
    loader = JSONLLoader(conversations_dir)
    dag = ConversationDAG(loader, session_id)

    # Convert to session
    session = dag.to_session()

    # === Basic Statistics ===
    print("\n[Session Statistics]")
    print(f"  Total messages: {session.message_count}")
    print(f"  Threads: {session.thread_count}")
    print(f"  Orphans: {session.orphan_count}")
    print(f"  Corruption score: {session.corruption_score:.2f}")

    # === Thread Analysis ===
    print("\n[Thread Analysis]")

    # Main thread
    if session.main_thread:
        thread = session.main_thread
        print(f"\n  Main Thread:")
        print(f"    Messages: {thread.message_count}")
        print(f"    Corruption: {thread.corruption_score:.2f}")
        print(f"    First: {thread.first_message.timestamp}")
        print(f"    Last: {thread.last_message.timestamp}")
        print(f"    Preview: {thread.first_message.content[:80]}...")

    # Side discussions
    if session.side_threads:
        print(f"\n  Side Discussions: {len(session.side_threads)}")
        for i, thread in enumerate(session.side_threads[:3], 1):
            print(f"    {i}. Thread {thread.thread_id[:20]}... ({thread.message_count} messages)")

    # Orphans
    if session.orphans:
        print(f"\n  Orphaned Threads: {len(session.orphans)}")
        for thread in session.orphans:
            print(f"    - {thread.thread_id[:20]}... ({thread.message_count} messages)")

    # === Structural Validation ===
    print("\n[Structural Validation]")
    validation = dag.validate_structure()

    print(f"  Valid: {validation['is_valid']}")

    if validation['errors']:
        print(f"  Errors: {len(validation['errors'])}")
        for error in validation['errors'][:3]:
            print(f"    - {error}")

    if validation['warnings']:
        print(f"  Warnings: {len(validation['warnings'])}")
        for warning in validation['warnings'][:3]:
            print(f"    - {warning}")

    # === Statistics ===
    stats = validation['stats']
    print(f"\n  Graph Statistics:")
    print(f"    Roots: {stats['root_count']}")
    print(f"    Components: {stats['component_count']}")
    print(f"    Orphaned messages: {stats['orphaned_messages']}")
    print(f"    Avg corruption: {stats['avg_corruption']:.2f}")

    # === Message Type Distribution ===
    print("\n[Message Types]")
    from collections import Counter
    type_counts = Counter(msg.type for msg in session.messages)
    for msg_type, count in type_counts.most_common():
        print(f"  {msg_type.value}: {count}")

    # === Corruption Hotspots ===
    corrupted_messages = [m for m in session.messages if m.corruption_score > 0.3]
    if corrupted_messages:
        print(f"\n[Corruption Hotspots]")
        print(f"  Found {len(corrupted_messages)} messages with corruption > 0.3")
        for msg in corrupted_messages[:5]:
            print(f"    - {msg.uuid[:20]}... (score: {msg.corruption_score:.2f})")
            if msg.is_orphaned:
                print(f"      Reason: Orphaned (parent: {msg.parent_uuid[:20] if msg.parent_uuid else 'None'}...)")

    # === Path Example ===
    print("\n[Example Path Analysis]")
    # Find a deep message
    deep_message = None
    max_depth = 0
    for msg in session.messages:
        path = dag.get_ancestry_path(msg.uuid)
        if len(path) > max_depth:
            max_depth = len(path)
            deep_message = msg

    if deep_message:
        path = dag.get_ancestry_path(deep_message.uuid)
        print(f"  Deepest message: {deep_message.uuid[:20]}... (depth: {len(path)})")
        print(f"  Path:")
        for i, ancestor in enumerate(path[:5]):
            indent = "    " * (i + 1)
            preview = ancestor.content[:60].replace("\n", " ")
            print(f"{indent}└─ {ancestor.type.value}: {preview}...")
        if len(path) > 5:
            print(f"    ... and {len(path) - 5} more ancestors")

    print("\n" + "=" * 70)
    print("Analysis complete!")


def main() -> None:
    """Run session analysis."""
    # Configuration
    conversations_dir = Path.home() / ".claude/projects/-Users-tryk--nabi"
    session_id = "794650a6-84a5-446b-879c-639ee85fbde4"

    # Run analysis
    analyze_session(session_id, conversations_dir)


if __name__ == "__main__":
    main()
