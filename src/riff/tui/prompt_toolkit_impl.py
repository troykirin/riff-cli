"""MVP TUI implementation using prompt_toolkit"""

from __future__ import annotations

from typing import Optional
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console

from .interface import InteractiveTUI, NavigationResult


class PromptToolkitTUI(InteractiveTUI):
    """
    MVP implementation of interactive TUI using prompt_toolkit

    Provides:
    - vim-style navigation (j=down, k=up, g=top, G=bottom, Enter=select, q=quit)
    - Real-time content preview
    - Time filter toggling with 'f' key
    """

    def __init__(self, results: list, console: Optional[Console] = None):
        self.results = results
        self.console = console or Console()
        self.current_index = 0
        self.filter_days: Optional[int] = None
        self.active = True

        # Create key bindings
        self.bindings = KeyBindings()
        self._setup_keybindings()

    def _setup_keybindings(self):
        """Setup vim-style key bindings"""

        @self.bindings.add("j")
        def _(event):
            """Down"""
            self.current_index = min(self.current_index + 1, len(self.results) - 1)

        @self.bindings.add("k")
        def _(event):
            """Up"""
            self.current_index = max(self.current_index - 1, 0)

        @self.bindings.add("g")
        def _(event):
            """Go to start (top)"""
            self.current_index = 0

        @self.bindings.add("G")
        def _(event):
            """Go to end (bottom) - Shift+G"""
            self.current_index = len(self.results) - 1

        @self.bindings.add("enter")
        def _(event):
            """Select current result"""
            self.active = False
            event.app.exit(result=NavigationResult(
                action="open",
                selected_index=self.current_index,
                session_id=self.results[self.current_index]['session_id']
            ))

        @self.bindings.add("f")
        def _(event):
            """Toggle filter prompt"""
            self.active = False
            event.app.exit(result=NavigationResult(
                action="filter",
                selected_index=self.current_index
            ))

        @self.bindings.add("o")
        def _(event):
            """Open/preview current result in modal"""
            self.active = False
            event.app.exit(result=NavigationResult(
                action="preview",
                selected_index=self.current_index,
                session_id=self.results[self.current_index]['session_id']
            ))

        @self.bindings.add("q")
        def _(event):
            """Quit"""
            self.active = False
            event.app.exit(result=NavigationResult(action="quit"))

        @self.bindings.add("c-c")
        def _(event):
            """Ctrl+C also quits"""
            self.active = False
            event.app.exit(result=NavigationResult(action="quit"))

    def _create_display_text(self) -> str:
        """Create formatted display of current results"""
        if not self.results:
            return "No results"

        lines = []
        for i, result in enumerate(self.results):
            prefix = "→ " if i == self.current_index else "  "
            line = f"{prefix}[{i+1}] {result['session_id'][:8]}... | {result['content_preview'][:60]}..."
            lines.append(line)

        # Add status line
        lines.append("")
        lines.append("Commands: j/k=navigate | g/G=top/bottom | Enter=open | o=preview | f=filter | q=quit")

        return "\n".join(lines)

    def navigate(self) -> NavigationResult:
        """Start interactive navigation loop"""
        try:
            # Create application
            text_control = FormattedTextControl(
                text=lambda: self._create_display_text()
            )
            body = Window(content=text_control, wrap_lines=True)
            layout = Layout(body)

            from prompt_toolkit.application import Application as PTKApp
            app: PTKApp[None] = Application(
                layout=layout,
                key_bindings=self.bindings,
                full_screen=False,
                enable_page_navigation_bindings=False
            )

            result = app.run()
            return result if isinstance(result, NavigationResult) else NavigationResult(action="quit")

        except Exception as e:
            self.console.print(f"[red]Navigation error: {e}[/red]")
            return NavigationResult(action="quit")

    def update_results(self, results: list) -> None:
        """Update displayed results"""
        self.results = results
        self.current_index = 0

    def show_filter_prompt(self) -> Optional[int]:
        """Show time filter prompt"""
        self.console.print("\n[yellow]Time filter options:[/yellow]")
        self.console.print("  1d = Past 1 day")
        self.console.print("  3d = Past 3 days  (default)")
        self.console.print("  1w = Past 1 week")
        self.console.print("  1m = Past 1 month")
        self.console.print("  all = All time")

        choice = input("\nSelect [3d]: ").strip().lower() or "3d"

        time_map = {
            "1d": 1,
            "3d": 3,
            "1w": 7,
            "1m": 30,
            "all": None
        }

        return time_map.get(choice, 3)

    def display_session(self, session_id: str, file_path: str) -> None:
        """Display full session content"""
        try:
            from pathlib import Path
            session_path = Path(file_path)

            if not session_path.exists():
                self.console.print(f"[red]Session not found: {file_path}[/red]")
                return

            with open(session_path) as f:
                content = f.read()
                self.console.print(f"\n[bold]Session: {session_id}[/bold]")
                self.console.print(f"[dim]File: {file_path}[/dim]\n")
                self.console.print(content[:5000])  # Show first 5000 chars
                if len(content) > 5000:
                    self.console.print("\n[dim]... (truncated)[/dim]")

        except Exception as e:
            self.console.print(f"[red]Error displaying session: {e}[/red]")

    def resume_session(self, session_id: str, file_path: str, working_directory: str) -> None:
        """
        Resume a Claude Code session by:
        1. Decoding the working directory (Claude stores paths with - instead of /)
        2. Changing to the working directory
        3. Executing 'claude --resume <session_id>'

        This uses os.execvp to replace the current process with Claude Code.

        Note: We trust the data and decode at point of use (not validation point).
        """
        try:
            import os
            import re
            from pathlib import Path

            # Decode at point of use: working_directory only
            # (file_path is kept as-is since it's used by Claude, not us)
            def decode_path(path_str: str) -> str:
                """Decode paths where / is replaced with -
                Example: -Users-tryk-leGen → /Users/tryk/leGen
                """
                if not path_str:
                    return path_str

                if path_str.startswith('-'):
                    decoded = '/' + path_str[1:]
                    return re.sub(r'-+', '/', decoded)

                return path_str

            # Decode working directory (where to CD before resume)
            decoded_work_dir = decode_path(working_directory)
            work_path = Path(decoded_work_dir).expanduser()

            # Check working directory exists
            if not work_path.exists():
                self.console.print(f"[red]Error: Working directory not found[/red]")
                self.console.print(f"[dim]Encoded: {working_directory}[/dim]")
                self.console.print(f"[dim]Decoded: {decoded_work_dir}[/dim]")
                self.console.print(f"[yellow]Tip: The session may have been created in a different context[/yellow]")
                return

            # Change to working directory
            self.console.print(f"\n[cyan]📁 Changing to directory: {decoded_work_dir}[/cyan]")
            os.chdir(str(work_path))

            # Resume session in Claude Code
            self.console.print(f"[cyan]🚀 Resuming session: {session_id}[/cyan]\n")

            # Execute claude --resume which replaces this process
            # Claude will handle finding the session file from here
            os.execvp('claude', ['claude', '--resume', session_id])

        except FileNotFoundError:
            self.console.print("[red]Error: 'claude' command not found[/red]")
            self.console.print("[dim]Make sure Claude Code is installed and in your PATH[/dim]")
        except Exception as e:
            self.console.print(f"[red]Error resuming session: {e}[/red]")

    def show_preview_modal(self, result: dict) -> None:
        """Display selected result in a formatted preview modal"""
        try:
            from rich.panel import Panel
            import sys

            session_id = result.get('session_id', 'Unknown')
            file_path = result.get('file_path', '')
            content = result.get('content_preview', '')
            score = result.get('score', 0.0)

            # Create formatted panel with metadata
            panel_content = f"""[bold cyan]Session ID:[/bold cyan] {session_id}
[bold cyan]Score:[/bold cyan] {score:.2%}
[bold cyan]Location:[/bold cyan] {file_path}

[bold]Preview:[/bold]
{content}
"""

            panel = Panel(
                panel_content,
                title=f"[bold cyan]Session Preview[/bold cyan]",
                subtitle="[dim]Press Enter to continue...[/dim]",
                expand=False
            )

            self.console.print(panel)

            # Wait for user input (works in all terminal contexts)
            try:
                input()
            except (EOFError, KeyboardInterrupt):
                pass

        except Exception as e:
            self.console.print(f"[red]Error showing preview: {e}[/red]")

    def is_active(self) -> bool:
        """Check if TUI is still active"""
        return self.active
