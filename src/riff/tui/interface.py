"""Abstract TUI interface for modular implementation"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NavigationResult:
    """Result from navigation: action taken and current state"""
    action: str  # 'next', 'prev', 'open', 'filter', 'quit'
    selected_index: Optional[int] = None
    filter_days: Optional[int] = None  # For 'f' filter action
    session_id: Optional[str] = None  # For 'open' action


class InteractiveTUI(ABC):
    """
    Abstract interface for interactive TUI implementations

    Implementations must handle:
    - vim-style navigation (j/k/g/G)
    - content preview and display
    - time-based filtering
    - session opening/viewing
    """

    @abstractmethod
    def navigate(self) -> NavigationResult:
        """
        Start interactive navigation loop

        Returns NavigationResult when user exits or selects action
        """
        pass

    @abstractmethod
    def update_results(self, results: list) -> None:
        """Update displayed results"""
        pass

    @abstractmethod
    def show_filter_prompt(self) -> Optional[int]:
        """
        Show time filter prompt

        Returns:
            int: number of days (1, 3, 7, 30, etc) or None to cancel
        """
        pass

    @abstractmethod
    def display_session(self, session_id: str, file_path: str) -> None:
        """Display full session content"""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if TUI is still active"""
        pass


class TUIConfig:
    """Configuration for TUI behavior"""

    def __init__(self):
        self.colors_enabled = True
        self.show_line_numbers = True
        self.wrap_text = True
        self.max_preview_lines = 10
        self.vim_keys_enabled = True
