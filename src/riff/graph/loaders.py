"""
Storage abstraction and JSONL loader for conversation data.

Provides abstract base class for conversation storage and concrete
implementation for Claude's JSONL conversation format.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from .models import Message, MessageType, Session


class ConversationStorage(ABC):
    """
    Abstract base class for conversation storage backends.

    Defines the interface for loading and persisting conversation data,
    allowing for different storage implementations (JSONL, database, etc).
    """

    @abstractmethod
    def load_messages(self, session_id: str) -> list[Message]:
        """
        Load all messages for a given session.

        Args:
            session_id: Unique identifier for the session

        Returns:
            List of Message objects

        Raises:
            FileNotFoundError: If session does not exist
            ValueError: If session data is corrupted
        """
        pass

    @abstractmethod
    def save_session(self, session: Session) -> None:
        """
        Save a complete session.

        Args:
            session: Session object to persist

        Raises:
            IOError: If save fails
        """
        pass

    @abstractmethod
    def update_message(self, message: Message) -> None:
        """
        Update a single message.

        Args:
            message: Message object with updated data

        Raises:
            ValueError: If message doesn't exist
            IOError: If update fails
        """
        pass


class JSONLLoader(ConversationStorage):
    """
    Loader for Claude's JSONL conversation format.

    Parses JSONL files exported from Claude, handling various message types
    and extracting structured conversation data.

    Attributes:
        conversations_dir: Directory containing JSONL conversation files
    """

    def __init__(self, conversations_dir: Path | str) -> None:
        """
        Initialize JSONL loader.

        Args:
            conversations_dir: Path to directory containing JSONL files
                              (e.g., ~/.claude/projects/-Users-tryk--nabi/)
        """
        self.conversations_dir = Path(conversations_dir)

        if not self.conversations_dir.exists():
            raise FileNotFoundError(f"Conversations directory not found: {self.conversations_dir}")

        if not self.conversations_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.conversations_dir}")

    def _get_session_path(self, session_id: str) -> Path:
        """
        Get the file path for a session ID.

        Args:
            session_id: Session UUID

        Returns:
            Path to JSONL file

        Raises:
            FileNotFoundError: If session file doesn't exist
        """
        session_path = self.conversations_dir / f"{session_id}.jsonl"

        if not session_path.exists():
            raise FileNotFoundError(f"Session file not found: {session_path}")

        return session_path

    def _parse_message_content(self, record: dict) -> str:
        """
        Extract message content from JSONL record.

        Handles various content formats:
        - Direct string content
        - message.content (string or array)
        - summary field for summary messages

        Args:
            record: Parsed JSONL record

        Returns:
            Extracted content string
        """
        # Handle summary messages
        if record.get("type") == "summary":
            return record.get("summary", "")

        # Handle system messages
        if record.get("type") == "system":
            return record.get("content", "")

        # Handle messages with nested message.content
        if "message" in record:
            content = record["message"].get("content", "")

            # Content can be string or array of content blocks
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # Extract text from content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            # Include tool use information
                            tool_name = block.get("name", "unknown")
                            text_parts.append(f"[Tool: {tool_name}]")
                return "\n".join(text_parts)

        return ""

    def _extract_message_type(self, record: dict) -> MessageType:
        """
        Determine message type from JSONL record.

        Args:
            record: Parsed JSONL record

        Returns:
            MessageType enum value
        """
        record_type = record.get("type", "")

        # Map JSONL types to MessageType enum
        type_mapping = {
            "user": MessageType.USER,
            "assistant": MessageType.ASSISTANT,
            "system": MessageType.SYSTEM,
            "summary": MessageType.SUMMARY,
            "file-history-snapshot": MessageType.FILE_HISTORY_SNAPSHOT,
        }

        return type_mapping.get(record_type, MessageType.SYSTEM)

    def load_messages(self, session_id: str) -> list[Message]:
        """
        Load all messages from a JSONL session file.

        Args:
            session_id: Session UUID (filename without .jsonl)

        Returns:
            List of Message objects in order of appearance

        Raises:
            FileNotFoundError: If session file doesn't exist
            ValueError: If JSONL is malformed
        """
        session_path = self._get_session_path(session_id)
        messages: list[Message] = []

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as e:
                        # Log corrupted line but continue processing
                        print(f"Warning: Corrupted JSONL at line {line_num}: {e}")
                        continue

                    # Extract message fields
                    uuid = record.get("uuid")
                    if not uuid:
                        # Skip records without UUID (metadata records)
                        continue

                    parent_uuid = record.get("parentUuid")
                    timestamp = record.get("timestamp", "")
                    is_sidechain = record.get("isSidechain", False)
                    message_type = self._extract_message_type(record)
                    content = self._parse_message_content(record)

                    # Determine corruption score based on structural issues
                    corruption_score = 0.0
                    if not timestamp:
                        corruption_score += 0.2
                    if not content:
                        corruption_score += 0.3

                    # Create message object
                    message = Message(
                        uuid=uuid,
                        parent_uuid=parent_uuid,
                        type=message_type,
                        content=content,
                        timestamp=timestamp,
                        session_id=session_id,
                        is_sidechain=is_sidechain,
                        corruption_score=min(corruption_score, 1.0),
                        metadata=record,  # Preserve full JSONL record
                    )

                    messages.append(message)

        except IOError as e:
            raise ValueError(f"Failed to read session file: {e}")

        return messages

    def save_session(self, session: Session) -> None:
        """
        Save session back to JSONL format.

        Args:
            session: Session to save

        Raises:
            IOError: If write fails

        Note:
            This recreates the JSONL file from the session's message metadata.
            Any modifications to message content will be reflected in the output.
        """
        session_path = self.conversations_dir / f"{session.session_id}.jsonl"

        try:
            with open(session_path, "w", encoding="utf-8") as f:
                for message in session.messages:
                    # Use preserved metadata as base
                    record = message.metadata.copy()

                    # Update fields that may have changed
                    record["uuid"] = message.uuid
                    record["parentUuid"] = message.parent_uuid
                    record["timestamp"] = message.timestamp
                    record["type"] = message.type.value

                    # Write JSONL line
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

        except IOError as e:
            raise IOError(f"Failed to save session: {e}")

    def update_message(self, message: Message) -> None:
        """
        Update a single message in its session file.

        Args:
            message: Message with updated data

        Raises:
            ValueError: If message's session doesn't exist
            IOError: If update fails

        Note:
            This is inefficient for batch updates. Use save_session() instead.
        """
        # Load all messages
        messages = self.load_messages(message.session_id)

        # Find and update target message
        found = False
        for i, msg in enumerate(messages):
            if msg.uuid == message.uuid:
                messages[i] = message
                found = True
                break

        if not found:
            raise ValueError(f"Message {message.uuid} not found in session {message.session_id}")

        # Create temporary session and save
        from .dag import ConversationDAG

        # Build DAG and session
        dag = ConversationDAG(self, message.session_id)
        session = dag.to_session()

        # Save updated session
        self.save_session(session)

    def list_sessions(self) -> list[str]:
        """
        List all available session IDs in the conversations directory.

        Returns:
            List of session IDs (filenames without .jsonl extension)
        """
        session_files = self.conversations_dir.glob("*.jsonl")
        return [f.stem for f in session_files]

    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session file exists.

        Args:
            session_id: Session UUID to check

        Returns:
            True if session file exists, False otherwise
        """
        session_path = self.conversations_dir / f"{session_id}.jsonl"
        return session_path.exists()
