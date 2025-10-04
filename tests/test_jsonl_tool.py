#!/usr/bin/env python3
"""
Test suite for jsonl_tool.py
Tests fuzzy search, snippet extraction, and UI components
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from jsonl_tool import (
    find_match_snippet,
    fuzzy_search,
    extract_uuid_from_parsed,
    wrap_text
)


class TestSnippetExtraction:
    """Test snippet extraction functionality"""

    def test_basic_snippet_extraction(self):
        """Test basic snippet extraction around search term"""
        text = "This is a test document with the word SEARCH in the middle of it."
        result = find_match_snippet(text, "search", snippet_length=50)

        assert "SEARCH" in result["snippet"]
        assert result["position"] > 0

    def test_multiline_snippet(self):
        """Test snippet extraction from multiline text"""
        text = """Line one without match
Line two with KEYWORD here
Line three after match
Line four for context"""

        result = find_match_snippet(text, "keyword", snippet_length=100)
        assert "KEYWORD" in result["snippet"]
        # Should include surrounding context
        assert "Line" in result["snippet"]

    def test_json_structure_snippet(self):
        """Test meaningful content extraction from JSON"""
        json_text = json.dumps({
            "id": "123",
            "content": "This is the actual content with IMPORTANT information",
            "metadata": {"author": "test"}
        }, indent=2)

        result = find_match_snippet(json_text, "important", snippet_length=100)
        assert "IMPORTANT" in result["snippet"]
        assert "content" in result["snippet"]

    def test_no_match_fallback(self):
        """Test fallback when no match is found"""
        text = "This text doesn't contain the search term"
        result = find_match_snippet(text, "missing", snippet_length=50)

        # Should return beginning of text
        assert result["position"] == 0
        assert result["snippet"].startswith("This text")

    def test_highlighting(self):
        """Test that matched terms are highlighted"""
        text = "The quick brown fox jumps"
        result = find_match_snippet(text, "quick", snippet_length=50)

        # Should highlight the matched term
        assert "**QUICK**" in result["snippet"] or "quick" in result["snippet"].lower()


class TestFuzzySearch:
    """Test fuzzy search functionality"""

    def test_basic_fuzzy_search(self):
        """Test basic fuzzy search in JSONL file"""
        # Create a temporary JSONL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "text": "Hello world"}\n')
            f.write('{"id": "2", "text": "Fuzzy searching is great"}\n')
            f.write('{"id": "3", "text": "Python testing with pytest"}\n')
            temp_path = f.name

        try:
            matches = fuzzy_search(temp_path, "fuzzy", threshold=70)
            assert len(matches) > 0
            assert matches[0]["score"] >= 70
            assert "fuzzy" in matches[0]["snippet"].lower()
        finally:
            Path(temp_path).unlink()

    def test_threshold_filtering(self):
        """Test that threshold properly filters results"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"text": "exact match"}\n')
            f.write('{"text": "partial mat"}\n')
            f.write('{"text": "completely different"}\n')
            temp_path = f.name

        try:
            # High threshold should be more restrictive
            matches_high = fuzzy_search(temp_path, "exact match", threshold=90)
            matches_low = fuzzy_search(temp_path, "exact match", threshold=50)

            assert len(matches_low) >= len(matches_high)
        finally:
            Path(temp_path).unlink()

    def test_invalid_json_handling(self):
        """Test handling of invalid JSON lines"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"another": "valid"}\n')
            temp_path = f.name

        try:
            # Should skip invalid lines without crashing
            matches = fuzzy_search(temp_path, "valid", threshold=50)
            assert len(matches) == 2  # Only valid JSON lines
        finally:
            Path(temp_path).unlink()

    def test_empty_file(self):
        """Test handling of empty file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_path = f.name  # Empty file

        try:
            matches = fuzzy_search(temp_path, "search", threshold=70)
            assert len(matches) == 0
        finally:
            Path(temp_path).unlink()


class TestTextWrapping:
    """Test text wrapping functionality"""

    def test_basic_wrapping(self):
        """Test basic text wrapping"""
        text = "This is a very long line that needs to be wrapped at a specific width"
        wrapped = wrap_text(text, width=20)

        assert isinstance(wrapped, list)
        for line in wrapped:
            assert len(line) <= 20

    def test_preserve_highlighting(self):
        """Test that highlighting is preserved during wrapping"""
        text = "This has **HIGHLIGHTED** text that should be preserved"
        wrapped = wrap_text(text, width=25)

        # Reconstruct to check highlighting is preserved
        reconstructed = " ".join(wrapped)
        assert "**HIGHLIGHTED**" in reconstructed

    def test_multiline_input(self):
        """Test wrapping of multiline input"""
        text = """First line
Second very long line that needs wrapping
Third line"""

        wrapped = wrap_text(text, width=20)
        assert len(wrapped) > 3  # Should have more lines due to wrapping

    def test_unicode_wrapping(self):
        """Test wrapping with unicode characters"""
        text = "Unicode 文字 test テスト with mixed content"
        wrapped = wrap_text(text, width=20)

        assert isinstance(wrapped, list)
        # Unicode should be preserved
        reconstructed = " ".join(wrapped)
        assert "文字" in reconstructed
        assert "テスト" in reconstructed


class TestUtilityFunctions:
    """Test utility functions"""

    def test_uuid_extraction(self):
        """Test UUID extraction from parsed JSON"""
        # Test with uuid field
        obj1 = {"uuid": "12345678-1234-1234-1234-123456789012"}
        assert extract_uuid_from_parsed(obj1) == "12345678-1234-1234-1234-123456789012"

        # Test with sessionId field
        obj2 = {"sessionId": "87654321-4321-4321-4321-210987654321"}
        assert extract_uuid_from_parsed(obj2) == "87654321-4321-4321-4321-210987654321"

        # Test with id field
        obj3 = {"id": "11111111-2222-3333-4444-555555555555"}
        assert extract_uuid_from_parsed(obj3) == "11111111-2222-3333-4444-555555555555"

        # Test with no UUID field
        obj4 = {"name": "test"}
        assert extract_uuid_from_parsed(obj4) is None

        # Test with invalid UUID format
        obj5 = {"uuid": "not-a-uuid"}
        assert extract_uuid_from_parsed(obj5) is None


class TestIntegration:
    """Integration tests for complete workflow"""

    def test_end_to_end_search(self):
        """Test complete search workflow"""
        # Create test data
        test_data = [
            {"uuid": "12345678-1234-1234-1234-123456789012",
             "content": "Discussion about nabia federation"},
            {"uuid": "87654321-4321-4321-4321-210987654321",
             "content": "Linear integration documentation"},
            {"uuid": "11111111-2222-3333-4444-555555555555",
             "content": "Random unrelated content"}
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for item in test_data:
                f.write(json.dumps(item) + '\n')
            temp_path = f.name

        try:
            # Search for specific content
            matches = fuzzy_search(temp_path, "nabia", threshold=60)
            assert len(matches) >= 1
            assert matches[0]["object"]["uuid"] == "12345678-1234-1234-1234-123456789012"

            # Search for different content
            matches = fuzzy_search(temp_path, "linear", threshold=60)
            assert len(matches) >= 1
            assert "linear" in matches[0]["snippet"].lower()
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])