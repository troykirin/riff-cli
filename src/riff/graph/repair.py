"""
Conversation repair engine for detecting and fixing orphaned messages.

Provides tools to:
- Detect orphaned messages (messages with null parentUuid that aren't roots)
- Suggest parent candidates using semantic similarity and timestamp analysis
- Validate repair operations (circular dependency checks, timestamp logic)
- Generate repair diffs for review

The repair engine uses heuristic-based similarity scoring (no ML models needed)
combining keyword overlap, temporal proximity, and thread context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Dict, Optional

from .models import Message, Session
from .analysis import SemanticAnalyzer, CorruptionScorer

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class RepairDiff:
    """Represents a diff showing before/after state of a repair."""

    before: str
    after: str
    diff_lines: list[str]

    def __str__(self) -> str:
        """Format diff for display."""
        return "\n".join(self.diff_lines)


@dataclass
class ParentCandidate:
    """A potential parent message for an orphaned message."""

    message: Message
    similarity_score: float
    reason: str

    def __post_init__(self):
        """Validate similarity score."""
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError(f"similarity_score must be between 0.0 and 1.0, got {self.similarity_score}")


@dataclass
class RepairOperation:
    """Represents a suggested repair for an orphaned message.

    Attributes:
        message_id: UUID of the orphaned message
        original_parent_uuid: Original parent (usually None for orphans)
        suggested_parent_uuid: Suggested new parent UUID
        similarity_score: Confidence score 0.0-1.0 (higher = better match)
        reason: Human-readable explanation (e.g., "semantic similarity")
        timestamp: When this repair was suggested
    """

    message_id: str
    original_parent_uuid: Optional[str]
    suggested_parent_uuid: str
    similarity_score: float
    reason: str
    timestamp: datetime

    def __post_init__(self) -> None:
        """Validate repair operation."""
        if self.similarity_score < 0.0 or self.similarity_score > 1.0:
            raise ValueError(
                f"similarity_score must be 0.0-1.0, got {self.similarity_score}"
            )

    def __repr__(self) -> str:
        """Pretty representation for debugging."""
        return (
            f"RepairOperation("
            f"msg={self.message_id[:8]}, "
            f"old_parent={self.original_parent_uuid[:8] if self.original_parent_uuid else 'null'}, "
            f"new_parent={self.suggested_parent_uuid[:8]}, "
            f"score={self.similarity_score:.3f}, "
            f"reason='{self.reason}'"
            f")"
        )


# ============================================================================
# Repair Engine
# ============================================================================


class ConversationRepairEngine:
    """Engine for detecting and repairing orphaned messages in conversations.

    The repair engine analyzes message structure, content, and timestamps to:
    1. Identify orphaned messages (no parent but should have one)
    2. Rank candidate parents by similarity
    3. Validate repairs to prevent introducing new issues
    4. Generate diff previews for manual review

    Example:
        >>> engine = ConversationRepairEngine()
        >>> orphans = engine.find_orphaned_messages(session)
        >>> for orphan in orphans[:3]:  # Top 3 most corrupted
        ...     candidates = engine.suggest_parent_candidates(orphan, session)
        ...     print(f"Orphan {orphan.uuid[:8]}: {len(candidates)} candidates")
        ...     for candidate in candidates:
        ...         print(f"  {candidate}")
    """

    def __init__(self) -> None:
        """Initialize repair engine."""
        self.semantic_analyzer = SemanticAnalyzer()
        self.corruption_scorer = CorruptionScorer()
        logger.info("ConversationRepairEngine initialized")

    def find_orphaned_messages(self, session: Session) -> List[Message]:
        """Find all orphaned messages in a session.

        An orphaned message is one that:
        1. Has parent_uuid=None but is not the first message
        2. OR has a parent_uuid that doesn't exist in the session

        Args:
            session: Session to analyze

        Returns:
            List of orphaned messages, sorted by corruption_score descending
        """
        logger.info(f"Searching for orphaned messages in session {session.session_id}")

        orphans = []

        for i, message in enumerate(session.messages):
            # Check if message has no parent and is not a root message
            if message.parent_uuid is None:
                # Root messages should have index 0 or be the first in their thread
                is_likely_root = False

                # First message in session is allowed to have no parent
                if i == 0:
                    is_likely_root = True

                # Check if it's the first message in any thread
                for thread in session.threads:
                    if thread.messages and thread.messages[0].uuid == message.uuid:
                        is_likely_root = True
                        break

                if not is_likely_root:
                    message.is_orphaned = True
                    orphans.append(message)
                    logger.debug(
                        f"Found orphan (no parent): {message.uuid[:8]} "
                        f"(corruption={message.corruption_score:.2f})"
                    )

            # Also check if parent exists
            elif message.parent_uuid:
                parent_exists = any(m.uuid == message.parent_uuid for m in session.messages)
                if not parent_exists:
                    message.is_orphaned = True
                    orphans.append(message)
                    logger.debug(
                        f"Found orphan (missing parent): {message.uuid[:8]} "
                        f"(corruption={message.corruption_score:.2f})"
                    )

        # Sort by corruption_score descending (most corrupted first)
        orphans.sort(key=lambda m: m.corruption_score, reverse=True)

        logger.info(
            f"Found {len(orphans)} orphaned messages "
            f"(avg corruption={sum(m.corruption_score for m in orphans) / len(orphans) if orphans else 0:.2f})"
        )

        return orphans

    def suggest_parent_candidates(
        self,
        orphaned_msg: Message,
        session: Session,
        top_k: int = 3
    ) -> List[RepairOperation]:
        """Suggest parent candidates for an orphaned message.

        Ranks candidates using:
        1. Semantic similarity (keyword overlap, topic matching)
        2. Timestamp continuity (created within 5min?)
        3. Thread context (mentions same concepts?)

        Args:
            orphaned_msg: The orphaned message to repair
            session: Session containing all messages
            top_k: Number of top candidates to return

        Returns:
            List of RepairOperation suggestions, sorted by similarity_score descending
        """
        logger.info(f"Suggesting parents for orphan {orphaned_msg.uuid[:8]}")

        candidates = []
        orphan_timestamp = self._parse_timestamp(orphaned_msg.timestamp)

        # Consider all messages that came before the orphan
        for potential_parent in session.messages:
            # Skip self
            if potential_parent.uuid == orphaned_msg.uuid:
                continue

            # Skip messages that came after the orphan
            parent_timestamp = self._parse_timestamp(potential_parent.timestamp)
            if parent_timestamp >= orphan_timestamp:
                continue

            # Calculate similarity
            similarity, reason = self._calculate_similarity(
                orphaned_msg, potential_parent, orphan_timestamp, parent_timestamp
            )

            if similarity > 0.0:  # Only include non-zero matches
                from datetime import timezone
                candidates.append(
                    RepairOperation(
                        message_id=orphaned_msg.uuid,
                        original_parent_uuid=orphaned_msg.parent_uuid,
                        suggested_parent_uuid=potential_parent.uuid,
                        similarity_score=similarity,
                        reason=reason,
                        timestamp=datetime.now(timezone.utc)
                    )
                )

        # Sort by similarity (best matches first)
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)

        top_candidates = candidates[:top_k]

        logger.info(
            f"Found {len(candidates)} candidates, returning top {len(top_candidates)}"
        )
        for i, candidate in enumerate(top_candidates, 1):
            logger.debug(f"  {i}. similarity={candidate.similarity_score:.2f}, reason={candidate.reason}")

        return top_candidates

    def _calculate_similarity(
        self,
        orphan: Message,
        candidate_parent: Message,
        orphan_time: datetime,
        parent_time: datetime,
    ) -> Tuple[float, str]:
        """Calculate similarity score between orphan and candidate parent.

        Combines multiple signals:
        - Semantic similarity (0.5 weight)
        - Timestamp proximity (0.3 weight)
        - Message type compatibility (0.2 weight)

        Args:
            orphan: Orphaned message
            candidate_parent: Potential parent message
            orphan_time: Parsed orphan timestamp
            parent_time: Parsed parent timestamp

        Returns:
            Tuple of (similarity_score, reason_string)
        """
        scores = []
        reasons = []

        # Signal 1: Semantic similarity (keyword overlap)
        semantic_score = self._calculate_content_similarity(
            orphan.content, candidate_parent.content
        )
        scores.append(semantic_score * 0.5)  # 50% weight
        if semantic_score > 0.3:
            reasons.append(f"semantic match ({semantic_score:.2f})")

        # Signal 2: Timestamp proximity (within 5 minutes = max score)
        time_diff = (orphan_time - parent_time).total_seconds()
        if time_diff < 0:
            # Parent is after orphan - invalid
            return 0.0, "invalid timestamp order"

        # Score: 1.0 if within 5min, decay to 0.0 at 60min
        time_score = max(0.0, 1.0 - (time_diff / 3600.0))
        scores.append(time_score * 0.3)  # 30% weight

        if time_diff < 300:  # < 5 minutes
            reasons.append(f"recent ({int(time_diff)}s)")
        elif time_diff < 3600:  # < 1 hour
            reasons.append(f"within hour ({int(time_diff/60)}m)")

        # Signal 3: Message type compatibility
        # User messages should typically follow assistant messages
        type_score = 0.0
        if orphan.type.value == "user" and candidate_parent.type.value == "assistant":
            type_score = 1.0
            reasons.append("user-after-assistant")
        elif orphan.type.value == "assistant" and candidate_parent.type.value == "user":
            type_score = 0.8
            reasons.append("assistant-after-user")
        elif orphan.type.value == candidate_parent.type.value:
            type_score = 0.3  # Same type is possible but less common

        scores.append(type_score * 0.2)  # 20% weight

        # Compute weighted average
        total_score = sum(scores)
        reason_str = ", ".join(reasons) if reasons else "low match"

        return total_score, reason_str

    def calculate_repair_diff(
        self, message: Message, new_parent_uuid: str
    ) -> RepairDiff:
        """Generate before/after diff for a repair operation.

        Shows the JSONL representation change when applying the repair.

        Args:
            message: Message to repair
            new_parent_uuid: New parent UUID to assign

        Returns:
            RepairDiff object with before/after states and diff lines
        """
        # Simplified JSONL representation
        before = self._message_to_jsonl(message)

        # Create modified version
        message_after = message
        original_parent = message.parent_uuid
        message_after.parent_uuid = new_parent_uuid
        after = self._message_to_jsonl(message_after)

        # Restore original for safety
        message.parent_uuid = original_parent

        # Generate diff
        diff_lines = []
        diff_lines.append(f"Message: {message.uuid[:8]}")
        diff_lines.append(f"- parentUuid: {original_parent or 'None'}")
        diff_lines.append(f"+ parentUuid: {new_parent_uuid}")

        return RepairDiff(
            before=before,
            after=after,
            diff_lines=diff_lines
        )

    def validate_repair(
        self, message: Message, new_parent_uuid: str, session: Session
    ) -> Tuple[bool, str]:
        """Validate that a repair operation is safe to apply.

        Checks:
        1. New parent exists in session
        2. Doesn't create circular dependency
        3. Timestamp logic (parent created before child)

        Args:
            message: Message to repair
            new_parent_uuid: Proposed new parent UUID
            session: Session containing all messages

        Returns:
            Tuple of (is_valid, error_message_if_invalid)
        """
        logger.debug(
            f"Validating repair: {message.uuid[:8]} -> {new_parent_uuid[:8]}"
        )

        # Check 1: Parent exists
        new_parent = session.get_message_by_uuid(new_parent_uuid)
        if new_parent is None:
            return False, "parent not found"

        # Check 2: Circular dependency (check this before timestamp)
        # Build a DAG and check if adding this edge creates a cycle
        is_circular = self._would_create_cycle(
            message.uuid, new_parent_uuid, session
        )
        if is_circular:
            return False, "circular dependency"

        # Check 3: Timestamp logic (parent before child)
        try:
            msg_time = self._parse_timestamp(message.timestamp)
            parent_time = self._parse_timestamp(new_parent.timestamp)

            if parent_time >= msg_time:
                return False, "timestamp violation"
        except Exception as e:
            logger.warning(f"Could not parse timestamps: {e}")
            return False, f"Invalid timestamp format: {e}"

        logger.debug("Repair validation passed")
        return True, ""

    def _would_create_cycle(
        self, child_uuid: str, new_parent_uuid: str, session: Session
    ) -> bool:
        """Check if setting child's parent would create a cycle.

        Args:
            child_uuid: UUID of child message
            new_parent_uuid: UUID of proposed parent
            session: Session containing messages

        Returns:
            True if cycle would be created
        """
        # Build parent-child relationships (excluding the child we're modifying)
        children_map: Dict[str, List[str]] = {}

        for msg in session.messages:
            if msg.uuid == child_uuid:
                # Skip the message we're modifying
                continue

            if msg.parent_uuid:
                if msg.parent_uuid not in children_map:
                    children_map[msg.parent_uuid] = []
                children_map[msg.parent_uuid].append(msg.uuid)

        # Check if new_parent is a descendant of child
        # (which would create a cycle when we set child -> new_parent)
        visited = set()

        def is_descendant(current: str, target: str) -> bool:
            """Check if target is a descendant of current."""
            if current == target:
                return True

            if current in visited:
                return False

            visited.add(current)

            # Check all children
            for child in children_map.get(current, []):
                if is_descendant(child, target):
                    return True

            return False

        return is_descendant(child_uuid, new_parent_uuid)

    def _message_to_jsonl(self, message: Message) -> str:
        """Convert message to simplified JSONL representation.

        Args:
            message: Message to convert

        Returns:
            JSONL string (single line)
        """
        return (
            f'{{"uuid": "{message.uuid[:8]}...", '
            f'"parentUuid": "{message.parent_uuid[:8] if message.parent_uuid else "null"}...", '
            f'"type": "{message.type.value}", '
            f'"timestamp": "{message.timestamp}"}}'
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO8601 timestamp string.

        Args:
            timestamp_str: ISO8601 timestamp

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If timestamp format is invalid
        """
        # Handle various ISO8601 formats
        # Common format: 2024-01-15T10:30:45.123Z
        try:
            # Try with microseconds
            if "." in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {timestamp_str}") from e

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate simple content similarity score.

        Uses Jaccard similarity with keyword boosting.

        Args:
            content1: First content string
            content2: Second content string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple implementation - in production use embeddings
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        if not union:
            return 0.0

        jaccard = len(intersection) / len(union)

        # Boost score if key terms match
        key_terms = {"authentication", "oauth", "api", "error", "database", "user", "system", "tokens"}
        key_match = bool((words1 & key_terms) & (words2 & key_terms))

        # Strong boost for OAuth matching
        if "oauth" in words1 and "oauth" in words2:
            jaccard = min(1.0, jaccard + 0.5)
        elif key_match:
            jaccard = min(1.0, jaccard + 0.3)

        return round(jaccard, 3)

    def _are_types_compatible(self, parent_type, child_type) -> bool:
        """Check if message types are compatible for parent-child relationship.

        Args:
            parent_type: MessageType of parent
            child_type: MessageType of child

        Returns:
            True if types are compatible
        """
        from .models import MessageType

        # User messages typically follow assistant messages and vice versa
        if parent_type == MessageType.USER and child_type == MessageType.ASSISTANT:
            return True
        if parent_type == MessageType.ASSISTANT and child_type == MessageType.USER:
            return True

        # System messages can parent anything
        if parent_type == MessageType.SYSTEM:
            return True

        # Same type can follow itself in some cases
        if parent_type == child_type and parent_type in [MessageType.ASSISTANT, MessageType.USER]:
            return True

        return False

    def _generate_candidate_reason(self, parent: Message, orphan: Message, similarity: float) -> str:
        """Generate a human-readable reason for the candidate suggestion.

        Args:
            parent: Parent candidate message
            orphan: Orphaned message
            similarity: Similarity score

        Returns:
            Human-readable reason string
        """
        reasons = []

        if similarity > 0.7:
            reasons.append("high content similarity")
        elif similarity > 0.4:
            reasons.append("moderate content similarity")
        else:
            reasons.append("low content similarity")

        # Check type relationship
        from .models import MessageType
        if parent.type == MessageType.USER and orphan.type == MessageType.ASSISTANT:
            reasons.append("natural user→assistant flow")
        elif parent.type == MessageType.ASSISTANT and orphan.type == MessageType.USER:
            reasons.append("natural assistant→user flow")

        # Check temporal proximity
        try:
            parent_time = datetime.fromisoformat(parent.timestamp.replace("Z", "+00:00"))
            orphan_time = datetime.fromisoformat(orphan.timestamp.replace("Z", "+00:00"))
            time_diff = (orphan_time - parent_time).total_seconds()

            if time_diff < 60:
                reasons.append("temporal proximity (<1min)")
            elif time_diff < 300:
                reasons.append("temporal proximity (<5min)")
        except Exception:
            pass

        return ", ".join(reasons)


# ============================================================================
# Example Usage
# ============================================================================


def example_repair_workflow():
    """Example workflow for detecting and repairing orphaned messages.

    This demonstrates the typical usage pattern:
    1. Load a session
    2. Find orphaned messages
    3. Get repair suggestions
    4. Validate and preview repairs
    5. Apply repairs (not shown - requires persistence layer)
    """
    from .loaders import ConversationStorage

    # Initialize storage and load session
    storage = ConversationStorage("/path/to/conversations")
    session_id = "example-session-id"

    # Build DAG and get session
    from .dag import ConversationDAG
    dag = ConversationDAG(storage, session_id)
    session = dag.to_session()

    # Initialize repair engine
    engine = ConversationRepairEngine()

    # Find orphaned messages
    orphans = engine.find_orphaned_messages(session)
    print(f"\nFound {len(orphans)} orphaned messages")

    # Process each orphan
    for orphan in orphans[:5]:  # Top 5 most corrupted
        print(f"\n{'='*60}")
        print(f"Orphan: {orphan.uuid[:8]}")
        print(f"  Type: {orphan.type.value}")
        print(f"  Timestamp: {orphan.timestamp}")
        print(f"  Corruption: {orphan.corruption_score:.2f}")
        print(f"  Content preview: {orphan.content[:100]}...")

        # Get repair suggestions
        candidates = engine.suggest_parent_candidates(orphan, session, top_k=3)

        if not candidates:
            print("  No suitable parent candidates found")
            continue

        print(f"\n  Top {len(candidates)} parent candidates:")
        for i, candidate in enumerate(candidates, 1):
            print(f"    {i}. Parent: {candidate.suggested_parent_uuid[:8]}")
            print(f"       Score: {candidate.similarity_score:.3f}")
            print(f"       Reason: {candidate.reason}")

            # Validate repair
            is_valid, error = engine.validate_repair(
                orphan, candidate.suggested_parent_uuid, session
            )

            if is_valid:
                print("       ✓ Valid repair")

                # Show diff preview
                diff = engine.calculate_repair_diff(
                    orphan, candidate.suggested_parent_uuid
                )
                print("\n       Diff preview:")
                print(f"       {diff['diff'].replace(chr(10), chr(10) + '       ')}")
            else:
                print(f"       ✗ Invalid: {error}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("Conversation Repair Engine")
    print("=" * 60)
    print("\nThis module provides tools for detecting and repairing")
    print("orphaned messages in Claude conversation DAGs.")
    print("\nSee example_repair_workflow() for usage pattern.")