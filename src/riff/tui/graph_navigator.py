"""
Interactive TUI navigator for conversation DAG visualization.

Provides vim-style navigation through conversation threads with semantic highlighting
and orphan detection. Supports both JSONL and SurrealDB backends for repair operations.
"""

import curses
import logging
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from ..graph.models import Session
from ..graph.dag import ConversationDAG
from ..graph.visualizer import ConversationTreeVisualizer, LineItem
from ..graph.repair_manager import RepairManager, create_repair_manager
from ..graph.persistence_provider import PersistenceProvider
from ..graph.loaders import JSONLLoader

logger = logging.getLogger(__name__)


def _create_persistence_provider() -> Optional[PersistenceProvider]:
    """
    Auto-detect and create appropriate persistence provider for repairs.

    Priority:
    1. SurrealDB if surrealdb_enabled=true in config and endpoint accessible
    2. JSONL (default fallback)

    Returns:
        PersistenceProvider instance (SurrealDB or JSONL) or None if creation fails
    """
    try:
        # Check if SurrealDB is enabled in config
        from ..config import get_config
        config = get_config()

        if config.surrealdb_enabled:
            logger.info(
                f"SurrealDB enabled in config, attempting to use backend: "
                f"{config.surrealdb_endpoint}"
            )
            try:
                from ..surrealdb import SurrealDBStorage, SurrealDBRepairProvider

                # Initialize storage with config values
                storage = SurrealDBStorage(
                    base_url=config.surrealdb_endpoint,
                    namespace=config.surrealdb_namespace,
                    database=config.surrealdb_database,
                    username=config.surrealdb_username,
                    password=config.surrealdb_password,
                )
                provider = SurrealDBRepairProvider(storage=storage, operator="tui")
                logger.info(
                    f"Using SurrealDB repair backend: "
                    f"{config.surrealdb_namespace}.{config.surrealdb_database}"
                )
                return provider
            except Exception as e:
                logger.warning(
                    f"Failed to initialize SurrealDB backend: {e}, falling back to JSONL"
                )

        # Default to JSONL backend
        from ..graph.persistence_providers import JSONLRepairProvider

        logger.debug("Using JSONL repair backend (SurrealDB not enabled in config)")
        return JSONLRepairProvider()

    except Exception as e:
        logger.error(f"Failed to create persistence provider: {e}")
        return None


@dataclass
class RepairOperation:
    """
    Record of a repair operation for undo functionality.

    Attributes:
        message_uuid: UUID of the repaired message
        old_parent_uuid: Previous parent UUID (None for orphans)
        new_parent_uuid: New parent UUID after repair
        timestamp: When the repair was performed
        semantic_score: Similarity score for the repair (0.0-1.0)
    """
    message_uuid: str
    old_parent_uuid: Optional[str]
    new_parent_uuid: str
    timestamp: str
    semantic_score: float = 0.0


@dataclass
class NavigationState:
    """
    Track current navigation position, view state, and repair operations.

    Attributes:
        current_line: Currently selected line index
        view_offset: Top line visible in viewport
        max_height: Terminal height
        max_width: Terminal width
        show_orphans: Whether to display orphaned messages
        show_details: Whether to show detailed message info
        marked_messages: Set of message UUIDs marked for repair
        undo_stack: History of repair operations (max 5)
        current_mode: Current interaction mode
    """
    current_line: int = 0
    view_offset: int = 0
    max_height: int = 0
    max_width: int = 0
    show_orphans: bool = True
    show_details: bool = False
    marked_messages: set[str] = field(default_factory=set)
    undo_stack: list[RepairOperation] = field(default_factory=list)
    current_mode: str = "navigate"  # "navigate", "repair", "undo"


class ConversationGraphNavigator:
    """
    Interactive TUI for navigating conversation DAG with repair capabilities.

    Provides vim-style key bindings for navigating through conversation
    threads, viewing message details, marking messages for repair, and
    analyzing orphaned messages.

    Navigation Key bindings:
        j/↓: Move down
        k/↑: Move up
        g: Go to top
        G: Go to bottom
        o: Toggle orphan display
        d: Toggle detail view
        Enter: Preview full message in modal
        /: Search (coming soon)
        q: Quit

    Repair Key bindings:
        m: Mark/unmark current message for repair
        r: Show repair preview with diff and semantic similarity
        u: Show undo stack and rollback repairs
    """

    def __init__(
        self,
        session: Session,
        dag: ConversationDAG,
        session_id: str,
        jsonl_path: Optional[Path] = None,
        loader: Optional[JSONLLoader] = None
    ) -> None:
        """
        Initialize navigator with session, DAG, and repair capabilities.

        Args:
            session: Session object with organized threads
            dag: ConversationDAG for tree operations
            session_id: Claude session UUID
            jsonl_path: Path to JSONL file (for repairs)
            loader: JSONLLoader instance (for reloading after repairs)
        """
        self.session = session
        self.dag = dag
        self.session_id = session_id
        self.jsonl_path = jsonl_path
        self.loader = loader
        self.visualizer = ConversationTreeVisualizer(session)
        self.state = NavigationState()
        self.lines: list[LineItem] = []
        self._pending_modal: Optional[tuple[str, list[str]]] = None  # (title, content_lines)
        self._repair_candidates: list = []  # For cycling through repair options
        self._current_candidate: int = 0
        self._pending_undo: bool = False
        self._last_key_was_g: bool = False  # For vim-style 'gg' to go to top

        # Initialize repair manager if paths available
        # Uses pluggable persistence provider (auto-detects SurrealDB or defaults to JSONL)
        self.repair_manager: Optional[RepairManager] = None
        if jsonl_path and loader and session_id:
            try:
                # Auto-detect persistence backend
                persistence_provider = _create_persistence_provider()

                self.repair_manager = create_repair_manager(
                    session_id=session_id,
                    jsonl_path=jsonl_path,
                    session=session,
                    dag=dag,
                    loader=loader,
                    persistence_provider=persistence_provider,
                )
                logger.info(
                    f"Repair manager initialized with "
                    f"{persistence_provider.get_backend_name() if persistence_provider else 'unknown'} backend"
                )
            except Exception as e:
                logger.warning(f"Repair manager initialization failed: {e}")

        self._refresh_lines()

    def _refresh_lines(self) -> None:
        """Regenerate flattened line items from current view."""
        self.lines = self.visualizer.flatten_to_lines(
            include_orphans=self.state.show_orphans,
            max_width=self.state.max_width or 100
        )

    def _draw_header(self, stdscr) -> int:
        """Draw header with session info."""
        try:
            # Title
            title = f"Conversation DAG: {self.session.session_id[:8]}..."
            stdscr.addstr(0, 0, title, curses.A_BOLD | curses.color_pair(1))

            # Stats line
            stats = (
                f"Messages: {self.session.message_count} | "
                f"Threads: {self.session.thread_count} | "
                f"Orphans: {self.session.orphan_count} | "
                f"Corruption: {self.session.corruption_score:.1%}"
            )
            stdscr.addstr(1, 0, stats, curses.color_pair(2))

            # Help line
            help_text = "j/k:Navigate | gg:Top | G:Bottom | m:Mark | r:Repair | u:Undo | o:Orphans | d:Details | q:Quit"
            stdscr.addstr(2, 0, help_text, curses.A_DIM)

            # Separator
            stdscr.addstr(3, 0, "─" * self.state.max_width)

            return 4  # Number of header lines
        except curses.error:
            return 4

    def _draw_content(self, stdscr, start_row: int) -> None:
        """Draw the conversation tree content."""
        visible_height = self.state.max_height - start_row - 1  # Leave room for footer

        # Calculate visible range
        end_line = min(
            self.state.view_offset + visible_height,
            len(self.lines)
        )

        for i, line_idx in enumerate(range(self.state.view_offset, end_line)):
            if line_idx >= len(self.lines):
                break

            line_item = self.lines[line_idx]
            row = start_row + i

            try:
                # Determine colors and attributes
                attr = curses.A_NORMAL
                color_pair = 0

                if line_idx == self.state.current_line:
                    attr |= curses.A_REVERSE  # Highlight current line

                if line_item.is_orphan:
                    color_pair = 3  # Red for orphans

                if line_item.corruption_score > 0.5:
                    attr |= curses.A_BOLD  # Bold for high corruption

                # Add prefix indicators for marked/orphaned messages
                prefix = ""
                if line_item.message_uuid and line_item.message_uuid in self.state.marked_messages:
                    prefix = "[*] "  # Marked for repair
                elif line_item.is_orphan:
                    prefix = "[!] "  # Orphaned message

                # Truncate to screen width (accounting for prefix)
                max_text_width = self.state.max_width - len(prefix) - 1
                text = prefix + line_item.text[:max_text_width]

                # Draw the line
                if color_pair > 0 and curses.has_colors():
                    stdscr.addstr(row, 0, text, attr | curses.color_pair(color_pair))
                else:
                    stdscr.addstr(row, 0, text, attr)

            except curses.error:
                # Handle drawing errors gracefully
                pass

    def _draw_footer(self, stdscr) -> None:
        """Draw footer with current position info."""
        try:
            footer_row = self.state.max_height - 1

            # Position indicator
            if len(self.lines) > 0:
                percent = int((self.state.current_line + 1) / len(self.lines) * 100)
                pos_text = f"Line {self.state.current_line + 1}/{len(self.lines)} ({percent}%)"
            else:
                pos_text = "No messages"

            # Mode indicators
            modes = []
            if self.state.show_orphans:
                modes.append("ORPHANS")
            if self.state.show_details:
                modes.append("DETAILS")
            if len(self.state.marked_messages) > 0:
                modes.append(f"MARKED:{len(self.state.marked_messages)}")
            if self.state.current_mode != "navigate":
                modes.append(f"MODE:{self.state.current_mode.upper()}")

            mode_text = " | ".join(modes) if modes else ""

            # Combine footer
            footer = f"{pos_text}"
            if mode_text:
                footer += f" | {mode_text}"

            # Draw footer
            stdscr.addstr(footer_row, 0, " " * self.state.max_width)  # Clear line
            stdscr.addstr(footer_row, 0, footer, curses.A_REVERSE)

        except curses.error:
            pass

    def _handle_navigation(self, key: int) -> bool:
        """
        Handle navigation key press.

        Returns:
            True to continue, False to quit
        """
        # Reset 'g' state for any non-'g' key
        if key != ord('g'):
            self._last_key_was_g = False

        if key == ord('q') or key == ord('Q'):
            return False

        elif key == ord('j') or key == curses.KEY_DOWN:
            if self.state.current_line < len(self.lines) - 1:
                self.state.current_line += 1
                self._adjust_viewport()

        elif key == ord('k') or key == curses.KEY_UP:
            if self.state.current_line > 0:
                self.state.current_line -= 1
                self._adjust_viewport()

        elif key == ord('g'):
            # Vim-style 'gg' to go to top
            if self._last_key_was_g:
                # Second 'g' press - go to top
                self.state.current_line = 0
                self.state.view_offset = 0
                self._last_key_was_g = False
            else:
                # First 'g' press - remember it for next keystroke
                self._last_key_was_g = True
            return True

        elif key == ord('G'):
            self.state.current_line = len(self.lines) - 1
            self._adjust_viewport()

        elif key == ord('o'):
            self.state.show_orphans = not self.state.show_orphans
            self._refresh_lines()

        elif key == ord('d'):
            self.state.show_details = not self.state.show_details

        elif key == ord('m'):
            # Mark/unmark current message for repair
            self._handle_mark_message()

        elif key == ord('r'):
            # Show repair mode with diff preview
            self._handle_repair_mode()

        elif key == ord('u'):
            # Show undo stack
            self._handle_undo_mode()

        elif key == ord('\n') or key == curses.KEY_ENTER:
            # Preview current message in modal
            self._handle_preview_message(stdscr)

        return True

    def _adjust_viewport(self) -> None:
        """Adjust view offset to keep current line visible."""
        visible_height = self.state.max_height - 5  # Header + footer

        if self.state.current_line < self.state.view_offset:
            self.state.view_offset = self.state.current_line

        elif self.state.current_line >= self.state.view_offset + visible_height:
            self.state.view_offset = self.state.current_line - visible_height + 1

    def _show_modal_message(self, stdscr, title: str, lines: list[str]) -> None:
        """
        Display a centered modal message box with title and content.

        Args:
            stdscr: Curses screen object
            title: Modal title
            lines: List of content lines to display
        """
        # Calculate modal dimensions
        max_line_width = max(len(line) for line in lines) if lines else 20
        modal_width = min(max_line_width + 4, self.state.max_width - 4)
        modal_height = len(lines) + 4  # Title + border + content + footer

        # Center the modal
        start_y = max(0, (self.state.max_height - modal_height) // 2)
        start_x = max(0, (self.state.max_width - modal_width) // 2)

        try:
            # Draw border
            for i in range(modal_height):
                stdscr.addstr(start_y + i, start_x, " " * modal_width, curses.A_REVERSE)

            # Draw title
            title_text = f" {title} "
            title_x = start_x + (modal_width - len(title_text)) // 2
            stdscr.addstr(start_y, title_x, title_text, curses.A_BOLD | curses.A_REVERSE)

            # Draw content lines
            for i, line in enumerate(lines):
                content_y = start_y + 2 + i
                content_x = start_x + 2
                stdscr.addstr(content_y, content_x, line[:modal_width - 4], curses.A_REVERSE)

            # Draw footer
            footer_text = "Press any key to continue..."
            footer_x = start_x + (modal_width - len(footer_text)) // 2
            stdscr.addstr(start_y + modal_height - 1, footer_x, footer_text, curses.A_DIM | curses.A_REVERSE)

            # Wait for keypress
            stdscr.getch()

        except curses.error:
            # Handle drawing errors gracefully
            pass

    def _show_confirmation_modal(self, stdscr, title: str, lines: list[str]) -> str:
        """
        Display confirmation modal and return user choice.

        Args:
            stdscr: Curses screen object
            title: Modal title
            lines: List of content lines

        Returns:
            'y' for yes, 'n' for no, or other key pressed
        """
        # Calculate modal dimensions
        max_line_width = max(len(line) for line in lines) if lines else 20
        modal_width = min(max_line_width + 4, self.state.max_width - 4)
        modal_height = len(lines) + 4

        # Center the modal
        start_y = max(0, (self.state.max_height - modal_height) // 2)
        start_x = max(0, (self.state.max_width - modal_width) // 2)

        try:
            while True:
                # Draw border
                for i in range(modal_height):
                    stdscr.addstr(start_y + i, start_x, " " * modal_width, curses.A_REVERSE)

                # Draw title
                title_text = f" {title} "
                title_x = start_x + (modal_width - len(title_text)) // 2
                stdscr.addstr(start_y, title_x, title_text, curses.A_BOLD | curses.A_REVERSE)

                # Draw content lines
                for i, line in enumerate(lines):
                    content_y = start_y + 2 + i
                    content_x = start_x + 2
                    stdscr.addstr(content_y, content_x, line[:modal_width - 4], curses.A_REVERSE)

                # Draw footer with Y/N options
                footer_text = "[Y]es / [N]o"
                footer_x = start_x + (modal_width - len(footer_text)) // 2
                stdscr.addstr(start_y + modal_height - 1, footer_x, footer_text, curses.A_DIM | curses.A_REVERSE)

                stdscr.refresh()

                # Wait for Y or N
                key = stdscr.getch()
                if key in (ord('y'), ord('Y')):
                    return 'y'
                elif key in (ord('n'), ord('N')):
                    return 'n'
                # Loop if other key pressed

        except curses.error:
            pass

        return 'n'  # Default to no on error

    def _handle_mark_message(self) -> None:
        """
        Mark or unmark the current message for repair.

        Toggles the marked status of the message at current_line.
        Only messages with valid UUIDs can be marked.
        """
        if self.state.current_line >= len(self.lines):
            return

        line_item = self.lines[self.state.current_line]

        # Only mark messages that have UUIDs (skip header/separator lines)
        if not line_item.message_uuid:
            return

        # Toggle marked status
        if line_item.message_uuid in self.state.marked_messages:
            self.state.marked_messages.remove(line_item.message_uuid)
        else:
            self.state.marked_messages.add(line_item.message_uuid)

    def _handle_repair_mode(self) -> None:
        """
        Enter repair mode and show repair preview for current message.

        Shows:
        - Current parent UUID (or "null" for orphans)
        - Suggested parent UUID with semantic similarity score
        - Diff preview: "parentUuid: null → <suggested-parent>"
        - Confirmation prompt
        """
        if not self.repair_manager:
            self._pending_modal = (
                "Repair Not Available",
                [
                    "Repair manager not initialized.",
                    "This may indicate missing JSONL path or loader.",
                ]
            )
            return

        if self.state.current_line >= len(self.lines):
            return

        line_item = self.lines[self.state.current_line]

        if not line_item.message_uuid:
            return

        # Get the message from DAG
        message = self.dag.get_message(line_item.message_uuid)
        if not message:
            return

        # Check if message is actually orphaned or marked
        if not (line_item.is_orphan or line_item.message_uuid in self.state.marked_messages):
            self._pending_modal = (
                "Repair Not Available",
                [
                    "This message is not orphaned or marked for repair.",
                    "",
                    "Use 'm' to mark messages for repair, or navigate to",
                    "an orphaned message (marked with [!]).",
                ]
            )
            return

        try:
            # Get repair candidates
            candidates = self.repair_manager.get_repair_candidates(message, top_k=3)

            if not candidates:
                self._pending_modal = (
                    "No Repair Candidates",
                    [
                        f"Could not find repair candidates for {message.uuid[:16]}...",
                        "",
                        "This might mean all other messages are incompatible,",
                        "or there are temporal ordering issues.",
                    ]
                )
                return

            # Show first candidate with option to confirm
            repair_op, parent_msg = candidates[0]

            # Create preview
            preview = self.repair_manager.create_repair_preview(
                message, repair_op, parent_msg
            )

            modal_lines = [
                f"Message: {preview.message_preview[:80]}",
                f"Current Parent: {preview.current_parent[:16] if preview.current_parent else 'null'}",
                "",
                "━━━━ SUGGESTED REPAIR (1/{count}) ━━━━".format(count=len(candidates)),
                f"Parent: {preview.parent_preview[:80]}",
                f"Similarity: {preview.similarity_score:.1%}",
                f"Reason: {preview.reason}",
                "",
                "Diff:",
                preview.diff[:200],
                "",
                "Press 'Y' to confirm, 'N' to cancel, '>' for next candidate",
            ]

            self._pending_modal = ("Repair Preview", modal_lines)
            self._repair_candidates = candidates  # Store for next/prev
            self._current_candidate = 0

        except Exception as e:
            self._pending_modal = (
                "Repair Error",
                [
                    f"Error getting repair candidates: {str(e)[:60]}",
                ]
            )

    def _handle_undo_mode(self) -> None:
        """
        Show undo stack and allow rollback of previous repairs.

        Displays:
        - Last 5 repair operations from persistence layer
        - Message UUIDs and parent changes
        - Timestamps
        - Prompt to undo last repair
        """
        if not self.repair_manager:
            self._pending_modal = (
                "Undo Not Available",
                [
                    "Repair manager not initialized.",
                    "This may indicate missing JSONL path or loader.",
                ]
            )
            return

        try:
            # Get undo history from persistence layer
            undo_history = self.repair_manager.show_undo_history()

            if not undo_history:
                self._pending_modal = (
                    "No Repairs to Undo",
                    [
                        "No repair operations available for undo.",
                        "",
                        "After you perform repairs using 'r', they will",
                        "appear here for potential rollback.",
                    ]
                )
                return

            # Build undo stack display
            modal_lines = ["Available Undo Points (Most Recent First):", ""]

            # Show recent snapshots (up to 5)
            for i, snapshot in enumerate(undo_history[:5], 1):
                modal_lines.append(f"{i}. Repairs: {snapshot.repair_count}")
                modal_lines.append(f"   Time: {snapshot.timestamp}")
                modal_lines.append(f"   Backup: {snapshot.backup_path.name if snapshot.backup_path else 'unknown'}")
                modal_lines.append("")

            modal_lines.extend([
                "Press 'Y' to undo last repair, 'N' to cancel",
                "",
                "Undo will restore the JSONL file and reload the DAG.",
            ])

            self._pending_modal = ("Undo Stack", modal_lines)
            self._pending_undo = True  # Flag to handle undo confirmation

        except Exception as e:
            self._pending_modal = (
                "Undo Error",
                [
                    f"Error retrieving undo history: {str(e)[:60]}",
                ]
            )

    def _handle_preview_message(self, stdscr) -> None:
        """
        Preview the current message in a modal with full content.

        Displays:
        - Message UUID
        - Message type (user, assistant, system)
        - Full content (with word wrapping)
        - Parent UUID if available
        """
        try:
            # Get current line's message
            if self.state.current_line >= len(self.lines):
                self._pending_modal = (
                    "No Message",
                    ["No message to preview at this line."]
                )
                return

            current_line_item = self.lines[self.state.current_line]

            # Extract message UUID from line text
            # Lines are formatted like: "├─ [UUID] message preview..."
            line_text = current_line_item.text if hasattr(current_line_item, 'text') else str(current_line_item)

            # Try to find a message UUID in the current line
            message = None
            if hasattr(current_line_item, 'message_id') and current_line_item.message_id:
                message = self.dag.get_message(current_line_item.message_id)
            else:
                # Fallback: try to find message by content
                for msg in self.session.all_messages:
                    if line_text and msg.content and msg.content[:50] in line_text:
                        message = msg
                        break

            if not message:
                self._pending_modal = (
                    "No Message Found",
                    [
                        "Could not find the message associated with",
                        "this line. This may be a tree node or label.",
                    ]
                )
                return

            # Build preview lines
            preview_lines = [
                f"UUID: {message.id}",
                f"Type: {message.type.value}",
                f"Timestamp: {message.timestamp}",
            ]

            if message.parent_id:
                preview_lines.append(f"Parent: {message.parent_id}")

            preview_lines.extend([
                "",
                "Content (first 500 chars):",
                "─" * 40,
            ])

            # Add message content with wrapping
            content = message.content or "(empty message)"
            # Simple word wrapping for content
            max_width = min(80, self.state.max_width - 6)
            words = content.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > max_width:
                    if current_line:
                        preview_lines.append(current_line)
                    current_line = word
                else:
                    current_line += (" " if current_line else "") + word
            if current_line:
                preview_lines.append(current_line)

            if len(content) > 500:
                preview_lines.append("... (truncated)")

            self._pending_modal = ("Message Preview", preview_lines)

        except Exception as e:
            self._pending_modal = (
                "Preview Error",
                [
                    f"Error previewing message:",
                    str(e)[:60],
                ]
            )

    def run(self) -> None:
        """Run the interactive TUI."""
        curses.wrapper(self._run_curses)

    def _run_curses(self, stdscr) -> None:
        """Main curses loop."""
        # Initialize colors
        curses.curs_set(0)  # Hide cursor
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Title
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Stats
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)  # Orphans

        # Main loop
        while True:
            # Get screen dimensions
            self.state.max_height, self.state.max_width = stdscr.getmaxyx()

            # Clear and redraw
            stdscr.clear()

            # Draw components
            header_rows = self._draw_header(stdscr)
            self._draw_content(stdscr, header_rows)
            self._draw_footer(stdscr)

            # Refresh display
            stdscr.refresh()

            # Show pending modal if any
            if self._pending_modal:
                title, lines = self._pending_modal
                self._pending_modal = None  # Clear before showing

                # Check if this is a confirmation modal
                if self._repair_candidates and not self._pending_undo:
                    # Show repair confirmation
                    choice = self._show_confirmation_modal(stdscr, title, lines)
                    if choice == 'y':
                        # Apply repair
                        if not self.repair_manager:
                            self._pending_modal = (
                                "Repair Failed",
                                ["Repair manager not initialized"]
                            )
                            continue

                        repair_op, parent_msg = self._repair_candidates[self._current_candidate]
                        message_to_repair = self.dag.get_message(repair_op.message_id)
                        if not message_to_repair:
                            self._pending_modal = (
                                "Repair Failed",
                                [f"Message {repair_op.message_id} not found in DAG"]
                            )
                            continue

                        result = self.repair_manager.apply_repair(
                            message_to_repair,
                            repair_op.suggested_parent_uuid
                        )
                        if result.success:
                            self._pending_modal = (
                                "Repair Applied",
                                [f"Successfully repaired: {result.message}"]
                            )
                        else:
                            self._pending_modal = (
                                "Repair Failed",
                                [f"Error: {result.message}"]
                            )
                    self._repair_candidates = []
                    self._current_candidate = 0

                elif self._pending_undo:
                    # Show undo confirmation
                    choice = self._show_confirmation_modal(stdscr, title, lines)
                    if choice == 'y':
                        if not self.repair_manager:
                            self._pending_modal = (
                                "Undo Failed",
                                ["Repair manager not initialized"]
                            )
                            continue

                        result = self.repair_manager.undo_repair()
                        if result.success:
                            self._pending_modal = (
                                "Undo Applied",
                                [f"Successfully undid repair: {result.message}"]
                            )
                        else:
                            self._pending_modal = (
                                "Undo Failed",
                                [f"Error: {result.message}"]
                            )
                    self._pending_undo = False

                else:
                    # Regular info modal
                    self._show_modal_message(stdscr, title, lines)

                # Redraw after modal closes
                continue

            # Handle input
            key = stdscr.getch()
            if not self._handle_navigation(key):
                break