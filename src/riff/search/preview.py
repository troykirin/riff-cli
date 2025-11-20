"""Rich content preview and vim-style navigation for search results"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


@dataclass
class ContentPreview:
    """Display and navigate search results with rich formatting"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.current_index = 0
        self.results: list[Any] = []

    def display_search_results(
        self,
        results: list,
        query: str,
        show_snippets: bool = True
    ) -> None:
        """Display search results in a formatted table"""
        if not results:
            self.console.print(f"[yellow]No results found for: {query}[/yellow]")
            return

        self.results = results

        # Header
        self.console.print(f"\n[bold cyan]🔍 Search Results ({len(results)} found)[/bold cyan]")
        self.console.print(f"[dim]Query: {query}[/dim]\n")

        # Results table
        table = Table(title="", show_header=True, header_style="bold magenta")
        table.add_column("Idx", style="dim", width=4)
        table.add_column("Session ID", style="cyan", width=15)
        table.add_column("Score", justify="right", width=8)
        table.add_column("Directory", style="blue", width=30)

        for i, result in enumerate(results, 1):
            score_color = "green" if result.score > 0.8 else "yellow" if result.score > 0.5 else "red"
            table.add_row(
                str(i),
                result.session_id[:15],
                f"[{score_color}]{result.score:.3f}[/{score_color}]",
                result.working_directory[-30:] if len(result.working_directory) > 30 else result.working_directory
            )

        self.console.print(table)

        # Show snippets
        if show_snippets:
            self.console.print("\n[bold]Content Previews:[/bold]")
            for i, result in enumerate(results[:3], 1):  # Show first 3 in detail
                preview_text = result.content_preview[:200] + "..." if len(result.content_preview) > 200 else result.content_preview
                panel = Panel(
                    Text(preview_text, style="dim white"),
                    title=f"[{i}] {result.session_id}",
                    border_style="blue"
                )
                self.console.print(panel)

        # Note: Interactive TUI will launch after this display
        # (No help text here - TUI provides its own)

    def display_full_content(self, result) -> None:
        """Display full content of a result"""
        self.console.clear()
        self.console.print(f"[bold cyan]Session: {result.session_id}[/bold cyan]")
        self.console.print(f"[dim]Directory: {result.working_directory}[/dim]")
        self.console.print(f"[dim]File: {result.file_path}[/dim]\n")

        # Display content with syntax highlighting if it looks like JSON
        content = result.content_preview
        if content.startswith('{') or content.startswith('['):
            from rich.syntax import Syntax
            syntax = Syntax(content, "json", theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            self.console.print(content)

        self.console.print("\n[dim]Press 'q' to return to results[/dim]")

    def display_help(self) -> None:
        """Display keyboard shortcuts"""
        help_text = """
[bold cyan]Riff Navigation Help[/bold cyan]

[bold yellow]Search Results:[/bold yellow]
  j/k        Navigate up/down through results
  g/G        Go to first/last result
  Enter      Open full content preview
  n/N        Next/previous match
  /          Search within results
  q          Quit

[bold yellow]Content View:[/bold yellow]
  j/k        Scroll up/down
  g/G        Go to start/end
  /          Search in content
  q          Back to results

[bold yellow]General:[/bold yellow]
  h/?        Show this help
  Ctrl+C     Exit
"""
        panel = Panel(help_text, title="[bold]Help[/bold]", border_style="green")
        self.console.print(panel)

    def create_interactive_navigator(self) -> VimNavigator:
        """Create an interactive vim-style navigator"""
        return VimNavigator(self.results, self.console)


class VimNavigator:
    """Interactive vim-style navigation for search results"""

    def __init__(self, results: list, console: Optional[Console] = None):
        self.results = results
        self.console = console or Console()
        self.current_index = 0
        self.search_filter = ""

    def navigate(self) -> Optional[dict]:
        """Start interactive navigation loop"""
        # This is a basic structure; full implementation would need
        # proper terminal event handling (e.g., with prompt_toolkit)
        self.display_current()
        return self.results[self.current_index] if self.results else None

    def next(self) -> None:
        """Move to next result"""
        if self.results:
            self.current_index = (self.current_index + 1) % len(self.results)

    def prev(self) -> None:
        """Move to previous result"""
        if self.results:
            self.current_index = (self.current_index - 1) % len(self.results)

    def first(self) -> None:
        """Jump to first result"""
        self.current_index = 0

    def last(self) -> None:
        """Jump to last result"""
        if self.results:
            self.current_index = len(self.results) - 1

    def display_current(self) -> None:
        """Display current result"""
        if self.current_index < len(self.results):
            result = self.results[self.current_index]
            self.console.clear()
            panel = Panel(
                f"[cyan]{result.session_id}[/cyan]\n"
                f"[dim]{result.working_directory}[/dim]\n\n"
                f"[white]{result.content_preview}[/white]",
                title=f"[bold][{self.current_index + 1}/{len(self.results)}][/bold]",
                border_style="cyan"
            )
            self.console.print(panel)
