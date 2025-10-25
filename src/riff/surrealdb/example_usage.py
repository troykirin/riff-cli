"""
Example usage of SurrealDB schema for conversation storage.

This demonstrates how to:
1. Connect to SurrealDB
2. Create sessions, threads, and messages
3. Query for orphaned messages
4. Perform full-text search
5. Analyze session statistics

Prerequisites:
    pip install surrealdb

    # Start SurrealDB
    surreal start --bind 0.0.0.0:8000 --user root --pass root

    # Import schema
    surreal import --conn http://localhost:8000 \
      --user root --pass root \
      --ns nabi --db conversations \
      schema.sql
"""

import asyncio

from surrealdb import Surreal  # type: ignore[import-untyped]

from .schema_utils import (
    build_high_corruption_query,
    build_orphaned_messages_query,
    build_parent_candidates_query,
    build_session_stats_query,
    prepare_message_record,
    prepare_session_record,
    prepare_thread_record,
    validate_message_data,
    validate_session_data,
    validate_thread_data,
)


async def example_basic_usage():
    """Example: Basic CRUD operations."""
    print("\n=== Basic Usage Example ===\n")

    async with Surreal("ws://localhost:8000/rpc") as db:
        # Sign in
        await db.signin({"user": "root", "pass": "root"})
        await db.use("nabi", "conversations")

        # Create a session
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        session = prepare_session_record(
            session_id=session_id,
            message_count=0,
            thread_count=0,
        )

        # Validate before insertion
        is_valid, error = validate_session_data(session)
        if not is_valid:
            print(f"Validation error: {error}")
            return

        result = await db.create("session", session)
        print(f"Created session: {result}")

        # Create a thread
        thread = prepare_thread_record(
            session_id=session_id,
            thread_type="main",
            message_count=0,
            topic="Introduction",
        )

        is_valid, error = validate_thread_data(thread)
        if not is_valid:
            print(f"Validation error: {error}")
            return

        thread_result = await db.create("thread", thread)
        thread_id = thread_result[0]["id"]
        print(f"Created thread: {thread_id}")

        # Create messages
        messages = [
            {
                "uuid": "msg-001",
                "type": "user",
                "role": "user",
                "content": "Hello! Can you help me understand SurrealDB?",
                "timestamp": "2025-01-15T10:00:00Z",
                "parent": None,
            },
            {
                "uuid": "msg-002",
                "type": "assistant",
                "role": "assistant",
                "content": "Of course! SurrealDB is a multi-model database that combines features of relational and graph databases.",
                "timestamp": "2025-01-15T10:00:05Z",
                "parent": "msg-001",
            },
            {
                "uuid": "msg-003",
                "type": "user",
                "role": "user",
                "content": "What makes it different from traditional databases?",
                "timestamp": "2025-01-15T10:00:15Z",
                "parent": "msg-002",
            },
        ]

        for msg in messages:
            message = prepare_message_record(
                session_id=session_id,
                message_uuid=msg["uuid"],
                message_type=msg["type"],
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                parent_uuid=msg["parent"],
                thread_id=thread_id,
            )

            is_valid, error = validate_message_data(message)
            if not is_valid:
                print(f"Validation error: {error}")
                continue

            result = await db.create("message", message)
            print(f"Created message: {msg['uuid']}")

        # Update session counts
        await db.query(
            f"""
            UPDATE session:{session_id}
            SET message_count = 3, thread_count = 1;
        """
        )

        print("\n✓ Basic operations completed successfully!")


async def example_query_operations():
    """Example: Query operations."""
    print("\n=== Query Operations Example ===\n")

    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("nabi", "conversations")

        session_id = "550e8400-e29b-41d4-a716-446655440000"

        # Get session statistics
        print("1. Session Statistics:")
        query = build_session_stats_query(session_id)
        stats = await db.query(query)
        print(f"   {stats}\n")

        # Full-text search
        print("2. Full-text Search:")
        search_query = f"""
            SELECT message_uuid, content, timestamp
            FROM message
            WHERE session_id = '{session_id}'
              AND content @@ 'SurrealDB database'
            ORDER BY timestamp DESC;
        """
        results = await db.query(search_query)
        print(f"   Found {len(results)} matching messages\n")

        # Get messages in chronological order
        print("3. Chronological Messages:")
        chrono_query = f"""
            SELECT message_uuid, role, content, timestamp
            FROM message
            WHERE session_id = '{session_id}'
            ORDER BY timestamp ASC;
        """
        messages = await db.query(chrono_query)
        for msg in messages[0]["result"]:
            print(f"   [{msg['role']}] {msg['content'][:50]}...")

        print("\n✓ Query operations completed successfully!")


async def example_orphan_detection():
    """Example: Orphan detection and repair."""
    print("\n=== Orphan Detection Example ===\n")

    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("nabi", "conversations")

        session_id = "550e8400-e29b-41d4-a716-446655440000"

        # Create an orphaned message (parent doesn't exist)
        orphan = prepare_message_record(
            session_id=session_id,
            message_uuid="msg-orphan-001",
            message_type="user",
            role="user",
            content="This message has a missing parent.",
            timestamp="2025-01-15T10:00:20Z",
            parent_uuid="msg-missing",  # Non-existent parent
            is_orphaned=True,
            corruption_score=0.8,
        )

        await db.create("message", orphan)
        print("Created orphaned message")

        # Find all orphaned messages
        query = build_orphaned_messages_query(session_id)
        orphans = await db.query(query)
        print(f"\nFound {len(orphans[0]['result'])} orphaned messages:")

        for orphan_msg in orphans[0]["result"]:
            print(f"  - {orphan_msg['message_uuid']}: {orphan_msg['content'][:50]}...")
            print(f"    Corruption score: {orphan_msg['corruption_score']}")

            # Find potential parent candidates
            candidates_query = build_parent_candidates_query(
                session_id, orphan_msg["timestamp"], limit=3
            )
            candidates = await db.query(candidates_query)

            if candidates[0]["result"]:
                print("    Potential parents:")
                for candidate in candidates[0]["result"]:
                    print(f"      - {candidate['message_uuid']} at {candidate['timestamp']}")
            else:
                print("    No parent candidates found")

        print("\n✓ Orphan detection completed successfully!")


async def example_corruption_analysis():
    """Example: Corruption analysis."""
    print("\n=== Corruption Analysis Example ===\n")

    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("nabi", "conversations")

        session_id = "550e8400-e29b-41d4-a716-446655440000"

        # Find high-corruption messages
        query = build_high_corruption_query(session_id, threshold=0.5, limit=10)
        corrupted = await db.query(query)

        print("High-corruption messages (score > 0.5):")
        if corrupted[0]["result"]:
            for msg in corrupted[0]["result"]:
                print(f"  - {msg['message_uuid']}: score={msg['corruption_score']:.2f}")
                print(f"    Content: {msg['content'][:50]}...")
                print(f"    Orphaned: {msg['is_orphaned']}")
        else:
            print("  No high-corruption messages found")

        # Calculate session corruption score
        session_query = f"""
            SELECT
                session_id,
                COUNT() as total_messages,
                math::sum(is_orphaned) as orphaned_count,
                math::avg(corruption_score) as avg_corruption,
                math::max(corruption_score) as max_corruption
            FROM message
            WHERE session_id = '{session_id}'
            GROUP ALL;
        """
        stats = await db.query(session_query)

        if stats[0]["result"]:
            session_stats = stats[0]["result"][0]
            print("\nSession Corruption Summary:")
            print(f"  Total messages: {session_stats['total_messages']}")
            print(f"  Orphaned messages: {session_stats['orphaned_count']}")
            print(f"  Average corruption: {session_stats['avg_corruption']:.3f}")
            print(f"  Max corruption: {session_stats['max_corruption']:.3f}")

        print("\n✓ Corruption analysis completed successfully!")


async def example_graph_traversal():
    """Example: Graph traversal with relations."""
    print("\n=== Graph Traversal Example ===\n")

    async with Surreal("ws://localhost:8000/rpc") as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("nabi", "conversations")

        # Create parent-child relations
        print("Creating message relationships...")

        # msg-001 → msg-002 (parent → child)
        await db.query(
            """
            RELATE (SELECT * FROM message WHERE message_uuid = 'msg-001')
              ->message_parent_of->
              (SELECT * FROM message WHERE message_uuid = 'msg-002');
        """
        )

        # msg-002 → msg-003
        await db.query(
            """
            RELATE (SELECT * FROM message WHERE message_uuid = 'msg-002')
              ->message_parent_of->
              (SELECT * FROM message WHERE message_uuid = 'msg-003');
        """
        )

        # Traverse graph: Get message with parent and children
        traverse_query = """
            SELECT *,
              <-message_parent_of<-message as children,
              ->message_parent_of->message as parent
            FROM message
            WHERE message_uuid = 'msg-002';
        """
        result = await db.query(traverse_query)

        if result[0]["result"]:
            msg = result[0]["result"][0]
            print(f"\nMessage: {msg['message_uuid']}")
            print(f"Content: {msg['content'][:50]}...")

            if msg.get("parent"):
                parent = msg["parent"][0]
                print(f"\nParent: {parent['message_uuid']}")
                print(f"  {parent['content'][:50]}...")

            if msg.get("children"):
                print("\nChildren:")
                for child in msg["children"]:
                    print(f"  - {child['message_uuid']}: {child['content'][:50]}...")

        print("\n✓ Graph traversal completed successfully!")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SurrealDB Conversation Schema - Usage Examples")
    print("=" * 60)

    try:
        await example_basic_usage()
        await example_query_operations()
        await example_orphan_detection()
        await example_corruption_analysis()
        await example_graph_traversal()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. SurrealDB is running: surreal start --bind 0.0.0.0:8000 --user root --pass root")
        print("2. Schema is imported: surreal import schema.sql")
        print("3. Python client is installed: pip install surrealdb")


if __name__ == "__main__":
    asyncio.run(main())
