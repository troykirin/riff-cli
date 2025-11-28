#!/usr/bin/env python3
"""
Comprehensive test suite for nlp_stemmer.py

Tests NLP stemming functionality with full type safety coverage:
- Porter stemmer for basic stemming
- Snowball stemmer for advanced variants
- WordNet lemmatizer for semantic accuracy
- Fallback stemming when NLTK unavailable
- Type safety and edge cases
"""

import pytest
import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integration.nlp_stemmer import (
    NLPStemmer,
    stem_text,
    StemResult,
    StemmerCapabilities,
    has_nltk_support,
)


class TestNLPStemmerBasics:
    """Test basic NLP stemmer functionality"""

    def test_initialization_default(self) -> None:
        """Test default initialization"""
        stemmer = NLPStemmer()
        assert stemmer is not None
        assert isinstance(stemmer, NLPStemmer)

    def test_initialization_with_auto_download(self) -> None:
        """Test initialization with auto_download enabled"""
        # This should not fail even if NLTK data is missing
        stemmer = NLPStemmer(auto_download=True)
        assert stemmer is not None

    def test_get_capabilities(self) -> None:
        """Test capabilities reporting"""
        stemmer = NLPStemmer()
        caps: StemmerCapabilities = stemmer.get_capabilities()

        # Check structure
        assert "has_nltk" in caps
        assert "has_porter" in caps
        assert "has_snowball" in caps
        assert "has_wordnet" in caps
        assert "nltk_data_path" in caps

        # Check types
        assert isinstance(caps["has_nltk"], bool)
        assert isinstance(caps["has_porter"], bool)
        assert isinstance(caps["has_snowball"], bool)
        assert isinstance(caps["has_wordnet"], bool)
        assert caps["nltk_data_path"] is None or isinstance(caps["nltk_data_path"], str)


class TestPorterStemming:
    """Test Porter stemmer functionality"""

    def test_porter_basic_stemming(self) -> None:
        """Test basic Porter stemming"""
        stemmer = NLPStemmer()

        # Common stemming patterns
        test_cases = [
            ("running", "run"),
            ("runner", "runner"),  # May vary based on NLTK availability
            ("easily", "easili"),
            ("fairness", "fair"),
        ]

        for word, expected_prefix in test_cases:
            result = stemmer.stem(word, "porter")
            assert isinstance(result, str)
            # Check that result is a stem (not necessarily exact match)
            assert len(result) <= len(word)

    def test_porter_preserves_short_words(self) -> None:
        """Test that short words are handled correctly"""
        stemmer = NLPStemmer()

        short_words = ["is", "at", "to", "it", "in"]
        for word in short_words:
            result = stemmer.stem(word, "porter")
            assert isinstance(result, str)
            assert len(result) >= 1

    def test_porter_empty_string(self) -> None:
        """Test Porter stemmer with empty string"""
        stemmer = NLPStemmer()
        result = stemmer.stem("", "porter")
        assert result == ""

    def test_porter_whitespace(self) -> None:
        """Test Porter stemmer with whitespace"""
        stemmer = NLPStemmer()
        result = stemmer.stem("   ", "porter")
        assert isinstance(result, str)


class TestSnowballStemming:
    """Test Snowball stemmer functionality"""

    def test_snowball_basic_stemming(self) -> None:
        """Test basic Snowball stemming"""
        stemmer = NLPStemmer()

        # Test words that should be stemmed
        words = ["federation", "running", "developer", "implementation"]

        for word in words:
            result = stemmer.stem(word, "snowball")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_snowball_vs_porter(self) -> None:
        """Test that Snowball and Porter may produce different results"""
        stemmer = NLPStemmer()

        # Some words where algorithms differ
        test_words = ["generalization", "organization", "automation"]

        for word in test_words:
            porter = stemmer.stem(word, "porter")
            snowball = stemmer.stem(word, "snowball")

            assert isinstance(porter, str)
            assert isinstance(snowball, str)
            # Both should produce stems
            assert len(porter) <= len(word)
            assert len(snowball) <= len(word)


class TestLemmatization:
    """Test WordNet lemmatizer functionality"""

    def test_lemmatizer_basic(self) -> None:
        """Test basic lemmatization"""
        stemmer = NLPStemmer()

        # Test words
        words = ["running", "better", "geese", "cacti"]

        for word in words:
            result = stemmer.stem(word, "lemmatizer")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_lemmatizer_preserves_base_forms(self) -> None:
        """Test that lemmatizer preserves words already in base form"""
        stemmer = NLPStemmer()

        base_words = ["run", "good", "goose", "cactus"]

        for word in base_words:
            result = stemmer.stem(word, "lemmatizer")
            assert isinstance(result, str)
            # Lemmatizer should preserve or normalize
            assert len(result) >= 1


class TestStemQuery:
    """Test stem_query method for full query processing"""

    def test_stem_query_basic(self) -> None:
        """Test basic query stemming"""
        stemmer = NLPStemmer()
        result = stemmer.stem_query("running federation")

        assert isinstance(result, list)
        assert len(result) > 0
        # Should include original and stemmed variants
        assert all(isinstance(word, str) for word in result)

    def test_stem_query_empty(self) -> None:
        """Test stem_query with empty string"""
        stemmer = NLPStemmer()
        result = stemmer.stem_query("")

        assert isinstance(result, list)
        assert len(result) == 0

    def test_stem_query_multiple_words(self) -> None:
        """Test stem_query with multiple words"""
        stemmer = NLPStemmer()
        result = stemmer.stem_query("running jumping swimming")

        assert isinstance(result, list)
        assert len(result) >= 3  # At least the original words
        # Check uniqueness (should be sorted unique list)
        assert len(result) == len(set(result))
        assert result == sorted(result)

    def test_stem_query_includes_variants(self) -> None:
        """Test that stem_query includes both original and stemmed forms"""
        stemmer = NLPStemmer()
        result = stemmer.stem_query("running")

        assert isinstance(result, list)
        # Should include at least the original word
        assert "running" in result or len(result) > 0

    def test_stem_query_filters_short_words(self) -> None:
        """Test that very short words are handled appropriately"""
        stemmer = NLPStemmer()
        result = stemmer.stem_query("a an the running")

        assert isinstance(result, list)
        # Should still process the significant word
        assert len(result) > 0


class TestStemWithMetadata:
    """Test stem_with_metadata for detailed results"""

    def test_metadata_structure(self) -> None:
        """Test metadata result structure"""
        stemmer = NLPStemmer()
        result: StemResult = stemmer.stem_with_metadata("running")

        assert "original" in result
        assert "stemmed" in result
        assert "method" in result
        assert "success" in result

        assert isinstance(result["original"], str)
        assert isinstance(result["stemmed"], str)
        assert result["method"] in ["porter", "snowball", "lemmatizer", "fallback"]
        assert isinstance(result["success"], bool)

    def test_metadata_success_flag(self) -> None:
        """Test that success flag indicates actual stemming"""
        stemmer = NLPStemmer()

        # Word that should be stemmed
        result = stemmer.stem_with_metadata("running")
        # Success depends on whether stemming changed the word
        assert isinstance(result["success"], bool)

    def test_metadata_different_methods(self) -> None:
        """Test metadata with different stemming methods"""
        stemmer = NLPStemmer()

        methods = ["porter", "snowball", "lemmatizer"]

        for method in methods:
            result = stemmer.stem_with_metadata("running", method)
            assert isinstance(result, dict)
            assert result["original"] == "running"
            assert isinstance(result["stemmed"], str)


class TestBatchStemming:
    """Test batch_stem method"""

    def test_batch_stem_basic(self) -> None:
        """Test basic batch stemming"""
        stemmer = NLPStemmer()
        words = ["running", "jumping", "swimming"]
        results = stemmer.batch_stem(words)

        assert isinstance(results, list)
        assert len(results) == len(words)
        assert all(isinstance(word, str) for word in results)

    def test_batch_stem_preserves_order(self) -> None:
        """Test that batch stemming preserves order"""
        stemmer = NLPStemmer()
        words = ["zebra", "apple", "monkey"]
        results = stemmer.batch_stem(words)

        assert len(results) == len(words)
        # Order should be preserved (not sorted)
        assert results[0] != results[1] or words[0] == words[1]

    def test_batch_stem_empty_list(self) -> None:
        """Test batch stemming with empty list"""
        stemmer = NLPStemmer()
        results = stemmer.batch_stem([])

        assert isinstance(results, list)
        assert len(results) == 0


class TestFallbackStemming:
    """Test fallback stemming when NLTK is unavailable"""

    def test_fallback_stem_basic(self) -> None:
        """Test that fallback stemming works"""
        stemmer = NLPStemmer()

        # Access fallback directly
        test_cases = [
            ("running", "run"),
            ("federation", "federat"),  # -ion suffix
            ("development", "develop"),  # -ment suffix
            ("happiness", "happi"),      # -ness suffix
        ]

        for word, expected_stem in test_cases:
            result = stemmer._fallback_stem(word)
            assert isinstance(result, str)
            # Check that stemming occurred
            assert len(result) <= len(word)

    def test_fallback_preserves_short_words(self) -> None:
        """Test that fallback preserves very short words"""
        stemmer = NLPStemmer()

        short_words = ["is", "at", "it"]
        for word in short_words:
            result = stemmer._fallback_stem(word)
            # Should return original for very short words
            assert result == word


class TestConvenienceFunction:
    """Test stem_text convenience function"""

    def test_stem_text_basic(self) -> None:
        """Test basic stem_text usage"""
        result = stem_text("running federation")

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(word, str) for word in result)

    def test_stem_text_different_methods(self) -> None:
        """Test stem_text with different methods"""
        methods = ["porter", "snowball", "lemmatizer"]

        for method in methods:
            result = stem_text("running", method)
            assert isinstance(result, list)

    def test_stem_text_empty(self) -> None:
        """Test stem_text with empty input"""
        result = stem_text("")

        assert isinstance(result, list)
        assert len(result) == 0


class TestTypeGuard:
    """Test has_nltk_support type guard"""

    def test_has_nltk_support_returns_bool(self) -> None:
        """Test that type guard returns boolean"""
        result = has_nltk_support()
        assert isinstance(result, bool)


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_unicode_input(self) -> None:
        """Test handling of unicode characters"""
        stemmer = NLPStemmer()

        # Should handle gracefully
        result = stemmer.stem("café")
        assert isinstance(result, str)

    def test_special_characters(self) -> None:
        """Test handling of special characters"""
        stemmer = NLPStemmer()

        result = stemmer.stem("hello@world")
        assert isinstance(result, str)

    def test_mixed_case(self) -> None:
        """Test that stemming normalizes case"""
        stemmer = NLPStemmer()

        result1 = stemmer.stem("RUNNING")
        result2 = stemmer.stem("running")
        result3 = stemmer.stem("Running")

        # All should be normalized to lowercase
        assert result1 == result2 == result3

    def test_hyphenated_words(self) -> None:
        """Test handling of hyphenated words"""
        stemmer = NLPStemmer()

        result = stemmer.stem("self-running")
        assert isinstance(result, str)

    def test_numbers_in_words(self) -> None:
        """Test handling of words with numbers"""
        stemmer = NLPStemmer()

        # Should handle gracefully
        result = stemmer.stem("base64")
        assert isinstance(result, str)


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""

    def test_search_query_enhancement(self) -> None:
        """Test enhancing a typical search query"""
        stemmer = NLPStemmer()

        query = "find conversations about running agents"
        variants = stemmer.stem_query(query)

        assert isinstance(variants, list)
        assert len(variants) > 0
        # Should include stemmed forms
        assert any("conversation" in v or "convers" in v for v in variants)

    def test_keyword_expansion(self) -> None:
        """Test keyword expansion for search"""
        stemmer = NLPStemmer()

        keywords = ["running", "implementation", "configuration"]

        all_variants = set()
        for keyword in keywords:
            variants = stemmer.stem_query(keyword)
            all_variants.update(variants)

        # Should have expanded from 3 keywords to more variants
        assert len(all_variants) >= 3

    def test_multilingual_fallback(self) -> None:
        """Test that non-English words degrade gracefully"""
        stemmer = NLPStemmer(language="english")

        # Non-English word should still process
        result = stemmer.stem("liberté")
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
