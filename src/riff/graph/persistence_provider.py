"""
Persistence Provider: Abstract interface for repair persistence backends.

This module defines the PersistenceProvider interface that allows RepairManager
to work with different backends (JSONL, SurrealDB, etc.) without code changes.

Architecture:
- PersistenceProvider (abstract): Defines repair persistence interface
- JSONLRepairProvider: Wraps JSONLRepairWriter for JSONL backend
- Pluggable design: Easy to add new backends (PostgreSQL, etc)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, TYPE_CHECKING
from dataclasses import dataclass
import logging

if TYPE_CHECKING:
    from .repair import RepairOperation

logger = logging.getLogger(__name__)


@dataclass
class RepairSnapshot:
    """Represents a backup point for undo/rollback."""

    backup_path: Path
    timestamp: str
    repair_count: int
    reason: str


class PersistenceProvider(ABC):
    """
    Abstract base class for repair persistence backends.

    Defines the interface for storing repair operations, creating backups,
    and managing undo/rollback capabilities.
    """

    @abstractmethod
    def create_backup(self, session_id: str, source_path: Path) -> Path:
        """
        Create a backup before repair.

        Args:
            session_id: Session UUID
            source_path: Path to source data (JSONL file or DB reference)

        Returns:
            Path to created backup

        Raises:
            IOError: If backup creation fails
        """
        pass

    @abstractmethod
    def apply_repair(self, target_path: Path, repair_op: 'RepairOperation') -> bool:
        """
        Apply a repair operation to persistent storage.

        Args:
            target_path: Path to target file (JSONL) or DB reference
            repair_op: Repair operation to apply

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If repair validation fails
            IOError: If write fails
        """
        pass

    @abstractmethod
    def rollback_to_backup(self, target_path: Path, backup_path: Path) -> bool:
        """
        Rollback to a previous backup.

        Args:
            target_path: Path to target file to restore
            backup_path: Path to backup to restore from

        Returns:
            True if successful, False otherwise

        Raises:
            IOError: If rollback fails
        """
        pass

    @abstractmethod
    def show_undo_history(self, session_id: str) -> List[RepairSnapshot]:
        """
        Get available undo points.

        Args:
            session_id: Session UUID

        Returns:
            List of RepairSnapshot objects, most recent first
        """
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Get human-readable backend name (e.g., 'JSONL', 'SurrealDB')."""
        pass
