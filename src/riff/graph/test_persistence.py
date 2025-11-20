"""
Tests for persistence module.

Demonstrates:
- Backup creation and management
- Single and batch repair operations
- Atomic JSONL updates
- Undo/rollback functionality
- Snapshot management
"""

import json
import tempfile
from pathlib import Path

import pytest  # type: ignore[import-not-found]

from .persistence import (
    RepairOperation,
    JSONLRepairWriter,
    create_repair_writer,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        backup_dir = tmppath / "backups"
        undo_dir = tmppath / "undo"
        data_dir = tmppath / "data"

        backup_dir.mkdir()
        undo_dir.mkdir()
        data_dir.mkdir()

        yield {
            "backup": backup_dir,
            "undo": undo_dir,
            "data": data_dir,
        }


@pytest.fixture
def sample_jsonl(temp_dirs):
    """Create a sample JSONL file for testing."""
    data_dir = temp_dirs["data"]
    session_id = "test-session-001"
    jsonl_path = data_dir / f"{session_id}.jsonl"

    # Sample conversation data
    messages = [
        {
            "uuid": "msg-root",
            "parentUuid": None,
            "type": "user",
            "timestamp": "2025-01-20T10:00:00Z",
            "content": "Hello",
            "message": {"content": "Hello"},
        },
        {
            "uuid": "msg-child-1",
            "parentUuid": "msg-root",
            "type": "assistant",
            "timestamp": "2025-01-20T10:00:01Z",
            "content": "Hi there!",
            "message": {"content": "Hi there!"},
        },
        {
            "uuid": "msg-child-2",
            "parentUuid": "msg-child-1",
            "type": "user",
            "timestamp": "2025-01-20T10:00:02Z",
            "content": "How are you?",
            "message": {"content": "How are you?"},
        },
        {
            "uuid": "msg-orphan",
            "parentUuid": "msg-nonexistent",  # Orphaned message
            "type": "user",
            "timestamp": "2025-01-20T10:00:03Z",
            "content": "Orphaned message",
            "message": {"content": "Orphaned message"},
        },
    ]

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return {
        "path": jsonl_path,
        "session_id": session_id,
        "messages": messages,
    }


@pytest.fixture
def writer(temp_dirs):
    """Create JSONLRepairWriter with temporary directories."""
    return JSONLRepairWriter(
        backup_root=temp_dirs["backup"],
        undo_root=temp_dirs["undo"],
    )


# ============================================================================
# Test RepairOperation
# ============================================================================


def test_repair_operation_creation():
    """Test RepairOperation dataclass."""
    repair = RepairOperation(
        message_uuid="msg-123",
        field_name="parentUuid",
        old_value="msg-old",
        new_value="msg-new",
        reason="Fixing orphan",
    )

    assert repair.message_uuid == "msg-123"
    assert repair.field_name == "parentUuid"
    assert repair.old_value == "msg-old"
    assert repair.new_value == "msg-new"
    assert repair.reason == "Fixing orphan"
    assert isinstance(repair.timestamp, str)


def test_repair_operation_serialization():
    """Test RepairOperation to/from dict."""
    repair = RepairOperation(
        message_uuid="msg-123",
        field_name="parentUuid",
        old_value="msg-old",
        new_value="msg-new",
    )

    # Convert to dict
    data = repair.to_dict()
    assert data["message_uuid"] == "msg-123"
    assert data["field"] == "parentUuid"
    assert data["old_value"] == "msg-old"
    assert data["new_value"] == "msg-new"

    # Convert back from dict
    restored = RepairOperation.from_dict(data)
    assert restored.message_uuid == repair.message_uuid
    assert restored.field == repair.field
    assert restored.old_value == repair.old_value
    assert restored.new_value == repair.new_value


# ============================================================================
# Test Backup Management
# ============================================================================


def test_create_backup(writer, sample_jsonl):
    """Test backup creation."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    backup_path = writer.create_backup(session_id, jsonl_path)

    assert backup_path.exists()
    assert backup_path.parent.name == session_id
    assert backup_path.suffix == ".jsonl"

    # Verify backup content matches original
    with open(jsonl_path, "r") as f:
        original = f.read()

    with open(backup_path, "r") as f:
        backup = f.read()

    assert original == backup


def test_list_backups(writer, sample_jsonl):
    """Test listing backups."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    # Create multiple backups
    backup1 = writer.create_backup(session_id, jsonl_path)
    backup2 = writer.create_backup(session_id, jsonl_path)

    backups = writer.list_backups(session_id)

    assert len(backups) >= 2
    assert backup1 in backups or backup2 in backups


def test_delete_backup(writer, sample_jsonl):
    """Test backup deletion."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    backup_path = writer.create_backup(session_id, jsonl_path)
    assert backup_path.exists()

    success = writer.delete_backup(backup_path)
    assert success
    assert not backup_path.exists()


# ============================================================================
# Test Repair Operations
# ============================================================================


def test_apply_repair(writer, sample_jsonl):
    """Test applying a single repair."""
    jsonl_path = sample_jsonl["path"]

    # Create repair: fix orphan message
    repair = RepairOperation(
        message_uuid="msg-orphan",
        field_name="parentUuid",
        old_value="msg-nonexistent",
        new_value="msg-child-2",  # Attach to valid parent
        reason="Repair orphan",
    )

    success = writer.apply_repair(jsonl_path, repair)
    assert success

    # Verify repair was applied
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line.strip())
            if record["uuid"] == "msg-orphan":
                assert record["parentUuid"] == "msg-child-2"
                break
        else:
            pytest.fail("Repaired message not found")


def test_apply_batch_repairs(writer, sample_jsonl):
    """Test applying multiple repairs."""
    jsonl_path = sample_jsonl["path"]

    repairs = [
        RepairOperation(
            message_uuid="msg-child-1",
            field_name="parentUuid",
            old_value="msg-root",
            new_value="msg-root",  # No-op for testing
        ),
        RepairOperation(
            message_uuid="msg-orphan",
            field_name="parentUuid",
            old_value="msg-nonexistent",
            new_value="msg-child-2",
        ),
    ]

    all_succeeded, applied = writer.apply_batch_repairs(jsonl_path, repairs)

    assert all_succeeded
    assert len(applied) == 2


def test_apply_repair_nonexistent_message(writer, sample_jsonl):
    """Test repair fails for nonexistent message."""
    jsonl_path = sample_jsonl["path"]

    repair = RepairOperation(
        message_uuid="msg-does-not-exist",
        field_name="parentUuid",
        old_value=None,
        new_value="msg-root",
    )

    with pytest.raises(ValueError):
        writer.apply_repair(jsonl_path, repair)


# ============================================================================
# Test Rollback
# ============================================================================


def test_rollback_to_backup(writer, sample_jsonl):
    """Test rolling back to a backup."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    # Create backup
    backup_path = writer.create_backup(session_id, jsonl_path)

    # Apply repair
    repair = RepairOperation(
        message_uuid="msg-orphan",
        field_name="parentUuid",
        old_value="msg-nonexistent",
        new_value="msg-child-2",
    )
    writer.apply_repair(jsonl_path, repair)

    # Verify repair was applied
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line.strip())
            if record["uuid"] == "msg-orphan":
                assert record["parentUuid"] == "msg-child-2"
                break

    # Rollback
    success = writer.rollback_to_backup(jsonl_path, backup_path)
    assert success

    # Verify rollback restored original state
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line.strip())
            if record["uuid"] == "msg-orphan":
                assert record["parentUuid"] == "msg-nonexistent"
                break


# ============================================================================
# Test Undo System
# ============================================================================


def test_push_and_show_undo_history(writer, sample_jsonl):
    """Test undo history management."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    # Create backup
    backup_path = writer.create_backup(session_id, jsonl_path)

    # Push repair snapshot
    repairs = [
        RepairOperation(
            message_uuid="msg-orphan",
            field_name="parentUuid",
            old_value="msg-nonexistent",
            new_value="msg-child-2",
        )
    ]

    writer.push_repair_snapshot(session_id, jsonl_path, backup_path, repairs)

    # Check undo history
    history = writer.show_undo_history(session_id)

    assert len(history) == 1
    assert history[0].session_id == session_id
    assert len(history[0].repairs_applied) == 1


def test_undo_last_repair(writer, sample_jsonl):
    """Test undoing last repair."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    # Full workflow: backup, repair, push snapshot
    backup_path = writer.create_backup(session_id, jsonl_path)

    repair = RepairOperation(
        message_uuid="msg-orphan",
        field_name="parentUuid",
        old_value="msg-nonexistent",
        new_value="msg-child-2",
    )

    writer.apply_repair(jsonl_path, repair)
    writer.push_repair_snapshot(session_id, jsonl_path, backup_path, [repair])

    # Undo
    success = writer.undo_last_repair(jsonl_path, session_id)
    assert success

    # Verify original state restored
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line.strip())
            if record["uuid"] == "msg-orphan":
                assert record["parentUuid"] == "msg-nonexistent"
                break


def test_undo_stack_size_limit(writer, sample_jsonl):
    """Test undo stack respects size limit."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    # Push more snapshots than stack limit
    for i in range(15):
        backup_path = writer.create_backup(session_id, jsonl_path)
        repairs = [
            RepairOperation(
                message_uuid="msg-root",
                field_name="parentUuid",
                old_value=None,
                new_value=None,
            )
        ]
        writer.push_repair_snapshot(session_id, jsonl_path, backup_path, repairs)

    history = writer.show_undo_history(session_id)

    # Should only keep last 10
    assert len(history) <= writer._max_undo_stack_size


# ============================================================================
# Test Workflow Helpers
# ============================================================================


def test_repair_with_backup_workflow(writer, sample_jsonl):
    """Test complete repair workflow."""
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    repairs = [
        RepairOperation(
            message_uuid="msg-orphan",
            field_name="parentUuid",
            old_value="msg-nonexistent",
            new_value="msg-child-2",
            reason="Fix orphan",
        )
    ]

    success, backup_path = writer.repair_with_backup(session_id, jsonl_path, repairs)

    assert success
    assert backup_path.exists()

    # Verify repair applied
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line.strip())
            if record["uuid"] == "msg-orphan":
                assert record["parentUuid"] == "msg-child-2"
                break

    # Verify snapshot in undo history
    history = writer.show_undo_history(session_id)
    assert len(history) == 1


def test_create_repair_writer_factory():
    """Test factory function."""
    writer = create_repair_writer()
    assert isinstance(writer, JSONLRepairWriter)
    assert writer.backup_root.exists()
    assert writer.undo_root.exists()


# ============================================================================
# Integration Example
# ============================================================================


def test_full_repair_and_undo_workflow(writer, sample_jsonl):
    """
    Integration test: Full repair and undo workflow.

    Demonstrates:
    1. Create backup
    2. Apply repairs
    3. Push snapshot
    4. Undo repair
    5. Verify restoration
    """
    session_id = sample_jsonl["session_id"]
    jsonl_path = sample_jsonl["path"]

    # Step 1: Read original state
    with open(jsonl_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Step 2: Apply repairs with backup
    repairs = [
        RepairOperation(
            message_uuid="msg-orphan",
            field_name="parentUuid",
            old_value="msg-nonexistent",
            new_value="msg-child-2",
            reason="Reattach orphan to main thread",
        ),
        RepairOperation(
            message_uuid="msg-child-2",
            field_name="parentUuid",
            old_value="msg-child-1",
            new_value="msg-root",  # Move branch
            reason="Restructure conversation",
        ),
    ]

    success, backup_path = writer.repair_with_backup(session_id, jsonl_path, repairs)
    assert success

    # Step 3: Verify repairs applied
    with open(jsonl_path, "r", encoding="utf-8") as f:
        repaired_content = f.read()

    assert repaired_content != original_content

    # Step 4: Undo repairs
    undo_success = writer.undo_last_repair(jsonl_path, session_id)
    assert undo_success

    # Step 5: Verify original state restored
    with open(jsonl_path, "r", encoding="utf-8") as f:
        restored_content = f.read()

    assert restored_content == original_content

    print("✓ Full repair and undo workflow complete")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
