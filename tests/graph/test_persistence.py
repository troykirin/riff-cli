"""
Comprehensive unit tests for JSONLRepairWriter persistence layer.

Tests backup creation, repair application, batch operations,
rollback functionality, and undo/redo system.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import time

from riff.graph.persistence import (
    JSONLRepairWriter,
    RepairOperation,
    RepairSnapshot,
    create_repair_writer,
)


@pytest.fixture
def temp_jsonl_file():
    """Create a temporary JSONL file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        # Write sample JSONL data
        messages = [
            {
                "uuid": "msg-001",
                "parentUuid": None,
                "type": "user",
                "content": "First message",
                "timestamp": "2024-01-01T10:00:00Z",
            },
            {
                "uuid": "msg-002",
                "parentUuid": "msg-001",
                "type": "assistant",
                "content": "Second message",
                "timestamp": "2024-01-01T10:01:00Z",
            },
            {
                "uuid": "msg-003",
                "parentUuid": None,  # Orphaned
                "type": "user",
                "content": "Third message (orphaned)",
                "timestamp": "2024-01-01T10:02:00Z",
            },
            {
                "uuid": "msg-004",
                "parentUuid": None,  # Orphaned
                "type": "assistant",
                "content": "Fourth message (orphaned)",
                "timestamp": "2024-01-01T10:03:00Z",
            },
            {
                "uuid": "msg-005",
                "parentUuid": None,  # Orphaned
                "type": "user",
                "content": "Fifth message (orphaned)",
                "timestamp": "2024-01-01T10:04:00Z",
            },
        ]

        for msg in messages:
            f.write(json.dumps(msg) + "\n")

        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_backup_dir():
    """Create a temporary directory for backups."""
    temp_dir = Path(tempfile.mkdtemp(prefix="riff_test_backups_"))
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_undo_dir():
    """Create a temporary directory for undo history."""
    temp_dir = Path(tempfile.mkdtemp(prefix="riff_test_undo_"))
    yield temp_dir
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def repair_writer(temp_backup_dir, temp_undo_dir):
    """Create a JSONLRepairWriter with temp directories."""
    return JSONLRepairWriter(backup_root=temp_backup_dir, undo_root=temp_undo_dir)


class TestJSONLRepairWriter:
    """Test suite for JSONLRepairWriter."""

    def test_create_backup(self, repair_writer, temp_jsonl_file):
        """
        Test backup creation for a JSONL file.
        Should create timestamped backup in correct location.
        """
        session_id = "test-session"

        # Create backup
        backup_path = repair_writer.create_backup(session_id, temp_jsonl_file)

        # Backup should exist
        assert backup_path.exists()

        # Should be in correct directory structure
        assert session_id in str(backup_path)
        assert backup_path.suffix == ".jsonl"

        # Backup content should match original
        with open(temp_jsonl_file) as f:
            original = f.read()
        with open(backup_path) as f:
            backup = f.read()

        assert original == backup

        # Filename should contain timestamp
        assert backup_path.stem.count("_") >= 2  # Format: YYYYMMDD_HHMMSS_microseconds

    def test_apply_repair(self, repair_writer, temp_jsonl_file):
        """
        Test applying a single repair operation.
        Should update parentUuid and preserve other fields.
        """
        # Create repair operation
        repair = RepairOperation(
            message_uuid="msg-003",
            field_name="parentUuid",
            old_value=None,
            new_value="msg-002",
            reason="Fixing orphaned message",
        )

        # Apply repair
        success = repair_writer.apply_repair(temp_jsonl_file, repair)
        assert success is True

        # Verify the change
        with open(temp_jsonl_file) as f:
            lines = f.readlines()
            updated = False
            for line in lines:
                msg = json.loads(line)
                if msg["uuid"] == "msg-003":
                    assert msg["parentUuid"] == "msg-002"
                    updated = True

        assert updated, "Message was not updated"

        # File should still be valid JSONL
        with open(temp_jsonl_file) as f:
            for line in f:
                json.loads(line)  # Should not raise

    def test_apply_batch_repairs(self, repair_writer, temp_jsonl_file):
        """
        Test applying multiple repairs in batch.
        Should apply all repairs and return success.
        """
        # Create 3 repair operations
        repairs = [
            RepairOperation(
                message_uuid="msg-003",
                field_name="parentUuid",
                old_value=None,
                new_value="msg-002",
            ),
            RepairOperation(
                message_uuid="msg-004",
                field_name="parentUuid",
                old_value=None,
                new_value="msg-003",
            ),
            RepairOperation(
                message_uuid="msg-005",
                field_name="parentUuid",
                old_value=None,
                new_value="msg-004",
            ),
        ]

        # Apply batch repairs
        success, applied = repair_writer.apply_batch_repairs(temp_jsonl_file, repairs)

        assert success is True
        assert len(applied) == 3
        assert applied == repairs

        # Verify all changes
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]

        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] == "msg-002"
        assert msg_map["msg-004"]["parentUuid"] == "msg-003"
        assert msg_map["msg-005"]["parentUuid"] == "msg-004"

    def test_apply_batch_repairs_partial_failure(self, repair_writer, temp_jsonl_file):
        """
        Test batch repair with partial failure.
        Should stop at first failure and return applied repairs.
        """
        # Create repairs with second one invalid
        repairs = [
            RepairOperation(
                message_uuid="msg-003",
                field_name="parentUuid",
                old_value=None,
                new_value="msg-002",
            ),
            RepairOperation(
                message_uuid="msg-999",  # Non-existent message
                field_name="parentUuid",
                old_value=None,
                new_value="msg-003",
            ),
            RepairOperation(
                message_uuid="msg-005",
                field_name="parentUuid",
                old_value=None,
                new_value="msg-004",
            ),
        ]

        # Apply batch repairs
        success, applied = repair_writer.apply_batch_repairs(temp_jsonl_file, repairs)

        assert success is False
        assert len(applied) == 1  # Only first repair applied
        assert applied[0].message_uuid == "msg-003"

        # Verify only first repair was applied
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]

        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] == "msg-002"
        assert msg_map["msg-005"]["parentUuid"] is None  # Not updated

    def test_rollback_to_backup(self, repair_writer, temp_jsonl_file):
        """
        Test rollback to a backup file.
        Should restore file to backup state.
        """
        session_id = "test-session"

        # Create backup
        backup_path = repair_writer.create_backup(session_id, temp_jsonl_file)

        # Modify the file
        repair = RepairOperation(
            message_uuid="msg-003",
            field_name="parentUuid",
            old_value=None,
            new_value="msg-002",
        )
        repair_writer.apply_repair(temp_jsonl_file, repair)

        # Verify modification
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]
        assert any(m["uuid"] == "msg-003" and m["parentUuid"] == "msg-002" for m in messages)

        # Rollback
        success = repair_writer.rollback_to_backup(temp_jsonl_file, backup_path)
        assert success is True

        # Verify rollback
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]
        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] is None  # Back to original

    def test_undo_last_repair(self, repair_writer, temp_jsonl_file):
        """
        Test undo of the last repair operation.
        Should revert to previous state.
        """
        session_id = "test-session"

        # Apply two repairs sequentially
        repair1 = RepairOperation(
            message_uuid="msg-003",
            field_name="parentUuid",
            old_value=None,
            new_value="msg-002",
        )

        repair2 = RepairOperation(
            message_uuid="msg-004",
            field_name="parentUuid",
            old_value=None,
            new_value="msg-003",
        )

        # First repair with backup
        backup1 = repair_writer.create_backup(session_id, temp_jsonl_file)
        repair_writer.apply_repair(temp_jsonl_file, repair1)
        repair_writer.push_repair_snapshot(
            session_id, temp_jsonl_file, backup1, [repair1]
        )

        # Second repair with backup
        backup2 = repair_writer.create_backup(session_id, temp_jsonl_file)
        repair_writer.apply_repair(temp_jsonl_file, repair2)
        repair_writer.push_repair_snapshot(
            session_id, temp_jsonl_file, backup2, [repair2]
        )

        # Verify both repairs applied
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]
        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] == "msg-002"
        assert msg_map["msg-004"]["parentUuid"] == "msg-003"

        # Undo last repair
        success = repair_writer.undo_last_repair(temp_jsonl_file, session_id)
        assert success is True

        # Verify only first repair remains
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]
        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] == "msg-002"  # Still repaired
        assert msg_map["msg-004"]["parentUuid"] is None  # Undone

    def test_undo_stack_persistence(self, temp_backup_dir, temp_undo_dir, temp_jsonl_file):
        """
        Test that undo history persists across writer instances.
        Should reload undo stack from disk.
        """
        session_id = "test-session"

        # First writer instance
        writer1 = JSONLRepairWriter(backup_root=temp_backup_dir, undo_root=temp_undo_dir)

        # Apply repair and create snapshot
        repair = RepairOperation(
            message_uuid="msg-003",
            field_name="parentUuid",
            old_value=None,
            new_value="msg-002",
        )

        backup_path = writer1.create_backup(session_id, temp_jsonl_file)
        writer1.apply_repair(temp_jsonl_file, repair)
        writer1.push_repair_snapshot(session_id, temp_jsonl_file, backup_path, [repair])

        # Check history
        history1 = writer1.show_undo_history(session_id)
        assert len(history1) == 1

        # Create new writer instance
        writer2 = JSONLRepairWriter(backup_root=temp_backup_dir, undo_root=temp_undo_dir)

        # History should be loaded from disk
        history2 = writer2.show_undo_history(session_id)
        assert len(history2) == 1
        assert history2[0].session_id == session_id
        assert len(history2[0].repairs_applied) == 1

        # Undo should work with new instance
        success = writer2.undo_last_repair(temp_jsonl_file, session_id)
        assert success is True

        # Verify undo worked
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]
        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] is None  # Undone

    def test_show_undo_history(self, repair_writer, temp_jsonl_file):
        """
        Test viewing undo history for a session.
        Should return snapshots in reverse chronological order.
        """
        session_id = "test-session"

        # Apply 3 repairs with small delays to ensure different timestamps
        repairs_data = [
            ("msg-003", "msg-002"),
            ("msg-004", "msg-003"),
            ("msg-005", "msg-004"),
        ]

        for msg_id, parent_id in repairs_data:
            repair = RepairOperation(
                message_uuid=msg_id,
                field_name="parentUuid",
                old_value=None,
                new_value=parent_id,
            )

            backup = repair_writer.create_backup(session_id, temp_jsonl_file)
            repair_writer.apply_repair(temp_jsonl_file, repair)
            repair_writer.push_repair_snapshot(
                session_id, temp_jsonl_file, backup, [repair]
            )
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Get history
        history = repair_writer.show_undo_history(session_id)

        # Should have 3 snapshots
        assert len(history) == 3

        # Should be in reverse chronological order (newest first)
        timestamps = [h.timestamp for h in history]
        assert timestamps == sorted(timestamps, reverse=True)

        # Each snapshot should have correct data
        for i, snapshot in enumerate(history):
            assert isinstance(snapshot, RepairSnapshot)
            assert snapshot.session_id == session_id
            assert len(snapshot.repairs_applied) == 1
            assert snapshot.can_rollback is True

    def test_create_backup_nonexistent_file(self, repair_writer):
        """Test backup creation with non-existent file."""
        fake_path = Path("/tmp/nonexistent.jsonl")

        with pytest.raises(FileNotFoundError):
            repair_writer.create_backup("test", fake_path)

    def test_apply_repair_nonexistent_file(self, repair_writer):
        """Test repair application with non-existent file."""
        fake_path = Path("/tmp/nonexistent.jsonl")
        repair = RepairOperation(
            message_uuid="msg-001",
            field_name="parentUuid",
            old_value=None,
            new_value="msg-000",
        )

        with pytest.raises(FileNotFoundError):
            repair_writer.apply_repair(fake_path, repair)

    def test_apply_repair_nonexistent_message(self, repair_writer, temp_jsonl_file):
        """Test repair application with non-existent message UUID."""
        repair = RepairOperation(
            message_uuid="msg-999",  # Doesn't exist
            field_name="parentUuid",
            old_value=None,
            new_value="msg-001",
        )

        with pytest.raises(ValueError) as exc_info:
            repair_writer.apply_repair(temp_jsonl_file, repair)

        assert "not found" in str(exc_info.value)

    def test_rollback_nonexistent_backup(self, repair_writer, temp_jsonl_file):
        """Test rollback with non-existent backup file."""
        fake_backup = Path("/tmp/nonexistent_backup.jsonl")

        with pytest.raises(FileNotFoundError):
            repair_writer.rollback_to_backup(temp_jsonl_file, fake_backup)

    def test_undo_empty_history(self, repair_writer, temp_jsonl_file):
        """Test undo with empty history."""
        success = repair_writer.undo_last_repair(temp_jsonl_file, "no-history-session")
        assert success is False

    def test_repair_with_backup_workflow(self, repair_writer, temp_jsonl_file):
        """Test complete repair workflow with backup."""
        session_id = "test-session"

        repairs = [
            RepairOperation(
                message_uuid="msg-003",
                field="parentUuid",
                old_value=None,
                new_value="msg-002",
            ),
            RepairOperation(
                message_uuid="msg-004",
                field="parentUuid",
                old_value=None,
                new_value="msg-003",
            ),
        ]

        # Execute workflow
        success, backup_path = repair_writer.repair_with_backup(
            session_id, temp_jsonl_file, repairs
        )

        assert success is True
        assert backup_path is not None
        assert backup_path.exists()

        # Verify repairs applied
        with open(temp_jsonl_file) as f:
            messages = [json.loads(line) for line in f]
        msg_map = {m["uuid"]: m for m in messages}
        assert msg_map["msg-003"]["parentUuid"] == "msg-002"
        assert msg_map["msg-004"]["parentUuid"] == "msg-003"

        # Verify snapshot created
        history = repair_writer.show_undo_history(session_id)
        assert len(history) == 1
        assert len(history[0].repairs_applied) == 2

    def test_list_backups(self, repair_writer, temp_jsonl_file):
        """Test listing backups for a session."""
        session_id = "test-session"

        # Create multiple backups
        for i in range(3):
            repair_writer.create_backup(session_id, temp_jsonl_file)
            time.sleep(0.01)  # Small delay

        # List backups
        backups = repair_writer.list_backups(session_id)

        assert len(backups) == 3
        # Should be sorted newest first
        assert all(b.exists() for b in backups)

    def test_delete_backup(self, repair_writer, temp_jsonl_file):
        """Test backup deletion."""
        session_id = "test-session"

        # Create backup
        backup_path = repair_writer.create_backup(session_id, temp_jsonl_file)
        assert backup_path.exists()

        # Delete backup
        success = repair_writer.delete_backup(backup_path)
        assert success is True
        assert not backup_path.exists()

        # Delete non-existent should return False
        success = repair_writer.delete_backup(backup_path)
        assert success is False

    def test_max_undo_stack_size(self, repair_writer, temp_jsonl_file):
        """Test that undo stack respects maximum size limit."""
        session_id = "test-session"

        # Create more repairs than max stack size (10)
        for i in range(15):
            repair = RepairOperation(
                message_uuid="msg-003",
                field_name="parentUuid",
                old_value=None if i == 0 else f"msg-00{i}",
                new_value=f"msg-00{i+1}",
            )

            backup = repair_writer.create_backup(session_id, temp_jsonl_file)
            repair_writer.apply_repair(temp_jsonl_file, repair)
            repair_writer.push_repair_snapshot(
                session_id, temp_jsonl_file, backup, [repair]
            )

        # History should be limited to 10 most recent
        history = repair_writer.show_undo_history(session_id)
        assert len(history) == 10

    def test_factory_function(self):
        """Test the create_repair_writer factory function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            writer = create_repair_writer(
                backup_root=temp_path / "backups",
                undo_root=temp_path / "undo"
            )

            assert isinstance(writer, JSONLRepairWriter)
            assert writer.backup_root == temp_path / "backups"
            assert writer.undo_root == temp_path / "undo"
            assert writer.backup_root.exists()
            assert writer.undo_root.exists()

    def test_repair_operation_serialization(self):
        """Test RepairOperation to_dict and from_dict methods."""
        original = RepairOperation(
            message_uuid="test-msg",
            field_name="parentUuid",
            old_value="old-parent",
            new_value="new-parent",
            reason="Test repair",
        )

        # Serialize
        data = original.to_dict()
        assert data["message_uuid"] == "test-msg"
        assert data["field"] == "parentUuid"  # Serializes as "field"
        assert data["reason"] == "Test repair"

        # Deserialize
        restored = RepairOperation.from_dict(data)
        assert restored.message_uuid == original.message_uuid
        assert restored.field_name == original.field_name
        assert restored.old_value == original.old_value
        assert restored.new_value == original.new_value
        assert restored.reason == original.reason

    def test_repair_snapshot_serialization(self):
        """Test RepairSnapshot to_dict and from_dict methods."""
        repairs = [
            RepairOperation(
                message_uuid="msg-001",
                field_name="parentUuid",
                old_value=None,
                new_value="msg-000",
            )
        ]

        original = RepairSnapshot(
            session_id="test-session",
            timestamp=datetime.now(),
            original_jsonl_path=Path("/tmp/test.jsonl"),
            backup_path=Path("/tmp/backup.jsonl"),
            repairs_applied=repairs,
            can_rollback=True,
        )

        # Serialize
        data = original.to_dict()
        assert data["session_id"] == "test-session"
        assert len(data["repairs_applied"]) == 1

        # Deserialize
        restored = RepairSnapshot.from_dict(data)
        assert restored.session_id == original.session_id
        assert len(restored.repairs_applied) == 1
        assert restored.repairs_applied[0].message_uuid == "msg-001"
        assert restored.can_rollback is True