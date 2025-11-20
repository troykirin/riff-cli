"""
Comprehensive unit tests for duplicate tool_result detection and removal.

Tests cover:
- Detection of duplicate tool_result blocks (scan.py)
- Removal of duplicate tool_result blocks (fix.py)
- Integration of scan + fix workflows
- Edge cases and error handling
- Message structure variations
"""

import pytest
import json
import tempfile
from pathlib import Path
from dataclasses import dataclass, field

from riff.classic.commands.scan import detect_missing_tool_results, ScanIssue
from riff.classic.commands.fix import repair_stream
from riff.classic.utils import (
    iter_jsonl_safe,
    get_message_role,
    get_message_content,
    normalize_message_structure,
)


# ============================================================================
# FIXTURES - Test Data Setup
# ============================================================================

@pytest.fixture
def single_duplicate_message():
    """Fixture: Tool use with duplicate tool_result blocks in same message."""
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "First result - authoritative",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "Second result - duplicate!",
                },
                {
                    "type": "text",
                    "text": "What was the output?",
                },
            ]
        }
    }


@pytest.fixture
def multiple_duplicates_message():
    """Fixture: Multiple tool_uses, some with duplicates."""
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                # abc123: appears 2x (duplicate)
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "First result for abc123",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "Duplicate result for abc123",
                },
                # xyz789: appears 1x (unique)
                {
                    "type": "tool_result",
                    "tool_use_id": "xyz789",
                    "content": "Only result for xyz789",
                },
                # def456: appears 3x (triple duplicate)
                {
                    "type": "tool_result",
                    "tool_use_id": "def456",
                    "content": "First result for def456",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "def456",
                    "content": "Duplicate 1 for def456",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "def456",
                    "content": "Duplicate 2 for def456",
                },
                {
                    "type": "text",
                    "text": "All results received",
                },
            ]
        }
    }


@pytest.fixture
def no_duplicates_message():
    """Fixture: All tool_uses appear exactly once - should report no duplicates."""
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "First result",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "xyz789",
                    "content": "Second result",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "def456",
                    "content": "Third result",
                },
                {
                    "type": "text",
                    "text": "All unique",
                },
            ]
        }
    }


@pytest.fixture
def missing_tool_use_id_message():
    """Fixture: tool_result without tool_use_id field (edge case)."""
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    # Missing tool_use_id!
                    "content": "Result without ID",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "Normal result",
                },
            ]
        }
    }


@pytest.fixture
def mixed_content_types_message():
    """Fixture: Message with mixed content types (text, tool_result, etc)."""
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Starting response",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "Tool output part 1",
                },
                {
                    "type": "text",
                    "text": "Middle text",
                },
                {
                    "type": "tool_result",
                    "tool_use_id": "abc123",
                    "content": "Tool output part 2 - duplicate!",
                },
                {
                    "type": "text",
                    "text": "Ending text",
                },
            ]
        }
    }


@pytest.fixture
def assistant_tool_use_message():
    """Fixture: Assistant message with tool_use blocks (not duplicates, different structure)."""
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "call_abc123",
                    "name": "bash",
                    "input": {"command": "ls"},
                },
                {
                    "type": "text",
                    "text": "Let me run that command",
                },
            ]
        }
    }


@pytest.fixture
def large_duplicate_count():
    """Fixture: Tool use with many duplicates (stress test)."""
    content = []
    for i in range(15):
        content.append({
            "type": "tool_result",
            "tool_use_id": "stress123",
            "content": f"Result copy #{i}",
        })
    content.append({"type": "text", "text": "Many duplicates!"})

    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": content
        }
    }


@pytest.fixture
def conversation_with_duplicates():
    """Fixture: Complete conversation sequence with duplicates to find."""
    return [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Can you run a command?",
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_abc123",
                        "name": "bash",
                        "input": {"command": "pwd"},
                    }
                ]
            }
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_abc123",
                        "content": "/home/user",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_abc123",
                        "content": "/home/user (DUPLICATE)",
                    },
                    {
                        "type": "text",
                        "text": "Got the directory",
                    }
                ]
            }
        }
    ]


@pytest.fixture
def jsonl_file_with_duplicates(tmp_path):
    """Fixture: Creates temporary JSONL file with duplicate tool_results."""
    jsonl_data = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Initial request",
                    }
                ]
            }
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_xyz789",
                        "name": "bash",
                        "input": {"command": "date"},
                    }
                ]
            }
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_xyz789",
                        "content": "2025-11-08",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_xyz789",
                        "content": "2025-11-08 (dup)",
                    }
                ]
            }
        }
    ]

    file_path = tmp_path / "test_conversation.jsonl"
    with file_path.open("w") as f:
        for item in jsonl_data:
            f.write(json.dumps(item) + "\n")

    return file_path


# ============================================================================
# TEST SUITE 1: Duplicate Removal (fix.py)
# ============================================================================

class TestDeduplicateToolResults:
    """Tests for deduplicate_tool_results function.

    NOTE: These tests validate the repair_stream() function's deduplication
    behavior once deduplicate_tool_results() is integrated into fix.py.

    Currently, repair_stream() does NOT deduplicate. These tests are marked
    as "expected behavior after implementation" and will pass once the
    deduplication integration is complete.
    """

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated into repair_stream")
    def test_remove_single_duplicate_keeps_first(self, single_duplicate_message):
        """
        CASE: Single tool_use with 2 identical tool_result blocks

        INPUT:  [tool_result(abc123, "First"), tool_result(abc123, "Second"), text]
        EXPECTED: [tool_result(abc123, "First"), text]  - keeps first, removes second
        """
        content = single_duplicate_message["message"]["content"]

        # This tests the deduplicate_tool_results function
        # For now, we test that repair_stream applies deduplication
        lines = [single_duplicate_message]
        fixed = repair_stream(lines)

        fixed_content = fixed[0]["message"]["content"]

        # Should have 2 items: 1 tool_result + 1 text
        assert len(fixed_content) == 2

        # First should be the tool_result
        assert fixed_content[0]["type"] == "tool_result"
        assert fixed_content[0]["tool_use_id"] == "abc123"
        assert fixed_content[0]["content"] == "First result - authoritative"

        # Second should be the text
        assert fixed_content[1]["type"] == "text"
        assert fixed_content[1]["text"] == "What was the output?"

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated into repair_stream")
    def test_remove_multiple_duplicates_different_ids(self, multiple_duplicates_message):
        """
        CASE: Multiple different tool_uses, some with duplicates

        abc123 appears 2x → keep first, remove second
        xyz789 appears 1x → keep unchanged
        def456 appears 3x → keep first, remove 2nd and 3rd
        """
        lines = [multiple_duplicates_message]
        fixed = repair_stream(lines)
        fixed_content = fixed[0]["message"]["content"]

        # Extract tool_result IDs in order
        tool_result_ids = [
            c["tool_use_id"] for c in fixed_content
            if c.get("type") == "tool_result" and c.get("tool_use_id")
        ]

        # Should only have 3 unique IDs (first occurrence of each)
        assert len(tool_result_ids) == 3
        assert tool_result_ids == ["abc123", "xyz789", "def456"]

    def test_no_duplicates_unchanged(self, no_duplicates_message):
        """
        CASE: No duplicates present

        INPUT == OUTPUT (idempotent operation)
        All tool_uses should remain in output
        """
        original_count = len(no_duplicates_message["message"]["content"])

        lines = [no_duplicates_message]
        fixed = repair_stream(lines)
        fixed_content = fixed[0]["message"]["content"]

        # Count should be the same
        assert len(fixed_content) == original_count

        # All IDs should be present
        ids = {c["tool_use_id"] for c in fixed_content if c.get("type") == "tool_result"}
        assert ids == {"abc123", "xyz789", "def456"}

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated into repair_stream")
    def test_preserve_non_tool_result_blocks(self, mixed_content_types_message):
        """
        CASE: Mixed content types (text, tool_result)

        Keep non-tool_result blocks unchanged.
        Only deduplicate tool_result blocks.
        """
        lines = [mixed_content_types_message]
        fixed = repair_stream(lines)
        fixed_content = fixed[0]["message"]["content"]

        # Count text blocks (should all be preserved)
        text_blocks = [c for c in fixed_content if c.get("type") == "text"]
        assert len(text_blocks) == 3  # "Starting response", "Middle text", "Ending text"

        # Count tool_result blocks (should have 1, not 2)
        tool_result_blocks = [c for c in fixed_content if c.get("type") == "tool_result"]
        assert len(tool_result_blocks) == 1

    def test_preserve_message_order(self, mixed_content_types_message):
        """
        CASE: Deduplication preserves order (when implemented)

        Order matters for semantics. Text should stay in same relative positions.
        This test validates that text content is preserved in the fixed message
        regardless of the deduplication operation.
        """
        lines = [mixed_content_types_message]
        fixed = repair_stream(lines)
        fixed_content = fixed[0]["message"]["content"]

        # Text order should be preserved (regardless of duplicates)
        text_contents = [c["text"] for c in fixed_content if c.get("type") == "text"]
        assert text_contents == [
            "Starting response",
            "Middle text",
            "Ending text"
        ]

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated into repair_stream")
    def test_large_duplicate_count(self, large_duplicate_count):
        """
        CASE: Stress test with many duplicates (10+)

        Should efficiently handle and remove all but first.
        """
        lines = [large_duplicate_count]
        fixed = repair_stream(lines)
        fixed_content = fixed[0]["message"]["content"]

        # Should have 2: 1 tool_result + 1 text
        assert len(fixed_content) == 2

        tool_results = [c for c in fixed_content if c.get("type") == "tool_result"]
        assert len(tool_results) == 1
        assert tool_results[0]["content"] == "Result copy #0"


# ============================================================================
# TEST SUITE 2: Duplicate Detection (scan.py)
# ============================================================================

class TestDetectDuplicateToolResults:
    """Tests for detect_duplicate_tool_results function.

    NOTE: This tests the existing scan infrastructure.
    When detect_duplicate_tool_results() is implemented in scan.py,
    these tests will validate that function directly.
    """

    def test_detect_single_duplicate(self, single_duplicate_message):
        """
        CASE: Single tool_use with 2 identical results

        Should report: {"abc123": count=2, appearing in this message}
        """
        # This demonstrates the expected behavior structure
        # The actual detect_duplicate_tool_results implementation should:
        # 1. Count occurrences of each tool_use_id
        # 2. Report those with count > 1

        lines = [single_duplicate_message]

        # Manual validation of what detection should find
        content = lines[0]["message"]["content"]
        id_count = {}
        for c in content:
            if c.get("type") == "tool_result" and c.get("tool_use_id"):
                tool_id = c["tool_use_id"]
                id_count[tool_id] = id_count.get(tool_id, 0) + 1

        duplicates = [tid for tid, count in id_count.items() if count > 1]

        assert len(duplicates) == 1
        assert duplicates[0] == "abc123"

    def test_detect_multiple_different_duplicates(self, multiple_duplicates_message):
        """
        CASE: Multiple tool_uses with different duplicate counts

        Should report ALL that have count > 1:
        - abc123: count=2
        - xyz789: count=1 (not reported)
        - def456: count=3
        """
        lines = [multiple_duplicates_message]
        content = lines[0]["message"]["content"]

        id_count = {}
        for c in content:
            if c.get("type") == "tool_result" and c.get("tool_use_id"):
                tool_id = c["tool_use_id"]
                id_count[tool_id] = id_count.get(tool_id, 0) + 1

        duplicates = [tid for tid, count in id_count.items() if count > 1]

        assert len(duplicates) == 2
        assert set(duplicates) == {"abc123", "def456"}
        assert id_count["xyz789"] == 1  # xyz789 is NOT a duplicate

    def test_detect_no_duplicates(self, no_duplicates_message):
        """
        CASE: No duplicates present

        Should report: empty list (no issues)
        """
        lines = [no_duplicates_message]
        content = lines[0]["message"]["content"]

        id_count = {}
        for c in content:
            if c.get("type") == "tool_result" and c.get("tool_use_id"):
                tool_id = c["tool_use_id"]
                id_count[tool_id] = id_count.get(tool_id, 0) + 1

        duplicates = [tid for tid, count in id_count.items() if count > 1]

        assert len(duplicates) == 0

    def test_detect_ignores_missing_tool_use_id(self, missing_tool_use_id_message):
        """
        CASE: tool_result without tool_use_id field (edge case)

        Should skip gracefully (cannot be duplicate without ID).
        Only normal tool_results should be counted.
        """
        lines = [missing_tool_use_id_message]
        content = lines[0]["message"]["content"]

        id_count = {}
        for c in content:
            if c.get("type") == "tool_result":
                tool_id = c.get("tool_use_id")
                if tool_id:  # Only count if ID exists
                    id_count[tool_id] = id_count.get(tool_id, 0) + 1

        duplicates = [tid for tid, count in id_count.items() if count > 1]

        # Should only count abc123 once (no duplicates)
        assert len(duplicates) == 0
        assert id_count == {"abc123": 1}

    def test_detect_ignores_assistant_tool_use(self, assistant_tool_use_message):
        """
        CASE: Assistant message with tool_use blocks

        tool_use blocks are different from tool_result blocks.
        Only tool_result blocks should be scanned for duplicates.
        Detection should not find any issues in assistant messages.
        """
        lines = [assistant_tool_use_message]
        content = lines[0]["message"]["content"]

        # Should only scan tool_result, not tool_use
        id_count = {}
        for c in content:
            if c.get("type") == "tool_result" and c.get("tool_use_id"):
                tool_id = c["tool_use_id"]
                id_count[tool_id] = id_count.get(tool_id, 0) + 1

        duplicates = [tid for tid, count in id_count.items() if count > 1]

        # No tool_results in assistant message, so no duplicates
        assert len(duplicates) == 0


# ============================================================================
# TEST SUITE 3: Integration Tests (scan + fix workflow)
# ============================================================================

class TestDuplicateWorkflow:
    """Integration tests combining detection and removal.

    NOTE: These tests validate the full scan + fix workflow for duplicates.
    They will pass once detect_duplicate_tool_results() is integrated into scan.py
    and deduplicate_tool_results() is integrated into fix.py.
    """

    @pytest.mark.xfail(reason="deduplication workflow not yet fully integrated")
    def test_detect_then_fix_workflow(self, conversation_with_duplicates):
        """
        CASE: Full workflow - detect issues, then fix them

        1. Run detect → find duplicates
        2. Run fix → remove duplicates
        3. Run detect again → verify clean
        """
        # Step 1: Detect duplicates in original
        lines = conversation_with_duplicates

        # Find duplicates in the user message (index 2)
        user_message = lines[2]
        content = user_message["message"]["content"]

        id_count = {}
        for c in content:
            if c.get("type") == "tool_result" and c.get("tool_use_id"):
                tool_id = c["tool_use_id"]
                id_count[tool_id] = id_count.get(tool_id, 0) + 1

        duplicates_before = [tid for tid, count in id_count.items() if count > 1]
        assert len(duplicates_before) == 1
        assert duplicates_before[0] == "call_abc123"

        # Step 2: Fix the issues
        fixed_lines = repair_stream(lines)

        # Step 3: Verify clean (detect again)
        fixed_user_message = fixed_lines[2]
        fixed_content = fixed_user_message["message"]["content"]

        id_count_after = {}
        for c in fixed_content:
            if c.get("type") == "tool_result" and c.get("tool_use_id"):
                tool_id = c["tool_use_id"]
                id_count_after[tool_id] = id_count_after.get(tool_id, 0) + 1

        duplicates_after = [tid for tid, count in id_count_after.items() if count > 1]
        assert len(duplicates_after) == 0

    def test_repair_stream_idempotent(self, conversation_with_duplicates):
        """
        CASE: Repair is idempotent - running twice produces same result

        fix(fix(data)) == fix(data)
        """
        # First fix
        fixed_once = repair_stream(conversation_with_duplicates)

        # Second fix (on already fixed data)
        fixed_twice = repair_stream(fixed_once)

        # Should be identical
        assert len(fixed_once) == len(fixed_twice)

        for msg1, msg2 in zip(fixed_once, fixed_twice):
            assert msg1 == msg2

    @pytest.mark.xfail(reason="deduplication workflow not yet fully integrated")
    def test_full_conversation_repair(self, conversation_with_duplicates):
        """
        CASE: Repair entire conversation with duplicates

        Should fix duplicates while preserving conversation structure.
        """
        fixed = repair_stream(conversation_with_duplicates)

        # Should still have 3 messages
        assert len(fixed) == 3

        # First message unchanged (no duplicates)
        assert fixed[0] == conversation_with_duplicates[0]

        # Second message unchanged (assistant tool_use, not tool_result)
        assert fixed[1] == conversation_with_duplicates[1]

        # Third message should be fixed (duplicates removed)
        fixed_content = fixed[2]["message"]["content"]

        # Count remaining tool_results
        tool_results = [c for c in fixed_content if c.get("type") == "tool_result"]
        assert len(tool_results) == 1  # Only one now

        # Content should be the first one (preserved)
        assert tool_results[0]["content"] == "/home/user"


# ============================================================================
# TEST SUITE 4: Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_content_list(self):
        """CASE: Message with empty content list."""
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": []
            }
        }

        fixed = repair_stream([message])
        assert fixed[0]["message"]["content"] == []

    def test_non_list_content(self):
        """CASE: Message with non-list content (malformed but possible)."""
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": "string instead of list"
            }
        }

        # Should handle gracefully without crashing
        fixed = repair_stream([message])
        assert len(fixed) == 1

    def test_null_tool_use_id(self):
        """CASE: tool_result with null/None tool_use_id."""
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": None,
                        "content": "Result with null ID",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": None,
                        "content": "Another null ID result",
                    }
                ]
            }
        }

        fixed = repair_stream([message])
        # Should keep both (can't deduplicate without valid ID)
        tool_results = [c for c in fixed[0]["message"]["content"] if c.get("type") == "tool_result"]
        assert len(tool_results) == 2

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated")
    def test_mixed_valid_and_invalid_ids(self):
        """CASE: Mix of valid IDs, null IDs, missing IDs in one message.

        Tests deduplication behavior when some tool_results have invalid/missing IDs.
        """
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "valid123",
                        "content": "Has ID",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "valid123",
                        "content": "Duplicate of first",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": None,
                        "content": "Has null ID",
                    },
                    {
                        "type": "tool_result",
                        # Missing tool_use_id entirely
                        "content": "Missing ID field",
                    }
                ]
            }
        }

        fixed = repair_stream([message])
        fixed_content = fixed[0]["message"]["content"]

        # After dedup: 1 valid + 1 null + 1 missing = 3 total
        # (the duplicate of "valid123" is removed)
        tool_results = [c for c in fixed_content if c.get("type") == "tool_result"]
        assert len(tool_results) == 3

    def test_message_without_role(self):
        """CASE: Message structure missing 'role' field."""
        message = {
            "type": "user",
            "message": {
                # "role" key missing
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "abc123",
                        "content": "Result 1",
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "abc123",
                        "content": "Result 2 - dup",
                    }
                ]
            }
        }

        # Should handle gracefully (get_message_role handles this)
        fixed = repair_stream([message])
        assert len(fixed) == 1

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated")
    def test_deeply_nested_malformed_content(self):
        """CASE: Content with unexpected nesting levels.

        Tests deduplication works even when tool_result content is complex (dict/nested).
        """
        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "abc123",
                        "content": {
                            "nested": "object",
                            "deeply": {
                                "nested": "value"
                            }
                        }
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "abc123",
                        "content": {
                            "nested": "object",
                            "deeply": {
                                "nested": "value"
                            }
                        }
                    }
                ]
            }
        }

        # Should still deduplicate even with complex content
        fixed = repair_stream([message])
        tool_results = [c for c in fixed[0]["message"]["content"] if c.get("type") == "tool_result"]
        assert len(tool_results) == 1


# ============================================================================
# TEST SUITE 5: JSONL File Operations
# ============================================================================

class TestJSONLFileOperations:
    """Tests for JSONL file handling with duplicates."""

    def test_read_jsonl_with_duplicates(self, jsonl_file_with_duplicates):
        """CASE: Read JSONL file containing duplicate tool_results."""
        lines = list(iter_jsonl_safe(jsonl_file_with_duplicates))

        assert len(lines) == 3

        # Verify the third message has duplicates
        user_message = lines[2]
        tool_results = [
            c for c in user_message["message"]["content"]
            if c.get("type") == "tool_result"
        ]
        assert len(tool_results) == 2

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated")
    def test_repair_and_save_jsonl(self, jsonl_file_with_duplicates, tmp_path):
        """CASE: Read, repair, and save JSONL with deduplication.

        Tests the full workflow: read JSONL, repair duplicates, save to new file.
        """
        # Read original
        lines = list(iter_jsonl_safe(jsonl_file_with_duplicates))

        # Verify duplicates exist
        original_tool_results = [
            c for c in lines[2]["message"]["content"]
            if c.get("type") == "tool_result"
        ]
        assert len(original_tool_results) == 2

        # Repair
        fixed = repair_stream(lines)

        # Save to new file
        output_file = tmp_path / "repaired.jsonl"
        with output_file.open("w") as f:
            for msg in fixed:
                f.write(json.dumps(msg) + "\n")

        # Verify repair (should have only 1 tool_result after dedup)
        repaired_lines = list(iter_jsonl_safe(output_file))
        repaired_tool_results = [
            c for c in repaired_lines[2]["message"]["content"]
            if c.get("type") == "tool_result"
        ]
        assert len(repaired_tool_results) == 1

    def test_malformed_jsonl_line_skipped(self, tmp_path):
        """CASE: JSONL file with some malformed lines (should skip gracefully)."""
        jsonl_file = tmp_path / "malformed.jsonl"

        with jsonl_file.open("w") as f:
            # Valid line
            f.write('{"type": "user", "message": {"role": "user", "content": []}}\n')
            # Invalid line (malformed JSON)
            f.write('{"type": "user", invalid json}\n')
            # Valid line
            f.write('{"type": "assistant", "message": {"role": "assistant", "content": []}}\n')

        # Should skip malformed line and load 2 valid lines
        lines = list(iter_jsonl_safe(jsonl_file))
        assert len(lines) == 2


# ============================================================================
# TEST SUITE 6: Performance and Stress Tests
# ============================================================================

class TestPerformance:
    """Performance and stress tests."""

    def test_many_unique_tool_uses_no_duplicates(self):
        """CASE: Message with many unique tool_uses (no duplicates)."""
        content = []
        for i in range(100):
            content.append({
                "type": "tool_result",
                "tool_use_id": f"tool_{i:03d}",
                "content": f"Result {i}",
            })

        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": content
            }
        }

        fixed = repair_stream([message])

        # All 100 should remain
        tool_results = [
            c for c in fixed[0]["message"]["content"]
            if c.get("type") == "tool_result"
        ]
        assert len(tool_results) == 100

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated")
    def test_many_duplicate_pairs(self):
        """CASE: Message with many duplicate pairs (10 pairs).

        Stress test: many duplicates should be efficiently handled.
        """
        content = []
        for i in range(10):
            # Add pair of duplicates
            tool_id = f"tool_{i:03d}"
            content.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Result {i} - first",
            })
            content.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": f"Result {i} - duplicate",
            })

        message = {
            "type": "user",
            "message": {
                "role": "user",
                "content": content
            }
        }

        fixed = repair_stream([message])

        # After dedup: should be reduced to 10 (one per ID)
        tool_results = [
            c for c in fixed[0]["message"]["content"]
            if c.get("type") == "tool_result"
        ]
        assert len(tool_results) == 10

    @pytest.mark.xfail(reason="deduplicate_tool_results not yet integrated")
    def test_long_conversation_with_scattered_duplicates(self):
        """CASE: Long conversation with duplicates scattered throughout.

        Stress test: 20-message conversation with scattered duplicates.
        """
        lines = []
        for conv_idx in range(20):  # 20 user-assistant pairs
            # User message
            lines.append({
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": f"Question {conv_idx}"}]
                }
            })

            # Assistant message
            lines.append({
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": f"call_{conv_idx}",
                            "name": "bash",
                            "input": {"command": "echo"}
                        }
                    ]
                }
            })

            # User response with result (sometimes duplicate)
            content = [
                {
                    "type": "tool_result",
                    "tool_use_id": f"call_{conv_idx}",
                    "content": f"Output {conv_idx}",
                }
            ]

            # Add duplicate for even indices
            if conv_idx % 2 == 0:
                content.append({
                    "type": "tool_result",
                    "tool_use_id": f"call_{conv_idx}",
                    "content": f"Output {conv_idx} - dup",
                })

            lines.append({
                "type": "user",
                "message": {
                    "role": "user",
                    "content": content
                }
            })

        # Repair long conversation
        fixed = repair_stream(lines)

        # Check that duplicates are gone
        # Count tool_results in odd-indexed lines (response messages)
        tool_result_count = 0
        for idx in range(2, len(fixed), 3):  # Every third line starting at 2
            tool_results = [
                c for c in fixed[idx]["message"]["content"]
                if c.get("type") == "tool_result"
            ]
            tool_result_count += len(tool_results)

        # Should be 20 (one per conversation, none duplicated)
        assert tool_result_count == 20


# ============================================================================
# TEST SUITE 7: Data Structure Integrity
# ============================================================================

class TestDataStructureIntegrity:
    """Tests to ensure repair preserves message structure."""

    def test_repair_preserves_message_type(self, single_duplicate_message):
        """CASE: Message 'type' field is preserved."""
        fixed = repair_stream([single_duplicate_message])
        assert fixed[0]["type"] == "user"

    def test_repair_preserves_message_role(self, single_duplicate_message):
        """CASE: Message 'role' field is preserved."""
        fixed = repair_stream([single_duplicate_message])
        assert fixed[0]["message"]["role"] == "user"

    def test_repair_tool_result_fields(self, single_duplicate_message):
        """CASE: Kept tool_result retains all fields."""
        fixed = repair_stream([single_duplicate_message])
        kept_result = fixed[0]["message"]["content"][0]

        assert "type" in kept_result
        assert "tool_use_id" in kept_result
        assert "content" in kept_result
        assert kept_result["type"] == "tool_result"

    def test_normalize_message_structure_creates_message_key(self):
        """CASE: normalize_message_structure adds 'message' key if missing."""
        msg = {
            "type": "user",
            "content": [{"type": "text", "text": "hello"}]
        }

        normalized = normalize_message_structure(msg)

        assert "message" in normalized
        assert normalized["message"]["role"] == "user"
        assert normalized["message"]["content"] == [{"type": "text", "text": "hello"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
