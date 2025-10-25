#!/usr/bin/env python3
"""Test semantic analysis module.

Demonstrates thread detection, corruption scoring, and semantic topic extraction.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from riff.graph.models import Message, MessageType
from riff.graph.analysis import (
    ThreadDetector,
    CorruptionScorer,
    SemanticAnalyzer,
)


def create_test_messages():
    """Create test messages representing a typical conversation with issues."""
    return [
        # Main thread
        Message(
            uuid="msg-1",
            parent_uuid=None,
            type=MessageType.USER,
            content="Can you help me implement a search feature?",
            timestamp="2025-10-20T10:00:00",
            session_id="test-session",
        ),
        Message(
            uuid="msg-2",
            parent_uuid="msg-1",
            type=MessageType.ASSISTANT,
            content="I'll help you implement a search feature using Qdrant vector database.",
            timestamp="2025-10-20T10:01:00",
            session_id="test-session",
        ),
        Message(
            uuid="msg-3",
            parent_uuid="msg-2",
            type=MessageType.USER,
            content="What about the architecture?",
            timestamp="2025-10-20T10:02:00",
            session_id="test-session",
        ),
        # Side discussion (sidechain)
        Message(
            uuid="msg-4",
            parent_uuid="msg-3",
            type=MessageType.USER,
            content="Quick question about debugging",
            timestamp="2025-10-20T10:03:00",
            session_id="test-session",
            is_sidechain=True,
        ),
        Message(
            uuid="msg-5",
            parent_uuid="msg-4",
            type=MessageType.ASSISTANT,
            content="For debugging, you can use logging and breakpoints.",
            timestamp="2025-10-20T10:04:00",
            session_id="test-session",
            is_sidechain=True,
        ),
        # Back to main
        Message(
            uuid="msg-6",
            parent_uuid="msg-3",
            type=MessageType.ASSISTANT,
            content="For the architecture, we'll use a three-layer design.",
            timestamp="2025-10-20T10:05:00",
            session_id="test-session",
        ),
        # Orphaned branch (broken parent)
        Message(
            uuid="msg-7",
            parent_uuid=None,  # Should have parent but doesn't
            type=MessageType.USER,
            content="Continue working on the search implementation",
            timestamp="2025-10-20T10:06:00",
            session_id="test-session",
        ),
        Message(
            uuid="msg-8",
            parent_uuid="msg-7",
            type=MessageType.ASSISTANT,
            content="Continuing with the search feature, let's add the query endpoint.",
            timestamp="2025-10-20T10:07:00",
            session_id="test-session",
        ),
    ]


def test_thread_detector():
    """Test ThreadDetector class."""
    print("=" * 80)
    print("TEST: ThreadDetector")
    print("=" * 80)

    messages = create_test_messages()
    detector = ThreadDetector(messages)

    threads = detector.identify_threads()

    print(f"\nFound {len(threads)} threads:")
    for i, thread in enumerate(threads):
        print(f"\nThread {i + 1}:")
        print(f"  ID: {thread.thread_id}")
        print(f"  Type: {thread.thread_type}")
        print(f"  Messages: {len(thread.messages)}")
        print(f"  Topic: {thread.semantic_topic}")
        if thread.corruption_score > 0:
            print(f"  Corruption: {thread.corruption_score:.2f}")

        # Show first message
        if thread.messages:
            first = thread.messages[0]
            print(f"  First: [{first.type.value}] {first.content[:50]}...")


def test_corruption_scorer():
    """Test CorruptionScorer class."""
    print("\n" + "=" * 80)
    print("TEST: CorruptionScorer")
    print("=" * 80)

    messages = create_test_messages()

    # Test individual message scoring
    orphaned_msg = messages[-2]  # msg-7 (orphaned)
    score = CorruptionScorer.score_corruption([orphaned_msg])

    print(f"\nOrphaned message corruption score: {score:.2f}")
    print(f"  UUID: {orphaned_msg.uuid}")
    print(f"  Parent: {orphaned_msg.parent_uuid}")
    print(f"  Content: {orphaned_msg.content[:50]}...")

    # Test orphan detection
    orphans = CorruptionScorer.detect_orphans(messages)

    print(f"\nDetected {len(orphans)} orphaned threads:")
    for orphan in orphans:
        print(f"\n  Thread ID: {orphan.thread_id}")
        print(f"  Corruption: {orphan.corruption_score:.2f}")
        print(f"  Messages: {len(orphan.messages)}")


def test_semantic_analyzer():
    """Test SemanticAnalyzer class."""
    print("\n" + "=" * 80)
    print("TEST: SemanticAnalyzer")
    print("=" * 80)

    messages = create_test_messages()

    # Extract topic for each message
    print("\nMessage topics:")
    for msg in messages[:5]:  # First 5 messages
        topic = SemanticAnalyzer.extract_semantic_topic([msg])
        print(f"  {msg.uuid}: {topic:20} - {msg.content[:40]}...")

    # Cluster by topic
    clusters = SemanticAnalyzer.cluster_by_topic(messages)

    print(f"\nClustered into {len(clusters)} topics:")
    for topic, msgs in clusters.items():
        print(f"  {topic}: {len(msgs)} messages")


def test_semantic_similarity():
    """Test semantic similarity calculation."""
    print("\n" + "=" * 80)
    print("TEST: Semantic Similarity")
    print("=" * 80)

    messages = create_test_messages()

    # Compare main thread vs side discussion
    main_msgs = messages[:3]
    side_msgs = messages[3:5]

    similarity = SemanticAnalyzer.calculate_semantic_similarity(main_msgs, side_msgs)

    print(f"\nSemantic similarity between main thread and side discussion: {similarity:.2f}")
    print(f"  Main thread topic: {SemanticAnalyzer.extract_semantic_topic(main_msgs)}")
    print(f"  Side discussion topic: {SemanticAnalyzer.extract_semantic_topic(side_msgs)}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("SEMANTIC ANALYSIS TEST SUITE")
    print("=" * 80)

    try:
        test_thread_detector()
        test_corruption_scorer()
        test_semantic_analyzer()
        test_semantic_similarity()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
