"""
Example usage of ConversationTreeVisualizer with real JSONL data.

This demonstrates loading a Claude conversation from JSONL and visualizing it.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from riff.graph.models import Message, Thread, Session, MessageType, ThreadType
from riff.graph.visualizer import visualize_session


def load_jsonl(jsonl_path: Path) -> List[Dict[str, Any]]:
    """
    Load JSONL file into list of message dictionaries.

    Args:
        jsonl_path: Path to JSONL file

    Returns:
        List of message dictionaries
    """
    messages = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))
    return messages


def extract_message_content(msg_data: Dict[str, Any]) -> str:
    """
    Extract text content from message data.

    Handles different message formats:
    - Simple string message
    - Structured message with role/content
    - Message with content array
    """
    msg = msg_data.get('message', {})

    # Handle string messages
    if isinstance(msg, str):
        return msg

    # Handle structured messages
    if isinstance(msg, dict):
        # Check for content array (assistant messages)
        if 'content' in msg and isinstance(msg['content'], list):
            text_parts = []
            for item in msg['content']:
                if isinstance(item, dict) and item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
            return '\n'.join(text_parts)

        # Check for direct content string
        if 'content' in msg and isinstance(msg['content'], str):
            return msg['content']

        # Fallback to role info
        role = msg.get('role', 'unknown')
        return f"[{role} message]"

    return "[empty message]"


def parse_message_type(msg_data: Dict[str, Any]) -> MessageType:
    """
    Parse message type from JSONL data.

    Args:
        msg_data: Raw message dictionary

    Returns:
        MessageType enum value
    """
    msg_type = msg_data.get('type', 'user')

    type_map = {
        'user': MessageType.USER,
        'assistant': MessageType.ASSISTANT,
        'system': MessageType.SYSTEM,
        'summary': MessageType.SUMMARY,
        'file-history-snapshot': MessageType.FILE_HISTORY_SNAPSHOT,
    }

    return type_map.get(msg_type, MessageType.USER)


def build_simple_session(jsonl_path: Path) -> Session:
    """
    Build a simple Session from JSONL file.

    This creates a basic session without advanced thread detection.
    For full DAG analysis, use ConversationDAG class.

    Args:
        jsonl_path: Path to JSONL file

    Returns:
        Session object
    """
    # Load raw data
    raw_messages = load_jsonl(jsonl_path)

    if not raw_messages:
        raise ValueError(f"No messages found in {jsonl_path}")

    session_id = raw_messages[0].get('sessionId', 'unknown')

    # Convert to Message objects
    messages = []
    for raw_msg in raw_messages:
        msg = Message(
            uuid=raw_msg['uuid'],
            parent_uuid=raw_msg.get('parentUuid'),
            type=parse_message_type(raw_msg),
            content=extract_message_content(raw_msg),
            timestamp=raw_msg.get('timestamp', datetime.now().isoformat()),
            session_id=session_id,
            is_sidechain=raw_msg.get('isSidechain', False)
        )
        messages.append(msg)

    # Simple thread detection: treat as single main thread
    # (For advanced analysis, use ConversationDAG)
    main_thread = Thread(
        thread_id="main",
        messages=messages,
        thread_type=ThreadType.MAIN
    )

    session = Session(
        session_id=session_id,
        messages=messages,
        threads=[main_thread],
        orphans=[]
    )

    return session


def main():
    """
    Example: Load and visualize a real conversation.

    Usage:
        python -m riff.graph.example_usage /path/to/session.jsonl
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m riff.graph.example_usage <session.jsonl>")
        print()
        print("Example:")
        print("  python -m riff.graph.example_usage ~/.claude/projects/*/session-id.jsonl")
        sys.exit(1)

    jsonl_path = Path(sys.argv[1])

    if not jsonl_path.exists():
        print(f"Error: File not found: {jsonl_path}")
        sys.exit(1)

    print(f"Loading session from: {jsonl_path}")
    print()

    # Load session
    session = build_simple_session(jsonl_path)

    print(f"Session ID: {session.session_id}")
    print(f"Total messages: {session.message_count}")
    print(f"Threads: {session.thread_count}")
    print()
    print("=" * 80)
    print("Conversation Tree:")
    print("=" * 80)
    print()

    # Visualize
    tree = visualize_session(session, max_preview_length=80)
    print(tree)


if __name__ == "__main__":
    main()
