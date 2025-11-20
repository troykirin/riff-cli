"""
Modular TUI abstractions for riff

Architecture:
- TUI Interface (abstract): Defines what a TUI must provide
- Implementation: prompt_toolkit (MVP), later replaceable with Rust/other
- Not tied to any specific library

This allows swapping implementations (e.g., to tui-types) without changing calling code.
"""

from .interface import InteractiveTUI, NavigationResult
from .prompt_toolkit_impl import PromptToolkitTUI

__all__ = ["InteractiveTUI", "NavigationResult", "PromptToolkitTUI"]
