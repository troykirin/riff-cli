#!/usr/bin/env python3
"""
Test suite for intent_enhancer_simple.py
Tests pattern-based keyword expansion and search routing
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from intent_enhancer_simple import (
    enhance_search_intent,
    extract_pattern_keywords,
    generate_domain_keywords,
    generate_semantic_variations,
    route_search_intent
)


class TestIntentEnhancement:
    """Test intent enhancement functionality"""

    def test_basic_enhancement(self):
        """Test basic keyword enhancement"""
        result = enhance_search_intent("nabia", depth=3)

        # Should include original and domain expansions
        assert "nabia" in result
        assert "federation" in result
        assert "memchain" in result
        assert "orchestration" in result

    def test_depth_parameter(self):
        """Test that depth affects expansion count"""
        shallow = enhance_search_intent("find project", depth=1)
        deep = enhance_search_intent("find project", depth=5)

        # Deeper searches should produce more keywords
        assert len(deep) >= len(shallow)

    def test_quoted_phrase_extraction(self):
        """Test extraction of quoted phrases"""
        keywords = extract_pattern_keywords('"exact phrase" search')
        assert "exact phrase" in keywords

    def test_technical_term_extraction(self):
        """Test extraction of technical terms"""
        # CamelCase
        keywords = extract_pattern_keywords("LinearIntegration")
        assert any("LinearIntegration" in k for k in keywords)

        # kebab-case
        keywords = extract_pattern_keywords("riff-cli tool")
        assert any("riff-cli" in k for k in keywords)

        # Abbreviations
        keywords = extract_pattern_keywords("API MCP OAuth")
        assert "API" in keywords
        assert "MCP" in keywords

    def test_domain_specific_expansions(self):
        """Test domain-specific keyword expansions"""
        # Claude domain
        keywords = extract_pattern_keywords("claude assistant")
        assert any(k in keywords for k in ["conversation", "chat", "ai", "llm"])

        # Linear domain
        keywords = extract_pattern_keywords("linear project")
        assert any(k in keywords for k in ["issue", "task", "ticket", "workflow"])

        # Federation domain
        keywords = extract_pattern_keywords("federation protocol")
        assert any(k in keywords for k in ["agent", "coordination", "handoff"])

    def test_action_based_expansions(self):
        """Test action-based keyword generation"""
        keywords = generate_domain_keywords("find conversations", depth=3)
        assert any(k in keywords for k in ["search", "locate", "discover"])

        keywords = generate_domain_keywords("debug error", depth=3)
        assert any(k in keywords for k in ["troubleshoot", "diagnose", "fix"])

    def test_semantic_variations(self):
        """Test semantic variation generation"""
        keywords = generate_semantic_variations("agent system")
        assert any(k in keywords for k in ["bot", "assistant", "worker"])
        assert any(k in keywords for k in ["platform", "framework", "infrastructure"])

    def test_search_routing(self):
        """Test search intent routing"""
        # Conversation-focused
        routing = route_search_intent("find chat discussions")
        assert routing["strategy"] == "conversation_focused"
        assert routing["primary_source"] == "conversations"

        # Project-focused
        routing = route_search_intent("project documentation")
        assert routing["strategy"] == "project_focused"
        assert routing["primary_source"] == "projects"

        # Technical-focused
        routing = route_search_intent("code implementation api")
        assert routing["strategy"] == "technical_focused"
        assert routing["primary_source"] == "both"

        # User-focused
        routing = route_search_intent("find user creator")
        assert routing["strategy"] == "user_focused"
        assert routing["primary_source"] == "users"

        # Balanced (default)
        routing = route_search_intent("general search")
        assert routing["strategy"] == "balanced"
        assert routing["primary_source"] == "all"

    def test_comprehensive_enhancement(self):
        """Test comprehensive enhancement with complex input"""
        intent = 'find "nabia federation" discussions about linear integration'
        keywords = enhance_search_intent(intent, depth=4)

        # Should include quoted phrase
        assert "nabia federation" in keywords

        # Should include domain expansions
        assert any(k in keywords for k in ["orchestration", "memchain"])
        assert any(k in keywords for k in ["issue", "ticket", "workflow"])

        # Should include action expansions
        assert any(k in keywords for k in ["search", "locate", "discover"])

        # Should include conversation terms
        assert any(k in keywords for k in ["chat", "dialogue", "conversation"])

    def test_no_duplicates(self):
        """Test that enhancement removes duplicates"""
        keywords = enhance_search_intent("agent agent agent", depth=3)

        # Count occurrences of "agent"
        agent_count = keywords.count("agent")
        assert agent_count == 1, "Duplicates should be removed"

    def test_empty_input(self):
        """Test handling of empty input"""
        keywords = enhance_search_intent("", depth=3)
        assert "" in keywords  # Should at least contain the empty string

    def test_case_insensitivity(self):
        """Test case-insensitive pattern matching"""
        keywords1 = extract_pattern_keywords("NABIA FEDERATION")
        keywords2 = extract_pattern_keywords("nabia federation")

        # Both should produce similar domain expansions
        assert "orchestration" in keywords1
        assert "orchestration" in keywords2


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_special_characters(self):
        """Test handling of special characters"""
        keywords = enhance_search_intent("test@example.com #hashtag", depth=2)
        assert isinstance(keywords, list)

    def test_very_long_input(self):
        """Test handling of very long input"""
        long_input = " ".join(["word"] * 100)
        keywords = enhance_search_intent(long_input, depth=2)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_unicode_input(self):
        """Test handling of unicode characters"""
        keywords = enhance_search_intent("测试 テスト test", depth=2)
        assert isinstance(keywords, list)
        assert "test" in keywords or "测试" in keywords or "テスト" in keywords


if __name__ == "__main__":
    pytest.main([__file__, "-v"])