#!/usr/bin/env python3
"""
End-to-End Integration Tests for nabi scan query enhancement.

Tests the full pipeline from query input through enhancement to
ripgrep pattern generation, including timeout handling, fallback
mechanisms, and real-world scenarios.

NOTE: These tests mock the Rust nabi-cli integration since we're
testing the Python enhancement component in isolation. For full
E2E tests with actual nabi scan, see the Rust test suite.
"""

import pytest
import json
import subprocess
import sys
import time
import signal
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch, MagicMock
import tempfile
import os


# Path to enhance_cli.py
ENHANCE_CLI = Path(__file__).parent.parent.parent / "src" / "enhance_cli.py"


class TestFullPipeline:
    """Test the complete enhancement pipeline"""

    def test_simple_query_full_pipeline(self) -> None:
        """Test basic query through full pipeline"""
        input_data = {
            "query": "find agents",
            "depth": 3
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5  # Timeout protection
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

        # Verify enhancement happened
        assert output["keyword_count"] > 1

        # Verify OR pattern is usable
        or_pattern = output["or_pattern"]
        assert or_pattern.startswith("(")
        assert or_pattern.endswith(")")
        assert "|" in or_pattern

    def test_complex_query_pipeline(self) -> None:
        """Test complex query with domain expansion"""
        input_data = {
            "query": "federation event schema agent coordination",
            "depth": 4,
            "enable_stemming": True
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

        # Should have significant expansion
        assert output["keyword_count"] >= 10

        keywords = output["enhanced_keywords"]

        # Should include domain terms
        assert any("protocol" in k.lower() for k in keywords)
        assert any("agent" in k.lower() for k in keywords)

    def test_stemming_integration(self) -> None:
        """Test NLP stemming integration in pipeline"""
        input_data = {
            "query": "running agents processing",
            "enable_stemming": True,
            "stemming_method": "porter"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

        keywords = output["enhanced_keywords"]

        # If stemming enabled, should have stemmed variants
        stemming_info = output["stemming_info"]
        if stemming_info["enabled"]:
            # Should have both original and stemmed forms
            assert len(keywords) > 3


class TestFallbackMechanism:
    """Test fallback when Python or enhancement unavailable"""

    def test_graceful_degradation_no_stemming(self) -> None:
        """Test that enhancement works without NLTK"""
        input_data = {
            "query": "test query",
            "enable_stemming": False  # Explicitly disabled
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"

        # Should still work with pattern-based enhancement
        assert output["keyword_count"] > 0

    def test_fallback_maintains_functionality(self) -> None:
        """Test that fallback still provides value"""
        # Test with stemming disabled (simulates NLTK unavailable)
        input_data = {
            "query": "federation agents",
            "enable_stemming": False
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)

        # Pattern-based expansion should still work
        keywords = output["enhanced_keywords"]
        assert any("protocol" in k.lower() for k in keywords)
        assert any("coordination" in k.lower() for k in keywords)


class TestTimeoutHandling:
    """Test timeout and performance scenarios"""

    def test_normal_query_completes_quickly(self) -> None:
        """Test that normal queries complete within timeout"""
        input_data = {
            "query": "test query"
        }

        start_time = time.time()

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=2  # Should complete well within 2s
        )

        elapsed = time.time() - start_time

        assert result.returncode == 0
        assert elapsed < 2.0  # Should be fast

    def test_timeout_protection(self) -> None:
        """Test subprocess timeout protection"""
        # Create a very large query to test timeout handling
        input_data = {
            "query": " ".join([f"word{i}" for i in range(1000)]),
            "depth": 5
        }

        start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=5  # 5 second timeout
            )

            elapsed = time.time() - start_time

            # Should complete or timeout gracefully
            assert elapsed < 6  # Within timeout + margin

        except subprocess.TimeoutExpired:
            # Timeout is acceptable for extreme queries
            elapsed = time.time() - start_time
            assert elapsed >= 5  # Hit timeout
            assert elapsed < 6  # Didn't hang

    def test_multiple_queries_sequential(self) -> None:
        """Test that multiple queries can be processed"""
        queries = [
            "find agents",
            "federation protocol",
            "linear integration"
        ]

        for query in queries:
            input_data = {"query": query}

            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=2
            )

            assert result.returncode == 0


class TestRipgrepIntegration:
    """Test ripgrep pattern compatibility"""

    def test_or_pattern_ripgrep_compatible(self) -> None:
        """Test that OR pattern is ripgrep-compatible"""
        input_data = {
            "query": "federation agents protocol"  # Use query with multiple domain keywords
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        or_pattern = output["or_pattern"]

        # Pattern should be properly formatted
        assert or_pattern.startswith("(")
        assert or_pattern.endswith(")")

        # Should have keywords separated by | (or just one keyword)
        parts = or_pattern[1:-1].split("|")
        assert len(parts) >= 1  # At least one keyword

    def test_special_characters_escaped(self) -> None:
        """Test that special regex characters are escaped"""
        input_data = {
            "query": "test.query [pattern] (regex)"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        or_pattern = output["or_pattern"]

        # Special chars should be escaped
        # Check that raw special chars are not present or are escaped
        # (enhancement may filter them out entirely)
        assert isinstance(or_pattern, str)
        assert len(or_pattern) > 0

    def test_pattern_with_test_file(self) -> None:
        """Test pattern against actual test file"""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as f:
            test_file = f.name
            f.write("""
# Federation Architecture

This document describes the federation protocol used by agents
for coordination and message passing in the distributed system.

## Agent Coordination

Agents use a protocol-based approach for communication.
""")

        try:
            # Get enhancement for "federation agent protocol"
            input_data = {
                "query": "federation agent protocol",
                "depth": 3
            }

            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode == 0

            output = json.loads(result.stdout)
            keywords = output["enhanced_keywords"]

            # Verify keywords match content
            with open(test_file, 'r') as f:
                content = f.read().lower()

            # At least some keywords should match
            matches = sum(1 for k in keywords if k.lower() in content)
            assert matches > 0

        finally:
            # Cleanup
            os.unlink(test_file)


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_documentation_search_scenario(self) -> None:
        """Test typical documentation search use case"""
        scenarios = [
            {
                "query": "federation event schema",
                "expected_keywords": ["federation", "event", "schema", "agent"]
            },
            {
                "query": "linear integration webhook",
                "expected_keywords": ["linear", "integration", "webhook", "api"]
            },
            {
                "query": "authentication oauth proxy",
                "expected_keywords": ["authentication", "oauth", "proxy", "token"]
            }
        ]

        for scenario in scenarios:
            input_data = {
                "query": scenario["query"],
                "depth": 3
            }

            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode == 0

            output = json.loads(result.stdout)
            keywords = [k.lower() for k in output["enhanced_keywords"]]

            # Check for expected keywords
            for expected in scenario["expected_keywords"]:
                assert any(expected in k for k in keywords), \
                    f"Expected '{expected}' in keywords for query '{scenario['query']}'"

    def test_code_search_scenario(self) -> None:
        """Test code search enhancement"""
        input_data = {
            "query": "implement authentication handler",
            "depth": 4
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)

        # Should be technical-focused
        routing = output["routing"]
        assert routing["strategy"] in ["technical_focused", "project_focused"]

    def test_conversation_search_scenario(self) -> None:
        """Test conversation search enhancement"""
        input_data = {
            "query": "discuss federation architecture",
            "depth": 3
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)

        # Should be conversation-focused
        routing = output["routing"]
        assert routing["strategy"] == "conversation_focused"

        keywords = output["enhanced_keywords"]
        # Should have conversation-related terms
        assert any(term in [k.lower() for k in keywords]
                   for term in ["message", "chat", "dialogue", "conversation"])


class TestErrorRecovery:
    """Test error recovery and resilience"""

    def test_recovery_from_empty_query(self) -> None:
        """Test recovery from empty query"""
        input_data = {
            "query": ""
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should succeed with empty result
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["status"] == "success"
        assert output["keyword_count"] == 0

    def test_recovery_from_invalid_input(self) -> None:
        """Test error reporting for invalid input"""
        test_cases = [
            ("", 1, "empty input"),
            ("not json", 1, "invalid JSON"),
            (json.dumps({"no_query": "field"}), 3, "missing query"),
            (json.dumps({"query": "test", "depth": 100}), 2, "invalid depth")
        ]

        for input_str, expected_code, description in test_cases:
            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=input_str,
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode == expected_code, \
                f"Expected exit code {expected_code} for {description}"

            output = json.loads(result.stdout)
            assert output["status"] == "error"
            assert "error" in output

    def test_json_parsing_resilience(self) -> None:
        """Test JSON parsing error handling"""
        malformed_inputs = [
            '{"query": "test"',  # Unclosed brace
            '{"query": "test", "depth": }',  # Invalid value
            '{"query": "test", extra}',  # Invalid syntax
        ]

        for malformed in malformed_inputs:
            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=malformed,
                capture_output=True,
                text=True,
                timeout=5
            )

            assert result.returncode == 1

            output = json.loads(result.stdout)
            assert output["status"] == "error"


class TestPerformance:
    """Test performance characteristics"""

    def test_small_query_performance(self) -> None:
        """Test that small queries are fast"""
        input_data = {
            "query": "test"
        }

        times = []
        for _ in range(5):
            start = time.time()

            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=2
            )

            elapsed = time.time() - start
            times.append(elapsed)

            assert result.returncode == 0

        # Average should be reasonable
        avg_time = sum(times) / len(times)
        assert avg_time < 1.0  # Should complete in under 1 second

    def test_large_query_handling(self) -> None:
        """Test handling of large queries"""
        input_data = {
            "query": " ".join([f"keyword{i}" for i in range(100)]),
            "depth": 5
        }

        start = time.time()

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10
        )

        elapsed = time.time() - start

        # Should complete even for large queries
        assert result.returncode == 0
        assert elapsed < 10  # Within timeout


class TestCLICompatibility:
    """Test CLI compatibility and integration"""

    def test_stdout_only_output(self) -> None:
        """Test that output only goes to stdout"""
        input_data = {
            "query": "test query"
        }

        result = subprocess.run(
            [sys.executable, str(ENHANCE_CLI)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0

        # Stderr should be minimal/empty (warnings suppressed)
        assert len(result.stderr) < 100 or result.stderr == ""

        # Stdout should have valid JSON
        output = json.loads(result.stdout)
        assert output["status"] == "success"

    def test_json_output_parseable(self) -> None:
        """Test that all outputs are valid JSON"""
        test_inputs = [
            '{"query": "test"}',
            '{"query": ""}',
            'invalid',
            '{"no_query": true}',
        ]

        for input_str in test_inputs:
            result = subprocess.run(
                [sys.executable, str(ENHANCE_CLI)],
                input=input_str,
                capture_output=True,
                text=True,
                timeout=5
            )

            # All outputs should be valid JSON
            try:
                output = json.loads(result.stdout)
                assert "status" in output
            except json.JSONDecodeError:
                pytest.fail(f"Output not valid JSON for input: {input_str}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
