# Copyright 2024 NabiaTech
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Welcome banner for first-time riff users.

Displays a friendly welcome message on first run only, then updates
the configuration to remember that the banner has been shown.
"""

from pathlib import Path
from typing import Optional
import toml

from rich.console import Console

console = Console()


def show_welcome_if_first_run() -> None:
    """Show welcome banner on first run only.

    Checks if ~/.config/nabi/riff.toml exists and has 'seen_welcome' flag.
    If not present, displays the welcome banner and updates the config.
    Handles missing config gracefully.
    """
    config_path = Path.home() / ".config" / "nabi" / "riff.toml"

    # Check if we've already shown welcome
    try:
        if config_path.exists():
            config = toml.load(config_path)
            if config.get("ui", {}).get("seen_welcome", False):
                return  # Already shown, skip
    except Exception:
        pass  # Config doesn't exist or can't be parsed, show welcome

    # Display banner
    banner = """
[bold cyan]╭─ Riff CLI - Teaching-First Claude Conversation Tool ─╮[/bold cyan]
[cyan]│                                                          │[/cyan]
[cyan]│[/cyan] [yellow]Quick Start[/yellow]
[cyan]│[/cyan]   [green]riff scan ~/path/to/sessions/[/green]    Scan for JSONL issues
[cyan]│[/cyan]   [green]riff fix session.jsonl[/green]           Repair conversations
[cyan]│[/cyan]   [green]riff tui ~/path/to/sessions/[/green]    Interactive browsing
[cyan]│[/cyan]   [green]riff --help[/green]                     Show all commands
[cyan]│[/cyan]
[cyan]│[/cyan] [yellow]First time?[/yellow] Try: [green]riff tui ~/.claude/projects/[/green]
[cyan]│                                                          │[/cyan]
[bold cyan]╰──────────────────────────────────────────────────────╯[/bold cyan]
"""
    console.print(banner)

    # Mark as seen in config
    _mark_welcome_seen(config_path)


def disable_welcome_banner() -> None:
    """Mark welcome banner as seen without displaying it.

    Used when --no-banner flag is provided.
    """
    config_path = Path.home() / ".config" / "nabi" / "riff.toml"
    _mark_welcome_seen(config_path)


def _mark_welcome_seen(config_path: Path) -> None:
    """Update config to mark welcome as seen.

    Creates the config file if it doesn't exist, and adds or updates
    the [ui] section with seen_welcome = true.

    Args:
        config_path: Path to the TOML config file
    """
    try:
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create empty dict
        config: dict = {}
        if config_path.exists():
            try:
                config = toml.load(config_path)
            except Exception:
                config = {}

        # Update or create [ui] section
        if "ui" not in config:
            config["ui"] = {}
        config["ui"]["seen_welcome"] = True

        # Write back to file
        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config, f)
    except Exception as e:
        # Graceful failure - don't crash if we can't update config
        console.print(f"[dim]Note: Could not update config ({e})[/dim]")
