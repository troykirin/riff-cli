"""Semantic analysis for ConversationDAG.

Implements thread detection and corruption scoring that identifies:
- Main threads (longest continuous path from roots)
- Side discussions (semantic similarity with re-entry points)
- Orphaned branches (disconnected, no valid path to main)

No ML models needed for MVP - uses heuristics based on:
- Keyword matching
- Message structure
- Temporal patterns
- Parent-child relationships

This module extends the existing DAG functionality with semantic analysis.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set

from .models import Message, Thread, Session, ThreadType

logger = logging.getLogger(__name__)


# ============================================================================
# Thread Detection
# ============================================================================


class ThreadDetector:
    """Identify threads in a conversation DAG.

    Enhances the existing ConversationDAG with additional semantic analysis:
    - Re-entry point detection for side discussions
    - Enhanced corruption scoring
    - Semantic topic extraction
    """

    def __init__(self, messages: List[Message]):
        """Initialize detector with messages.

        Args:
            messages: List of messages to analyze
        """
        self.messages = {msg.uuid: msg for msg in messages}
        self.children_map = self._build_children_map()
        self.parent_map = self._build_parent_map()

        logger.info(
            f"ThreadDetector initialized: {len(messages)} messages, "
            f"{len(self.children_map)} with children"
        )

    def _build_children_map(self) -> Dict[str, List[Message]]:
        """Build map of parent_uuid -> children."""
        children: Dict[str, List[Message]] = defaultdict(list)
        for msg in self.messages.values():
            if msg.parent_uuid:
                children[msg.parent_uuid].append(msg)
        return dict(children)

    def _build_parent_map(self) -> Dict[str, Message]:
        """Build map of uuid -> parent message."""
        parent_map: Dict[str, Message] = {}
        for msg in self.messages.values():
            if msg.parent_uuid and msg.parent_uuid in self.messages:
                parent_map[msg.uuid] = self.messages[msg.parent_uuid]
        return parent_map

    def identify_threads(self) -> List[Thread]:
        """Identify all threads in the conversation.

        Returns:
            List of threads (main, side discussions, orphaned)
        """
        logger.info("Starting thread identification")

        # Find root messages (no parent or parent=null)
        roots = self._find_roots()
        logger.info(f"Found {len(roots)} root messages")

        # Build connected components
        components = self._find_connected_components(roots)
        logger.info(f"Found {len(components)} connected components")

        # Identify main thread (longest path from roots)
        main_thread = self._find_main_thread(components)
        threads = [main_thread]

        # Analyze remaining components
        for component in components:
            if component == main_thread.messages:
                continue

            # Check if it's a side discussion or orphan
            thread = self._classify_component(component, main_thread)
            threads.append(thread)

        logger.info(
            f"Thread identification complete: {len(threads)} threads "
            f"(1 main, {sum(1 for t in threads if t.thread_type == ThreadType.SIDE_DISCUSSION)} side, "
            f"{sum(1 for t in threads if t.thread_type == ThreadType.ORPHANED)} orphaned)"
        )

        return threads

    def _find_roots(self) -> List[Message]:
        """Find root messages (no parent or parent not in messages)."""
        roots = []
        for msg in self.messages.values():
            if not msg.parent_uuid or msg.parent_uuid not in self.messages:
                roots.append(msg)
                logger.debug(f"Root: {msg.uuid[:8]} ({msg.type})")
        return roots

    def _find_connected_components(self, roots: List[Message]) -> List[List[Message]]:
        """Find all connected components starting from roots.

        Args:
            roots: List of root messages

        Returns:
            List of components (each component is a list of messages)
        """
        components = []
        visited: Set[str] = set()

        for root in roots:
            if root.uuid in visited:
                continue

            component = self._traverse_from_root(root, visited)
            if component:
                components.append(component)
                logger.debug(
                    f"Component from {root.uuid[:8]}: {len(component)} messages"
                )

        return components

    def _traverse_from_root(
        self, root: Message, visited: Set[str]
    ) -> List[Message]:
        """Traverse from a root message, collecting all descendants.

        Args:
            root: Root message to start from
            visited: Set of already visited message UUIDs

        Returns:
            List of messages in this component
        """
        component = []
        stack = [root]

        while stack:
            msg = stack.pop()
            if msg.uuid in visited:
                continue

            visited.add(msg.uuid)
            component.append(msg)

            # Add children to stack
            children = self.children_map.get(msg.uuid, [])
            stack.extend(children)

        return component

    def _find_main_thread(self, components: List[List[Message]]) -> Thread:
        """Find the main thread (longest continuous path from roots).

        Args:
            components: List of connected components

        Returns:
            Main thread
        """
        if not components:
            logger.warning("No components found, creating empty main thread")
            return Thread(
                thread_id="main",
                thread_type=ThreadType.MAIN,
                messages=[],
                semantic_topic="empty",
            )

        # Find longest component
        longest = max(components, key=len)
        logger.info(f"Main thread: {len(longest)} messages")

        return Thread(
            thread_id="main",
            thread_type=ThreadType.MAIN,
            messages=sorted(longest, key=lambda m: m.timestamp),
            semantic_topic=self._extract_dominant_topic(longest),
        )

    def _classify_component(
        self, component: List[Message], main_thread: Thread
    ) -> Thread:
        """Classify a component as side discussion or orphaned.

        Args:
            component: Component to classify
            main_thread: The main thread

        Returns:
            Classified thread
        """
        # Check for re-entry point to main thread
        re_entry = self._find_re_entry_point(component, main_thread)

        if re_entry:
            logger.debug(
                f"Side discussion: {len(component)} messages, "
                f"re-entry at {re_entry[:8]}"
            )
            return Thread(
                thread_id=f"side_{component[0].uuid[:8]}",
                thread_type=ThreadType.SIDE_DISCUSSION,
                messages=sorted(component, key=lambda m: m.timestamp),
                semantic_topic=self._extract_dominant_topic(component),
                parent_thread_id=main_thread.thread_id,
            )
        else:
            corruption_score = CorruptionScorer.score_corruption(component)
            logger.debug(
                f"Orphaned branch: {len(component)} messages, "
                f"corruption={corruption_score:.2f}"
            )
            return Thread(
                thread_id=f"orphan_{component[0].uuid[:8]}",
                thread_type=ThreadType.ORPHANED,
                messages=sorted(component, key=lambda m: m.timestamp),
                semantic_topic=self._extract_dominant_topic(component),
                corruption_score=corruption_score,
            )

    def _find_re_entry_point(
        self, component: List[Message], main_thread: Thread
    ) -> Optional[str]:
        """Find where a component rejoins the main thread.

        Args:
            component: Component to check
            main_thread: Main thread

        Returns:
            UUID of re-entry point in main thread, or None
        """
        main_uuids = {msg.uuid for msg in main_thread.messages}

        # Check if any message in component has children in main thread
        for msg in component:
            children = self.children_map.get(msg.uuid, [])
            for child in children:
                if child.uuid in main_uuids:
                    return child.uuid

        return None

    def _extract_dominant_topic(self, messages: List[Message]) -> str:
        """Extract dominant topic from messages using keyword analysis.

        Args:
            messages: Messages to analyze

        Returns:
            Dominant topic string
        """
        return SemanticAnalyzer.extract_semantic_topic(messages)


# ============================================================================
# Corruption Scoring
# ============================================================================


class CorruptionScorer:
    """Score likelihood of corruption in message threads."""

    @staticmethod
    def score_corruption(messages: List[Message]) -> float:
        """Score corruption likelihood for a list of messages.

        Factors (0.0-1.0):
        - parentUuid=null for non-root: +0.4
        - Timestamp immediately after previous message: +0.2
        - isSidechain=true without valid parent: +0.3
        - Semantic disconnection from main thread: +0.1

        Args:
            messages: Messages to score

        Returns:
            Corruption score 0.0-1.0 (higher = more likely corrupted)
        """
        if not messages:
            return 0.0

        score = 0.0
        first_msg = messages[0]

        # Signal 1: Invalid parent (null parent but not truly a root)
        if first_msg.parent_uuid is None:
            # Could be legitimate root or corruption
            # Check if it looks like a continuation
            if CorruptionScorer._looks_like_continuation(first_msg):
                score += 0.4
                logger.debug(
                    f"Corruption signal: null parent but looks like continuation ({first_msg.uuid[:8]})"
                )

        # Signal 2: Timestamp pattern analysis
        if len(messages) > 1:
            timestamp_score = CorruptionScorer._analyze_timestamp_pattern(messages)
            score += timestamp_score * 0.2
            if timestamp_score > 0:
                logger.debug(
                    f"Corruption signal: suspicious timestamp pattern ({first_msg.uuid[:8]})"
                )

        # Signal 3: Check for sidechain flag (if exists)
        # Note: This field may not exist in all message formats
        if hasattr(first_msg, "is_sidechain") and first_msg.is_sidechain:
            if first_msg.parent_uuid is None:
                score += 0.3
                logger.debug(
                    f"Corruption signal: sidechain flag without parent ({first_msg.uuid[:8]})"
                )

        # Signal 4: Content analysis for continuation markers
        continuation_score = CorruptionScorer._analyze_continuation_markers(messages)
        score += continuation_score * 0.1
        if continuation_score > 0:
            logger.debug(
                f"Corruption signal: continuation markers present ({first_msg.uuid[:8]})"
            )

        return min(score, 1.0)

    @staticmethod
    def _looks_like_continuation(msg: Message) -> bool:
        """Check if message looks like it should have a parent.

        Args:
            msg: Message to check

        Returns:
            True if it looks like a continuation
        """
        # User messages without context usually indicate resume attempt
        if msg.type == "user":
            content_lower = msg.content.lower()
            continuation_markers = [
                "continue",
                "resume",
                "back to",
                "as we were discussing",
                "returning to",
            ]
            return any(marker in content_lower for marker in continuation_markers)

        # Assistant messages without parent are suspicious
        if msg.type == "assistant":
            content_lower = msg.content.lower()
            reference_markers = [
                "as mentioned",
                "as we discussed",
                "continuing from",
                "building on",
            ]
            return any(marker in content_lower for marker in reference_markers)

        return False

    @staticmethod
    def _analyze_timestamp_pattern(messages: List[Message]) -> float:
        """Analyze timestamp patterns for corruption signals.

        Args:
            messages: Messages to analyze

        Returns:
            Score 0.0-1.0
        """
        # For now, just check if messages are in order
        # In a real implementation, could check for suspicious gaps/overlaps
        try:
            timestamps = [msg.timestamp for msg in messages]
            is_ordered = all(
                timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1)
            )
            return 0.0 if is_ordered else 0.5
        except Exception as e:
            logger.warning(f"Error analyzing timestamps: {e}")
            return 0.0

    @staticmethod
    def _analyze_continuation_markers(messages: List[Message]) -> float:
        """Analyze content for continuation markers.

        Args:
            messages: Messages to analyze

        Returns:
            Score 0.0-1.0
        """
        continuation_count = 0
        for msg in messages[:5]:  # Check first 5 messages
            content_lower = msg.content.lower()
            markers = [
                "resume",
                "continue",
                "pick up where",
                "where we left off",
            ]
            if any(marker in content_lower for marker in markers):
                continuation_count += 1

        return min(continuation_count / 5.0, 1.0)

    @staticmethod
    def detect_orphans(messages: List[Message]) -> List[Thread]:
        """Detect orphaned branches and score by corruption likelihood.

        Args:
            messages: All messages to analyze

        Returns:
            List of orphaned threads sorted by corruption score (descending)
        """
        detector = ThreadDetector(messages)
        threads = detector.identify_threads()

        # Filter orphaned threads and sort by corruption score
        orphans = [t for t in threads if t.thread_type == ThreadType.ORPHANED]
        orphans.sort(key=lambda t: t.corruption_score, reverse=True)

        logger.info(
            f"Detected {len(orphans)} orphaned branches "
            f"from {len(messages)} messages"
        )

        return orphans


# ============================================================================
# Semantic Analysis
# ============================================================================


class SemanticAnalyzer:
    """Semantic topic extraction and clustering (heuristic-based MVP)."""

    # Common topic keywords (extensible)
    TOPIC_KEYWORDS = {
        "architecture": [
            "architecture",
            "design",
            "structure",
            "component",
            "module",
            "system",
        ],
        "debugging": [
            "error",
            "bug",
            "fix",
            "debug",
            "issue",
            "problem",
            "broken",
        ],
        "implementation": [
            "implement",
            "code",
            "function",
            "class",
            "method",
            "feature",
        ],
        "documentation": ["doc", "document", "readme", "comment", "explain"],
        "testing": ["test", "unit test", "integration", "coverage", "pytest"],
        "configuration": ["config", "setup", "install", "environment", "settings"],
        "question": ["how", "what", "why", "when", "where", "?"],
        "planning": ["plan", "roadmap", "todo", "task", "milestone"],
    }

    @staticmethod
    def extract_semantic_topic(messages: List[Message]) -> str:
        """Extract semantic topic from messages using keyword matching.

        Args:
            messages: Messages to analyze

        Returns:
            Topic label (short string)
        """
        if not messages:
            return "unknown"

        # Combine all message content
        combined_text = " ".join(msg.content.lower() for msg in messages)

        # Count keyword matches for each topic
        topic_scores: Dict[str, int] = defaultdict(int)
        for topic, keywords in SemanticAnalyzer.TOPIC_KEYWORDS.items():
            for keyword in keywords:
                topic_scores[topic] += combined_text.count(keyword)

        # Return topic with highest score
        if topic_scores:
            dominant_topic = max(topic_scores.items(), key=lambda x: x[1])
            if dominant_topic[1] > 0:
                logger.debug(
                    f"Topic detected: {dominant_topic[0]} (score={dominant_topic[1]})"
                )
                return dominant_topic[0]

        # Fallback: generic topic based on message types
        user_count = sum(1 for msg in messages if msg.type == "user")
        assistant_count = sum(1 for msg in messages if msg.type == "assistant")

        if user_count > assistant_count * 2:
            return "questions"
        elif assistant_count > user_count * 2:
            return "explanation"
        else:
            return "discussion"

    @staticmethod
    def cluster_by_topic(messages: List[Message]) -> Dict[str, List[Message]]:
        """Group messages by semantic similarity.

        Args:
            messages: Messages to cluster

        Returns:
            Dict mapping topic -> messages
        """
        clusters: Dict[str, List[Message]] = defaultdict(list)

        for msg in messages:
            # Extract topic for individual message
            topic = SemanticAnalyzer.extract_semantic_topic([msg])
            clusters[topic].append(msg)
            msg.semantic_topic = topic
            msg.semantic_confidence = 1.0  # Heuristic always confident

        logger.info(
            f"Clustered {len(messages)} messages into {len(clusters)} topics: "
            f"{list(clusters.keys())}"
        )

        return dict(clusters)

    @staticmethod
    def calculate_semantic_similarity(
        messages1: List[Message], messages2: List[Message]
    ) -> float:
        """Calculate semantic similarity between two message groups.

        Args:
            messages1: First group
            messages2: Second group

        Returns:
            Similarity score 0.0-1.0
        """
        topic1 = SemanticAnalyzer.extract_semantic_topic(messages1)
        topic2 = SemanticAnalyzer.extract_semantic_topic(messages2)

        # Simple topic matching for MVP
        if topic1 == topic2:
            return 1.0
        else:
            # Check for keyword overlap
            text1 = " ".join(msg.content.lower() for msg in messages1)
            text2 = " ".join(msg.content.lower() for msg in messages2)

            words1 = set(re.findall(r"\w+", text1))
            words2 = set(re.findall(r"\w+", text2))

            if not words1 or not words2:
                return 0.0

            overlap = len(words1 & words2)
            union = len(words1 | words2)

            return overlap / union if union > 0 else 0.0


# ============================================================================
# Utility Functions
# ============================================================================


def analyze_session_semantics(session: Session) -> Session:
    """Enhance a session with semantic analysis.

    Takes an existing Session (created by ConversationDAG) and enriches it with:
    - Semantic topic extraction for threads
    - Enhanced corruption scoring
    - Message clustering by topic

    Args:
        session: Session to enhance

    Returns:
        Enhanced session with semantic analysis
    """
    logger.info(f"Starting semantic analysis: {len(session.messages)} messages")

    # Semantic clustering for all messages
    clusters = SemanticAnalyzer.cluster_by_topic(session.messages)

    # Enhance threads with semantic topics
    for thread in session.threads + session.orphans:
        if not thread.semantic_topic:
            thread.semantic_topic = SemanticAnalyzer.extract_semantic_topic(
                thread.messages
            )

    logger.info(
        f"Semantic analysis complete: {len(session.threads)} threads, "
        f"{len(clusters)} topics identified"
    )

    return session


def detect_orphans_with_scoring(messages: List[Message]) -> List[Thread]:
    """Detect and score orphaned branches.

    This is a convenience function for analyzing orphans independently
    from a full DAG build.

    Args:
        messages: All messages to analyze

    Returns:
        List of orphaned threads sorted by corruption score (descending)
    """
    return CorruptionScorer.detect_orphans(messages)
