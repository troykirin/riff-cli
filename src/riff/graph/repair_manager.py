"""
Repair Manager: Coordinates repair engine, persistence, and DAG updates.

This module bridges the gap between:
- TUI (requests repairs, shows diffs, handles confirmations)
- RepairEngine (finds orphans, suggests parents, validates repairs)
- PersistenceProvider (abstract backend for persisting repairs)
  - JSONLRepairProvider: JSONL backend
  - SurrealDBRepairProvider: Event-sourced backend
- ConversationDAG (rebuilds graph after repairs)

Architecture:
- RepairManager is backend-agnostic (pluggable persistence)
- Different backends log repairs differently:
  - JSONL: Mutates JSONL with atomic writes
  - SurrealDB: Appends immutable repair events
"""

from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass
import logging

from .models import Session, Message
from .dag import ConversationDAG
from .loaders import JSONLLoader
from .repair import ConversationRepairEngine, RepairOperation as EngineRepairOperation
from .persistence_provider import PersistenceProvider, RepairSnapshot
from .persistence_providers import JSONLRepairProvider

logger = logging.getLogger(__name__)


@dataclass
class RepairPreview:
    """Preview of a suggested repair before confirmation."""

    message_id: str
    message_preview: str  # First 100 chars of message content
    current_parent: Optional[str]
    suggested_parent: Optional[str]
    parent_preview: str  # First 100 chars of parent content
    similarity_score: float
    reason: str
    diff: str  # Unified diff showing change


@dataclass
class RepairResult:
    """Result of applying a repair operation."""

    success: bool
    message: str
    backup_path: Optional[Path] = None
    repair_op: Optional[EngineRepairOperation] = None


class RepairManager:
    """
    Coordinates repair operations between TUI, engine, and persistence.

    Workflow:
    1. User marks orphaned messages (m keybinding)
    2. User requests repair preview (r keybinding) -> show_repair_preview()
    3. User confirms or cancels
    4. If confirmed -> apply_repair()
    5. DAG reloads automatically
    6. User can undo (u keybinding) -> undo_repair()

    Backend Flexibility:
    - Constructor accepts any PersistenceProvider implementation
    - Can switch between JSONL and SurrealDB without code changes
    - Backend choice propagates to apply/undo operations
    """

    def __init__(
        self,
        session_id: str,
        jsonl_path: Path,
        session: Session,
        dag: ConversationDAG,
        loader: JSONLLoader,
        persistence_provider: Optional[PersistenceProvider] = None,
    ):
        """
        Initialize repair manager with pluggable persistence backend.

        Args:
            session_id: Claude session UUID
            jsonl_path: Path to JSONL file
            session: Current Session object
            dag: ConversationDAG instance
            loader: JSONLLoader instance for reloading after repairs
            persistence_provider: Backend for persisting repairs
                                 (default: JSONLRepairProvider)
        """
        self.session_id = session_id
        self.jsonl_path = jsonl_path
        self.session = session
        self.dag = dag
        self.loader = loader

        # Initialize repair components
        self.repair_engine = ConversationRepairEngine()

        # Use provided provider or default to JSONL
        self.persistence_provider: PersistenceProvider
        if persistence_provider is None:
            self.persistence_provider = JSONLRepairProvider()
        else:
            self.persistence_provider = persistence_provider

        logger.info(
            f"RepairManager using {self.persistence_provider.get_backend_name()} backend"
        )

        # Track current repair state
        self.pending_repair: Optional[RepairPreview] = None
        self.applied_repairs: List[EngineRepairOperation] = []

    def get_orphaned_messages(self) -> List[Message]:
        """Get list of orphaned messages in current session."""
        return self.repair_engine.find_orphaned_messages(self.session)

    def get_repair_candidates(
        self,
        message: Message,
        top_k: int = 3
    ) -> List[Tuple[EngineRepairOperation, Message]]:
        """
        Get repair candidate parents for an orphaned message.

        Args:
            message: Orphaned message to repair
            top_k: Number of candidates to return

        Returns:
            List of (RepairOperation, parent_message) tuples
        """
        candidates = self.repair_engine.suggest_parent_candidates(
            message, self.session, top_k=top_k
        )

        # Enrich with parent message objects for preview
        result = []
        for repair_op in candidates:
            parent_msg = self._find_message_by_uuid(
                repair_op.suggested_parent_uuid
            )
            if parent_msg:
                result.append((repair_op, parent_msg))

        return result

    def create_repair_preview(
        self,
        message: Message,
        repair_op: EngineRepairOperation,
        parent_message: Optional[Message] = None
    ) -> RepairPreview:
        """
        Create a preview of the repair before confirmation.

        Args:
            message: Message to repair
            repair_op: Suggested repair operation
            parent_message: Parent message (if available)

        Returns:
            RepairPreview with diff and details
        """
        if not parent_message:
            parent_message = self._find_message_by_uuid(
                repair_op.suggested_parent_uuid
            )

        # Generate diff
        diff_obj = self.repair_engine.calculate_repair_diff(
            message,
            repair_op.suggested_parent_uuid
        )

        parent_content = (
            parent_message.content[:100] if parent_message
            else "<<unknown parent>>"
        )

        return RepairPreview(
            message_id=message.uuid,
            message_preview=message.content[:100],
            current_parent=message.parent_uuid,
            suggested_parent=repair_op.suggested_parent_uuid,
            parent_preview=parent_content,
            similarity_score=repair_op.similarity_score,
            reason=repair_op.reason,
            diff=str(diff_obj)
        )

    def apply_repair(
        self,
        message: Message,
        new_parent_uuid: str
    ) -> RepairResult:
        """
        Apply a repair operation: validate, backup, persist, reload.

        Args:
            message: Message to repair
            new_parent_uuid: Suggested parent UUID

        Returns:
            RepairResult with success status and details
        """
        # Step 1: Validate repair
        is_valid, validation_msg = self.repair_engine.validate_repair(
            message, new_parent_uuid, self.session
        )

        if not is_valid:
            return RepairResult(
                success=False,
                message=f"Validation failed: {validation_msg}"
            )

        try:
            # Step 2: Create backup (backend-specific)
            backup_path = self.persistence_provider.create_backup(
                self.session_id, self.jsonl_path
            )
            logger.info(f"Created backup: {backup_path}")

            # Step 3: Create repair operation
            parent_msg = self._find_message_by_uuid(new_parent_uuid)
            if not parent_msg:
                return RepairResult(
                    success=False,
                    message=f"Parent message {new_parent_uuid} not found"
                )

            # Calculate similarity with proper timestamp parsing
            from datetime import datetime, timezone
            similarity_score, _ = self.repair_engine._calculate_similarity(
                message,
                parent_msg,
                self.repair_engine._parse_timestamp(message.timestamp),
                self.repair_engine._parse_timestamp(parent_msg.timestamp)
            )

            repair_op = EngineRepairOperation(
                message_id=message.uuid,
                original_parent_uuid=message.parent_uuid,
                suggested_parent_uuid=new_parent_uuid,
                similarity_score=similarity_score,
                reason="User-initiated repair from TUI",
                timestamp=datetime.now(timezone.utc)
            )

            # Step 4: Apply repair (backend-specific)
            success = self.persistence_provider.apply_repair(
                self.jsonl_path, repair_op
            )

            if not success:
                return RepairResult(
                    success=False,
                    message=f"Failed to persist repair to {self.persistence_provider.get_backend_name()}"
                )

            logger.info(
                f"Applied repair to {repair_op.message_id} "
                f"({self.persistence_provider.get_backend_name()} backend)"
            )

            # Step 5: Reload DAG and session
            self._reload_session()

            # Track repair for undo
            self.applied_repairs.append(repair_op)

            return RepairResult(
                success=True,
                message=f"Repaired {message.uuid}",
                backup_path=backup_path,
                repair_op=repair_op
            )

        except Exception as e:
            logger.error(f"Error applying repair: {e}")
            return RepairResult(
                success=False,
                message=f"Error: {str(e)}"
            )

    def undo_repair(self) -> RepairResult:
        """
        Undo the last applied repair (backend-agnostic).

        Returns:
            RepairResult with success status
        """
        if not self.applied_repairs:
            return RepairResult(
                success=False,
                message="No repairs to undo"
            )

        try:
            # Get last repair
            last_repair = self.applied_repairs[-1]

            # Find corresponding backup from provider
            backups = self.persistence_provider.show_undo_history(
                self.session_id
            )

            if not backups:
                return RepairResult(
                    success=False,
                    message="No backups available for rollback"
                )

            # Get most recent backup
            latest_backup = backups[0].backup_path

            # Rollback (backend-specific)
            success = self.persistence_provider.rollback_to_backup(
                self.jsonl_path, latest_backup
            )

            if not success:
                return RepairResult(
                    success=False,
                    message=f"Rollback failed ({self.persistence_provider.get_backend_name()})"
                )

            # Reload session
            self._reload_session()

            # Remove from tracked repairs
            self.applied_repairs.pop()

            logger.info(
                f"Undid repair for {last_repair.message_id} "
                f"({self.persistence_provider.get_backend_name()} backend)"
            )

            return RepairResult(
                success=True,
                message=f"Undid repair for {last_repair.message_id}"
            )

        except Exception as e:
            logger.error(f"Error undoing repair: {e}")
            return RepairResult(
                success=False,
                message=f"Undo error: {str(e)}"
            )

    def show_undo_history(self) -> List[RepairSnapshot]:
        """
        Get list of available undo points (backend-agnostic).

        Returns:
            List of RepairSnapshot objects from persistence provider
        """
        return self.persistence_provider.show_undo_history(self.session_id)

    def _find_message_by_uuid(self, message_uuid: str) -> Optional[Message]:
        """Find message in session by UUID."""
        for message in self.session.messages:
            if message.uuid == message_uuid:
                return message
        return None

    def _reload_session(self) -> None:
        """Reload session and DAG from disk after repair."""
        try:
            # Reload messages from JSONL
            messages = self.loader.load_messages(self.session_id)

            # Rebuild DAG by updating messages and rebuilding graph
            self.dag.messages = messages
            self.dag._build_graph()

            # Rebuild session
            self.session = self.dag.to_session()

            logger.info(f"Reloaded session {self.session_id}")

        except Exception as e:
            logger.error(f"Error reloading session: {e}")
            raise


def create_repair_manager(
    session_id: str,
    jsonl_path: Path,
    session: Session,
    dag: ConversationDAG,
    loader: JSONLLoader,
    persistence_provider: Optional[PersistenceProvider] = None,
) -> RepairManager:
    """
    Factory function to create a RepairManager with optional backend specification.

    Args:
        session_id: Claude session UUID
        jsonl_path: Path to JSONL file
        session: Current Session object
        dag: ConversationDAG instance
        loader: JSONLLoader instance
        persistence_provider: Optional PersistenceProvider backend
                             (default: JSONLRepairProvider)

    Returns:
        Initialized RepairManager instance

    Examples:
        # Use default JSONL backend:
        manager = create_repair_manager(session_id, jsonl_path, session, dag, loader)

        # Use SurrealDB backend:
        from riff.surrealdb import SurrealDBRepairProvider
        surrealdb_provider = SurrealDBRepairProvider(...)
        manager = create_repair_manager(..., persistence_provider=surrealdb_provider)
    """
    return RepairManager(
        session_id=session_id,
        jsonl_path=jsonl_path,
        session=session,
        dag=dag,
        loader=loader,
        persistence_provider=persistence_provider,
    )
