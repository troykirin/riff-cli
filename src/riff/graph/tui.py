"""
Interactive TUI for navigating conversation DAGs with vim-style controls.

Provides flattened tree visualization with:
- Vim-style navigation (j/k/g/G)
- Message details view (Enter)
- Orphan repair suggestions (r)
- Real-time cursor positioning
"""

from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

from ..tui.interface import InteractiveTUI, NavigationResult
from .dag import ConversationDAG
from .models import Message
from .visualizer import LineItem, flatten_session_for_navigation


class ConversationGraphNavigator(InteractiveTUI):
    """
    Vim-style TUI for navigating conversation DAGs.

    Provides flattened tree view with:
    - j/k: Navigate down/up
    - g/G: Jump to top/bottom
    - Enter: Show message details
    - r: Show repair suggestions (for orphans)
    - q: Quit

    Handles arbitrarily large conversations with viewport pagination.
    """

    def __init__(self, dag: ConversationDAG, console: Optional[Console] = None):
        """
        Initialize graph navigator.

        Args:
            dag: ConversationDAG to navigate
            console: Optional Rich Console for rendering
        """
        self.dag = dag
        self.console = console or Console()
        self.session = dag.to_session()

        # Flatten tree for linear navigation using existing visualizer
        self.lines = flatten_session_for_navigation(self.session)

        # Navigation state
        self.current_index = 0
        self.viewport_height = 20  # Lines to show at once
        self.active = True

        # Key bindings
        self.bindings = KeyBindings()
        self._setup_keybindings()

    def _get_message_from_line(self, line: LineItem) -> Optional[Message]:
        """
        Get Message object from a LineItem.

        Args:
            line: LineItem to extract message from

        Returns:
            Message object if line has a message UUID, None otherwise
        """
        if line.message_uuid:
            return self.dag.get_message(line.message_uuid)
        return None

    def _setup_keybindings(self) -> None:
        """Setup vim-style key bindings."""

        @self.bindings.add("j")
        def move_down(event):
            """Move cursor down one line."""
            if self.current_index < len(self.lines) - 1:
                self.current_index += 1

        @self.bindings.add("k")
        def move_up(event):
            """Move cursor up one line."""
            if self.current_index > 0:
                self.current_index -= 1

        @self.bindings.add("g")
        def go_top(event):
            """Jump to top of conversation."""
            self.current_index = 0

        @self.bindings.add("shift+g")
        def go_bottom(event):
            """Jump to bottom of conversation (Shift+G)."""
            self.current_index = len(self.lines) - 1

        @self.bindings.add("enter")
        def show_details(event):
            """Show message details."""
            current_line = self.lines[self.current_index]
            message = self._get_message_from_line(current_line)
            if message:
                self.active = False
                event.app.exit(result=NavigationResult(
                    action="open",
                    selected_index=self.current_index,
                ))

        @self.bindings.add("r")
        def show_repair(event):
            """Show repair suggestions."""
            current_line = self.lines[self.current_index]
            message = self._get_message_from_line(current_line)
            if current_line.is_orphan and message:
                self.active = False
                event.app.exit(result=NavigationResult(
                    action="repair",
                    selected_index=self.current_index,
                ))

        @self.bindings.add("q")
        def quit_nav(event):
            """Quit navigator."""
            self.active = False
            event.app.exit(result=NavigationResult(action="quit"))

        @self.bindings.add("c-c")
        def force_quit(event):
            """Force quit (Ctrl+C)."""
            self.active = False
            event.app.exit(result=NavigationResult(action="quit"))

    def _render_display(self) -> str:
        """
        Render current viewport with cursor highlighting.

        Shows viewport_height lines centered on current_index,
        with cursor marker and position indicator.

        Returns:
            Formatted display string
        """
        if not self.lines:
            return "No messages in conversation"

        # Calculate viewport window
        start_idx = max(0, self.current_index - self.viewport_height // 2)
        end_idx = min(len(self.lines), start_idx + self.viewport_height)

        # Adjust if we're near the end
        if end_idx == len(self.lines):
            start_idx = max(0, end_idx - self.viewport_height)

        # Build display lines
        display_lines = []

        # Header
        display_lines.append(f"Session: {self.session.session_id[:8]}...")
        display_lines.append(f"Messages: {self.session.message_count} | "
                           f"Threads: {self.session.thread_count} | "
                           f"Orphans: {self.session.orphan_count}")
        display_lines.append("-" * 80)

        # Viewport lines
        for i in range(start_idx, end_idx):
            line = self.lines[i]
            cursor = "→ " if i == self.current_index else "  "

            # Color code based on type
            if line.is_orphan:
                line_display = f"[red]{line.text}[/red]"
            elif line.message_uuid:
                line_display = line.text
            else:
                line_display = f"[dim]{line.text}[/dim]"

            display_lines.append(f"{cursor}{line_display}")

        # Footer
        display_lines.append("-" * 80)
        display_lines.append(
            f"Line {self.current_index + 1}/{len(self.lines)} | "
            f"j/k=nav | g/G=top/bot | Enter=details | r=repair | q=quit"
        )

        return "\n".join(display_lines)

    def navigate(self) -> NavigationResult:
        """
        Start interactive navigation loop.

        Returns:
            NavigationResult indicating user action
        """
        try:
            # Create prompt_toolkit application
            text_control = FormattedTextControl(
                text=lambda: self._render_display(),
            )

            body = Window(
                content=text_control,
                wrap_lines=True,
            )

            layout = Layout(body)

            from prompt_toolkit.application import Application as PTKApp
            app: PTKApp[NavigationResult | None] = Application(
                layout=layout,
                key_bindings=self.bindings,
                full_screen=False,
                enable_page_navigation_bindings=False,
            )

            # Run application
            result = app.run()
            return result if isinstance(result, NavigationResult) else NavigationResult(action="quit")

        except Exception as e:
            self.console.print(f"[red]Navigation error: {e}[/red]")
            return NavigationResult(action="quit")

    def show_message_details(self, message: Message) -> None:
        """
        Display detailed message information.

        Shows:
        - Full message content
        - Timestamp
        - Parent/child relationships
        - Thread membership
        - Corruption metrics

        Args:
            message: Message to display
        """
        self.console.print("\n")

        # Create details table
        table = Table(title=f"Message Details: {message.uuid[:8]}...")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("UUID", message.uuid)
        table.add_row("Type", message.type.value)
        table.add_row("Timestamp", str(message.timestamp))
        table.add_row("Session", message.session_id[:8] + "...")

        # Parent info
        parent_display = message.parent_uuid[:8] + "..." if message.parent_uuid else "None (root)"
        table.add_row("Parent UUID", parent_display)

        # Children info
        children = self.dag.get_children(message.uuid)
        children_display = f"{len(children)} children" if children else "No children"
        table.add_row("Children", children_display)

        # Thread info
        thread_display = message.thread_id[:8] + "..." if message.thread_id else "None"
        table.add_row("Thread ID", thread_display)

        # Status
        status_parts = []
        if message.is_orphaned:
            status_parts.append("ORPHANED")
        if message.is_sidechain:
            status_parts.append("SIDECHAIN")
        status_display = ", ".join(status_parts) if status_parts else "Normal"
        table.add_row("Status", status_display)

        # Corruption
        corruption_color = "red" if message.corruption_score > 0.5 else "yellow" if message.corruption_score > 0.0 else "green"
        table.add_row("Corruption", f"[{corruption_color}]{message.corruption_score:.2f}[/{corruption_color}]")

        self.console.print(table)

        # Content section
        self.console.print("\n[bold]Content:[/bold]")

        # Show full content with syntax highlighting if it looks like code
        content = message.content
        if len(content) > 2000:
            content = content[:2000] + "\n\n... (truncated, showing first 2000 chars)"

        self.console.print(Panel(content, border_style="blue"))

        # Ancestry path
        if message.parent_uuid:
            self.console.print("\n[bold]Ancestry Path:[/bold]")
            path = self.dag.get_ancestry_path(message.uuid)
            for i, ancestor in enumerate(path):
                indent = "  " * i
                marker = "└─" if i == len(path) - 1 else "├─"
                self.console.print(f"{indent}{marker} {ancestor.uuid[:8]}... [{ancestor.type.value}]")

        self.console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

    def show_repair_suggestions(self, orphan_message: Message) -> None:
        """
        Show repair suggestions for orphaned message.

        Analyzes:
        - Possible parent candidates
        - Timestamp-based heuristics
        - Content similarity
        - Structural patterns

        Args:
            orphan_message: Orphaned message to analyze
        """
        self.console.print("\n")
        self.console.print(Panel(
            f"[yellow]Repair Suggestions for Orphan[/yellow]\n"
            f"UUID: {orphan_message.uuid[:8]}...\n"
            f"Corruption Score: {orphan_message.corruption_score:.2f}",
            border_style="yellow"
        ))

        # Find potential parent candidates
        candidates = self._find_repair_candidates(orphan_message)

        if not candidates:
            self.console.print("\n[red]No suitable parent candidates found[/red]")
            self.console.print("\nPossible reasons:")
            self.console.print("  • Orphan is from a completely separate conversation")
            self.console.print("  • Parent message was deleted")
            self.console.print("  • Severe data corruption")
            self.console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            return

        # Display candidates
        self.console.print("\n[bold]Suggested parent candidates:[/bold]")
        table = Table()
        table.add_column("#", style="cyan")
        table.add_column("UUID", style="white")
        table.add_column("Type", style="green")
        table.add_column("Timestamp", style="yellow")
        table.add_column("Score", style="magenta")

        for i, (candidate_msg, score) in enumerate(candidates[:5], start=1):
            table.add_row(
                str(i),
                candidate_msg.uuid[:8] + "...",
                candidate_msg.type.value,
                str(candidate_msg.timestamp)[:19],
                f"{score:.2f}"
            )

        self.console.print(table)

        # Repair instructions
        self.console.print("\n[bold]To repair:[/bold]")
        self.console.print("1. Note the UUID of the best candidate")
        self.console.print("2. Run: riff repair --session <session-id> --orphan <orphan-uuid> --parent <candidate-uuid>")
        self.console.print("3. Or use the interactive repair command: riff repair --interactive")

        self.console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

    def _find_repair_candidates(self, orphan: Message) -> list[tuple[Message, float]]:
        """
        Find potential parent candidates for orphaned message.

        Uses heuristics:
        - Timestamp proximity
        - Message type patterns (user -> assistant -> user)
        - Thread membership
        - Content similarity

        Args:
            orphan: Orphaned message to find parents for

        Returns:
            List of (candidate_message, confidence_score) tuples, sorted by score
        """
        from ..graph.models import Message
        candidates: list[tuple[Message, float]] = []

        # Get main thread messages as candidates
        main_thread = self.session.main_thread
        if not main_thread:
            return candidates

        for candidate in main_thread.messages:
            score = 0.0

            # Skip if candidate is also orphaned
            if candidate.is_orphaned:
                continue

            # Timestamp proximity (if timestamps are valid)
            if orphan.timestamp and candidate.timestamp:
                try:
                    # Simple timestamp comparison (could be improved)
                    orphan_ts = int(orphan.timestamp) if isinstance(orphan.timestamp, (int, str)) else 0
                    candidate_ts = int(candidate.timestamp) if isinstance(candidate.timestamp, (int, str)) else 0

                    time_diff = abs(orphan_ts - candidate_ts)

                    # Closer in time = higher score
                    if time_diff < 1000:  # Very close
                        score += 0.5
                    elif time_diff < 10000:  # Close
                        score += 0.3
                    elif time_diff < 100000:  # Moderately close
                        score += 0.1
                except (ValueError, TypeError):
                    pass

            # Type pattern (assistant -> user or user -> assistant)
            if candidate.type.value != orphan.type.value:
                score += 0.3

            # Has children (potential insertion point)
            if self.dag.get_children(candidate.uuid):
                score += 0.1

            if score > 0:
                candidates.append((candidate, score))

        # Sort by score (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates

    # Interface method implementations
    def update_results(self, results: list) -> None:
        """Update displayed results (not used in graph navigator)."""
        pass

    def show_filter_prompt(self) -> Optional[int]:
        """Show time filter prompt (not used in graph navigator)."""
        return None

    def display_session(self, session_id: str, file_path: str) -> None:
        """Display full session (not used in graph navigator)."""
        pass

    def is_active(self) -> bool:
        """Check if TUI is still active."""
        return self.active
