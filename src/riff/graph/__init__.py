"""
Conversation DAG analysis module for riff-cli.

This module provides semantic DAG construction from Claude conversation JSONL files,
enabling analysis of conversation structure, thread detection, and orphan identification.

Key components:
- models: Data structures (Message, Thread, Session)
- loaders: JSONL file loading and parsing
- dag: Graph construction and structural analysis
- visualizer: ASCII tree visualization
- analysis: Semantic analysis and corruption scoring
- persistence: JSONL repair writer with undo/rollback
"""

from .models import Message, Thread, Session, MessageType, ThreadType
from .loaders import ConversationStorage, JSONLLoader
from .dag import ConversationDAG
from .visualizer import (
    ConversationTreeVisualizer,
    LineItem,
    visualize_session,
    flatten_session_for_navigation,
)
from .analysis import (
    ThreadDetector,
    CorruptionScorer,
    SemanticAnalyzer,
    analyze_session_semantics,
    detect_orphans_with_scoring,
)
from .persistence import (
    RepairOperation,
    RepairSnapshot,
    JSONLRepairWriter,
    create_repair_writer,
)

# Optional TUI import (requires prompt_toolkit)
try:
    from .tui import ConversationGraphNavigator
    _has_tui = True
except ImportError:
    _has_tui = False
    ConversationGraphNavigator = None

__all__ = [
    # Core models
    "Message",
    "Thread",
    "Session",
    "MessageType",
    "ThreadType",
    # Storage
    "ConversationStorage",
    "JSONLLoader",
    # DAG construction
    "ConversationDAG",
    # Visualization
    "ConversationTreeVisualizer",
    "LineItem",
    "visualize_session",
    "flatten_session_for_navigation",
    # Semantic analysis
    "ThreadDetector",
    "CorruptionScorer",
    "SemanticAnalyzer",
    "analyze_session_semantics",
    "detect_orphans_with_scoring",
    # Persistence and repair
    "RepairOperation",
    "RepairSnapshot",
    "JSONLRepairWriter",
    "create_repair_writer",
    # Interactive TUI (optional)
    "ConversationGraphNavigator",
]
