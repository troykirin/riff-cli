"""
Example usage of the persistence layer for riff-cli.

Demonstrates:
- Creating repair operations
- Applying repairs with automatic backups
- Viewing undo history
- Rolling back changes
"""

from pathlib import Path

from .persistence import RepairOperation, create_repair_writer
from .loaders import JSONLLoader
from .dag import ConversationDAG


def example_basic_repair():
    """
    Example 1: Basic repair workflow.

    Fix a single orphaned message by reattaching it to the main conversation thread.
    """
    print("=" * 60)
    print("Example 1: Basic Repair Workflow")
    print("=" * 60)

    # Setup paths
    conversations_dir = Path.home() / ".claude" / "projects" / "-Users-tryk--nabi"
    session_id = "your-session-id-here"
    jsonl_path = conversations_dir / f"{session_id}.jsonl"

    # Create repair writer
    writer = create_repair_writer()

    # Create a repair operation
    repair = RepairOperation(
        message_uuid="orphaned-message-uuid",
        field_name="parentUuid",
        old_value="missing-parent-uuid",
        new_value="valid-parent-uuid",
        reason="Reattach orphan to main thread",
    )

    # Apply repair with automatic backup
    success, backup_path = writer.repair_with_backup(
        session_id=session_id,
        jsonl_path=jsonl_path,
        repairs=[repair],
    )

    if success:
        print("✓ Repair applied successfully")
        print(f"  Backup created at: {backup_path}")
    else:
        print("✗ Repair failed")


def example_batch_repairs():
    """
    Example 2: Batch repair workflow.

    Apply multiple repairs in a single transaction with rollback support.
    """
    print("\n" + "=" * 60)
    print("Example 2: Batch Repair Workflow")
    print("=" * 60)

    conversations_dir = Path.home() / ".claude" / "projects" / "-Users-tryk--nabi"
    session_id = "your-session-id-here"
    jsonl_path = conversations_dir / f"{session_id}.jsonl"

    writer = create_repair_writer()

    # Create multiple repairs
    repairs = [
        RepairOperation(
            message_uuid="orphan-1",
            field_name="parentUuid",
            old_value="missing-parent-1",
            new_value="main-thread-parent",
            reason="Reattach orphan 1",
        ),
        RepairOperation(
            message_uuid="orphan-2",
            field_name="parentUuid",
            old_value="missing-parent-2",
            new_value="main-thread-parent",
            reason="Reattach orphan 2",
        ),
        RepairOperation(
            message_uuid="misplaced-message",
            field_name="parentUuid",
            old_value="wrong-parent",
            new_value="correct-parent",
            reason="Fix conversation flow",
        ),
    ]

    # Apply all repairs
    success, backup_path = writer.repair_with_backup(
        session_id=session_id,
        jsonl_path=jsonl_path,
        repairs=repairs,
    )

    if success:
        print(f"✓ Applied {len(repairs)} repairs successfully")
        print(f"  Backup: {backup_path}")
    else:
        print("✗ Some repairs failed")


def example_undo_workflow():
    """
    Example 3: Undo workflow.

    Show undo history and roll back the last repair.
    """
    print("\n" + "=" * 60)
    print("Example 3: Undo Workflow")
    print("=" * 60)

    conversations_dir = Path.home() / ".claude" / "projects" / "-Users-tryk--nabi"
    session_id = "your-session-id-here"
    jsonl_path = conversations_dir / f"{session_id}.jsonl"

    writer = create_repair_writer()

    # Show undo history
    history = writer.show_undo_history(session_id)

    print(f"Undo history ({len(history)} snapshots):")
    for i, snapshot in enumerate(history, start=1):
        print(f"\n  {i}. Timestamp: {snapshot.timestamp}")
        print(f"     Repairs: {len(snapshot.repairs_applied)}")
        print(f"     Can rollback: {snapshot.can_rollback}")

        for repair in snapshot.repairs_applied:
            print(f"       - {repair.message_uuid}: {repair.old_value} -> {repair.new_value}")

    # Undo last repair
    if history:
        print("\nUndoing last repair...")
        success = writer.undo_last_repair(jsonl_path, session_id)

        if success:
            print("✓ Undo successful - restored to previous state")
        else:
            print("✗ Undo failed")
    else:
        print("\nNo undo history available")


def example_integrated_repair_workflow():
    """
    Example 4: Integrated workflow with DAG analysis.

    Analyze conversation DAG, find orphans, create repair suggestions, and apply repairs.
    """
    print("\n" + "=" * 60)
    print("Example 4: Integrated Repair Workflow")
    print("=" * 60)

    conversations_dir = Path.home() / ".claude" / "projects" / "-Users-tryk--nabi"
    session_id = "your-session-id-here"
    jsonl_path = conversations_dir / f"{session_id}.jsonl"

    # Step 1: Load and analyze conversation
    print("\n1. Loading conversation...")
    loader = JSONLLoader(conversations_dir)
    dag = ConversationDAG(loader, session_id)
    session = dag.to_session()

    print(f"   Messages: {session.message_count}")
    print(f"   Threads: {session.thread_count}")
    print(f"   Orphans: {session.orphan_count}")

    # Step 2: Find orphaned messages
    print("\n2. Finding orphaned messages...")
    orphaned_messages = [msg for msg in session.messages if msg.is_orphaned]

    if not orphaned_messages:
        print("   No orphaned messages found")
        return

    print(f"   Found {len(orphaned_messages)} orphaned messages")

    # Step 3: Create repair operations for orphans
    print("\n3. Creating repair operations...")
    repairs = []

    for orphan in orphaned_messages:
        # Find a suitable parent (simplified heuristic: attach to root of main thread)
        main_thread = session.main_thread
        if main_thread and main_thread.messages:
            suggested_parent = main_thread.messages[0].uuid

            repair = RepairOperation(
                message_uuid=orphan.uuid,
                field_name="parentUuid",
                old_value=orphan.parent_uuid,
                new_value=suggested_parent,
                reason=f"Auto-repair: reattach orphan (corruption={orphan.corruption_score:.2f})",
            )

            repairs.append(repair)
            print(f"   - {orphan.uuid[:8]}: {orphan.parent_uuid} -> {suggested_parent}")

    # Step 4: Apply repairs
    print("\n4. Applying repairs...")
    writer = create_repair_writer()

    success, backup_path = writer.repair_with_backup(
        session_id=session_id,
        jsonl_path=jsonl_path,
        repairs=repairs,
    )

    if success:
        print(f"✓ Applied {len(repairs)} repairs")
        print(f"  Backup: {backup_path}")
        print("\n5. To undo these repairs, run:")
        print(f"   writer.undo_last_repair('{jsonl_path}', '{session_id}')")
    else:
        print("✗ Repair failed")


def example_backup_management():
    """
    Example 5: Backup management.

    List, inspect, and manage backups.
    """
    print("\n" + "=" * 60)
    print("Example 5: Backup Management")
    print("=" * 60)

    session_id = "your-session-id-here"
    writer = create_repair_writer()

    # List all backups
    backups = writer.list_backups(session_id)

    print(f"Backups for session {session_id} ({len(backups)} total):")
    for i, backup in enumerate(backups, start=1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        mtime = backup.stat().st_mtime

        print(f"\n  {i}. {backup.name}")
        print(f"     Size: {size_mb:.2f} MB")
        print(f"     Modified: {mtime}")

    # Delete old backups (keep last 5)
    if len(backups) > 5:
        print("\nDeleting old backups (keeping last 5)...")
        for backup in backups[5:]:
            success = writer.delete_backup(backup)
            if success:
                print(f"  ✓ Deleted: {backup.name}")


def example_rollback_to_specific_backup():
    """
    Example 6: Roll back to a specific backup.

    Choose a specific backup from history and restore to that point.
    """
    print("\n" + "=" * 60)
    print("Example 6: Roll Back to Specific Backup")
    print("=" * 60)

    conversations_dir = Path.home() / ".claude" / "projects" / "-Users-tryk--nabi"
    session_id = "your-session-id-here"
    jsonl_path = conversations_dir / f"{session_id}.jsonl"

    writer = create_repair_writer()

    # List backups
    backups = writer.list_backups(session_id)

    if not backups:
        print("No backups available")
        return

    print(f"Available backups ({len(backups)}):")
    for i, backup in enumerate(backups, start=1):
        print(f"  {i}. {backup.name}")

    # Roll back to second-most-recent backup (index 1)
    if len(backups) > 1:
        target_backup = backups[1]
        print(f"\nRolling back to: {target_backup.name}")

        success = writer.rollback_to_backup(jsonl_path, target_backup)

        if success:
            print("✓ Rollback successful")
        else:
            print("✗ Rollback failed")


def main():
    """Run all examples (commented out to prevent accidental execution)."""
    print("\n" + "=" * 60)
    print("Riff-CLI Persistence Layer Examples")
    print("=" * 60)
    print("\nNote: These examples are for demonstration only.")
    print("Uncomment the example calls in main() to execute.")
    print("=" * 60)

    # Uncomment to run specific examples:
    # example_basic_repair()
    # example_batch_repairs()
    # example_undo_workflow()
    # example_integrated_repair_workflow()
    # example_backup_management()
    # example_rollback_to_specific_backup()


if __name__ == "__main__":
    main()
