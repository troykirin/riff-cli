"""
SurrealDB schema utilities for conversation storage.

Provides programmatic access to schema definitions, validation helpers,
and data transformation utilities for Phase 6B integration.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ============================================================================
# SCHEMA DICTIONARY: Python representation of SurrealDB schema
# ============================================================================

SCHEMA_DICT: Dict[str, Any] = {
    "version": "1.0.0",
    "namespace": "nabi",
    "database": "conversations",
    "tables": {
        "session": {
            "type": "SCHEMAFULL",
            "fields": {
                "session_id": {
                    "type": "string",
                    "required": True,
                    "unique": True,
                    "description": "Claude session UUID",
                },
                "message_count": {
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "description": "Total messages in session",
                },
                "thread_count": {
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "description": "Total threads in session",
                },
                "corruption_score": {
                    "type": "float",
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "Session-level corruption score (0.0-1.0)",
                },
                "last_updated": {
                    "type": "datetime",
                    "required": True,
                    "description": "Last modification timestamp",
                },
                "created_at": {
                    "type": "datetime",
                    "required": True,
                    "description": "Session creation timestamp",
                },
            },
            "indexes": ["session_id", "last_updated"],
        },
        "thread": {
            "type": "SCHEMAFULL",
            "fields": {
                "session_id": {
                    "type": "string",
                    "required": True,
                    "description": "Parent session ID",
                },
                "thread_type": {
                    "type": "string",
                    "required": True,
                    "allowed_values": ["main", "side_discussion", "orphaned"],
                    "description": "Thread classification",
                },
                "message_count": {
                    "type": "int",
                    "default": 0,
                    "min": 0,
                    "description": "Total messages in thread",
                },
                "topic": {
                    "type": "option<string>",
                    "required": False,
                    "description": "Semantic topic extracted from messages",
                },
                "created_at": {
                    "type": "datetime",
                    "required": True,
                    "description": "Thread creation timestamp",
                },
            },
            "indexes": ["session_id", "thread_type", "session_id,thread_type"],
        },
        "message": {
            "type": "SCHEMAFULL",
            "fields": {
                "session_id": {
                    "type": "string",
                    "required": True,
                    "description": "Parent session ID",
                },
                "message_uuid": {
                    "type": "string",
                    "required": True,
                    "description": "Unique message identifier",
                },
                "parent_uuid": {
                    "type": "option<string>",
                    "required": False,
                    "description": "Parent message UUID (null for roots)",
                },
                "message_type": {
                    "type": "string",
                    "required": True,
                    "allowed_values": ["user", "assistant", "system"],
                    "description": "Message type classification",
                },
                "role": {
                    "type": "string",
                    "required": True,
                    "allowed_values": ["user", "assistant"],
                    "description": "Message role in conversation",
                },
                "content": {
                    "type": "string",
                    "required": True,
                    "searchable": True,
                    "description": "Message content text",
                },
                "timestamp": {
                    "type": "datetime",
                    "required": True,
                    "description": "Message timestamp",
                },
                "thread_id": {
                    "type": "option<string>",
                    "required": False,
                    "description": "Parent thread ID",
                },
                "is_orphaned": {
                    "type": "bool",
                    "default": False,
                    "description": "Whether message lacks valid parent",
                },
                "corruption_score": {
                    "type": "float",
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "Message-level corruption score",
                },
                "created_at": {
                    "type": "datetime",
                    "required": True,
                    "description": "Record creation timestamp",
                },
            },
            "indexes": [
                "message_uuid",
                "session_id",
                "parent_uuid",
                "thread_id",
                "timestamp",
                "is_orphaned",
                "corruption_score",
                "session_id,timestamp",
            ],
            "full_text_indexes": ["content"],
        },
    },
    "relations": {
        "message_parent_of": {
            "from": "message",
            "to": "message",
            "type": "one_to_many",
            "description": "Parent-child relationship in conversation DAG",
        },
        "message_belongs_to_thread": {
            "from": "message",
            "to": "thread",
            "type": "many_to_one",
            "properties": {
                "position": {
                    "type": "int",
                    "min": 0,
                    "description": "Message position within thread",
                }
            },
            "description": "Links messages to their containing thread",
        },
        "thread_belongs_to_session": {
            "from": "thread",
            "to": "session",
            "type": "many_to_one",
            "description": "Links threads to their parent session",
        },
        "session_contains_message": {
            "from": "session",
            "to": "message",
            "type": "one_to_many",
            "description": "Direct session-to-message link for fast queries",
        },
    },
    "analyzers": {
        "message_search": {
            "tokenizers": ["blank", "class"],
            "filters": ["lowercase", "snowball(english)"],
            "description": "Full-text search analyzer for message content",
        }
    },
}


# ============================================================================
# SCHEMA LOADING
# ============================================================================


def get_schema_sql() -> str:
    """
    Load the SQL schema file content.

    Returns:
        str: Complete SQL schema definition
    """
    schema_path = Path(__file__).parent / "schema.sql"
    return schema_path.read_text()


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def validate_session_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate session data against schema.

    Args:
        data: Session data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["session_id", "last_updated", "created_at"]

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate session_id
    if not isinstance(data["session_id"], str) or not data["session_id"]:
        return False, "session_id must be a non-empty string"

    # Validate message_count
    if "message_count" in data:
        if not isinstance(data["message_count"], int) or data["message_count"] < 0:
            return False, "message_count must be a non-negative integer"

    # Validate thread_count
    if "thread_count" in data:
        if not isinstance(data["thread_count"], int) or data["thread_count"] < 0:
            return False, "thread_count must be a non-negative integer"

    # Validate corruption_score
    if "corruption_score" in data:
        if not isinstance(data["corruption_score"], (int, float)):
            return False, "corruption_score must be a number"
        if not 0.0 <= data["corruption_score"] <= 1.0:
            return False, "corruption_score must be between 0.0 and 1.0"

    # Validate timestamps
    for field in ["last_updated", "created_at"]:
        if not isinstance(data[field], (str, datetime)):
            return False, f"{field} must be a datetime or ISO 8601 string"

    return True, None


def validate_message_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate message data against schema.

    Args:
        data: Message data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = [
        "session_id",
        "message_uuid",
        "message_type",
        "role",
        "content",
        "timestamp",
        "created_at",
    ]

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate session_id
    if not isinstance(data["session_id"], str) or not data["session_id"]:
        return False, "session_id must be a non-empty string"

    # Validate message_uuid
    if not isinstance(data["message_uuid"], str) or not data["message_uuid"]:
        return False, "message_uuid must be a non-empty string"

    # Validate message_type
    valid_types = ["user", "assistant", "system"]
    if data["message_type"] not in valid_types:
        return False, f"message_type must be one of {valid_types}"

    # Validate role
    valid_roles = ["user", "assistant"]
    if data["role"] not in valid_roles:
        return False, f"role must be one of {valid_roles}"

    # Validate content
    if not isinstance(data["content"], str):
        return False, "content must be a string"

    # Validate corruption_score
    if "corruption_score" in data:
        if not isinstance(data["corruption_score"], (int, float)):
            return False, "corruption_score must be a number"
        if not 0.0 <= data["corruption_score"] <= 1.0:
            return False, "corruption_score must be between 0.0 and 1.0"

    # Validate is_orphaned
    if "is_orphaned" in data:
        if not isinstance(data["is_orphaned"], bool):
            return False, "is_orphaned must be a boolean"

    # Validate timestamps
    for field in ["timestamp", "created_at"]:
        if not isinstance(data[field], (str, datetime)):
            return False, f"{field} must be a datetime or ISO 8601 string"

    return True, None


def validate_thread_data(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate thread data against schema.

    Args:
        data: Thread data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["session_id", "thread_type", "created_at"]

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate session_id
    if not isinstance(data["session_id"], str) or not data["session_id"]:
        return False, "session_id must be a non-empty string"

    # Validate thread_type
    valid_types = ["main", "side_discussion", "orphaned"]
    if data["thread_type"] not in valid_types:
        return False, f"thread_type must be one of {valid_types}"

    # Validate message_count
    if "message_count" in data:
        if not isinstance(data["message_count"], int) or data["message_count"] < 0:
            return False, "message_count must be a non-negative integer"

    # Validate topic (optional)
    if "topic" in data and data["topic"] is not None:
        if not isinstance(data["topic"], str):
            return False, "topic must be a string or None"

    # Validate created_at
    if not isinstance(data["created_at"], (str, datetime)):
        return False, "created_at must be a datetime or ISO 8601 string"

    return True, None


# ============================================================================
# DATA TRANSFORMATION UTILITIES
# ============================================================================


def prepare_session_record(
    session_id: str,
    message_count: int = 0,
    thread_count: int = 0,
    corruption_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Prepare a session record for SurrealDB insertion.

    Args:
        session_id: Claude session UUID
        message_count: Total messages in session
        thread_count: Total threads in session
        corruption_score: Session-level corruption score

    Returns:
        Dict ready for SurrealDB insertion
    """
    now = datetime.utcnow().isoformat()
    return {
        "session_id": session_id,
        "message_count": message_count,
        "thread_count": thread_count,
        "corruption_score": corruption_score,
        "last_updated": now,
        "created_at": now,
    }


def prepare_message_record(
    session_id: str,
    message_uuid: str,
    message_type: str,
    role: str,
    content: str,
    timestamp: str,
    parent_uuid: Optional[str] = None,
    thread_id: Optional[str] = None,
    is_orphaned: bool = False,
    corruption_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Prepare a message record for SurrealDB insertion.

    Args:
        session_id: Parent session ID
        message_uuid: Unique message identifier
        message_type: Message type (user/assistant/system)
        role: Message role (user/assistant)
        content: Message content text
        timestamp: Message timestamp (ISO 8601)
        parent_uuid: Parent message UUID (optional)
        thread_id: Parent thread ID (optional)
        is_orphaned: Whether message lacks valid parent
        corruption_score: Message-level corruption score

    Returns:
        Dict ready for SurrealDB insertion
    """
    now = datetime.utcnow().isoformat()
    record = {
        "session_id": session_id,
        "message_uuid": message_uuid,
        "message_type": message_type,
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "is_orphaned": is_orphaned,
        "corruption_score": corruption_score,
        "created_at": now,
    }

    # Add optional fields only if provided
    if parent_uuid is not None:
        record["parent_uuid"] = parent_uuid
    if thread_id is not None:
        record["thread_id"] = thread_id

    return record


def prepare_thread_record(
    session_id: str,
    thread_type: str,
    message_count: int = 0,
    topic: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prepare a thread record for SurrealDB insertion.

    Args:
        session_id: Parent session ID
        thread_type: Thread classification (main/side_discussion/orphaned)
        message_count: Total messages in thread
        topic: Semantic topic extracted from messages

    Returns:
        Dict ready for SurrealDB insertion
    """
    now = datetime.utcnow().isoformat()
    record = {
        "session_id": session_id,
        "thread_type": thread_type,
        "message_count": message_count,
        "created_at": now,
    }

    # Add optional fields only if provided
    if topic is not None:
        record["topic"] = topic

    return record


# ============================================================================
# QUERY BUILDERS
# ============================================================================


def build_orphaned_messages_query(session_id: str) -> str:
    """
    Build query to find all orphaned messages in a session.

    Args:
        session_id: Session ID to search

    Returns:
        SurrealQL query string
    """
    return f"""
        SELECT * FROM message
        WHERE session_id = '{session_id}' AND is_orphaned = true
        ORDER BY timestamp DESC;
    """


def build_session_stats_query(session_id: str) -> str:
    """
    Build query to get session statistics.

    Args:
        session_id: Session ID to analyze

    Returns:
        SurrealQL query string
    """
    return f"""
        SELECT
            session_id,
            COUNT() as total_messages,
            math::sum(is_orphaned) as orphaned_count,
            math::avg(corruption_score) as avg_corruption
        FROM message
        WHERE session_id = '{session_id}'
        GROUP ALL;
    """


def build_parent_candidates_query(
    session_id: str, orphan_timestamp: str, limit: int = 5
) -> str:
    """
    Build query to find potential parent candidates for orphaned message.

    Args:
        session_id: Session ID to search
        orphan_timestamp: Timestamp of orphaned message
        limit: Maximum number of candidates to return

    Returns:
        SurrealQL query string
    """
    return f"""
        SELECT * FROM message
        WHERE session_id = '{session_id}'
          AND timestamp < '{orphan_timestamp}'
          AND is_orphaned = false
        ORDER BY timestamp DESC
        LIMIT {limit};
    """


def build_high_corruption_query(
    session_id: str, threshold: float = 0.5, limit: int = 20
) -> str:
    """
    Build query to get messages with high corruption scores.

    Args:
        session_id: Session ID to search
        threshold: Minimum corruption score
        limit: Maximum number of messages to return

    Returns:
        SurrealQL query string
    """
    return f"""
        SELECT * FROM message
        WHERE session_id = '{session_id}'
          AND corruption_score > {threshold}
        ORDER BY corruption_score DESC, timestamp ASC
        LIMIT {limit};
    """


def build_time_range_query(
    session_id: str, start_time: str, end_time: str
) -> str:
    """
    Build query for messages in specific time window.

    Args:
        session_id: Session ID to search
        start_time: Start timestamp (ISO 8601)
        end_time: End timestamp (ISO 8601)

    Returns:
        SurrealQL query string
    """
    return f"""
        SELECT * FROM message
        WHERE session_id = '{session_id}'
          AND timestamp >= '{start_time}'
          AND timestamp <= '{end_time}'
        ORDER BY timestamp ASC;
    """


# ============================================================================
# SCHEMA EXPORT
# ============================================================================


def export_schema_as_dict() -> Dict[str, Any]:
    """
    Export schema as Python dictionary.

    Returns:
        Complete schema dictionary
    """
    return SCHEMA_DICT.copy()


def get_table_schema(table_name: str) -> Optional[Dict[str, Any]]:
    """
    Get schema for specific table.

    Args:
        table_name: Name of table (session/message/thread)

    Returns:
        Table schema dictionary or None if not found
    """
    return SCHEMA_DICT["tables"].get(table_name)


def get_relation_schema(relation_name: str) -> Optional[Dict[str, Any]]:
    """
    Get schema for specific relation.

    Args:
        relation_name: Name of relation

    Returns:
        Relation schema dictionary or None if not found
    """
    return SCHEMA_DICT["relations"].get(relation_name)
