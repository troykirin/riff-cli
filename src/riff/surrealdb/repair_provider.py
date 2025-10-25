"""
SurrealDB Repair Provider: Event-sourced repairs with immutable audit trail.

This module implements PersistenceProvider using SurrealDB as the backend,
providing immutable append-only repair event logging with full audit trails.

Key Features:
- Immutable repair events (never updated or deleted)
- Full audit trail: who, what, when, why, confidence
- Event replay for point-in-time session reconstruction
- Automatic revert events for undo operations
- No JSONL mutations (read-only reference)
"""

from pathlib import Path
from typing import List
from datetime import datetime, timezone
import logging

from ..graph.persistence_provider import PersistenceProvider, RepairSnapshot
from ..graph.repair import RepairOperation as EngineRepairOperation
from .storage import SurrealDBStorage

logger = logging.getLogger(__name__)


class SurrealDBRepairProvider(PersistenceProvider):
    """
    Repair persistence provider using SurrealDB backend.

    Immutable event-sourced repairs with:
    - Append-only repair_events table
    - Automatic audit trail
    - Event replay capability
    - Revert events for undo (no destructive updates)
    """

    def __init__(
        self,
        storage: SurrealDBStorage,
        operator: str = "tui",
    ):
        """
        Initialize SurrealDB repair provider.

        Args:
            storage: SurrealDBStorage instance (HTTP-connected)
            operator: Operator name for audit trail (default: "tui")
        """
        self.storage = storage
        self.operator = operator
        self.backend_name = "SurrealDB"
        self._event_history: List[str] = []  # Track event IDs for revert

    def create_backup(self, session_id: str, source_path: Path) -> Path:
        """
        Create a "backup" by recording session state before repair.

        For SurrealDB backend, this creates a timestamp marker for rollback.
        No physical backup file is created - events are immutable.

        Args:
            session_id: Session UUID
            source_path: Path to source (used for consistency with interface)

        Returns:
            Virtual backup path (SurrealDB event timestamp)
        """
        try:
            # Record current state as a reference point
            # In SurrealDB, the backup is implicit in the event log
            timestamp = datetime.now(timezone.utc).isoformat()

            # Return a virtual backup path indicating the current state
            backup_path = Path(f"surrealdb://session/{session_id}/snapshot/{timestamp}")

            logger.info(
                f"Created virtual SurrealDB backup marker: {backup_path}"
            )
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create SurrealDB backup marker: {e}")
            raise IOError(f"Backup creation failed: {e}")

    def apply_repair(
        self, target_path: Path, repair_op: EngineRepairOperation
    ) -> bool:
        """
        Apply repair by creating immutable repair event in SurrealDB.

        The event is appended to repairs_events table and never modified.
        This creates a permanent audit trail.

        Args:
            target_path: Path to JSONL (for session_id extraction)
            repair_op: Repair operation to log

        Returns:
            True if event successfully created, False otherwise
        """
        try:
            # Extract session_id from JSONL path
            _session_id = self._extract_session_id(target_path)

            # Log immutable repair event to SurrealDB
            success = self.storage.log_repair_event(
                repair_op=repair_op,
                operator=self.operator,
            )

            if success:
                # Track for potential revert
                self._event_history.append(repair_op.message_id)

                logger.info(
                    f"Created immutable repair event for message={repair_op.message_id}, "
                    f"parent: {repair_op.original_parent_uuid} → "
                    f"{repair_op.suggested_parent_uuid} "
                    f"(SurrealDB append-only log)"
                )
                return True
            else:
                logger.error("Failed to log repair event to SurrealDB")
                return False

        except Exception as e:
            logger.error(f"Error applying repair to SurrealDB: {e}")
            return False

    def rollback_to_backup(self, target_path: Path, backup_path: Path) -> bool:
        """
        Undo repair by creating revert event (no destructive updates).

        In SurrealDB, undo doesn't mutate existing events.
        Instead, we create a new "revert" event that documents the undo action.

        Args:
            target_path: Path to JSONL (for session_id extraction)
            backup_path: Virtual backup path (SurrealDB event timestamp)

        Returns:
            True if revert event successfully created, False otherwise
        """
        try:
            _session_id = self._extract_session_id(target_path)

            # Get last event from history
            if not self._event_history:
                logger.error("No repair events to revert")
                return False

            last_message_id = self._event_history[-1]

            # Create revert operation to log the undo action
            # Note: For revert operations, we use empty string for suggested_parent_uuid
            # to indicate this is a revert rather than a standard repair
            revert_operation = EngineRepairOperation(
                message_id=last_message_id,
                original_parent_uuid=None,
                suggested_parent_uuid="",  # Empty string indicates revert operation
                similarity_score=1.0,
                reason="System-initiated revert/undo",
                timestamp=datetime.now(timezone.utc),
            )

            # Log revert event to audit trail
            success = self.storage.log_repair_event(
                repair_op=revert_operation,
                operator=f"{self.operator}:system-revert",
            )

            if success:
                self._event_history.pop()
                logger.info(
                    f"Created revert event for {last_message_id} "
                    f"(no destructive update, immutable audit trail preserved)"
                )
                return True
            else:
                logger.error("Failed to create revert event")
                return False

        except Exception as e:
            logger.error(f"Error during SurrealDB rollback: {e}")
            return False

    def show_undo_history(self, session_id: str) -> List[RepairSnapshot]:
        """
        Get repair event history for undo display.

        Retrieves immutable repair events from SurrealDB.

        Args:
            session_id: Session UUID

        Returns:
            List of RepairSnapshot objects representing events
        """
        try:
            # Get repair events from SurrealDB
            events = self.storage.get_session_history(session_id)

            if not events:
                logger.debug(f"No repair events found for session {session_id}")
                return []

            # Convert to RepairSnapshot for UI display
            # Most recent events first for undo display
            snapshots = []
            for event in reversed(events):
                # Skip system revert events in display (they're markers)
                if "revert" in event.reason.lower():
                    continue

                snapshot = RepairSnapshot(
                    backup_path=Path(
                        f"surrealdb://event/{event.event_id}/timestamp/{event.timestamp.isoformat()}"
                    ),
                    timestamp=event.timestamp.isoformat(),
                    repair_count=1,  # One event per snapshot
                    reason=event.reason or "Immutable repair event",
                )
                snapshots.append(snapshot)

            return snapshots

        except Exception as e:
            logger.error(f"Error retrieving SurrealDB undo history: {e}")
            return []

    def get_backend_name(self) -> str:
        """Get backend name."""
        return self.backend_name

    def _extract_session_id(self, path: Path) -> str:
        """
        Extract session UUID from JSONL path.

        Format: ~/.claude/projects/-Users-tryk--nabi/{session-id}.jsonl

        Args:
            path: Path object

        Returns:
            Session UUID string
        """
        # Get filename without extension
        filename = path.stem

        # If it looks like a UUID, use it
        if len(filename) == 36 and filename.count("-") == 4:
            return filename

        # Fallback: use full filename
        logger.warning(f"Could not extract session UUID from path: {path}")
        return path.stem
