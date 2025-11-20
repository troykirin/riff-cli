"""
Persistence layer for riff-cli with JSONL writer and undo/rollback capabilities.

Provides:
- RepairOperation and RepairSnapshot dataclasses
- JSONLRepairWriter for atomic JSONL updates
- Undo/rollback system with backup management
- Session-scoped undo history
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

from .loaders import JSONLLoader

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class RepairOperation:
    """
    Represents a single repair operation on a message.

    Attributes:
        message_uuid: UUID of the message being repaired (renamed from message_id for consistency)
        field: Field being modified (e.g., "parentUuid")
        old_value: Original value
        new_value: New value
        timestamp: When this repair was performed
        reason: Optional explanation for the repair
    """

    message_uuid: str  # Renamed from message_id to match test expectations
    field_name: str = "parentUuid"  # Renamed to avoid conflict with dataclass field
    old_value: Any = None
    new_value: Any = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reason: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "message_uuid": self.message_uuid,
            "field": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RepairOperation":
        """Create RepairOperation from dictionary."""
        return cls(
            message_uuid=data["message_uuid"],
            field_name=data.get("field", "parentUuid"),  # Support both field and field_name
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            reason=data.get("reason", ""),
        )


@dataclass
class RepairSnapshot:
    """
    Represents a snapshot of repairs applied to a session.

    Attributes:
        session_id: Session identifier
        timestamp: When this snapshot was created
        original_jsonl_path: Path to the session JSONL file
        backup_path: Path to full backup before repairs
        repairs_applied: List of repairs in this snapshot
        can_rollback: Whether rollback is possible (backup exists)
    """

    session_id: str
    timestamp: datetime
    original_jsonl_path: Path
    backup_path: Path
    repairs_applied: List[RepairOperation]
    can_rollback: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "original_jsonl_path": str(self.original_jsonl_path),
            "backup_path": str(self.backup_path),
            "repairs_applied": [r.to_dict() for r in self.repairs_applied],
            "can_rollback": self.can_rollback,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RepairSnapshot:
        """Create RepairSnapshot from dictionary."""
        return cls(
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            original_jsonl_path=Path(data["original_jsonl_path"]),
            backup_path=Path(data["backup_path"]),
            repairs_applied=[RepairOperation.from_dict(r) for r in data["repairs_applied"]],
            can_rollback=data.get("can_rollback", True),
        )


# ============================================================================
# JSONLRepairWriter
# ============================================================================


class JSONLRepairWriter:
    """
    Writer for persisting repairs to JSONL with rollback/undo support.

    Features:
    - Atomic JSONL updates (write to temp file, then rename)
    - Timestamped backups before repairs
    - In-memory undo stack (last 10 operations per session)
    - Persistent undo history to disk
    - Validation after each write

    Attributes:
        backup_root: Root directory for backups (~/.riff/backups/)
        undo_root: Root directory for undo history (~/.riff/undo/)
        undo_stacks: In-memory undo stacks per session
    """

    def __init__(
        self,
        backup_root: Optional[Path] = None,
        undo_root: Optional[Path] = None,
    ) -> None:
        """
        Initialize JSONL repair writer.

        Args:
            backup_root: Override default backup directory
            undo_root: Override default undo directory
        """
        # Setup directories
        home = Path.home()
        self.backup_root = backup_root or home / ".riff" / "backups"
        self.undo_root = undo_root or home / ".riff" / "undo"

        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.undo_root.mkdir(parents=True, exist_ok=True)

        # In-memory undo stacks (session_id -> List[RepairSnapshot])
        self.undo_stacks: dict[str, List[RepairSnapshot]] = {}
        self._max_undo_stack_size = 10

        logger.info(f"JSONLRepairWriter initialized: backups={self.backup_root}, undo={self.undo_root}")

    # ========================================================================
    # Backup Management
    # ========================================================================

    def create_backup(self, session_id: str, jsonl_path: Path) -> Path:
        """
        Create timestamped backup of JSONL file.

        Args:
            session_id: Session identifier
            jsonl_path: Path to JSONL file to backup

        Returns:
            Path to created backup file

        Raises:
            FileNotFoundError: If jsonl_path doesn't exist
            IOError: If backup creation fails
        """
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

        # Create session backup directory
        session_backup_dir = self.backup_root / session_id
        session_backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"{timestamp}.jsonl"
        backup_path = session_backup_dir / backup_filename

        try:
            # Copy file to backup
            shutil.copy2(jsonl_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except IOError as e:
            logger.error(f"Failed to create backup: {e}")
            raise IOError(f"Backup creation failed: {e}")

    def list_backups(self, session_id: str) -> List[Path]:
        """
        List all backups for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of backup paths, sorted by timestamp (newest first)
        """
        session_backup_dir = self.backup_root / session_id

        if not session_backup_dir.exists():
            return []

        backups = sorted(
            session_backup_dir.glob("*.jsonl"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        return backups

    def delete_backup(self, backup_path: Path) -> bool:
        """
        Delete a specific backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Deleted backup: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_path}: {e}")
            return False

    # ========================================================================
    # Repair Operations
    # ========================================================================

    def apply_repair(
        self,
        jsonl_path: Path,
        repair_op: RepairOperation,
    ) -> bool:
        """
        Apply a single repair operation to JSONL file.

        Atomically updates the parentUuid field for a message.

        Args:
            jsonl_path: Path to JSONL file
            repair_op: Repair operation to apply

        Returns:
            True if repair succeeded, False otherwise

        Raises:
            FileNotFoundError: If jsonl_path doesn't exist
            ValueError: If message_id not found in JSONL
        """
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

        try:
            # Load all records
            records = []
            message_found = False

            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    record = json.loads(line)

                    # Update target message
                    if record.get("uuid") == repair_op.message_uuid:
                        # Apply the field update
                        if repair_op.field_name == "parentUuid":
                            record["parentUuid"] = repair_op.new_value
                        else:
                            record[repair_op.field_name] = repair_op.new_value
                        message_found = True
                        logger.debug(
                            f"Updated message {repair_op.message_uuid}: "
                            f"{repair_op.field_name} = {repair_op.old_value} -> {repair_op.new_value}"
                        )

                    records.append(record)

            if not message_found:
                raise ValueError(f"Message {repair_op.message_uuid} not found in {jsonl_path}")

            # Atomic write: write to temp file, then rename
            temp_path = jsonl_path.with_suffix(".jsonl.tmp")

            with open(temp_path, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Atomic rename
            os.replace(temp_path, jsonl_path)

            # Validate written JSONL
            if not self._validate_jsonl(jsonl_path):
                logger.error(f"Validation failed after repair: {jsonl_path}")
                return False

            logger.info(f"Applied repair to {jsonl_path}: message={repair_op.message_uuid}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply repair: {e}")
            return False

    def apply_batch_repairs(
        self,
        jsonl_path: Path,
        repairs: List[RepairOperation],
    ) -> Tuple[bool, List[RepairOperation]]:
        """
        Apply multiple repairs in order.

        Stops on first failure and returns which repairs were applied.

        Args:
            jsonl_path: Path to JSONL file
            repairs: List of repair operations to apply

        Returns:
            Tuple of (all_succeeded, repairs_that_were_applied)
        """
        applied_repairs: list[RepairOperation] = []

        for repair in repairs:
            success = self.apply_repair(jsonl_path, repair)

            if not success:
                logger.warning(
                    f"Batch repair stopped at repair #{len(applied_repairs) + 1} "
                    f"(message={repair.message_uuid})"
                )
                return False, applied_repairs

            applied_repairs.append(repair)

        logger.info(f"Applied {len(applied_repairs)} repairs successfully to {jsonl_path}")
        return True, applied_repairs

    # ========================================================================
    # Rollback Operations
    # ========================================================================

    def rollback_to_backup(self, jsonl_path: Path, backup_path: Path) -> bool:
        """
        Restore JSONL from backup.

        Args:
            jsonl_path: Target JSONL file path
            backup_path: Backup file to restore from

        Returns:
            True if rollback succeeded, False otherwise

        Raises:
            FileNotFoundError: If backup_path doesn't exist
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            # Copy backup to temp file
            temp_path = jsonl_path.with_suffix(".jsonl.tmp")
            shutil.copy2(backup_path, temp_path)

            # Validate restored JSONL
            if not self._validate_jsonl(temp_path):
                logger.error(f"Restored backup failed validation: {backup_path}")
                temp_path.unlink()
                return False

            # Atomic rename
            os.replace(temp_path, jsonl_path)

            logger.info(f"Rolled back {jsonl_path} to backup {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    # ========================================================================
    # Undo System
    # ========================================================================

    def _get_undo_stack(self, session_id: str) -> List[RepairSnapshot]:
        """Get or initialize undo stack for a session."""
        if session_id not in self.undo_stacks:
            # Try to load from disk
            self.undo_stacks[session_id] = self._load_undo_stack(session_id)

        return self.undo_stacks[session_id]

    def _save_undo_stack(self, session_id: str) -> None:
        """Persist undo stack to disk."""
        undo_file = self.undo_root / f"{session_id}.json"
        stack = self.undo_stacks.get(session_id, [])

        try:
            with open(undo_file, "w", encoding="utf-8") as f:
                data = {
                    "session_id": session_id,
                    "snapshots": [snapshot.to_dict() for snapshot in stack],
                }
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved undo stack for {session_id}: {len(stack)} snapshots")

        except Exception as e:
            logger.error(f"Failed to save undo stack: {e}")

    def _load_undo_stack(self, session_id: str) -> List[RepairSnapshot]:
        """Load undo stack from disk."""
        undo_file = self.undo_root / f"{session_id}.json"

        if not undo_file.exists():
            return []

        try:
            with open(undo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                snapshots = [RepairSnapshot.from_dict(s) for s in data.get("snapshots", [])]
                logger.debug(f"Loaded undo stack for {session_id}: {len(snapshots)} snapshots")
                return snapshots

        except Exception as e:
            logger.error(f"Failed to load undo stack: {e}")
            return []

    def push_repair_snapshot(
        self,
        session_id: str,
        jsonl_path: Path,
        backup_path: Path,
        repairs: List[RepairOperation],
    ) -> None:
        """
        Push a new repair snapshot onto the undo stack.

        Args:
            session_id: Session identifier
            jsonl_path: Path to JSONL file
            backup_path: Path to backup before repairs
            repairs: List of repairs applied
        """
        snapshot = RepairSnapshot(
            session_id=session_id,
            timestamp=datetime.now(),
            original_jsonl_path=jsonl_path,
            backup_path=backup_path,
            repairs_applied=repairs,
            can_rollback=backup_path.exists(),
        )

        stack = self._get_undo_stack(session_id)
        stack.append(snapshot)

        # Limit stack size
        if len(stack) > self._max_undo_stack_size:
            removed = stack.pop(0)
            logger.debug(f"Removed oldest snapshot from undo stack: {removed.timestamp}")

        self.undo_stacks[session_id] = stack
        self._save_undo_stack(session_id)

        logger.info(
            f"Pushed repair snapshot for {session_id}: "
            f"{len(repairs)} repairs, stack size={len(stack)}"
        )

    def show_undo_history(self, session_id: str) -> List[RepairSnapshot]:
        """
        List all available undo points for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of repair snapshots, newest first
        """
        stack = self._get_undo_stack(session_id)
        return list(reversed(stack))  # Newest first

    def undo_last_repair(self, jsonl_path: Path, session_id: str) -> bool:
        """
        Undo the last repair operation.

        Restores to the previous state using the most recent backup.

        Args:
            jsonl_path: Path to JSONL file
            session_id: Session identifier

        Returns:
            True if undo succeeded, False otherwise
        """
        stack = self._get_undo_stack(session_id)

        if not stack:
            logger.warning(f"No undo history for session {session_id}")
            return False

        # Pop last snapshot
        last_snapshot = stack.pop()
        self.undo_stacks[session_id] = stack
        self._save_undo_stack(session_id)

        # Rollback to backup
        if not last_snapshot.can_rollback:
            logger.error(f"Cannot rollback: backup missing ({last_snapshot.backup_path})")
            return False

        success = self.rollback_to_backup(jsonl_path, last_snapshot.backup_path)

        if success:
            logger.info(
                f"Undid {len(last_snapshot.repairs_applied)} repairs "
                f"(timestamp={last_snapshot.timestamp})"
            )
        else:
            logger.error("Undo failed")

        return success

    # ========================================================================
    # Validation
    # ========================================================================

    def _validate_jsonl(self, jsonl_path: Path) -> bool:
        """
        Validate JSONL file integrity.

        Uses JSONLLoader to parse and ensure structural validity.

        Args:
            jsonl_path: Path to JSONL file

        Returns:
            True if valid, False otherwise
        """
        try:
            # Extract session_id from filename
            session_id = jsonl_path.stem

            # Try to load with JSONLLoader
            loader = JSONLLoader(jsonl_path.parent)
            messages = loader.load_messages(session_id)

            # Basic validation: should have at least one message
            if not messages:
                logger.warning(f"Validation: JSONL contains no messages: {jsonl_path}")
                return False

            logger.debug(f"Validation passed: {len(messages)} messages in {jsonl_path}")
            return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    # ========================================================================
    # Workflow Helpers
    # ========================================================================

    def repair_with_backup(
        self,
        session_id: str,
        jsonl_path: Path,
        repairs: List[RepairOperation],
    ) -> Tuple[bool, Optional[Path]]:
        """
        Complete workflow: backup, apply repairs, push snapshot.

        Args:
            session_id: Session identifier
            jsonl_path: Path to JSONL file
            repairs: List of repairs to apply

        Returns:
            Tuple of (success, backup_path)
        """
        try:
            # Create backup
            backup_path = self.create_backup(session_id, jsonl_path)

            # Apply repairs
            success, applied_repairs = self.apply_batch_repairs(jsonl_path, repairs)

            if not success:
                logger.warning(
                    f"Partial repair failure: {len(applied_repairs)}/{len(repairs)} applied"
                )
                # Still push snapshot with partial repairs
                self.push_repair_snapshot(session_id, jsonl_path, backup_path, applied_repairs)
                return False, backup_path

            # Push snapshot to undo stack
            self.push_repair_snapshot(session_id, jsonl_path, backup_path, applied_repairs)

            logger.info(f"Repair workflow complete: {len(repairs)} repairs applied")
            return True, backup_path

        except Exception as e:
            logger.error(f"Repair workflow failed: {e}")
            return False, None


# ============================================================================
# Convenience Functions
# ============================================================================


def create_repair_writer(
    backup_root: Optional[Path] = None,
    undo_root: Optional[Path] = None,
) -> JSONLRepairWriter:
    """
    Factory function to create a JSONLRepairWriter.

    Args:
        backup_root: Override default backup directory
        undo_root: Override default undo directory

    Returns:
        Configured JSONLRepairWriter instance
    """
    return JSONLRepairWriter(backup_root=backup_root, undo_root=undo_root)
