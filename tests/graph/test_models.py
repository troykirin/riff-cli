"""
Test suite for conversation DAG models.

Tests Message, Thread, and Session dataclasses including validation,
type conversion, and property computation.
"""

import pytest
from datetime import datetime

from riff.graph.models import (
    Message,
    Thread,
    Session,
    MessageType,
    ThreadType,
)


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test basic message creation."""
        msg = Message(
            uuid="msg-001",
            parent_uuid=None,
            type=MessageType.USER,
            content="Hello world",
            timestamp="2025-10-20T10:00:00Z",
            session_id="session-001"
        )

        assert msg.uuid == "msg-001"
        assert msg.parent_uuid is None
        assert msg.type == MessageType.USER
        assert msg.content == "Hello world"
        assert msg.is_orphaned == False
        assert msg.corruption_score == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
