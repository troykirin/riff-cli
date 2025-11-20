"""
Pytest configuration and fixtures for riff-cli tests
"""

import pytest
import json
import tempfile
from pathlib import Path


@pytest.fixture
def sample_claude_export():
    """Create a sample Claude export structure"""
    conversations = [
        {
            "uuid": "conv-123-456",
            "name": "Test Conversation about Federation",
            "created_at": "2024-01-01T00:00:00Z",
            "chat_messages": [
                {"text": "Let's discuss the nabia federation architecture"},
                {"text": "The federation uses orchestration patterns"}
            ]
        }
    ]

    projects = [
        {
            "uuid": "proj-789-012",
            "name": "Linear Integration Project",
            "description": "Integrating Linear with federation",
            "created_at": "2024-01-02T00:00:00Z",
            "docs": [
                {"content": "API documentation for Linear integration"},
                {"content": "OAuth proxy configuration"}
            ]
        }
    ]

    users = [
        {
            "uuid": "user-345-678",
            "full_name": "Test User",
            "email_address": "test@example.com"
        }
    ]

    return {
        "conversations": conversations,
        "projects": projects,
        "users": users
    }


@pytest.fixture
def temp_claude_export_dir(sample_claude_export):
    """Create temporary directory with Claude export files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Write conversations.json
        with open(tmpdir_path / "conversations.json", "w") as f:
            json.dump(sample_claude_export["conversations"], f)

        # Write projects.json
        with open(tmpdir_path / "projects.json", "w") as f:
            json.dump(sample_claude_export["projects"], f)

        # Write users.json
        with open(tmpdir_path / "users.json", "w") as f:
            json.dump(sample_claude_export["users"], f)

        yield tmpdir_path


@pytest.fixture
def sample_jsonl_file():
    """Create a sample JSONL file"""
    data = [
        {"uuid": "123", "content": "First line with federation"},
        {"uuid": "456", "content": "Second line about Linear"},
        {"uuid": "789", "content": "Third line discussing agents"}
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        for item in data:
            f.write(json.dumps(item) + '\n')
        temp_path = Path(f.name)

    yield temp_path
    temp_path.unlink()


@pytest.fixture
def mock_conversation_data():
    """Provide mock conversation data for testing"""
    return {
        "uuid": "mock-conv-123",
        "name": "Mock Conversation",
        "chat_messages": [
            {"text": "Question about implementation"},
            {"text": "Answer with technical details"}
        ],
        "metadata": {
            "tags": ["technical", "implementation"]
        }
    }


@pytest.fixture
def mock_project_data():
    """Provide mock project data for testing"""
    return {
        "uuid": "mock-proj-456",
        "name": "Mock Project",
        "description": "A test project for unit testing",
        "docs": [
            {"title": "README", "content": "Project documentation"},
            {"title": "API", "content": "API reference guide"}
        ]
    }