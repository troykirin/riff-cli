"""
Test and demonstration of ConversationTreeVisualizer.

This script creates a synthetic conversation session with:
- Main thread
- Side discussion (branch and rejoin)
- Orphaned messages (simulating resume failure)

Then visualizes it using the ASCII tree format.
"""

from datetime import datetime, timedelta
from riff.graph.models import Message, Thread, Session, MessageType, ThreadType
from riff.graph.visualizer import visualize_session, flatten_session_for_navigation


def create_test_session() -> Session:
    """
    Create a synthetic test session with various thread types.

    Structure:
    - Main thread: 5 messages (user/assistant pairs + final user)
    - Side discussion: 4 messages (branching off main)
    - Orphaned branch: 3 messages (disconnected, high corruption)
    """
    session_id = "test-session-001"
    base_time = datetime.now()

    # Helper to create timestamps
    def ts(minutes_offset: int) -> str:
        return (base_time + timedelta(minutes=minutes_offset)).isoformat()

    # Main thread messages
    msg1 = Message(
        uuid="msg-001",
        parent_uuid=None,
        type=MessageType.USER,
        content="Can you analyze the riff-cli architecture and explain how the search works?",
        timestamp=ts(0),
        session_id=session_id,
        thread_id="main"
    )

    msg2 = Message(
        uuid="msg-002",
        parent_uuid="msg-001",
        type=MessageType.ASSISTANT,
        content="I'll examine the riff-cli architecture. Let me start by reading the main CLI file and search module structure.",
        timestamp=ts(1),
        session_id=session_id,
        thread_id="main"
    )

    msg3 = Message(
        uuid="msg-003",
        parent_uuid="msg-002",
        type=MessageType.USER,
        content="What about the TUI components? How do they integrate with the search backend?",
        timestamp=ts(5),
        session_id=session_id,
        thread_id="main"
    )

    msg4 = Message(
        uuid="msg-004",
        parent_uuid="msg-003",
        type=MessageType.ASSISTANT,
        content="The TUI uses prompt_toolkit for the interactive interface. It connects to the search backend through...",
        timestamp=ts(6),
        session_id=session_id,
        thread_id="main"
    )

    msg9 = Message(
        uuid="msg-009",
        parent_uuid="msg-008",
        type=MessageType.USER,
        content="Got it, back to the main architecture discussion. Can you explain the semantic search implementation?",
        timestamp=ts(25),
        session_id=session_id,
        thread_id="main"
    )

    msg10 = Message(
        uuid="msg-010",
        parent_uuid="msg-009",
        type=MessageType.ASSISTANT,
        content="The semantic search uses embeddings stored in Qdrant. When you search, it converts your query to a vector...",
        timestamp=ts(26),
        session_id=session_id,
        thread_id="main"
    )

    # Side discussion (tangent about Qdrant)
    msg5 = Message(
        uuid="msg-005",
        parent_uuid="msg-004",
        type=MessageType.USER,
        content="Quick question - what's Qdrant exactly? I've heard of it but never used it.",
        timestamp=ts(10),
        session_id=session_id,
        thread_id="side-001",
        is_sidechain=True
    )

    msg6 = Message(
        uuid="msg-006",
        parent_uuid="msg-005",
        type=MessageType.ASSISTANT,
        content="Qdrant is a vector database specifically designed for similarity search and embeddings. It's written in Rust...",
        timestamp=ts(11),
        session_id=session_id,
        thread_id="side-001",
        is_sidechain=True
    )

    msg7 = Message(
        uuid="msg-007",
        parent_uuid="msg-006",
        type=MessageType.USER,
        content="Interesting! How does it compare to alternatives like Pinecone or Weaviate?",
        timestamp=ts(15),
        session_id=session_id,
        thread_id="side-001",
        is_sidechain=True
    )

    msg8 = Message(
        uuid="msg-008",
        parent_uuid="msg-007",
        type=MessageType.ASSISTANT,
        content="Qdrant is self-hosted and open source, while Pinecone is primarily cloud-based. For our use case...",
        timestamp=ts(16),
        session_id=session_id,
        thread_id="side-001",
        is_sidechain=True
    )

    # Orphaned messages (simulating resume failure)
    msg11 = Message(
        uuid="msg-011",
        parent_uuid=None,  # NULL parent - strong corruption signal
        type=MessageType.USER,
        content="Resume: Let's continue working on the DAG visualization implementation.",
        timestamp=ts(30),
        session_id=session_id,
        thread_id="orphan-001",
        is_orphaned=True,
        corruption_score=0.92,
        is_sidechain=True  # Was a resume attempt
    )

    msg12 = Message(
        uuid="msg-012",
        parent_uuid="msg-011",
        type=MessageType.ASSISTANT,
        content="Continuing from where we left off. I'll create the visualizer module for the conversation graph.",
        timestamp=ts(31),
        session_id=session_id,
        thread_id="orphan-001",
        is_orphaned=True,
        corruption_score=0.85
    )

    msg13 = Message(
        uuid="msg-013",
        parent_uuid="msg-012",
        type=MessageType.USER,
        content="Great! Can you also add the ASCII tree rendering like git log --graph?",
        timestamp=ts(35),
        session_id=session_id,
        thread_id="orphan-001",
        is_orphaned=True,
        corruption_score=0.80
    )

    # Build threads
    main_thread = Thread(
        thread_id="main",
        messages=[msg1, msg2, msg3, msg4, msg9, msg10],
        thread_type=ThreadType.MAIN,
        corruption_score=0.0
    )

    side_thread = Thread(
        thread_id="side-001",
        messages=[msg5, msg6, msg7, msg8],
        thread_type=ThreadType.SIDE_DISCUSSION,
        parent_thread_id="main",
        corruption_score=0.0
    )

    orphan_thread = Thread(
        thread_id="orphan-001",
        messages=[msg11, msg12, msg13],
        thread_type=ThreadType.ORPHANED,
        corruption_score=0.92
    )

    # Build session
    all_messages = [msg1, msg2, msg3, msg4, msg5, msg6, msg7, msg8, msg9, msg10, msg11, msg12, msg13]

    session = Session(
        session_id=session_id,
        messages=all_messages,
        threads=[main_thread, side_thread],
        orphans=[orphan_thread],
        corruption_score=0.25  # Overall session has some corruption
    )

    return session


def main():
    """Run visualization test."""
    print("=" * 80)
    print("ConversationTreeVisualizer Test")
    print("=" * 80)
    print()

    # Create test session
    session = create_test_session()

    print(f"Session: {session.session_id}")
    print(f"Total messages: {session.message_count}")
    print(f"Threads: {session.thread_count}")
    print(f"Orphaned threads: {session.orphan_count}")
    print(f"Corruption score: {session.corruption_score:.2f}")
    print()
    print("-" * 80)
    print("ASCII Tree Visualization:")
    print("-" * 80)
    print()

    # Visualize
    tree = visualize_session(session, max_preview_length=80)
    print(tree)

    print()
    print("-" * 80)
    print("Flattened Navigation (first 10 items):")
    print("-" * 80)
    print()

    # Test navigation flattening
    nav_items = flatten_session_for_navigation(session)
    for i, item in enumerate(nav_items[:10]):
        print(f"{i:2d}. {item.text}")
        if item.message_uuid:
            print(f"    -> msg_uuid: {item.message_uuid}, thread: {item.thread_id}, orphan: {item.is_orphan}")

    print()
    print(f"Total navigation items: {len(nav_items)}")


if __name__ == "__main__":
    main()
