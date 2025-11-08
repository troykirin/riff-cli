"""Subprocess handler for riff-dag-tui lifecycle management"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional
from rich.console import Console

console = Console()


class RiffDagTUIHandler:
    """Manages riff-dag-tui subprocess lifecycle and binary discovery.

    Responsibilities:
    - Discover riff-dag-tui binary in standard locations
    - Launch subprocess with JSONL input
    - Handle process lifecycle and error cases
    - Provide helpful error messages
    """

    def __init__(self):
        """Initialize handler and attempt binary discovery."""
        self.binary_path: Optional[Path] = None
        self._discover_binary()

    def _discover_binary(self) -> None:
        """Discover riff-dag-tui binary in standard locations.

        Searches in order:
        1. ~/.cargo/bin/riff-dag-tui (Cargo install)
        2. ./target/release/riff-dag-tui (Local build)
        3. System PATH
        4. ../nabi-tui/target/release/dag-tui (nabi-tui as fallback)

        Raises:
            FileNotFoundError: If binary not found in any location
        """
        candidates = [
            Path.home() / ".cargo" / "bin" / "riff-dag-tui",
            Path("/Users/tryk/nabia/tui/production/riff-dag-tui/target/release/riff-dag-tui"),
            Path("/home/tryk/nabia/tui/production/riff-dag-tui/target/release/riff-dag-tui"),
        ]

        # Check candidates
        for candidate in candidates:
            if candidate.exists():
                self.binary_path = candidate
                console.print(f"[dim]Found riff-dag-tui at: {candidate}[/dim]")
                return

        # Try PATH search
        binary_in_path = shutil.which("riff-dag-tui")
        if binary_in_path:
            self.binary_path = Path(binary_in_path)
            console.print(f"[dim]Found riff-dag-tui in PATH: {binary_in_path}[/dim]")
            return

        # Try dag-tui (nabi-tui)
        dag_tui_candidate = shutil.which("dag-tui")
        if dag_tui_candidate:
            console.print(
                "[yellow]Warning:[/yellow] Found dag-tui (nabi-tui) but not riff-dag-tui"
            )

        raise FileNotFoundError(
            "riff-dag-tui binary not found. Install with:\n"
            "  cargo install --path ~/nabia/tui/production/riff-dag-tui\n"
            "Or build locally:\n"
            "  cd ~/nabia/tui/production/riff-dag-tui && cargo build --release"
        )

    def launch(self, jsonl_path: Path) -> int:
        """Launch riff-dag-tui subprocess with JSONL input.

        Args:
            jsonl_path: Path to JSONL file with DAG nodes and edges

        Returns:
            Exit code from riff-dag-tui process

        Raises:
            FileNotFoundError: If binary not found
            OSError: If subprocess launch fails
        """
        if not self.binary_path:
            self._discover_binary()

        if not jsonl_path.exists():
            console.print(f"[red]Error: Input file not found: {jsonl_path}[/red]")
            return 1

        console.print(f"[cyan]Launching interactive DAG viewer...[/cyan]")
        console.print(f"[dim]Input: {jsonl_path}[/dim]\n")

        try:
            # Launch subprocess, letting it take over TTY
            result = subprocess.run(
                [str(self.binary_path), "--input", str(jsonl_path)],
                capture_output=False,  # Let riff-dag-tui control terminal
            )
            return result.returncode

        except OSError as e:
            console.print(
                f"[red]Error launching riff-dag-tui:[/red] {e}\n"
                f"Binary: {self.binary_path}\n"
                f"Input: {jsonl_path}"
            )
            return 1

    def verify_installed(self) -> bool:
        """Check if riff-dag-tui is available.

        Returns:
            True if binary found and accessible, False otherwise
        """
        try:
            self._discover_binary()
            return self.binary_path is not None and self.binary_path.exists()
        except FileNotFoundError:
            return False

    def get_installation_hint(self) -> str:
        """Get helpful installation instructions.

        Returns:
            Formatted installation hint message
        """
        return (
            "riff-dag-tui not found. Install with:\n"
            "  [bold]cargo install --path ~/nabia/tui/production/riff-dag-tui[/bold]\n\n"
            "Or build locally:\n"
            "  [bold]cd ~/nabia/tui/production/riff-dag-tui && cargo build --release[/bold]\n\n"
            "Binary location: [dim]~/.cargo/bin/riff-dag-tui[/dim]"
        )
