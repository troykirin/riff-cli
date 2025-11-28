#!/usr/bin/env python3
"""
Test suite for Intent Enhancer with NLP stemming integration

Tests the integration of NLP stemming into the IntentEnhancer class:
- Stemming integration with existing pattern matching
- Backward compatibility when NLP unavailable
- Type safety across all enhancement methods
- Performance and edge cases
"""

import pytest
import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from integration.intent_enhancer_module import (
    IntentEnhancer,
    enhance_search_intent,
    HAS_NLP_STEMMER,
    has_nltk_support,
)


class TestIntentEnhancerWithStemming:
    """Test IntentEnhancer with NLP stemming enabled"""

    def test_initialization_default(self) -> None:
        """Test default initialization enables stemming if available"""
        enhancer = IntentEnhancer()
        assert enhancer is not None

        info = enhancer.get_stemming_info()
        assert isinstance(info, dict)
        assert "enabled" in info
        assert "method" in info
        assert "has_nltk" in info

    def test_initialization_disable_stemming(self) -> None:
        """Test initialization with stemming explicitly disabled"""
        enhancer = IntentEnhancer(enable_stemming=False)

        info = enhancer.get_stemming_info()
        assert info["enabled"] is False
        assert info["method"] is None

    def test_initialization_different_methods(self) -> None:
        """Test initialization with different stemming methods"""
        methods = ["porter", "snowball", "lemmatizer"]

        for method in methods:
            enhancer = IntentEnhancer(
                enable_stemming=True,
                stemming_method=method
            )
            info = enhancer.get_stemming_info()

            if info["enabled"]:
                assert info["method"] == method

    def test_stem_query_basic(self) -> None:
        """Test stem_query method"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.stem_query("running federation")

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(word, str) for word in result)

    def test_stem_query_disabled(self) -> None:
        """Test stem_query when stemming disabled"""
        enhancer = IntentEnhancer(enable_stemming=False)
        result = enhancer.stem_query("running federation")

        # Should still return tokenized words
        assert isinstance(result, list)

    def test_enhanced_keywords_include_stems(self) -> None:
        """Test that enhanced keywords include stemmed variants"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("running agents", depth=3)

        keywords = result["enhanced_keywords"]
        assert isinstance(keywords, list)
        assert len(keywords) > 0

        # Original intent should be included
        assert "running agents" in keywords

        # If stemming is enabled and working, should have more keywords
        if enhancer.get_stemming_info()["enabled"]:
            # Should have both original and potentially stemmed forms
            assert len(keywords) >= 2

    def test_stemming_enhances_domain_keywords(self) -> None:
        """Test that stemming works with domain keyword expansion"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("federation orchestration", depth=3)

        keywords = result["enhanced_keywords"]

        # Should include domain expansions
        assert any("agent" in k for k in keywords)
        assert any("protocol" in k or "protoc" in k for k in keywords)

        # If stemming enabled, should have stemmed variants too
        if enhancer.get_stemming_info()["enabled"]:
            assert len(keywords) >= 5


class TestBackwardCompatibility:
    """Test backward compatibility with existing API"""

    def test_enhance_without_stemming_params(self) -> None:
        """Test that enhance() works without stemming parameters"""
        enhancer = IntentEnhancer()
        result = enhancer.enhance("test query")

        # Should return same structure as before
        assert "original_intent" in result
        assert "enhanced_keywords" in result
        assert "routing" in result
        assert "keyword_count" in result

    def test_convenience_function_still_works(self) -> None:
        """Test that enhance_search_intent convenience function works"""
        result = enhance_search_intent("test query", depth=3)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(word, str) for word in result)

    def test_existing_pattern_matching_preserved(self) -> None:
        """Test that existing pattern matching still works"""
        enhancer = IntentEnhancer()
        result = enhancer.enhance("nabia linear integration", depth=3)

        keywords = result["enhanced_keywords"]

        # Should still have domain expansions
        assert any("federation" in k for k in keywords)
        assert any("issue" in k or "task" in k for k in keywords)
        assert any("api" in k or "webhook" in k for k in keywords)


class TestStemmingIntegration:
    """Test integration of stemming with pattern matching"""

    def test_stemming_plus_domain_patterns(self) -> None:
        """Test that stemming combines with domain patterns"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("developing federation agents", depth=3)

        keywords = result["enhanced_keywords"]

        # Should have domain keywords
        assert any("protocol" in k for k in keywords)

        # If stemming enabled, should have stemmed forms
        if enhancer.get_stemming_info()["enabled"]:
            # "developing" -> "develop" (or similar)
            assert any("develop" in k for k in keywords)

    def test_stemming_plus_semantic_variations(self) -> None:
        """Test that stemming works with semantic variations"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("agent systems processing", depth=3)

        keywords = result["enhanced_keywords"]

        # Should have semantic variations
        assert any("bot" in k or "assistant" in k for k in keywords)
        assert any("workflow" in k or "pipeline" in k for k in keywords)

    def test_stemming_with_quoted_phrases(self) -> None:
        """Test that quoted phrases are preserved alongside stemming"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance('"exact phrase" running', depth=3)

        keywords = result["enhanced_keywords"]

        # Quoted phrase should be preserved
        assert "exact phrase" in keywords

        # Should still stem other words
        assert len(keywords) >= 2


class TestRoutingWithStemming:
    """Test that routing strategies work with stemming"""

    def test_routing_conversation_focused(self) -> None:
        """Test conversation-focused routing with stemming"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("find chat conversations about running", depth=3)

        # Should detect conversation-focused routing
        routing = result["routing"]
        assert routing["strategy"] == "conversation_focused"
        assert routing["primary_source"] == "conversations"

        # Keywords should include conversation terms
        keywords = result["enhanced_keywords"]
        assert any("message" in k or "chat" in k or "dialogue" in k for k in keywords)

    def test_routing_project_focused(self) -> None:
        """Test project-focused routing with stemming"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("implementing project features", depth=3)

        assert result["routing"]["strategy"] == "project_focused"

        keywords = result["enhanced_keywords"]
        assert any("implementation" in k or "feature" in k for k in keywords)

    def test_routing_technical_focused(self) -> None:
        """Test technical-focused routing with stemming"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("code implementation config", depth=3)

        assert result["routing"]["strategy"] == "technical_focused"

        keywords = result["enhanced_keywords"]
        assert any("code" in k or "technical" in k for k in keywords)


class TestStemmingInfo:
    """Test get_stemming_info method"""

    def test_stemming_info_structure(self) -> None:
        """Test stemming info return structure"""
        enhancer = IntentEnhancer()
        info = enhancer.get_stemming_info()

        assert isinstance(info, dict)
        assert "enabled" in info
        assert "method" in info
        assert "has_nltk" in info
        assert "capabilities" in info

    def test_stemming_info_when_disabled(self) -> None:
        """Test stemming info when explicitly disabled"""
        enhancer = IntentEnhancer(enable_stemming=False)
        info = enhancer.get_stemming_info()

        assert info["enabled"] is False
        assert info["method"] is None
        assert info["capabilities"] == {}

    def test_stemming_info_reflects_availability(self) -> None:
        """Test that stemming info reflects actual availability"""
        enhancer = IntentEnhancer(enable_stemming=True)
        info = enhancer.get_stemming_info()

        # enabled should match HAS_NLP_STEMMER
        if HAS_NLP_STEMMER:
            # May be enabled if NLTK is available
            assert isinstance(info["enabled"], bool)
        else:
            # Should be disabled if no NLP stemmer
            assert info["enabled"] is False


class TestPerformance:
    """Test performance characteristics"""

    def test_large_query_handling(self) -> None:
        """Test handling of large queries"""
        enhancer = IntentEnhancer(enable_stemming=True)

        # Large query with many words
        large_query = " ".join(["word"] * 50)
        result = enhancer.enhance(large_query, depth=3)

        assert isinstance(result, dict)
        assert "enhanced_keywords" in result
        assert len(result["enhanced_keywords"]) > 0

    def test_depth_affects_keyword_count(self) -> None:
        """Test that depth parameter affects keyword count"""
        enhancer = IntentEnhancer(enable_stemming=True)

        shallow = enhancer.enhance("find project", depth=1)
        deep = enhancer.enhance("find project", depth=5)

        # Deeper should generally have more keywords
        assert deep["keyword_count"] >= shallow["keyword_count"]


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_intent(self) -> None:
        """Test handling of empty intent"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("", depth=3)

        assert result["original_intent"] == ""
        assert result["keyword_count"] == 0

    def test_special_characters(self) -> None:
        """Test handling of special characters"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("test@example.com #hashtag", depth=3)

        assert isinstance(result, dict)
        assert "enhanced_keywords" in result

    def test_unicode_characters(self) -> None:
        """Test handling of unicode characters"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("测试 test café", depth=3)

        assert isinstance(result, dict)
        assert "enhanced_keywords" in result
        # Should handle unicode gracefully and extract words
        assert len(result["enhanced_keywords"]) > 0

    def test_very_long_word(self) -> None:
        """Test handling of very long words"""
        enhancer = IntentEnhancer(enable_stemming=True)

        long_word = "a" * 100
        result = enhancer.enhance(long_word, depth=3)

        assert isinstance(result, dict)
        assert "enhanced_keywords" in result


class TestTypeSafety:
    """Test type safety of all methods"""

    def test_enhance_return_type(self) -> None:
        """Test that enhance returns correct typed dict"""
        enhancer = IntentEnhancer()
        result = enhancer.enhance("test", depth=3)

        assert isinstance(result, dict)
        assert isinstance(result["original_intent"], str)
        assert isinstance(result["enhanced_keywords"], list)
        assert isinstance(result["routing"], dict)
        assert isinstance(result["keyword_count"], int)

    def test_stem_query_return_type(self) -> None:
        """Test that stem_query returns list of strings"""
        enhancer = IntentEnhancer()
        result = enhancer.stem_query("test query")

        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_get_stemming_info_return_type(self) -> None:
        """Test that get_stemming_info returns correct structure"""
        enhancer = IntentEnhancer()
        info = enhancer.get_stemming_info()

        assert isinstance(info, dict)
        assert isinstance(info["enabled"], bool)
        assert info["method"] is None or isinstance(info["method"], str)
        assert isinstance(info["has_nltk"], bool)
        assert isinstance(info["capabilities"], dict)


class TestFallbackBehavior:
    """Test fallback behavior when NLTK unavailable"""

    def test_graceful_degradation(self) -> None:
        """Test that system works even without NLTK"""
        # Initialize with stemming but it may fall back
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance("running federation", depth=3)

        # Should still work and return results
        assert isinstance(result, dict)
        assert len(result["enhanced_keywords"]) > 0

    def test_pattern_matching_works_without_nltk(self) -> None:
        """Test that pattern matching still works without NLTK"""
        enhancer = IntentEnhancer(enable_stemming=False)
        result = enhancer.enhance("nabia agent linear", depth=3)

        keywords = result["enhanced_keywords"]

        # Should still have domain expansions
        assert any("federation" in k for k in keywords)
        assert any("issue" in k or "task" in k for k in keywords)


class TestRealWorldScenarios:
    """Test realistic usage scenarios"""

    def test_code_search_query(self) -> None:
        """Test enhancement for code search query"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance(
            "find implementations of authentication handlers",
            depth=4
        )

        keywords = result["enhanced_keywords"]

        # Should include technical terms
        assert any("implement" in k for k in keywords)
        assert any("auth" in k for k in keywords)

    def test_conversation_search_query(self) -> None:
        """Test enhancement for conversation search"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance(
            "chat discussions about Linear integration configuration",
            depth=3
        )

        keywords = result["enhanced_keywords"]
        routing = result["routing"]

        # Should be conversation-focused (uses "chat" trigger word)
        assert routing["strategy"] == "conversation_focused"

        # Should have conversation terms
        assert any("chat" in k or "dialogue" in k or "message" in k for k in keywords)

    def test_project_documentation_search(self) -> None:
        """Test enhancement for project documentation search"""
        enhancer = IntentEnhancer(enable_stemming=True)
        result = enhancer.enhance(
            "project documentation for federation architecture",
            depth=4
        )

        keywords = result["enhanced_keywords"]
        routing = result["routing"]

        # Should be project-focused
        assert routing["strategy"] == "project_focused"

        # Should have architecture terms
        assert any("design" in k or "pattern" in k for k in keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
