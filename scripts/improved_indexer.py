#!/usr/bin/env python3
"""
Improved Claude Session Indexer
Extracts meaningful conversation content instead of hook output
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime


def is_hook_message(text: str) -> bool:
    """Detect if message is hook/system output"""
    hook_patterns = [
        r'PreToolUse:',
        r'PostToolUse:',
        r'hook_wrapper\.sh',
        r'completed successfully',
        r'Running.*\.\.\.',
        r'Conversation compacted',
        r'Session interrupted',
        r'Checkpoint saved:',
        r'\[/Users/.*/hooks/',
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in hook_patterns)


def extract_meaningful_content(session_file: Path) -> Dict[str, Any]:
    """
    Extract MEANINGFUL conversation content from Claude session

    Priority:
    1. User queries (what they asked)
    2. Assistant responses (what Claude answered)
    3. Filter out hook/system messages
    4. Create intelligent preview snippets
    """
    user_messages = []
    assistant_messages = []
    metadata = {
        'session_id': session_file.stem,
        'file_path': str(session_file),
        'working_directory': '',
        'session_timestamp': None  # Will be populated from JSONL
    }

    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                try:
                    data = json.loads(line.strip())

                    # Extract timestamp from first line (all lines should have it)
                    if line_num == 0 and 'timestamp' in data:
                        metadata['session_timestamp'] = data['timestamp']

                    # Extract working directory
                    if 'cwd' in data:
                        metadata['working_directory'] = data['cwd']

                    # Skip system messages (hook output)
                    if data.get('type') == 'system':
                        continue

                    # Skip if no message field
                    if 'message' not in data:
                        continue

                    message = data['message']
                    msg_type = data.get('type', '')

                    # Extract content from message
                    content_field = message.get('content')
                    if not content_field:
                        continue

                    # Handle content - can be string or array
                    text_parts = []
                    if isinstance(content_field, str):
                        text_parts.append(content_field)
                    elif isinstance(content_field, list):
                        for item in content_field:
                            if isinstance(item, dict):
                                # Extract text from text blocks
                                if item.get('type') == 'text' and 'text' in item:
                                    text_parts.append(item['text'])
                                # Skip tool_use, tool_result, etc.
                            elif isinstance(item, str):
                                text_parts.append(item)

                    # Combine text parts
                    full_text = ' '.join(text_parts).strip()

                    # Skip if empty or hook message
                    if not full_text or is_hook_message(full_text):
                        continue

                    # Extract by message type
                    if msg_type == 'user':
                        if len(full_text) > 10:  # Skip tiny messages
                            user_messages.append(full_text)

                    elif msg_type == 'assistant':
                        if len(full_text) > 20:  # Skip tiny responses
                            assistant_messages.append(full_text)

                except (json.JSONDecodeError, KeyError):
                    continue

        # Build intelligent content for embedding
        content_parts = []

        # Add user queries (what they were looking for)
        for msg in user_messages[:5]:  # First 5 user messages
            content_parts.append(f"User asked: {msg}")

        # Add assistant responses
        for msg in assistant_messages[:5]:  # First 5 assistant responses
            content_parts.append(f"Assistant responded: {msg}")

        full_content = " ".join(content_parts)

        # Create intelligent preview (not just first 500 chars)
        preview_parts = []

        # Most recent user query
        if user_messages:
            last_user = user_messages[-1][:200]
            preview_parts.append(f"Last query: {last_user}")

        # First user query (what session started with)
        if user_messages and len(user_messages) > 1:
            first_user = user_messages[0][:200]
            preview_parts.append(f"Started with: {first_user}")

        # Sample of assistant response
        if assistant_messages:
            sample_response = assistant_messages[0][:200]
            preview_parts.append(f"Response: {sample_response}")

        content_preview = " | ".join(preview_parts) if preview_parts else full_content[:500]

        return {
            'content': full_content,
            'preview': content_preview,
            'metadata': metadata,
            'stats': {
                'user_messages': len(user_messages),
                'assistant_messages': len(assistant_messages)
            }
        }

    except Exception as e:
        print(f"❌ Error processing {session_file}: {e}")
        return None


def index_session_improved(client: QdrantClient, model: SentenceTransformer,
                          session_file: Path, collection_name: str = "claude_sessions") -> bool:
    """Index session with improved content extraction"""

    session_data = extract_meaningful_content(session_file)
    if not session_data or not session_data['content']:
        print(f"⏭️  Skipped {session_file.name} (no meaningful content)")
        return False

    # Create embedding
    embedding = model.encode(session_data['content']).tolist()

    # Create point
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=embedding,
        payload={
            'session_id': session_data['metadata']['session_id'],
            'file_path': session_data['metadata']['file_path'],
            'working_directory': session_data['metadata']['working_directory'],
            'content_preview': session_data['preview'],
            'user_message_count': session_data['stats']['user_messages'],
            'assistant_message_count': session_data['stats']['assistant_messages'],
            'session_timestamp': session_data['metadata']['session_timestamp'],
            'indexed_at': datetime.now().isoformat()
        }
    )

    # Upsert
    try:
        client.upsert(collection_name=collection_name, points=[point])
        print(f"✅ Indexed: {session_file.name} ({session_data['stats']['user_messages']} user, "
              f"{session_data['stats']['assistant_messages']} assistant msgs)")
        return True
    except Exception as e:
        print(f"❌ Failed {session_file.name}: {e}")
        return False


def main():
    """Re-index Claude sessions with improved extraction"""
    print("🚀 Improved Claude Session Indexer\n")

    # Setup
    client = QdrantClient(url="http://localhost:6333")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Find sessions
    claude_dir = Path.home() / ".claude" / "projects"
    sessions = list(claude_dir.glob("**/*.jsonl"))

    print(f"📁 Found {len(sessions)} session files\n")

    # Index
    success_count = 0
    for session_file in sessions:
        if index_session_improved(client, model, session_file):
            success_count += 1

    print(f"\n✅ Successfully indexed {success_count}/{len(sessions)} sessions")


if __name__ == "__main__":
    main()
