"""
Phase 6B Example: Immutable Event-Based Repairs with SurrealDB

This example demonstrates the complete workflow for:
1. Detecting orphaned messages
2. Logging immutable repair events
3. Materializing sessions from event replay
4. Viewing repair history and audit trails

Requirements:
- SurrealDB running on localhost:8000
- Namespace: conversations
- Database: repairs
- Schema applied (schema.sql)
"""

from datetime import datetime, timezone
from pathlib import Path

from .storage import (
    create_surrealdb_storage,
)
from ..graph.loaders import JSONLLoader
from ..graph.dag import ConversationDAG
from ..graph.repair import ConversationRepairEngine


# ============================================================================
# Example 1: Basic Repair Event Logging
# ============================================================================


def example_log_repair_event():
    """
    Example: Log an immutable repair event to SurrealDB.

    This demonstrates the core Phase 6B functionality:
    - All repairs are logged as immutable events
    - No direct JSONL mutation
    - Full audit trail preserved
    """
    print("=" * 80)
    print("Example 1: Logging Immutable Repair Events")
    print("=" * 80)

    # Initialize storage
    storage = create_surrealdb_storage(
        base_url="http://localhost:8000",
        namespace="conversations",
        database="repairs",
    )

    # Simulate a repair operation from the repair engine
    from ..graph.repair import RepairOperation as EngineRepairOperation

    repair_op = EngineRepairOperation(
        message_id="msg-orphaned-123",
        original_parent_uuid=None,  # Orphaned message
        suggested_parent_uuid="msg-parent-456",
        similarity_score=0.87,
        reason="High semantic similarity (0.87), temporal proximity (<5min)",
        timestamp=datetime.now(timezone.utc),
    )

    # Log the repair event (immutable append-only)
    print("\nLogging repair event...")
    success = storage.log_repair_event(
        repair_op=repair_op,
        operator="tui-user",  # or "agent-orchestrator", "system-auto"
    )

    if success:
        print("✓ Repair event logged successfully")
        print(f"  Message: {repair_op.message_id}")
        print(f"  Old Parent: {repair_op.original_parent_uuid or 'None (orphan)'}")
        print(f"  New Parent: {repair_op.suggested_parent_uuid}")
        print(f"  Similarity: {repair_op.similarity_score:.2f}")
        print(f"  Reason: {repair_op.reason}")
    else:
        print("✗ Failed to log repair event")

    storage.close()


# ============================================================================
# Example 2: View Repair History (Audit Trail)
# ============================================================================


def example_view_repair_history(session_id: str):
    """
    Example: View all repair events for a session.

    This demonstrates:
    - Chronological event retrieval
    - Audit trail inspection
    - Operator tracking
    """
    print("\n" + "=" * 80)
    print(f"Example 2: Viewing Repair History for Session {session_id[:8]}")
    print("=" * 80)

    storage = create_surrealdb_storage()

    # Get all repair events for session
    print("\nRetrieving repair history...")
    history = storage.get_session_history(session_id)

    if not history:
        print("No repair events found for this session")
        storage.close()
        return

    print(f"\nFound {len(history)} repair event(s):\n")

    for i, event in enumerate(history, 1):
        print(f"Event {i}:")
        print(f"  Event ID: {event.event_id}")
        print(f"  Timestamp: {event.timestamp.isoformat()}")
        print(f"  Operator: {event.operator}")
        print(f"  Message: {event.message_id[:8]}...")
        print(f"  Repair: {event.old_parent_uuid or 'None'} → {event.new_parent_uuid[:8]}...")
        print(f"  Reason: {event.reason}")
        print(f"  Valid: {event.validation_passed}")
        print()

    storage.close()


# ============================================================================
# Example 3: Session Materialization (Event Replay)
# ============================================================================


def example_materialize_session(session_id: str, jsonl_path: Path):
    """
    Example: Materialize session from JSONL + repair events.

    This demonstrates:
    1. Load original messages from JSONL
    2. Load all repair events from SurrealDB
    3. Replay events in chronological order
    4. Return fully-repaired Session
    """
    print("\n" + "=" * 80)
    print(f"Example 3: Materializing Session {session_id[:8]}")
    print("=" * 80)

    storage = create_surrealdb_storage()

    print("\nMaterialization steps:")
    print("1. Loading original JSONL messages...")
    print("2. Loading repair events from SurrealDB...")
    print("3. Replaying events in chronological order...")
    print("4. Building conversation DAG...")

    # Materialize session
    session = storage.materialize_session(session_id, jsonl_path)

    print("\n✓ Session materialized successfully")
    print(f"  Total Messages: {session.message_count}")
    print(f"  Threads: {session.thread_count}")
    print(f"  Orphans: {session.orphan_count}")
    print(f"  Corruption Score: {session.corruption_score:.2f}")

    # Show messages with repaired parents
    print("\nMessages (with repairs applied):")
    for i, msg in enumerate(session.messages[:10], 1):  # First 10
        parent_info = f"→ {msg.parent_uuid[:8]}..." if msg.parent_uuid else "ROOT"
        orphan_flag = " [ORPHAN]" if msg.is_orphaned else ""
        print(
            f"  {i}. {msg.uuid[:8]}... {parent_info} "
            f"({msg.type.value}){orphan_flag}"
        )

    if len(session.messages) > 10:
        print(f"  ... and {len(session.messages) - 10} more messages")

    storage.close()
    return session


# ============================================================================
# Example 4: Full Repair Workflow (End-to-End)
# ============================================================================


def example_full_repair_workflow(jsonl_path: Path):
    """
    Example: Complete repair workflow from detection to materialization.

    Workflow:
    1. Load JSONL conversation
    2. Detect orphaned messages
    3. Suggest parent candidates
    4. Log repair events
    5. Materialize repaired session
    6. Compare before/after
    """
    print("\n" + "=" * 80)
    print("Example 4: Full Repair Workflow")
    print("=" * 80)

    # Step 1: Load original JSONL
    print("\n[Step 1] Loading JSONL conversation...")
    session_id = jsonl_path.stem
    loader = JSONLLoader(jsonl_path.parent)
    messages = loader.load_messages(session_id)
    print(f"  Loaded {len(messages)} messages")

    # Step 2: Build DAG and detect orphans
    print("\n[Step 2] Analyzing conversation structure...")
    dag = ConversationDAG(loader, session_id)
    session = dag.to_session()

    repair_engine = ConversationRepairEngine()
    orphans = repair_engine.find_orphaned_messages(session)
    print(f"  Found {len(orphans)} orphaned message(s)")

    if not orphans:
        print("  No repairs needed - conversation is healthy!")
        return

    # Step 3: Suggest repairs for orphans
    print("\n[Step 3] Suggesting repair candidates...")
    storage = create_surrealdb_storage()

    for i, orphan in enumerate(orphans[:3], 1):  # First 3 orphans
        print(f"\n  Orphan {i}: {orphan.uuid[:8]}...")
        print(f"    Corruption: {orphan.corruption_score:.2f}")

        # Get repair candidates
        candidates = repair_engine.suggest_parent_candidates(
            orphan, session, top_k=3
        )

        if not candidates:
            print("    No suitable parents found")
            continue

        print(f"    Found {len(candidates)} candidate(s):")

        # Take best candidate
        best_candidate = candidates[0]
        print(f"    → Best: {best_candidate.suggested_parent_uuid[:8]}... "
              f"(score: {best_candidate.similarity_score:.2f})")

        # Step 4: Validate and log repair
        is_valid, error = repair_engine.validate_repair(
            orphan, best_candidate.suggested_parent_uuid, session
        )

        if is_valid:
            print("    ✓ Validation passed")

            # Log repair event
            success = storage.log_repair_event(
                repair_op=best_candidate,
                operator="example-workflow",
            )

            if success:
                print("    ✓ Repair event logged")
            else:
                print("    ✗ Failed to log event")
        else:
            print(f"    ✗ Validation failed: {error}")

    # Step 5: Materialize repaired session
    print("\n[Step 5] Materializing repaired session...")
    repaired_session = storage.materialize_session(session_id, jsonl_path)

    # Step 6: Compare before/after
    print("\n[Step 6] Comparison:")
    print(f"  Before: {session.orphan_count} orphans, "
          f"corruption={session.corruption_score:.2f}")
    print(f"  After:  {repaired_session.orphan_count} orphans, "
          f"corruption={repaired_session.corruption_score:.2f}")

    improvement = session.corruption_score - repaired_session.corruption_score
    if improvement > 0:
        print(f"  Improvement: {improvement:.2f} ({improvement/session.corruption_score*100:.1f}%)")
    else:
        print("  No improvement (may need more repairs)")

    storage.close()


# ============================================================================
# Example 5: Repair Statistics and Analytics
# ============================================================================


def example_repair_analytics():
    """
    Example: Analyze repair events for insights.

    Demonstrates:
    - Repair counts by operator
    - Messages with most repairs
    - Repair success rates
    """
    print("\n" + "=" * 80)
    print("Example 5: Repair Analytics")
    print("=" * 80)

    storage = create_surrealdb_storage()

    # Query 1: Repair counts by operator
    print("\n[Query 1] Repair counts by operator:")
    query = """
        SELECT operator, count() as repair_count
        FROM repairs_events
        GROUP BY operator
        ORDER BY repair_count DESC;
    """

    try:
        results = storage._query(query)
        for result in results:
            print(f"  {result['operator']}: {result['repair_count']} repairs")
    except Exception as e:
        print(f"  Error: {e}")

    # Query 2: Messages with most repairs
    print("\n[Query 2] Messages with most repairs:")
    query = """
        SELECT message_id, count() as repair_count
        FROM repairs_events
        GROUP BY message_id
        ORDER BY repair_count DESC
        LIMIT 5;
    """

    try:
        results = storage._query(query)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['message_id'][:8]}...: "
                  f"{result['repair_count']} repair(s)")
    except Exception as e:
        print(f"  Error: {e}")

    # Query 3: Recent repair activity (last 24 hours)
    print("\n[Query 3] Recent repair activity:")
    query = """
        SELECT count() as recent_repairs
        FROM repairs_events
        WHERE timestamp > time::unix(time::unix(time::now()) - 86400);
    """

    try:
        results = storage._query(query)
        if results:
            count = results[0].get('recent_repairs', 0)
            print(f"  {count} repairs in the last 24 hours")
    except Exception as e:
        print(f"  Error: {e}")

    storage.close()


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Run all Phase 6B examples."""
    print("\n" + "=" * 80)
    print("PHASE 6B: IMMUTABLE EVENT-BASED REPAIRS")
    print("=" * 80)
    print("\nThese examples demonstrate SurrealDB-backed repair event logging")
    print("with full audit trails and session materialization.\n")

    # Example 1: Basic repair event logging
    example_log_repair_event()

    # Example 2: View repair history
    # Replace with actual session ID
    # example_view_repair_history("your-session-id-here")

    # Example 3: Materialize session
    # Replace with actual paths
    # example_materialize_session(
    #     session_id="your-session-id",
    #     jsonl_path=Path("~/.claude/projects/your-project/your-session.jsonl")
    # )

    # Example 4: Full workflow
    # Replace with actual path
    # example_full_repair_workflow(
    #     jsonl_path=Path("~/.claude/projects/your-project/your-session.jsonl")
    # )

    # Example 5: Analytics
    # example_repair_analytics()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
