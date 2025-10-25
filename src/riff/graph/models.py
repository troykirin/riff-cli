"""
Data models for conversation DAG analysis.

Provides type-safe dataclasses representing messages, threads, and sessions
with proper Python 3.13+ type annotations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class MessageType(str, Enum):
    """Types of messages in Claude conversations."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    SUMMARY = "summary"
    FILE_HISTORY_SNAPSHOT = "file-history-snapshot"


class ThreadType(str, Enum):
    """Types of conversation threads."""

    MAIN = "main"
    SIDE_DISCUSSION = "side_discussion"
    ORPHANED = "orphaned"


@dataclass
class Message:
    """
    Represents a single message in a conversation DAG.

    Attributes:
        uuid: Unique identifier for this message
        parent_uuid: UUID of parent message (None for root messages)
        type: Message type (user/assistant/system/etc)
        content: Message content (text or structured data)
        timestamp: ISO8601 timestamp
        session_id: Session this message belongs to
        is_sidechain: Whether this is a sidechain/subagent message
        semantic_topic: Optional semantic topic classification
        thread_id: Optional thread identifier (computed)
        is_orphaned: Whether this message is disconnected from main tree
        corruption_score: Measure of structural issues (0.0-1.0)
        metadata: Additional message metadata from JSONL
    """

    uuid: str
    parent_uuid: Optional[str]
    type: MessageType
    content: str
    timestamp: str
    session_id: str
    is_sidechain: bool = False
    semantic_topic: Optional[str] = None
    thread_id: Optional[str] = None
    is_orphaned: bool = False
    corruption_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate message after initialization."""
        if self.corruption_score < 0.0 or self.corruption_score > 1.0:
            raise ValueError(f"corruption_score must be between 0.0 and 1.0, got {self.corruption_score}")

        # Ensure type is a MessageType enum
        if isinstance(self.type, str):
            self.type = MessageType(self.type)


@dataclass
class Thread:
    """
    Represents a coherent thread of conversation.

    A thread is a connected sequence of messages, which can be:
    - Main thread: The primary conversation flow
    - Side discussion: Tangential conversations (e.g., subagent execution)
    - Orphaned: Disconnected messages with no path to root

    Attributes:
        thread_id: Unique identifier for this thread
        messages: Ordered list of messages in this thread
        thread_type: Classification of thread type
        semantic_topic: Optional semantic topic for this thread
        corruption_score: Aggregate corruption score for thread
        parent_thread_id: Optional parent thread (for side discussions)
    """

    thread_id: str
    messages: list[Message]
    thread_type: ThreadType
    semantic_topic: Optional[str] = None
    corruption_score: float = 0.0
    parent_thread_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate thread after initialization."""
        if not self.messages:
            raise ValueError("Thread must contain at least one message")

        if self.corruption_score < 0.0 or self.corruption_score > 1.0:
            raise ValueError(f"corruption_score must be between 0.0 and 1.0, got {self.corruption_score}")

        # Ensure thread_type is a ThreadType enum
        if isinstance(self.thread_type, str):
            self.thread_type = ThreadType(self.thread_type)

    @property
    def message_count(self) -> int:
        """Number of messages in this thread."""
        return len(self.messages)

    @property
    def first_message(self) -> Message:
        """First message in thread (chronologically)."""
        return self.messages[0]

    @property
    def last_message(self) -> Message:
        """Last message in thread (chronologically)."""
        return self.messages[-1]


@dataclass
class Session:
    """
    Represents a complete conversation session.

    A session contains:
    - All messages from a Claude conversation
    - Organized into threads (main + side discussions)
    - Identified orphaned messages
    - Computed corruption metrics

    Attributes:
        session_id: Unique identifier for this session
        messages: All messages in session (flat list)
        threads: Organized threads (main + side discussions)
        orphans: Disconnected message threads
        corruption_score: Overall session corruption score
        metadata: Additional session metadata
    """

    session_id: str
    messages: list[Message]
    threads: list[Thread]
    orphans: list[Thread]
    corruption_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate session after initialization."""
        if self.corruption_score < 0.0 or self.corruption_score > 1.0:
            raise ValueError(f"corruption_score must be between 0.0 and 1.0, got {self.corruption_score}")

    @property
    def message_count(self) -> int:
        """Total number of messages in session."""
        return len(self.messages)

    @property
    def thread_count(self) -> int:
        """Number of threads (excluding orphans)."""
        return len(self.threads)

    @property
    def orphan_count(self) -> int:
        """Number of orphaned threads."""
        return len(self.orphans)

    @property
    def main_thread(self) -> Optional[Thread]:
        """The main conversation thread, if it exists."""
        for thread in self.threads:
            if thread.thread_type == ThreadType.MAIN:
                return thread
        return None

    @property
    def side_threads(self) -> list[Thread]:
        """All side discussion threads."""
        return [t for t in self.threads if t.thread_type == ThreadType.SIDE_DISCUSSION]

    def get_thread_by_id(self, thread_id: str) -> Optional[Thread]:
        """Retrieve a thread by its ID."""
        for thread in self.threads + self.orphans:
            if thread.thread_id == thread_id:
                return thread
        return None

    def get_message_by_uuid(self, uuid: str) -> Optional[Message]:
        """Retrieve a message by its UUID."""
        for message in self.messages:
            if message.uuid == uuid:
                return message
        return None
