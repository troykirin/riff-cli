"""
Concrete implementations of PersistenceProvider for different backends.

This module provides:
- JSONLRepairProvider: Backend using JSONLRepairWriter for JSONL files
- Can be extended with SurrealDBRepairProvider, PostgreSQL, etc.
"""

from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime

from .persistence import JSONLRepairWriter, RepairOperation as JSONLRepairOperation
from .persistence_provider import PersistenceProvider, RepairSnapshot
from .repair import RepairOperation as EngineRepairOperation

logger = logging.getLogger(__name__)


class JSONLRepairProvider(PersistenceProvider):
    """
    Repair persistence provider using JSONL backend.

    Wraps JSONLRepairWriter to provide PersistenceProvider interface.
    """

    def __init__(self, backup_root: Optional[Path] = None):
        """
        Initialize JSONL repair provider.

        Args:
            backup_root: Root directory for backups (default: ~/.riff/backups/)
        """
        self.writer = JSONLRepairWriter(backup_root=backup_root)
        self.backend_name = "JSONL"

    def create_backup(self, session_id: str, source_path: Path) -> Path:
        """
        Create a backup of JSONL file before repair.

        Args:
            session_id: Session UUID
            source_path: Path to JSONL file

        Returns:
            Path to created backup

        Raises:
            IOError: If backup creation fails
        """
        try:
            backup_path = self.writer.create_backup(session_id, source_path)
            logger.info(f"Created JSONL backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise IOError(f"Backup creation failed: {e}")

    def apply_repair(
        self, target_path: Path, repair_op: EngineRepairOperation
    ) -> bool:
        """
        Apply a repair operation to JSONL.

        Args:
            target_path: Path to JSONL file
            repair_op: Repair operation from repair engine

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert EngineRepairOperation to JSONLRepairOperation
            timestamp_str: str = repair_op.timestamp.isoformat() if isinstance(repair_op.timestamp, datetime) else str(repair_op.timestamp)
            jsonl_repair = JSONLRepairOperation(
                message_uuid=repair_op.message_id,
                field_name="parentUuid",
                old_value=repair_op.original_parent_uuid,
                new_value=repair_op.suggested_parent_uuid,
                timestamp=timestamp_str,
                reason=repair_op.reason,
            )

            success = self.writer.apply_repair(target_path, jsonl_repair)

            if success:
                logger.info(
                    f"Applied repair to {repair_op.message_id}: "
                    f"{repair_op.original_parent_uuid} → {repair_op.suggested_parent_uuid}"
                )
            else:
                logger.error(f"Failed to apply repair: {repair_op.message_id}")

            return success
        except Exception as e:
            logger.error(f"Error applying repair: {e}")
            return False

    def rollback_to_backup(self, target_path: Path, backup_path: Path) -> bool:
        """
        Rollback JSONL to a previous backup.

        Args:
            target_path: Path to JSONL file to restore
            backup_path: Path to backup to restore from

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.writer.rollback_to_backup(target_path, backup_path)

            if success:
                logger.info(f"Rolled back {target_path} from {backup_path}")
            else:
                logger.error(f"Rollback failed: {target_path}")

            return success
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            return False

    def show_undo_history(self, session_id: str) -> List[RepairSnapshot]:
        """
        Get available undo points for a session.

        Args:
            session_id: Session UUID

        Returns:
            List of RepairSnapshot objects, most recent first
        """
        try:
            jsonl_snapshots = self.writer.show_undo_history(session_id)

            # Convert JSONLRepairSnapshot to PersistenceProvider RepairSnapshot
            snapshots = []
            for js in jsonl_snapshots:
                snapshot = RepairSnapshot(
                    backup_path=js.backup_path,
                    timestamp=js.timestamp.isoformat(),
                    repair_count=len(js.repairs_applied),
                    reason="; ".join(r.reason for r in js.repairs_applied if r.reason),
                )
                snapshots.append(snapshot)

            return snapshots
        except Exception as e:
            logger.error(f"Error retrieving undo history: {e}")
            return []

    def get_backend_name(self) -> str:
        """Get backend name."""
        return self.backend_name
