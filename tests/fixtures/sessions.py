"""
Test fixtures for Claude session data
Based on actual Qdrant payload structure discovered through exploration
"""

from datetime import datetime, timedelta
import uuid

# Base timestamp for consistent test data
BASE_TIME = datetime(2025, 1, 1, 12, 0, 0)

def generate_session_id():
    """Generate a deterministic test session ID"""
    return str(uuid.uuid4())

# Core test fixtures based on actual Qdrant structure
FIXTURE_SESSIONS = {
    "empty": {
        "session_id": "test-empty-00000000-0000-0000-0000-000000000001",
        "file_path": "/Users/test/.claude/projects/test-empty/session.jsonl",
        "working_directory": "/Users/test/empty-project",
        "content_preview": "",
        "content_length": 0,
        "last_activity": BASE_TIME.isoformat() + "Z",
        "indexed_at": BASE_TIME.isoformat()
    },

    "typical_todowrite": {
        "session_id": "test-todo-00000000-0000-0000-0000-000000000002",
        "file_path": "/Users/test/.claude/projects/test-todo/session.jsonl",
        "working_directory": "/Users/test/nabia/memchain",
        "content_preview": "[1mPreToolUse:TodoWrite[22m [/Users/test/nabia/memchain/.nabi/governance/hooks/hook_wrapper.sh pre_tool_use] Task tracking initialized with federation context",
        "content_length": 8500,
        "last_activity": (BASE_TIME + timedelta(days=5)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=5, hours=1)).isoformat()
    },

    "typical_hooks": {
        "session_id": "test-hooks-00000000-0000-0000-0000-000000000003",
        "file_path": "/Users/test/.claude/projects/test-hooks/session.jsonl",
        "working_directory": "/Users/test/.config/nabi",
        "content_preview": "[1mPreToolUse:Read[22m [/Users/test/nabia/memchain/.nabi/governance/hooks/hook_wrapper.sh] Analyzing federation hook patterns",
        "content_length": 12000,
        "last_activity": (BASE_TIME + timedelta(days=10)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=10, minutes=30)).isoformat()
    },

    "federation_context": {
        "session_id": "test-fed-00000000-0000-0000-0000-000000000004",
        "file_path": "/Users/test/.claude/projects/test-federation/session.jsonl",
        "working_directory": "/Users/test/nabia/memchain",
        "content_preview": "Implementing federation protocol with STOP validation and Loki event streaming",
        "content_length": 15000,
        "last_activity": (BASE_TIME + timedelta(days=15)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=15, hours=2)).isoformat()
    },

    "python_code": {
        "session_id": "test-py-00000000-0000-0000-0000-000000000005",
        "file_path": "/Users/test/.claude/projects/test-python/session.jsonl",
        "working_directory": "/Users/test/projects/python-app",
        "content_preview": "def process_data():\n    \"\"\"Process incoming federation events\"\"\"\n    return {'status': 'success'}",
        "content_length": 5500,
        "last_activity": (BASE_TIME + timedelta(days=3)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=3, hours=1)).isoformat()
    },

    "edge_case_unicode": {
        "session_id": "test-unicode-00000000-0000-0000-0000-000000000006",
        "file_path": "/Users/test/.claude/projects/test-unicode/session.jsonl",
        "working_directory": "/Users/test/unicode-project",
        "content_preview": "Testing with 测试 テスト тест and emojis 🚀 🎯 ⚡",
        "content_length": 2000,
        "last_activity": (BASE_TIME + timedelta(days=7)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=7, minutes=15)).isoformat()
    },

    "edge_case_long_preview": {
        "session_id": "test-long-00000000-0000-0000-0000-000000000007",
        "file_path": "/Users/test/.claude/projects/test-long/session.jsonl",
        "working_directory": "/Users/test/long-content",
        "content_preview": "A" * 500,  # Very long content preview
        "content_length": 50000,
        "last_activity": (BASE_TIME + timedelta(days=20)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=20, hours=3)).isoformat()
    },

    "edge_case_special_chars": {
        "session_id": "test-special-00000000-0000-0000-0000-000000000008",
        "file_path": "/Users/test/.claude/projects/test-special/session.jsonl",
        "working_directory": "/Users/test/special-chars",
        "content_preview": "Testing with special chars: $var = 'test'; <html> & \"quotes\" 'apostrophes'",
        "content_length": 3500,
        "last_activity": (BASE_TIME + timedelta(days=12)).isoformat() + "Z",
        "indexed_at": (BASE_TIME + timedelta(days=12, hours=1)).isoformat()
    },

    "minimal": {
        "session_id": "test-min-00000000-0000-0000-0000-000000000009",
        "file_path": "/test.jsonl",
        "working_directory": "/",
        "content_preview": "x",
        "content_length": 1,
        "last_activity": BASE_TIME.isoformat() + "Z",
        "indexed_at": BASE_TIME.isoformat()
    }
}

# Grouped fixtures for different test scenarios
TEST_SCENARIOS = {
    "search_basic": [
        FIXTURE_SESSIONS["typical_todowrite"],
        FIXTURE_SESSIONS["typical_hooks"],
        FIXTURE_SESSIONS["federation_context"]
    ],

    "search_edge_cases": [
        FIXTURE_SESSIONS["empty"],
        FIXTURE_SESSIONS["edge_case_unicode"],
        FIXTURE_SESSIONS["edge_case_long_preview"],
        FIXTURE_SESSIONS["edge_case_special_chars"]
    ],

    "uuid_lookup": [
        FIXTURE_SESSIONS["typical_todowrite"],
        FIXTURE_SESSIONS["minimal"]
    ],

    "performance_test": [
        FIXTURE_SESSIONS[key] for key in FIXTURE_SESSIONS.keys()
    ] * 100  # 900 sessions for load testing
}

# Expected search results for validation
EXPECTED_RESULTS = {
    "TodoWrite": ["test-todo-00000000-0000-0000-0000-000000000002"],
    "hooks": [
        "test-hooks-00000000-0000-0000-0000-000000000003",
        "test-todo-00000000-0000-0000-0000-000000000002"
    ],
    "federation": ["test-fed-00000000-0000-0000-0000-000000000004"],
    "python": ["test-py-00000000-0000-0000-0000-000000000005"],
    "测试": ["test-unicode-00000000-0000-0000-0000-000000000006"],
    "": [],  # Empty query
    "nonexistent-query-xyz": []  # No matches
}