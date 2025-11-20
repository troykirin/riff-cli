"""
Conversation DAG construction and analysis.

Builds a directed acyclic graph from conversation messages, identifies threads,
detects orphaned messages, and computes corruption metrics.
"""

from typing import Any, Optional, TypeAlias
from collections import defaultdict

from .models import Message, Thread, Session, ThreadType
from .loaders import ConversationStorage


# Type alias for adjacency list representation
AdjacencyList: TypeAlias = dict[str, list[str]]


class ConversationDAG:
    """
    Semantic DAG representation of a conversation.

    Builds a graph structure from messages using parent-child relationships,
    identifies connected components (threads), detects orphaned messages,
    and computes structural health metrics.

    Attributes:
        loader: Storage backend for conversation data
        session_id: Session identifier
        messages: All messages in the session
        message_index: Fast UUID -> Message lookup
        children: Adjacency list (parent UUID -> child UUIDs)
        parents: Reverse adjacency list (child UUID -> parent UUID)
    """

    def __init__(self, loader: ConversationStorage, session_id: str) -> None:
        """
        Initialize DAG from a session.

        Args:
            loader: Storage backend to load messages from
            session_id: Session UUID to analyze

        Raises:
            FileNotFoundError: If session doesn't exist
            ValueError: If session is empty
        """
        self.loader = loader
        self.session_id = session_id

        # Load messages
        self.messages = loader.load_messages(session_id)

        if not self.messages:
            raise ValueError(f"Session {session_id} contains no messages")

        # Build lookup index
        self.message_index: dict[str, Message] = {msg.uuid: msg for msg in self.messages}

        # Build graph structure
        self.children: AdjacencyList = defaultdict(list)
        self.parents: dict[str, str] = {}

        self._build_graph()

    def _build_graph(self) -> None:
        """
        Construct parent-child adjacency lists from messages.

        Populates:
        - self.children: parent_uuid -> [child_uuid, ...]
        - self.parents: child_uuid -> parent_uuid

        Handles missing parent references gracefully.
        """
        for message in self.messages:
            if message.parent_uuid:
                # Add to children list of parent
                self.children[message.parent_uuid].append(message.uuid)

                # Add to parents mapping
                self.parents[message.uuid] = message.parent_uuid

                # Check if parent exists (detect orphans)
                if message.parent_uuid not in self.message_index:
                    message.is_orphaned = True
                    message.corruption_score = max(message.corruption_score, 0.5)

    def _find_roots(self) -> list[str]:
        """
        Find all root messages (messages with no parent).

        Returns:
            List of root message UUIDs
        """
        roots = []
        for message in self.messages:
            if message.parent_uuid is None:
                roots.append(message.uuid)
        return roots

    def _traverse_from_root(self, root_uuid: str) -> list[str]:
        """
        Depth-first traversal from a root message.

        Args:
            root_uuid: Starting message UUID

        Returns:
            List of all message UUIDs reachable from root (DFS order)
        """
        visited = set()
        result = []

        def dfs(uuid: str) -> None:
            if uuid in visited:
                return

            visited.add(uuid)
            result.append(uuid)

            # Visit children
            for child_uuid in self.children.get(uuid, []):
                dfs(child_uuid)

        dfs(root_uuid)
        return result

    def _find_connected_components(self) -> list[list[str]]:
        """
        Identify all connected components in the conversation graph.

        Each component represents a distinct thread of conversation.
        Components are ordered by size (largest first).

        Returns:
            List of components, where each component is a list of message UUIDs
        """
        visited = set()
        components = []

        # Start from all roots
        roots = self._find_roots()

        for root_uuid in roots:
            if root_uuid not in visited:
                component = self._traverse_from_root(root_uuid)
                visited.update(component)
                components.append(component)

        # Find orphaned messages (messages in graph but not reachable from roots)
        all_message_uuids = set(self.message_index.keys())
        reachable_uuids = visited

        orphaned_uuids = all_message_uuids - reachable_uuids

        # Each orphaned message forms its own component
        for orphan_uuid in orphaned_uuids:
            # Try to traverse from orphan (might have children)
            orphan_component = self._traverse_from_root(orphan_uuid)
            components.append(orphan_component)

            # Mark as orphaned
            for uuid in orphan_component:
                msg = self.message_index[uuid]
                msg.is_orphaned = True
                msg.corruption_score = max(msg.corruption_score, 0.5)

        # Sort components by size (largest first)
        components.sort(key=len, reverse=True)

        return components

    def _classify_thread_type(
        self, component: list[str], component_idx: int, total_components: int
    ) -> ThreadType:
        """
        Classify a component as main thread, side discussion, or orphaned.

        Heuristics:
        - Largest component is the main thread (if not all orphaned)
        - Components containing sidechain messages are side discussions
        - Components with all orphaned messages are orphaned threads

        Args:
            component: List of message UUIDs in component
            component_idx: Index of component in sorted list
            total_components: Total number of components

        Returns:
            ThreadType classification
        """
        # Check if all messages are orphaned
        all_orphaned = all(self.message_index[uuid].is_orphaned for uuid in component)

        if all_orphaned:
            return ThreadType.ORPHANED

        # Check if any messages are sidechains
        has_sidechain = any(self.message_index[uuid].is_sidechain for uuid in component)

        if has_sidechain:
            return ThreadType.SIDE_DISCUSSION

        # Largest non-orphaned component is main thread
        if component_idx == 0:
            return ThreadType.MAIN

        # Other non-sidechain components are side discussions
        return ThreadType.SIDE_DISCUSSION

    def _compute_thread_corruption(self, component: list[str]) -> float:
        """
        Compute aggregate corruption score for a thread.

        Args:
            component: List of message UUIDs in thread

        Returns:
            Corruption score (0.0 = perfect, 1.0 = completely corrupted)
        """
        if not component:
            return 1.0

        # Average corruption scores of messages
        total_corruption = sum(self.message_index[uuid].corruption_score for uuid in component)
        avg_corruption = total_corruption / len(component)

        # Additional penalties
        penalty = 0.0

        # Penalty for very small threads (likely fragmented)
        if len(component) < 3:
            penalty += 0.2

        return min(avg_corruption + penalty, 1.0)

    def _build_thread(self, component: list[str], thread_type: ThreadType) -> Thread:
        """
        Construct a Thread object from a component.

        Args:
            component: List of message UUIDs
            thread_type: Classification of thread

        Returns:
            Thread object with computed metadata
        """
        # Get messages in chronological order
        messages = [self.message_index[uuid] for uuid in component]
        messages.sort(key=lambda m: m.timestamp)

        # Assign thread ID based on first message
        thread_id = messages[0].uuid if messages else "unknown"

        # Update messages with thread ID
        for msg in messages:
            msg.thread_id = thread_id

        # Compute corruption score
        corruption_score = self._compute_thread_corruption(component)

        return Thread(
            thread_id=thread_id,
            messages=messages,
            thread_type=thread_type,
            corruption_score=corruption_score,
        )

    def to_session(self) -> Session:
        """
        Convert DAG to a Session object with organized threads.

        Returns:
            Session containing all messages, organized threads, and orphans
        """
        # Find all connected components
        components = self._find_connected_components()

        # Classify and build threads
        threads = []
        orphans = []

        for idx, component in enumerate(components):
            thread_type = self._classify_thread_type(component, idx, len(components))
            thread = self._build_thread(component, thread_type)

            if thread_type == ThreadType.ORPHANED:
                orphans.append(thread)
            else:
                threads.append(thread)

        # Compute overall session corruption
        all_threads = threads + orphans
        if all_threads:
            session_corruption = sum(t.corruption_score for t in all_threads) / len(all_threads)
        else:
            session_corruption = 1.0

        return Session(
            session_id=self.session_id,
            messages=self.messages,
            threads=threads,
            orphans=orphans,
            corruption_score=session_corruption,
        )

    def get_message(self, uuid: str) -> Optional[Message]:
        """
        Retrieve a message by UUID.

        Args:
            uuid: Message UUID

        Returns:
            Message object or None if not found
        """
        return self.message_index.get(uuid)

    def get_children(self, uuid: str) -> list[Message]:
        """
        Get all direct children of a message.

        Args:
            uuid: Parent message UUID

        Returns:
            List of child Message objects
        """
        child_uuids = self.children.get(uuid, [])
        return [self.message_index[child_uuid] for child_uuid in child_uuids]

    def get_parent(self, uuid: str) -> Optional[Message]:
        """
        Get the parent of a message.

        Args:
            uuid: Child message UUID

        Returns:
            Parent Message object or None if no parent
        """
        parent_uuid = self.parents.get(uuid)
        return self.message_index.get(parent_uuid) if parent_uuid else None

    def get_ancestry_path(self, uuid: str) -> list[Message]:
        """
        Get the full path from root to a message.

        Args:
            uuid: Target message UUID

        Returns:
            List of messages from root to target (inclusive)
        """
        path: list[Message] = []
        current_uuid: Optional[str] = uuid

        # Walk up the parent chain
        while current_uuid:
            message = self.message_index.get(current_uuid)
            if not message:
                break

            path.insert(0, message)
            current_uuid = message.parent_uuid

        return path

    def get_subtree(self, uuid: str) -> list[Message]:
        """
        Get all descendants of a message.

        Args:
            uuid: Root message UUID

        Returns:
            List of all descendant messages (DFS order)
        """
        descendant_uuids = self._traverse_from_root(uuid)
        return [self.message_index[desc_uuid] for desc_uuid in descendant_uuids]

    def validate_structure(self) -> dict[str, Any]:
        """
        Perform structural validation on the conversation DAG.

        Returns:
            Dictionary with validation results:
            - is_valid: Overall validity
            - errors: List of structural errors
            - warnings: List of potential issues
            - stats: Graph statistics
        """
        errors = []
        warnings = []

        # Check for cycles (DAG property)
        visited = set()
        rec_stack = set()

        def has_cycle(uuid: str) -> bool:
            visited.add(uuid)
            rec_stack.add(uuid)

            for child_uuid in self.children.get(uuid, []):
                if child_uuid not in visited:
                    if has_cycle(child_uuid):
                        return True
                elif child_uuid in rec_stack:
                    return True

            rec_stack.remove(uuid)
            return False

        # Check all roots for cycles
        for root_uuid in self._find_roots():
            if has_cycle(root_uuid):
                errors.append(f"Cycle detected starting from {root_uuid}")

        # Check for missing parents
        for message in self.messages:
            if message.parent_uuid and message.parent_uuid not in self.message_index:
                warnings.append(f"Message {message.uuid} references missing parent {message.parent_uuid}")

        # Compute statistics
        roots = self._find_roots()
        components = self._find_connected_components()

        stats = {
            "total_messages": len(self.messages),
            "root_count": len(roots),
            "component_count": len(components),
            "orphaned_messages": sum(1 for m in self.messages if m.is_orphaned),
            "avg_corruption": sum(m.corruption_score for m in self.messages) / len(self.messages),
        }

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }
