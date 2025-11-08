"""
Comprehensive test suite for duplicate_handler.py

Tests cover:
- Valid and invalid tool_result blocks
- Partial corruption scenarios
- OOM risk detection
- Graceful degradation on malformed data
- Full detection and deduplication workflows
- Recovery suggestion generation
- Metric tracking
"""

import pytest
from typing import Dict, Any, List
from riff.classic.duplicate_handler import (
    validate_tool_result_block,
    validate_content_blocks,
    detect_duplicate_tool_results,
    deduplicate_tool_results,
    apply_deduplication_to_lines,
    log_detection_summary,
    log_deduplication_summary,
    DuplicateDetectionErrorType,
    ValidationResult,
    DuplicateDetectionMetrics,
    DeduplicationResult,
    RiffDuplicateDetectionError,
    RiffDeduplicationError,
)


class TestValidateToolResultBlock:
    """Test suite for validate_tool_result_block function."""

    def test_valid_block(self):
        """Test validation of a properly formed tool_result block."""
        block = {
            "type": "tool_result",
            "tool_use_id": "tool_123",
            "content": "Success"
        }
        result = validate_tool_result_block(block)
        assert result.is_valid
        assert result.tool_use_id == "tool_123"
        assert result.error_type is None

    def test_valid_block_with_whitespace_tool_use_id(self):
        """Test that whitespace in tool_use_id is stripped."""
        block = {
            "type": "tool_result",
            "tool_use_id": "  tool_123  ",
            "content": "Success"
        }
        result = validate_tool_result_block(block)
        assert result.is_valid
        assert result.tool_use_id == "tool_123"

    def test_missing_tool_use_id_field(self):
        """Test detection of missing tool_use_id field."""
        block = {
            "type": "tool_result",
            "content": "Success"
        }
        result = validate_tool_result_block(block)
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.MISSING_FIELD
        assert "tool_use_id" in result.error_message

    def test_empty_tool_use_id(self):
        """Test detection of empty tool_use_id."""
        block = {
            "type": "tool_result",
            "tool_use_id": "",
            "content": "Success"
        }
        result = validate_tool_result_block(block)
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.INVALID_TYPE

    def test_whitespace_only_tool_use_id(self):
        """Test detection of whitespace-only tool_use_id."""
        block = {
            "type": "tool_result",
            "tool_use_id": "   ",
            "content": "Success"
        }
        result = validate_tool_result_block(block)
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.INVALID_TYPE

    def test_tool_use_id_not_string(self):
        """Test detection of non-string tool_use_id."""
        block = {
            "type": "tool_result",
            "tool_use_id": 123,
            "content": "Success"
        }
        result = validate_tool_result_block(block)
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.INVALID_TYPE

    def test_block_not_dict(self):
        """Test detection of non-dict block."""
        result = validate_tool_result_block("not a dict")
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.INVALID_TYPE

    def test_block_is_list(self):
        """Test detection of list where dict expected."""
        result = validate_tool_result_block([])
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.INVALID_TYPE

    def test_block_is_none(self):
        """Test detection of None block."""
        result = validate_tool_result_block(None)
        assert not result.is_valid
        assert result.error_type == DuplicateDetectionErrorType.INVALID_TYPE

    def test_block_index_preserved(self):
        """Test that block_index is preserved in result."""
        block = {"type": "tool_result", "tool_use_id": "test"}
        result = validate_tool_result_block(block, block_index=5)
        assert result.block_index == 5


class TestValidateContentBlocks:
    """Test suite for validate_content_blocks function."""

    def test_valid_list_content(self):
        """Test validation of valid content list."""
        content = [{"type": "text", "text": "hello"}]
        is_valid, msg = validate_content_blocks(content)
        assert is_valid
        assert msg == ""

    def test_empty_list_is_valid(self):
        """Test that empty list is valid."""
        is_valid, msg = validate_content_blocks([])
        assert is_valid

    def test_none_content(self):
        """Test that None content is invalid."""
        is_valid, msg = validate_content_blocks(None)
        assert not is_valid
        assert "None" in msg

    def test_non_list_content(self):
        """Test that non-list content is invalid."""
        is_valid, msg = validate_content_blocks({"type": "text"})
        assert not is_valid
        assert "expected list" in msg

    def test_string_content(self):
        """Test that string content is invalid."""
        is_valid, msg = validate_content_blocks("not a list")
        assert not is_valid


class TestDetectDuplicateToolResults:
    """Test suite for detect_duplicate_tool_results function."""

    def test_empty_lines(self):
        """Test detection on empty lines."""
        duplicates, metrics = detect_duplicate_tool_results([])
        assert duplicates == {}
        assert metrics.blocks_processed == 0

    def test_no_duplicates(self):
        """Test detection when no duplicates exist."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tool_1",
                            "content": "Result 1"
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
                            "type": "tool_result",
                            "tool_use_id": "tool_2",
                            "content": "Result 2"
                        }
                    ]
                }
            }
        ]
        duplicates, metrics = detect_duplicate_tool_results(lines)
        assert duplicates == {}
        assert metrics.duplicates_detected == 0
        assert metrics.blocks_valid == 2

    def test_single_duplicate(self):
        """Test detection of a single duplicate."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "tool_1",
                            "content": "Result 1"
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "tool_1",
                            "content": "Result 1 (duplicate)"
                        }
                    ]
                }
            }
        ]
        duplicates, metrics = detect_duplicate_tool_results(lines)
        assert duplicates == {"tool_1": 1}
        assert metrics.duplicates_detected == 1
        assert metrics.blocks_valid == 2

    def test_multiple_duplicates_same_id(self):
        """Test detection of multiple duplicates of same tool_use_id."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "2"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "3"},
                    ]
                }
            }
        ]
        duplicates, metrics = detect_duplicate_tool_results(lines)
        assert duplicates == {"tool_1": 2}  # 3 occurrences = 2 duplicates
        assert metrics.duplicates_detected == 2

    def test_multiple_different_duplicates(self):
        """Test detection of different tool_use_ids with duplicates."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1b"},
                        {"type": "tool_result", "tool_use_id": "tool_2", "content": "2"},
                        {"type": "tool_result", "tool_use_id": "tool_2", "content": "2b"},
                    ]
                }
            }
        ]
        duplicates, metrics = detect_duplicate_tool_results(lines)
        assert duplicates == {"tool_1": 1, "tool_2": 1}
        assert metrics.duplicates_detected == 2

    def test_partial_corruption_graceful_handling(self):
        """Test graceful handling when some blocks are malformed."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result"},  # Missing tool_use_id
                        {"type": "tool_result", "tool_use_id": "tool_2", "content": "2"},
                        {"type": "tool_result", "tool_use_id": 123},  # Invalid type
                    ]
                }
            }
        ]
        duplicates, metrics = detect_duplicate_tool_results(lines)
        # Should process valid blocks, skip invalid
        assert metrics.blocks_valid == 2
        assert metrics.blocks_invalid == 2
        assert len(metrics.errors) == 2

    def test_invalid_lines_type_raises_error(self):
        """Test that non-list lines raises error."""
        with pytest.raises(RiffDuplicateDetectionError):
            detect_duplicate_tool_results("not a list")

    def test_oom_risk_detection(self):
        """Test detection of OOM risk from excessive duplicates."""
        # Create a tool_use_id that appears 150 times (exceeds default 100 threshold)
        blocks = [{"type": "tool_result", "tool_use_id": "tool_1", "content": f"dup_{i}"}
                  for i in range(150)]
        lines = [{
            "type": "user",
            "message": {"role": "user", "content": blocks}
        }]

        duplicates, metrics = detect_duplicate_tool_results(lines, max_duplicates_per_id=100)

        # Should detect the massive duplication
        assert "tool_1" in duplicates
        assert duplicates["tool_1"] == 149  # 150 - 1 first occurrence
        # Should have OOM risk error
        oom_errors = [e for e in metrics.errors
                     if e.get("error_type") == DuplicateDetectionErrorType.OOM_RISK.value]
        assert len(oom_errors) > 0

    def test_corrupted_message_structure(self):
        """Test handling of corrupted message structure."""
        lines = [
            123,  # Not a dict
            {"type": "user", "message": None},  # Null message
            {"type": "user"},  # Missing message key
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": "not a list"  # Content is string, not list
                }
            },
            {
                "type": "user",
                "message": {"role": "user", "content": []}  # Valid but empty
            }
        ]

        duplicates, metrics = detect_duplicate_tool_results(lines)

        # Should process without crashing
        assert isinstance(duplicates, dict)
        # First message isn't dict - counted as invalid message
        assert metrics.blocks_invalid == 1
        # Total messages scanned = 5, but only valid ones update message count
        assert metrics.blocks_processed == 0  # No tool_result blocks in any message

    def test_metrics_accuracy(self):
        """Test that metrics are tracked accurately."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "hello"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "text", "text": "world"},
                    ]
                }
            }
        ]

        duplicates, metrics = detect_duplicate_tool_results(lines)

        assert metrics.blocks_processed == 3  # All blocks
        assert metrics.blocks_valid == 1  # Only tool_result is valid
        assert metrics.blocks_invalid == 0
        assert metrics.unique_tool_use_ids == 1


class TestDeduplicateToolResults:
    """Test suite for deduplicate_tool_results function."""

    def test_empty_duplicates_dict(self):
        """Test deduplication with no duplicates to remove."""
        lines = [
            {"type": "user", "message": {"role": "user", "content": []}}
        ]
        duplicates = {}

        result = deduplicate_tool_results(lines, duplicates)

        assert result.success
        assert result.duplicates_removed == 0

    def test_remove_single_duplicate(self):
        """Test removal of a single duplicate."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1dup"},
                    ]
                }
            }
        ]
        duplicates = {"tool_1": 1}

        result = deduplicate_tool_results(lines, duplicates)

        assert result.success
        assert result.duplicates_removed == 1
        # Verify first occurrence kept, second removed
        content = lines[0]["message"]["content"]
        assert len(content) == 1
        assert content[0]["content"] == "1"

    def test_preserve_first_occurrence(self):
        """Test that first occurrence of tool_use_id is preserved."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "FIRST"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "SECOND"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "THIRD"},
                    ]
                }
            }
        ]
        duplicates = {"tool_1": 2}

        result = deduplicate_tool_results(lines, duplicates)

        content = lines[0]["message"]["content"]
        assert len(content) == 1
        assert content[0]["content"] == "FIRST"

    def test_preserve_non_tool_result_blocks(self):
        """Test that non-tool_result blocks are preserved."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "before"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1dup"},
                        {"type": "text", "text": "after"},
                    ]
                }
            }
        ]
        duplicates = {"tool_1": 1}

        result = deduplicate_tool_results(lines, duplicates)

        content = lines[0]["message"]["content"]
        assert len(content) == 3
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "before"
        assert content[1]["type"] == "tool_result"
        assert content[1]["content"] == "1"
        assert content[2]["type"] == "text"
        assert content[2]["text"] == "after"

    def test_invalid_tool_use_id_blocks_preserved(self):
        """Test that invalid tool_result blocks are preserved (not removed)."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result"},  # Missing tool_use_id
                    ]
                }
            }
        ]
        duplicates = {}

        result = deduplicate_tool_results(lines, duplicates)

        content = lines[0]["message"]["content"]
        # Both blocks should be preserved - we don't remove invalid data
        assert len(content) == 2

    def test_invalid_lines_type_returns_error(self):
        """Test that non-list lines returns error result."""
        result = deduplicate_tool_results("not a list", {})

        assert not result.success
        assert result.error is not None

    def test_multiple_messages_with_duplicates(self):
        """Test deduplication across multiple messages."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "first"},
                    ]
                }
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "response"}]
                }
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "dup"},
                    ]
                }
            }
        ]
        duplicates = {"tool_1": 1}

        result = deduplicate_tool_results(lines, duplicates)

        assert result.success
        assert result.duplicates_removed == 1
        # Second message should be modified
        assert len(lines[2]["message"]["content"]) == 0

    def test_recovery_suggestions_on_failure(self):
        """Test that recovery suggestions are provided on failure."""
        result = deduplicate_tool_results("invalid", {})

        assert not result.success
        assert len(result.recovery_suggestions) > 0


class TestIntegrationWorkflow:
    """Integration tests for full detect + deduplicate workflow."""

    def test_full_workflow_real_scenario(self):
        """Test complete workflow: detect then deduplicate."""
        # Realistic scenario with session resume causing duplicates
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello"}
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
                            "id": "call_1",
                            "name": "some_tool",
                            "input": {}
                        }
                    ]
                }
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "call_1", "content": "result"}
                    ]
                }
            },
            # Session resumed, duplicate tool_result appeared
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Continue"
                        },
                        {"type": "tool_result", "tool_use_id": "call_1", "content": "result (dup)"}
                    ]
                }
            }
        ]

        # Detect
        duplicates, detect_metrics = detect_duplicate_tool_results(lines)

        assert duplicates == {"call_1": 1}
        assert detect_metrics.duplicates_detected == 1

        # Deduplicate
        ded_result = deduplicate_tool_results(lines, duplicates)

        assert ded_result.success
        assert ded_result.duplicates_removed == 1

        # Verify structure
        tool_results = []
        for msg in lines:
            if "message" in msg and isinstance(msg["message"], dict):
                content = msg["message"].get("content", [])
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_results.append(block)

        assert len(tool_results) == 1
        assert tool_results[0]["content"] == "result"

    def test_workflow_with_partial_corruption(self):
        """Test workflow handles partial corruption gracefully."""
        lines = [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1"},
                        {"type": "tool_result"},  # Invalid
                        {"type": "tool_result", "tool_use_id": "tool_1", "content": "1dup"},
                    ]
                }
            }
        ]

        # Detect
        duplicates, metrics = detect_duplicate_tool_results(lines)
        assert metrics.blocks_invalid == 1

        # Deduplicate should still work
        result = deduplicate_tool_results(lines, duplicates)
        assert result.success


class TestLogging:
    """Test suite for logging functions."""

    def test_log_detection_summary(self, caplog):
        """Test that detection summary is logged correctly."""
        metrics = DuplicateDetectionMetrics(
            blocks_processed=100,
            blocks_valid=95,
            blocks_invalid=5,
            duplicates_detected=10,
            unique_tool_use_ids=25
        )

        log_detection_summary(metrics)

        log_output = caplog.text
        assert "100" in log_output
        assert "SUMMARY" in log_output

    def test_log_deduplication_summary(self, caplog):
        """Test that deduplication summary is logged correctly."""
        result = DeduplicationResult(
            success=True,
            duplicates_removed=10,
            messages_processed=50
        )

        log_deduplication_summary(result)

        log_output = caplog.text
        assert "True" in log_output or "success" in log_output.lower()
        assert "10" in log_output
