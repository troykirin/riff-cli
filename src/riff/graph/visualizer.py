"""
ASCII tree visualization for conversation DAG structures.

Generates git log --graph style output showing conversation threads,
branches, and orphaned messages.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from .models import Thread, Session, MessageType


@dataclass
class LineItem:
    """
    Single line in the flattened visualization.

    Each LineItem represents one message in the tree view, with its
    visual formatting (tree graphics), content preview, and navigation metadata.

    Attributes:
        text: The formatted line text to display
        message_uuid: UUID of the message (for navigation)
        thread_id: Which thread this line belongs to
        is_orphan: True if this is an orphaned message
        corruption_score: Corruption score for this message (0.0-1.0)
        indent_level: Indentation depth for tree structure
    """
    text: str
    message_uuid: Optional[str] = None
    thread_id: Optional[str] = None
    is_orphan: bool = False
    corruption_score: float = 0.0
    indent_level: int = 0


class ConversationTreeVisualizer:
    """
    Generate ASCII tree visualization for conversation DAG.

    Output format similar to 'git log --graph':
    * 2025-10-20 User: "message preview"
    * 2025-10-20 Assistant: "response preview"
    |\\
    | * [Side] User: "tangent question"
    | * [Side] Assistant: "answer"
    |/
    * 2025-10-20 User: "back to main"
    |
    | ! [ORPHAN] User: "Resume attempt"
    | ! [ORPHAN] Assistant: "Continuing..."
    | ! (corruption_score: 0.92)
    """

    def __init__(self, session: Session, max_preview_length: int = 80):
        """
        Initialize visualizer.

        Args:
            session: Session to visualize
            max_preview_length: Maximum length for message preview text
        """
        self.session = session
        self.max_preview_length = max_preview_length

    def visualize(self, session: Session) -> str:
        """
        Generate ASCII tree visualization of conversation DAG.

        Args:
            session: Session containing threads and messages

        Returns:
            Multi-line string with ASCII tree representation
        """
        lines = self._build_visualization_lines(session)
        return "\n".join(line.text for line in lines)

    def flatten_for_navigation(self, session: Session) -> List[LineItem]:
        """
        Convert tree to flat list of LineItems for TUI navigation.

        Args:
            session: Session to flatten

        Returns:
            List of LineItems preserving tree structure via indentation
        """
        return self._build_visualization_lines(session)

    def _build_visualization_lines(self, session: Session) -> List[LineItem]:
        """
        Build complete list of visualization lines.

        Processes:
        1. Main thread (straight line with * markers)
        2. Side discussions (branching with | markers)
        3. Orphaned branches (! markers with warnings)

        Args:
            session: Session to visualize

        Returns:
            List of LineItems with formatted text and metadata
        """
        lines: List[LineItem] = []

        # Get threads in display order
        main_thread = session.main_thread
        side_threads = session.side_threads
        orphan_threads = session.orphans

        # 1. Render main thread
        if main_thread:
            lines.extend(self._render_main_thread(main_thread))

        # 2. Render side discussions interspersed
        for side_thread in side_threads:
            lines.extend(self._render_side_thread(side_thread))

        # 3. Render orphaned branches
        for orphan_thread in orphan_threads:
            lines.extend(self._render_orphaned_thread(orphan_thread))

        return lines

    def _render_main_thread(self, thread: Thread) -> List[LineItem]:
        """
        Render main conversation thread with * markers.

        Format:
        * 2025-10-20 12:34 User: "message preview..."
        * 2025-10-20 12:35 Assistant: "response preview..."

        Args:
            thread: Main thread to render

        Returns:
            List of LineItems for main thread
        """
        lines: List[LineItem] = []

        for msg in thread.messages:
            timestamp = self._format_timestamp(msg.timestamp)
            msg_type = self._format_message_type(msg.type)
            preview = self._truncate_content(msg.content)

            text = f"* {timestamp} {msg_type}: \"{preview}\""

            lines.append(LineItem(
                text=text,
                message_uuid=msg.uuid,
                thread_id=thread.thread_id,
                is_orphan=False,
                corruption_score=msg.corruption_score,
                indent_level=0
            ))

        return lines

    def _render_side_thread(self, thread: Thread) -> List[LineItem]:
        """
        Render side discussion with branch markers.

        Format:
        |\\
        | * [Side] User: "side question..."
        | * [Side] Assistant: "side answer..."
        |/
        * [Main] User: "back to main..."

        Args:
            thread: Side discussion thread to render

        Returns:
            List of LineItems for side thread with branch markers
        """
        lines: List[LineItem] = []

        # Branch start marker
        lines.append(LineItem(
            text="|\\",
            message_uuid=None,
            thread_id=thread.thread_id,
            indent_level=0
        ))

        # Side thread messages (indented)
        for msg in thread.messages:
            timestamp = self._format_timestamp(msg.timestamp)
            msg_type = self._format_message_type(msg.type)
            preview = self._truncate_content(msg.content)

            text = f"| * [Side] {timestamp} {msg_type}: \"{preview}\""

            lines.append(LineItem(
                text=text,
                message_uuid=msg.uuid,
                thread_id=thread.thread_id,
                is_orphan=False,
                corruption_score=msg.corruption_score,
                indent_level=1
            ))

        # Branch end marker
        lines.append(LineItem(
            text="|/",
            message_uuid=None,
            thread_id=thread.thread_id,
            indent_level=0
        ))

        return lines

    def _render_orphaned_thread(self, thread: Thread) -> List[LineItem]:
        """
        Render orphaned branch with ! markers and warnings.

        Format:
        |
        | ! [ORPHAN] User: "disconnected message..."
        | ! [ORPHAN] Assistant: "orphaned response..."
        | ! (corruption_score: 0.92, likely resume failure)

        Args:
            thread: Orphaned thread to render

        Returns:
            List of LineItems for orphaned thread with warnings
        """
        lines: List[LineItem] = []

        # Separator before orphan section
        lines.append(LineItem(
            text="|",
            message_uuid=None,
            thread_id=thread.thread_id,
            indent_level=0
        ))

        # Orphaned messages
        for msg in thread.messages:
            timestamp = self._format_timestamp(msg.timestamp)
            msg_type = self._format_message_type(msg.type)
            preview = self._truncate_content(msg.content)

            # Color hint: These should be rendered in red/warning color in TUI
            text = f"| ! [ORPHAN] {timestamp} {msg_type}: \"{preview}\""

            lines.append(LineItem(
                text=text,
                message_uuid=msg.uuid,
                thread_id=thread.thread_id,
                is_orphan=True,
                corruption_score=msg.corruption_score,
                indent_level=1
            ))

        # Corruption warning
        score = thread.corruption_score
        reason = self._infer_corruption_reason(thread)
        warning_text = f"| ! (corruption_score: {score:.2f}, {reason})"

        lines.append(LineItem(
            text=warning_text,
            message_uuid=None,
            thread_id=thread.thread_id,
            is_orphan=True,
            corruption_score=score,
            indent_level=1
        ))

        return lines

    def _format_timestamp(self, timestamp_str: str) -> str:
        """
        Format timestamp for display.

        Args:
            timestamp_str: ISO8601 timestamp string

        Returns:
            Formatted timestamp (e.g., "2025-10-20 12:34")
        """
        try:
            # Parse ISO8601 timestamp
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            # Fallback if parsing fails
            return timestamp_str[:16]

    def _format_message_type(self, msg_type: MessageType) -> str:
        """
        Format message type for display.

        Args:
            msg_type: MessageType enum

        Returns:
            Formatted type string
        """
        type_map = {
            MessageType.USER: "User",
            MessageType.ASSISTANT: "Assistant",
            MessageType.SYSTEM: "System",
            MessageType.SUMMARY: "Summary",
            MessageType.FILE_HISTORY_SNAPSHOT: "FileSnapshot",
        }
        return type_map.get(msg_type, str(msg_type.value))

    def _truncate_content(self, content: str) -> str:
        """
        Truncate content to max preview length.

        Args:
            content: Full message content

        Returns:
            Truncated content with "..." if needed
        """
        # Get first line only
        first_line = content.split('\n')[0].strip()

        if len(first_line) > self.max_preview_length:
            return first_line[:self.max_preview_length - 3] + "..."

        return first_line

    def _infer_corruption_reason(self, thread: Thread) -> str:
        """
        Infer likely cause of corruption based on thread properties.

        Args:
            thread: Orphaned thread to analyze

        Returns:
            Human-readable reason string
        """
        first_msg = thread.first_message

        reasons = []

        # Check for null parent
        if first_msg.parent_uuid is None:
            reasons.append("null parent")

        # Check for sidechain flag
        if first_msg.is_sidechain:
            reasons.append("resume failure")

        # Check corruption score
        if thread.corruption_score > 0.8:
            reasons.append("high corruption score")

        if not reasons:
            reasons.append("unknown cause")

        return ", ".join(reasons)

    def flatten_to_lines(self, include_orphans: bool = True, max_width: int = 100) -> List[LineItem]:
        """
        Flatten tree to list of LineItems for TUI navigation.

        Args:
            include_orphans: Whether to include orphaned threads
            max_width: Maximum line width for content

        Returns:
            List of LineItems for TUI navigation
        """
        lines = []

        # Main thread
        main_thread = self.session.main_thread
        if main_thread:
            lines.extend(self._render_main_thread(main_thread))

        # Side threads
        for side_thread in self.session.side_threads:
            lines.extend(self._render_side_thread(side_thread))

        # Orphans (if requested)
        if include_orphans:
            for orphan_thread in self.session.orphans:
                lines.extend(self._render_orphaned_thread(orphan_thread))

        return lines

    def render_ascii_tree(self) -> str:
        """
        Render the complete ASCII tree visualization.

        Returns:
            Multi-line string with ASCII tree
        """
        lines = self.flatten_to_lines(include_orphans=True)
        return "\n".join(line.text for line in lines)


def visualize_session(session: Session, max_preview_length: int = 80) -> str:
    """
    Convenience function to visualize a session.

    Args:
        session: Session to visualize
        max_preview_length: Maximum length for message previews

    Returns:
        ASCII tree visualization string
    """
    visualizer = ConversationTreeVisualizer(session, max_preview_length=max_preview_length)
    return visualizer.visualize(session)


def flatten_session_for_navigation(session: Session, max_preview_length: int = 80) -> List[LineItem]:
    """
    Convenience function to flatten a session for navigation.

    Args:
        session: Session to flatten
        max_preview_length: Maximum length for message previews

    Returns:
        List of LineItems for TUI navigation
    """
    visualizer = ConversationTreeVisualizer(session, max_preview_length=max_preview_length)
    return visualizer.flatten_for_navigation(session)
