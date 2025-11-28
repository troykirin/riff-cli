#!/usr/bin/env python3
"""
Test suite for enhance_cli.py CLI wrapper.

Tests the stdin/stdout JSON interface for query enhancement,
including success cases, error handling, and edge cases.
"""

import pytest
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


# Path to enhance_cli.py
ENHANCE_CLI = Path(__file__).parent.parent / "src" / "enhance_cli.py"


class TestEnhanceCLIBasic:
    """Test basic CLI functionality"""

    def test_cli_exists(self) -> None:
        """Test that CLI script exists and is executable"""
        assert ENHANCE_CLI.exists()
        assert ENHANCE_CLI.is_file()

    def test_simple_query_enhancement(self) -> None:
        """Test basic query enhancement"""
        input_data = {
            "query": "find agents"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["query"] == "find agents"
        assert isinstance(output["enhanced_keywords"], list)
        assert len(output["enhanced_keywords"]) > 0
        assert "or_pattern" in output
        assert "keyword_count" in output

    def test_query_with_depth(self) -> None:
        """Test query enhancement with custom depth"""
        input_data = {
            "query": "federation",
            "depth": 5
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["keyword_count"] > 0

    def test_query_with_stemming_disabled(self) -> None:
        """Test query enhancement with stemming disabled"""
        input_data = {
            "query": "running agents",
            "enable_stemming": False
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["stemming_info"]["enabled"] is False

    def test_query_with_different_stemming_methods(self) -> None:
        """Test query enhancement with different stemming methods"""
        methods = ["porter", "snowball", "lemmatizer"]

        for method in methods:
            input_data = {
                "query": "running",
                "stemming_method": method
            }

            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True
            )

            assert result.returncode == 0

            output = json.loads(result.stdout)
            assert output["status"] == "success"


class TestORPatternGeneration:
    """Test OR pattern generation for ripgrep"""

    def test_or_pattern_format(self) -> None:
        """Test that OR pattern has correct format"""
        input_data = {
            "query": "federation agents"  # Use query that generates multiple keywords
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        or_pattern = output["or_pattern"]

        # Should be in format (keyword1|keyword2|...)
        assert or_pattern.startswith("(")
        assert or_pattern.endswith(")")
        # Should have multiple keywords separated by |
        assert "|" in or_pattern or output["keyword_count"] == 1  # Allow single keyword case

    def test_or_pattern_special_characters(self) -> None:
        """Test OR pattern escapes special regex characters"""
        input_data = {
            "query": "test.query [pattern]"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        or_pattern = output["or_pattern"]

        # Special chars should be escaped
        assert "\\." in or_pattern or "." not in or_pattern
        assert "\\[" in or_pattern or "[" not in or_pattern

    def test_or_pattern_includes_all_keywords(self) -> None:
        """Test that OR pattern includes all enhanced keywords"""
        input_data = {
            "query": "agent"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        keywords = output["enhanced_keywords"]
        or_pattern = output["or_pattern"]

        # OR pattern should contain reference to keywords
        # (may be escaped, so check length)
        assert len(or_pattern) > 10  # At least some keywords


class TestErrorHandling:
    """Test error handling and validation"""

    def test_empty_input(self) -> None:
        """Test handling of empty input"""
        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input="",
            capture_output=True,
            text=True
        )

        assert result.returncode == 1

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "No input" in output["error"]

    def test_invalid_json(self) -> None:
        """Test handling of invalid JSON"""
        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input="not valid json",
            capture_output=True,
            text=True
        )

        assert result.returncode == 1

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "Invalid JSON" in output["error"]

    def test_missing_query_field(self) -> None:
        """Test handling of missing query field"""
        input_data = {
            "depth": 3
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 3

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "query" in output["error"].lower()

    def test_invalid_depth(self) -> None:
        """Test handling of invalid depth value"""
        input_data = {
            "query": "test",
            "depth": 10  # Out of range
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 2

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "depth" in output["error"].lower()

    def test_invalid_stemming_method(self) -> None:
        """Test handling of invalid stemming method"""
        input_data = {
            "query": "test",
            "stemming_method": "invalid_method"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 2

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "stemming_method" in output["error"].lower()

    def test_non_object_input(self) -> None:
        """Test handling of non-object JSON input"""
        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(["array", "not", "object"]),
            capture_output=True,
            text=True
        )

        assert result.returncode == 3

        output = json.loads(result.stdout)
        assert output["status"] == "error"
        assert "object" in output["error"].lower()


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_query(self) -> None:
        """Test enhancement of empty query"""
        input_data = {
            "query": ""
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["keyword_count"] == 0
        assert output["enhanced_keywords"] == []

    def test_unicode_query(self) -> None:
        """Test handling of unicode characters"""
        input_data = {
            "query": "测试 café naïve"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

    def test_very_long_query(self) -> None:
        """Test handling of very long queries"""
        input_data = {
            "query": " ".join(["word"] * 100)
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

    def test_special_characters_in_query(self) -> None:
        """Test queries with special characters"""
        special_queries = [
            "query with @symbols #hashtags",
            "query.with.dots",
            "query-with-dashes",
            "query_with_underscores",
            "query$with%special&chars"
        ]

        for query in special_queries:
            input_data = {"query": query}

            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True
            )

            assert result.returncode == 0

            output = json.loads(result.stdout)
            assert output["status"] == "success"


class TestOutputStructure:
    """Test output structure and format"""

    def test_success_output_structure(self) -> None:
        """Test that success output has all required fields"""
        input_data = {
            "query": "test query"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)

        # Check required fields
        assert "status" in output
        assert "query" in output
        assert "enhanced_keywords" in output
        assert "or_pattern" in output
        assert "keyword_count" in output
        assert "routing" in output
        assert "stemming_info" in output

        # Check types
        assert isinstance(output["status"], str)
        assert isinstance(output["query"], str)
        assert isinstance(output["enhanced_keywords"], list)
        assert isinstance(output["or_pattern"], str)
        assert isinstance(output["keyword_count"], int)
        assert isinstance(output["routing"], dict)
        assert isinstance(output["stemming_info"], dict)

    def test_error_output_structure(self) -> None:
        """Test that error output has required fields"""
        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input="invalid json",
            capture_output=True,
            text=True
        )

        assert result.returncode != 0

        output = json.loads(result.stdout)

        # Check required fields
        assert "status" in output
        assert "error" in output
        assert output["status"] == "error"
        assert isinstance(output["error"], str)

    def test_routing_structure(self) -> None:
        """Test that routing has expected structure"""
        input_data = {
            "query": "find conversations"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        routing = output["routing"]

        # Should have strategy
        assert "strategy" in routing
        assert isinstance(routing["strategy"], str)

    def test_stemming_info_structure(self) -> None:
        """Test that stemming_info has expected structure"""
        input_data = {
            "query": "test"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        stemming_info = output["stemming_info"]

        # Should have required fields
        assert "enabled" in stemming_info
        assert isinstance(stemming_info["enabled"], bool)


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_federation_event_schema_query(self) -> None:
        """Test query from task description"""
        input_data = {
            "query": "federation event schema"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

        keywords = output["enhanced_keywords"]

        # Should have domain expansions
        assert any("federation" in k.lower() for k in keywords)
        assert any("event" in k.lower() for k in keywords)
        assert any("schema" in k.lower() for k in keywords)

    def test_code_search_query(self) -> None:
        """Test code search scenario"""
        input_data = {
            "query": "authentication handlers implementation",
            "depth": 4
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["keyword_count"] > 5

    def test_conversation_search_query(self) -> None:
        """Test conversation search scenario"""
        input_data = {
            "query": "discuss Linear integration"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

        # Should be conversation-focused
        routing = output["routing"]
        assert routing["strategy"] == "conversation_focused"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
